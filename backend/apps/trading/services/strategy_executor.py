"""
Exécution des stratégies : signaux + placement d'ordres (live) ou simulation.
Réutilisé par l'API manuelle et la commande cron `execute_automated_strategies`.
"""
from __future__ import annotations

import inspect
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, List, Optional, Tuple

from django.db.models import Max
from django.utils import timezone

from apps.trading.models import Order, Position, Strategy, StrategyExecution, Trade
from apps.trading.services.broker_service import BrokerService

logger = logging.getLogger('trading_app.strategy_executor')


class StrategyExecutor:
    """Calcule les signaux et, selon le mode, passe les ordres broker."""

    def build_portfolio_data(self, strategy: Strategy) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        positions = Position.objects.filter(
            all_asset=strategy.all_asset,
            user=strategy.user,
            is_open=True,
        )
        quantity_total = sum(Decimal(str(p.quantity)) for p in positions)

        if strategy.broker_account and strategy.broker_account.balance is not None:
            cash_total = float(strategy.broker_account.balance)
        elif strategy.budget is not None:
            cash_total = float(strategy.budget)
        else:
            cash_total = 10000.0

        portfolio = {
            'cash_total': float(cash_total),
            'quantity_total': float(quantity_total),
            'broker_name': (
                strategy.broker_account.broker.name
                if strategy.broker_account and strategy.broker_account.broker
                else 'Simulation'
            ),
        }

        pending_orders_qs = Order.objects.filter(
            all_asset=strategy.all_asset,
            user=strategy.user,
            status='pending',
        )
        pending_orders = [
            {
                'type': order.order_type.upper(),
                'qty': float(order.quantity),
                'price': float(order.price) if order.price is not None else 0.0,
            }
            for order in pending_orders_qs
        ]
        return portfolio, pending_orders

    def load_price_data(self, strategy: Strategy, limit: int = 100) -> List[Dict[str, Any]]:
        if not strategy.all_asset:
            raise ValueError('Stratégie sans all_asset')

        price_history_json = getattr(strategy.all_asset, 'price_history_json', {}) or {}
        if not price_history_json:
            raise ValueError(
                f'Aucune donnée de prix disponible pour {strategy.all_asset} (JSONB empty)'
            )

        sorted_dates = sorted(price_history_json.keys())[-limit:]
        price_data: List[Dict[str, Any]] = []
        for d in sorted_dates:
            data = price_history_json[d]
            try:
                dt_obj = datetime.strptime(d, '%Y-%m-%d').date()
            except ValueError:
                dt_obj = datetime.fromisoformat(d.replace('Z', '')).date()
            price_data.append({
                'date': dt_obj,
                'open': data.get('open'),
                'high': data.get('high'),
                'low': data.get('low'),
                'close': data.get('close'),
                'volume': data.get('volume'),
            })

        if not price_data:
            raise ValueError(f'Aucune donnée de prix disponible pour {strategy.all_asset}')
        return price_data

    def _calculate_signals(self, algo, price_data, portfolio, pending_orders) -> Dict[str, Any]:
        """Compatible avec les algos (price_data) ou (price_data, portfolio, pending)."""
        try:
            params = list(inspect.signature(algo.calculate_signals).parameters.values())
            # self + args
            n_args = len([p for p in params if p.kind in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )]) - 1
        except (TypeError, ValueError):
            n_args = 3

        if n_args >= 3:
            return algo.calculate_signals(price_data, portfolio, pending_orders)
        return algo.calculate_signals(price_data)

    def should_run_now(self, strategy: Strategy, force: bool = False) -> bool:
        if force:
            return True
        freq = int(strategy.check_frequency or 45)
        last_completed = (
            StrategyExecution.objects.filter(
                strategy=strategy,
                status__in=['completed', 'failed'],
            )
            .aggregate(last=Max('completed_at'))
            .get('last')
        )
        if not last_completed:
            return True
        return timezone.now() - last_completed >= timedelta(minutes=freq)

    def execute_strategy(
        self,
        strategy: Strategy,
        *,
        place_orders: Optional[bool] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Exécute une stratégie.

        place_orders:
          - None → dérivé de execution_mode + is_automated
            (live_trading + is_automated → True, sinon False)
          - True/False → forcé (ex. dry-run cron)
        """
        if place_orders is None:
            place_orders = (
                bool(strategy.is_automated)
                and (strategy.execution_mode or 'live_trading') == 'live_trading'
            )

        execution = StrategyExecution.objects.create(strategy=strategy, status='running')

        try:
            algo = strategy.get_algorithm_instance()
            if not algo:
                raise ValueError(f"Impossible de créer l'algorithme {strategy.algorithm_type}")

            portfolio, pending_orders = self.build_portfolio_data(strategy)
            price_data = self.load_price_data(strategy)
            signals = self._calculate_signals(algo, price_data, portfolio, pending_orders)

            signal_type = signals.get('signal', 'NONE')
            signal_price = float(price_data[-1]['close']) if price_data else None
            signal_quantity = signals.get('quantity', 0) or 0
            output_data: Dict[str, Any] = {
                'signals': signals,
                'price_data_count': len(price_data),
                'portfolio': portfolio,
                'pending_orders_count': len(pending_orders),
                'execution_mode': strategy.execution_mode,
                'place_orders': place_orders,
                'forced': force,
            }

            execution.status = 'completed'
            execution.signal = signal_type
            execution.signal_price = signal_price
            execution.signal_quantity = signal_quantity
            execution.output = json.dumps(output_data, default=str)
            execution.completed_at = timezone.now()
            execution.save()

            if (
                place_orders
                and signal_type in ('BUY', 'SELL')
                and float(signal_quantity) > 0
            ):
                try:
                    broker_response = self.execute_signal(
                        strategy, signal_type, signal_quantity, signal_price, execution
                    )
                    output_data['execution_executed'] = True
                    output_data['broker_api_url'] = broker_response.get('api_url')
                    output_data['broker_api_response'] = broker_response.get('api_response')
                    output_data['broker_api_error'] = broker_response.get('api_error')
                    execution.output = json.dumps(output_data, default=str)
                    execution.save()
                except Exception as exc:
                    logger.exception('Erreur placement ordre stratégie %s', strategy.id)
                    execution.error = f'Execution error: {exc}'
                    execution.status = 'failed'
                    execution.save()
                    return {
                        'status': 'error',
                        'execution_id': execution.id,
                        'signal': signal_type,
                        'signal_price': signal_price,
                        'signal_quantity': signal_quantity,
                        'error': str(exc),
                        'output': output_data,
                    }

            return {
                'status': 'success',
                'execution_id': execution.id,
                'signal': signal_type,
                'signal_price': signal_price,
                'signal_quantity': signal_quantity,
                'output': output_data,
            }
        except Exception as exc:
            logger.exception('Erreur exécution stratégie %s', strategy.id)
            execution.status = 'failed'
            execution.error = str(exc)
            execution.completed_at = timezone.now()
            execution.save()
            return {
                'status': 'error',
                'execution_id': execution.id,
                'error': str(exc),
            }

    def execute_signal(
        self,
        strategy: Strategy,
        signal_type: str,
        quantity: Any,
        price: Any,
        execution: StrategyExecution,
    ) -> Dict[str, Any]:
        """Place l'ordre broker + enregistre Order/Trade/Position locaux."""
        if not strategy.broker_account or not strategy.broker_account.broker:
            raise ValueError('Aucun compte broker configuré pour cette stratégie')

        broker = strategy.broker_account.broker
        qty_decimal = Decimal(str(quantity))
        price_decimal = Decimal(str(price))

        broker_api_response = None
        broker_api_url = None
        broker_api_error = None
        adjusted_quantity = qty_decimal

        try:
            broker_name = (broker.name or '').lower()
            broker_type = (getattr(broker, 'broker_type', '') or '').lower()
            if 'binance' in broker_name or broker_type == 'binance':
                broker_api_url = 'POST https://api.binance.com/api/v3/order'
            elif 'saxo' in broker_name or broker_type == 'saxo':
                broker_api_url = 'POST https://gateway.saxobank.com/openapi/trade/v2/orders'
            else:
                broker_api_url = f'API {broker.name} (endpoint inconnu)'

            broker_service = BrokerService(user=strategy.user)
            asset_symbol = strategy.all_asset.symbol if strategy.all_asset else 'UNKNOWN'

            try:
                broker_instance = broker_service.get_broker_instance(strategy.broker_account)
                if 'binance' in broker_name or broker_type == 'binance':
                    exchange_info = (
                        broker_instance._get_exchange_info()
                        if hasattr(broker_instance, '_get_exchange_info')
                        else None
                    )
                    if exchange_info:
                        symbols = exchange_info.get('symbols', [])
                        symbol_info = next(
                            (s for s in symbols if s.get('symbol') == asset_symbol.upper()),
                            None,
                        )
                        if symbol_info:
                            filters = symbol_info.get('filters', [])
                            lot_size_filter = next(
                                (f for f in filters if f.get('filterType') == 'LOT_SIZE'),
                                None,
                            )
                            if lot_size_filter:
                                min_qty = Decimal(str(lot_size_filter.get('minQty', '0')))
                                max_qty = Decimal(str(lot_size_filter.get('maxQty', '999999999')))
                                step_size = Decimal(str(lot_size_filter.get('stepSize', '1')))
                                if step_size > 0:
                                    adjusted_quantity = (
                                        qty_decimal / step_size
                                    ).quantize(Decimal('1'), rounding=ROUND_DOWN) * step_size
                                if adjusted_quantity < min_qty:
                                    adjusted_quantity = min_qty
                                elif adjusted_quantity > max_qty:
                                    adjusted_quantity = max_qty
            except Exception as adjust_error:
                logger.warning(
                    'Ajustement quantité échoué (%s), quantité originale conservée',
                    adjust_error,
                )
                adjusted_quantity = qty_decimal

            order_result = broker_service.place_order(
                broker_account=strategy.broker_account,
                symbol=asset_symbol,
                side=signal_type,
                quantity=adjusted_quantity,
                order_type='MARKET',
                price=None,
            )

            if order_result.success:
                broker_api_response = {
                    'success': True,
                    'order_id': order_result.order_id,
                    'message': order_result.message,
                    'raw_data': getattr(order_result, 'raw_data', None),
                }
            else:
                broker_api_error = order_result.error
                broker_api_response = {
                    'success': False,
                    'error': order_result.error,
                }
        except Exception as exc:
            logger.exception('Erreur API broker stratégie %s', strategy.id)
            broker_api_error = str(exc)
            broker_api_response = {
                'success': False,
                'error': str(exc),
                'exception_type': type(exc).__name__,
            }

        broker_order_id = f'AUTO-{execution.id}'
        if broker_api_response and broker_api_response.get('success') and broker_api_response.get('order_id'):
            broker_order_id = broker_api_response['order_id']

        Order.objects.create(
            user=strategy.user,
            all_asset=strategy.all_asset,
            broker=broker,
            strategy=strategy,
            order_type='MARKET',
            side='BUY' if signal_type == 'BUY' else 'SELL',
            status='FILLED' if broker_api_response and broker_api_response.get('success') else 'FAILED',
            quantity=adjusted_quantity,
            filled_quantity=(
                adjusted_quantity
                if broker_api_response and broker_api_response.get('success')
                else Decimal('0')
            ),
            price=price_decimal,
            broker_order_id=broker_order_id,
        )

        trade = None
        if broker_api_response and broker_api_response.get('success'):
            trade = Trade.objects.create(
                user=strategy.user,
                all_asset=strategy.all_asset,
                broker=broker,
                position=None,
                strategy=strategy,
                trade_type='BUY' if signal_type == 'BUY' else 'SELL',
                quantity=adjusted_quantity,
                price=price_decimal,
                fees=Decimal('0'),
                executed_at=timezone.now(),
                broker_trade_id=f'TRD-{execution.id}',
            )

            position = Position.objects.filter(
                user=strategy.user,
                all_asset=strategy.all_asset,
                is_open=True,
            ).first()

            if signal_type == 'BUY':
                if position:
                    current_val = position.entry_price * position.quantity
                    trade_val = price_decimal * adjusted_quantity
                    new_qty = position.quantity + adjusted_quantity
                    position.entry_price = (current_val + trade_val) / new_qty
                    position.quantity = new_qty
                    position.save()
                else:
                    position = Position.objects.create(
                        user=strategy.user,
                        all_asset=strategy.all_asset,
                        broker=broker,
                        strategy=strategy,
                        side='LONG',
                        quantity=adjusted_quantity,
                        entry_price=price_decimal,
                        current_price=price_decimal,
                        is_open=True,
                    )
            elif signal_type == 'SELL' and position:
                position.quantity -= adjusted_quantity
                if position.quantity <= Decimal('0.00000001'):
                    position.is_open = False
                    position.closed_at = timezone.now()
                    position.quantity = 0
                position.save()

            if trade and position:
                trade.position = position
                trade.save()

        return {
            'api_url': broker_api_url,
            'api_response': broker_api_response,
            'api_error': broker_api_error,
            'quantity_original': float(qty_decimal),
            'quantity_adjusted': float(adjusted_quantity),
            'quantity_was_adjusted': qty_decimal != adjusted_quantity,
        }

    def run_due_strategies(
        self,
        *,
        force: bool = False,
        dry_run: bool = False,
        strategy_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Sélectionne les stratégies actives+auto dues et les exécute."""
        qs = Strategy.objects.filter(is_active=True, is_automated=True).select_related(
            'all_asset', 'broker_account', 'broker_account__broker', 'user'
        )
        if strategy_ids:
            qs = qs.filter(id__in=strategy_ids)

        results = []
        skipped = 0
        for strategy in qs:
            if not self.should_run_now(strategy, force=force):
                skipped += 1
                results.append({
                    'strategy_id': strategy.id,
                    'name': strategy.name,
                    'status': 'skipped',
                    'reason': 'check_frequency',
                })
                continue

            place_orders = None if not dry_run else False
            if dry_run:
                # Signaux seulement, jamais d'ordre
                result = self.execute_strategy(strategy, place_orders=False, force=force)
            else:
                result = self.execute_strategy(strategy, place_orders=place_orders, force=force)

            results.append({
                'strategy_id': strategy.id,
                'name': strategy.name,
                **result,
            })

        return {
            'ran': sum(1 for r in results if r.get('status') in ('success', 'error')),
            'skipped': skipped,
            'dry_run': dry_run,
            'results': results,
        }
