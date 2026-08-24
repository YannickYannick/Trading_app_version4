"""Service Saxo : coûts pré-trade (illustration + precheck) et post-trade (reports)."""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone as dt_timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote

from django.db.models import Q
from django.utils import timezone

from .client import SaxoHttpClient, SaxoHttpError
from .payloads import build_order_payload

logger = logging.getLogger('trading_app.saxo')


def _dec(value: Any) -> Decimal:
    if value is None or value == '':
        return Decimal('0')
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal('0')


def _sum_values(items: Any) -> Decimal:
    total = Decimal('0')
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                total += _dec(item.get('Value'))
            else:
                total += _dec(item)
    elif isinstance(items, dict):
        total += _dec(items.get('Value'))
    else:
        total += _dec(items)
    return total


@dataclass
class TradingCostBreakdown:
    commissions: Decimal = Decimal('0')
    spread: Decimal = Decimal('0')
    conversion_cost: Decimal = Decimal('0')
    exchange_fee: Decimal = Decimal('0')
    ticket: Decimal = Decimal('0')

    @classmethod
    def from_api(cls, data: Optional[Dict[str, Any]]) -> 'TradingCostBreakdown':
        data = data or {}
        conversion = data.get('ConversionCost') or data.get('CurrencyConversionCost') or {}
        ticket = data.get('Ticket') or data.get('TicketFee') or {}
        return cls(
            commissions=_sum_values(data.get('Commissions')),
            spread=_dec((data.get('Spread') or {}).get('Value') if isinstance(data.get('Spread'), dict) else data.get('Spread')),
            conversion_cost=_dec(conversion.get('Value') if isinstance(conversion, dict) else conversion),
            exchange_fee=_dec((data.get('ExchangeFee') or {}).get('Value') if isinstance(data.get('ExchangeFee'), dict) else data.get('ExchangeFee')),
            ticket=_dec(ticket.get('Value') if isinstance(ticket, dict) else ticket),
        )


@dataclass
class HoldingCostBreakdown:
    funding_cost: Decimal = Decimal('0')
    carrying_cost: Decimal = Decimal('0')
    custody: Decimal = Decimal('0')
    tax: Decimal = Decimal('0')

    @classmethod
    def from_api(cls, data: Optional[Dict[str, Any]]) -> 'HoldingCostBreakdown':
        data = data or {}
        funding = data.get('FundingCost') or data.get('OvernightFinancing') or {}
        carrying = data.get('CarryingCost') or {}
        custody = data.get('Custody') or data.get('CustodyFee') or {}
        return cls(
            funding_cost=_dec(funding.get('Value') if isinstance(funding, dict) else funding),
            carrying_cost=_dec(carrying.get('Value') if isinstance(carrying, dict) else carrying),
            custody=_dec(custody.get('Value') if isinstance(custody, dict) else custody),
            tax=_sum_values(data.get('Tax')),
        )


@dataclass
class SideCost:
    buy_sell: str = ''
    currency: str = ''
    total_cost: Decimal = Decimal('0')
    total_cost_pct: Decimal = Decimal('0')
    trading: TradingCostBreakdown = field(default_factory=TradingCostBreakdown)
    holding: HoldingCostBreakdown = field(default_factory=HoldingCostBreakdown)

    @classmethod
    def from_api(cls, data: Optional[Dict[str, Any]]) -> 'SideCost':
        data = data or {}
        return cls(
            buy_sell=str(data.get('BuySell') or ''),
            currency=str(data.get('Currency') or ''),
            total_cost=_dec(data.get('TotalCost')),
            total_cost_pct=_dec(data.get('TotalCostPct')),
            trading=TradingCostBreakdown.from_api(data.get('TradingCost')),
            holding=HoldingCostBreakdown.from_api(data.get('HoldingCost')),
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        for key, value in list(payload.items()):
            if isinstance(value, Decimal):
                payload[key] = float(value)
        payload['trading'] = {
            k: float(v) if isinstance(v, Decimal) else v
            for k, v in asdict(self.trading).items()
        }
        payload['holding'] = {
            k: float(v) if isinstance(v, Decimal) else v
            for k, v in asdict(self.holding).items()
        }
        return payload


@dataclass
class InstrumentCostEstimate:
    uic: int
    asset_type: str
    amount: float
    price: Optional[float]
    holding_period_in_days: int
    account_currency: str
    instrument: str
    long: SideCost
    short: SideCost
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'uic': self.uic,
            'asset_type': self.asset_type,
            'amount': self.amount,
            'price': self.price,
            'holding_period_in_days': self.holding_period_in_days,
            'account_currency': self.account_currency,
            'instrument': self.instrument,
            'long': self.long.to_dict(),
            'short': self.short.to_dict(),
        }


@dataclass
class PrecheckResult:
    ok: bool
    result: str
    commission: Decimal = Decimal('0')
    exchange_fee: Decimal = Decimal('0')
    stamp_duty: Decimal = Decimal('0')
    guaranteed_stop_fee: Decimal = Decimal('0')
    estimated_cash_required: Decimal = Decimal('0')
    estimated_cash_currency: str = ''
    estimated_total_cost: Decimal = Decimal('0')
    error: str = ''
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_error(self) -> bool:
        return (self.result or '').lower() == 'error' or not self.ok

    def to_dict(self) -> Dict[str, Any]:
        return {
            'precheck_ok': self.ok,
            'precheck_result': self.result,
            'commission': float(self.commission),
            'exchange_fee': float(self.exchange_fee),
            'stamp_duty': float(self.stamp_duty),
            'guaranteed_stop_fee': float(self.guaranteed_stop_fee),
            'total_cost': float(self.commission + self.exchange_fee + self.stamp_duty + self.guaranteed_stop_fee),
            'estimated_cash_required': float(self.estimated_cash_required),
            'estimated_cash_currency': self.estimated_cash_currency,
            'estimated_total_cost': float(self.estimated_total_cost),
            'error': self.error,
        }


@dataclass
class ExecutedTradeCost:
    trade_id: str
    uic: Optional[int]
    asset_type: str
    amount: Decimal
    buy_sell: str
    trade_date: Optional[datetime]
    commission: Decimal
    exchange_fee: Decimal
    spread_cost: Decimal
    financing_cost: Decimal
    tax: Decimal
    total_cost: Decimal
    currency: str
    raw: Dict[str, Any] = field(default_factory=dict)


class SaxoCostService:
    """Coûts Saxo pré-trade et post-trade."""

    def __init__(self, client: SaxoHttpClient):
        self.client = client
        self._keys: Optional[Dict[str, Optional[str]]] = None
        self._uic_cache: Dict[Tuple[str, str], Optional[int]] = {}

    @classmethod
    def from_credentials(cls, credentials: Dict[str, Any]) -> 'SaxoCostService':
        return cls(SaxoHttpClient(credentials))

    def get_account_keys(self, force: bool = False) -> Dict[str, Optional[str]]:
        if self._keys and not force:
            return self._keys
        client_key = None
        account_key = None
        try:
            client_data = self.client.request('GET', '/port/v1/clients/me')
            client_key = client_data.get('ClientKey')
        except SaxoHttpError as exc:
            logger.warning('Saxo clients/me failed: %s', exc)
        try:
            account_data = self.client.request('GET', '/port/v1/accounts/me')
            accounts = account_data.get('Data') or []
            if accounts:
                account_key = accounts[0].get('AccountKey')
        except SaxoHttpError as exc:
            logger.warning('Saxo accounts/me failed: %s', exc)
        self._keys = {
            'client_key': client_key or self.client.credentials.get('client_key'),
            'account_key': account_key or self.client.credentials.get('account_key'),
        }
        return self._keys

    def resolve_uic(self, keywords: str, asset_type: str = 'Stock') -> Optional[int]:
        cache_key = (keywords.upper(), asset_type)
        if cache_key in self._uic_cache:
            return self._uic_cache[cache_key]
        data = self.client.request(
            'GET',
            '/ref/v1/instruments',
            params={'Keywords': keywords, 'AssetTypes': asset_type, '$top': 5},
        )
        items = data.get('Data') or []
        uic = items[0].get('Identifier') if items else None
        self._uic_cache[cache_key] = uic
        return uic

    def estimate_instrument_cost(
        self,
        uic: int,
        asset_type: str,
        amount: float,
        price: Optional[float] = None,
        holding_days: int = 1,
        apply_costs_zero_floor: bool = False,
    ) -> InstrumentCostEstimate:
        keys = self.get_account_keys()
        account_key = keys.get('account_key')
        if not account_key:
            raise SaxoHttpError('AccountKey unavailable')
        if price is None:
            price = self._fetch_mid_price(uic, asset_type, account_key)
        encoded_key = quote(str(account_key), safe='')
        params = {
            'Amount': amount,
            'HoldingPeriodInDays': holding_days,
            'ApplyCostsZeroFloor': str(apply_costs_zero_floor).lower(),
            'FieldGroups': 'DisplayAndFormat',
            'Price': price,
        }
        path = f'/cs/v1/tradingconditions/cost/{encoded_key}/{int(uic)}/{asset_type}'
        data = self.client.request('GET', path, params=params)
        cost = data.get('Cost') or {}
        return InstrumentCostEstimate(
            uic=int(data.get('Uic') or uic),
            asset_type=str(data.get('AssetType') or asset_type),
            amount=float(data.get('Amount') or amount),
            price=float(data['Price']) if data.get('Price') is not None else price,
            holding_period_in_days=int(data.get('HoldingPeriodInDays') or holding_days),
            account_currency=str(data.get('AccountCurrency') or ''),
            instrument=str(data.get('Instrument') or ''),
            long=SideCost.from_api(cost.get('Long')),
            short=SideCost.from_api(cost.get('Short')),
            raw=data,
        )

    def get_instrument_conditions(self, uic: int, asset_type: str) -> Dict[str, Any]:
        keys = self.get_account_keys()
        account_key = keys.get('account_key')
        if not account_key:
            raise SaxoHttpError('AccountKey unavailable')
        encoded_key = quote(str(account_key), safe='')
        path = f'/cs/v1/tradingconditions/instrument/{encoded_key}/{int(uic)}/{asset_type}'
        return self.client.request('GET', path)

    def precheck_order(self, order_payload: Dict[str, Any]) -> PrecheckResult:
        payload = dict(order_payload)
        payload['FieldGroups'] = ['Costs']
        try:
            data = self.client.request('POST', '/trade/v2/orders/precheck', json_data=payload)
        except SaxoHttpError as exc:
            return PrecheckResult(
                ok=False,
                result='Error',
                error=str(exc),
                raw={'body': exc.body},
            )
        cost = data.get('Cost') or {}
        result = str(data.get('PreCheckResult') or '')
        return PrecheckResult(
            ok=result == 'Ok',
            result=result,
            commission=_dec(cost.get('Commission')),
            exchange_fee=_dec(cost.get('ExchangeFee')),
            stamp_duty=_dec(cost.get('StampDuty')),
            guaranteed_stop_fee=_dec(cost.get('GuaranteedStopFee')),
            estimated_cash_required=_dec(data.get('EstimatedCashRequired')),
            estimated_cash_currency=str(data.get('EstimatedCashRequiredCurrency') or ''),
            estimated_total_cost=_dec(data.get('EstimatedTotalCost')),
            error=str((data.get('ErrorInfo') or {}).get('Message') or ''),
            raw=data,
        )

    def build_and_precheck(
        self,
        *,
        uic: int,
        asset_type: str,
        side: str,
        quantity: float,
        order_type: str = 'Market',
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        manual_order: bool = True,
    ) -> Tuple[Dict[str, Any], PrecheckResult]:
        keys = self.get_account_keys()
        payload = build_order_payload(
            uic=uic,
            asset_type=asset_type,
            side=side,
            quantity=quantity,
            account_key=keys.get('account_key') or '',
            order_type=order_type,
            price=price,
            stop_price=stop_price,
            manual_order=manual_order,
            include_costs_field_group=True,
        )
        return payload, self.precheck_order(payload)

    def fetch_executed_costs(
        self,
        from_date: date,
        to_date: date,
        top: int = 1000,
    ) -> List[ExecutedTradeCost]:
        keys = self.get_account_keys()
        client_key = keys.get('client_key')
        if not client_key:
            raise SaxoHttpError('ClientKey unavailable')
        encoded_key = quote(str(client_key), safe='')
        endpoint = f'/cs/v1/reports/trades/{encoded_key}'
        params = {
            'FromDate': from_date.isoformat(),
            'ToDate': to_date.isoformat(),
            '$top': top,
        }
        rows: List[ExecutedTradeCost] = []
        while endpoint:
            data = self.client.request('GET', endpoint, params=params)
            params = None
            items = data.get('Data') or data.get('Trades') or []
            if isinstance(data, list):
                items = data
            for item in items:
                parsed = self._parse_executed_trade(item)
                if parsed:
                    rows.append(parsed)
            next_url = data.get('__next') if isinstance(data, dict) else None
            endpoint = next_url
        return rows

    def fetch_trades_executed_report(self, client_key: Optional[str] = None) -> Any:
        key = client_key or self.get_account_keys().get('client_key')
        if not key:
            raise SaxoHttpError('ClientKey unavailable')
        encoded_key = quote(str(key), safe='')
        return self.client.request('GET', f'/cr/v1/reports/TradesExecuted/{encoded_key}')

    def _fetch_mid_price(self, uic: int, asset_type: str, account_key: str) -> float:
        params = {
            'Uic': uic,
            'AssetType': asset_type,
            'AccountKey': account_key,
            'FieldGroups': 'Quote',
        }
        try:
            data = self.client.request('GET', '/trade/v1/prices', params=params)
        except SaxoHttpError:
            data = self.client.request('GET', '/trade/v1/infoprices', params=params)
        if isinstance(data, dict) and data.get('Data'):
            data = data['Data'][0]
        quote = (data or {}).get('Quote') or {}
        price = quote.get('Mid') or quote.get('Ask') or quote.get('Bid')
        if price is None:
            raise SaxoHttpError('Price required and unavailable from Saxo quote')
        return float(price)

    def persist_executed_costs(
        self,
        user,
        executed: Iterable[ExecutedTradeCost],
        source: str = 'report',
    ) -> Dict[str, int]:
        from apps.trading.models import TransactionCost, Trade

        created = 0
        updated = 0
        unmatched = 0
        for row in executed:
            trade = match_trade_for_cost(user, row)
            total = row.total_cost
            defaults = {
                'user': user,
                'commission': row.commission,
                'exchange_fee': row.exchange_fee,
                'spread_cost': row.spread_cost,
                'financing_cost': row.financing_cost,
                'tax': row.tax,
                'total_cost': total,
                'currency': row.currency or 'EUR',
                'is_estimate': False,
                'saxo_trade_id': row.trade_id,
                'uic': row.uic,
                'raw_payload': row.raw,
                'fetched_at': timezone.now(),
            }
            lookup = {'source': source}
            if trade:
                lookup['trade'] = trade
                TransactionCost.objects.filter(
                    saxo_trade_id=row.trade_id,
                    source=source,
                    trade__isnull=True,
                ).delete()
            else:
                lookup['saxo_trade_id'] = row.trade_id or f'unmatched-{row.uic}-{row.trade_date}'
                defaults['trade'] = None
                unmatched += 1
                logger.warning(
                    'Saxo cost unmatched trade_id=%s uic=%s date=%s amount=%s side=%s',
                    row.trade_id, row.uic, row.trade_date, row.amount, row.buy_sell,
                )

            obj, was_created = TransactionCost.objects.update_or_create(
                **lookup,
                defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1
            if trade and not obj.is_estimate:
                Trade.objects.filter(pk=trade.pk).update(fees=total)
        return {'created': created, 'updated': updated, 'unmatched': unmatched}

    @staticmethod
    def _parse_executed_trade(item: Dict[str, Any]) -> Optional[ExecutedTradeCost]:
        if not isinstance(item, dict):
            return None
        booked = item.get('BookedAmounts') or item.get('BookedAmount') or {}
        commissions = item.get('Commissions') if item.get('Commissions') is not None else item.get('Commission')
        commission = _sum_values(commissions) if not isinstance(commissions, (int, float, str, Decimal)) else _dec(commissions)
        if commission == 0 and isinstance(booked, dict):
            commission = abs(_dec(booked.get('Commission') or booked.get('Commissions')))
        exchange_fee = _dec(item.get('ExchangeFee'))
        spread = _dec(item.get('Spread') or item.get('SpreadCost'))
        financing = _dec(item.get('FinancingCost') or item.get('OvernightFinancing'))
        tax = _dec(item.get('Tax') or item.get('StampDuty'))
        total = _dec(item.get('TotalCost'))
        if total == 0:
            total = commission + exchange_fee + spread + financing + tax
        trade_date = _parse_dt(item.get('TradeDate') or item.get('TradeTime') or item.get('ExecutionTime') or item.get('Date'))
        currency = (
            item.get('AccountCurrency')
            or (booked.get('Currency') if isinstance(booked, dict) else None)
            or item.get('Currency')
            or ''
        )
        amount = _dec(item.get('Amount') or item.get('TradedQuantity') or item.get('Quantity'))
        return ExecutedTradeCost(
            trade_id=str(item.get('TradeId') or item.get('Id') or ''),
            uic=item.get('Uic') or (item.get('Instrument') or {}).get('Uic'),
            asset_type=str(item.get('AssetType') or (item.get('Instrument') or {}).get('AssetType') or ''),
            amount=abs(amount),
            buy_sell=str(item.get('BuySell') or item.get('TradeType') or item.get('Event') or ''),
            trade_date=trade_date,
            commission=abs(commission),
            exchange_fee=abs(exchange_fee),
            spread_cost=abs(spread),
            financing_cost=abs(financing),
            tax=abs(tax),
            total_cost=abs(total),
            currency=str(currency),
            raw=item,
        )


def _parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).replace('Z', '+00:00')
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        try:
            return datetime.strptime(str(value)[:10], '%Y-%m-%d')
        except ValueError:
            return None


def match_trade_for_cost(user, row: ExecutedTradeCost):
    from apps.trading.models import Trade

    qs = Trade.objects.filter(user=user)
    trade_id = (row.trade_id or '').strip()
    if trade_id:
        exact = qs.filter(broker_trade_id=trade_id).first()
        if exact:
            return exact
        contained = qs.filter(broker_trade_id__icontains=trade_id).first()
        if contained:
            return contained

    if not row.trade_date:
        return None
    day = row.trade_date.date() if hasattr(row.trade_date, 'date') else row.trade_date
    start = datetime.combine(day, datetime.min.time())
    end = start + timedelta(days=1)
    if timezone.is_naive(start):
        start = timezone.make_aware(start, dt_timezone.utc)
        end = timezone.make_aware(end, dt_timezone.utc)

    side = (row.buy_sell or '').upper()
    if side in ('BUY', 'BOUGHT'):
        side_filter = Q(trade_type='BUY')
    elif side in ('SELL', 'SOLD'):
        side_filter = Q(trade_type='SELL')
    else:
        side_filter = Q()

    candidates = qs.filter(executed_at__gte=start, executed_at__lt=end).filter(side_filter)
    if row.uic:
        candidates = candidates.filter(all_asset__saxo_uic=row.uic)

    amount = row.amount
    for trade in candidates:
        if amount and abs(trade.quantity - amount) > Decimal('0.0001'):
            continue
        return trade
    logger.warning(
        'No Saxo cost match for trade_id=%s uic=%s date=%s amount=%s side=%s',
        trade_id, row.uic, row.trade_date, row.amount, row.buy_sell,
    )
    return None
