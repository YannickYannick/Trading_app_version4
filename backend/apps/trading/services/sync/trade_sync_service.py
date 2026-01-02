"""
Trade Synchronization Service.

This service synchronizes trade history from brokers to the local database.
"""
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from .base_sync_service import BaseSyncService
from ...brokers.factory import BrokerFactory
from ...brokers.base import BrokerTrade, BrokerBase
from ...models import BrokerAccount, Trade, Position, Asset, AllAssets
from ...exceptions import SyncException, SyncAuthenticationError

logger = logging.getLogger('trading.services.sync.trades')


class TradeSyncService(BaseSyncService):
    """
    Service for synchronizing trade history from brokers.
    
    Features:
    - Sync trades from any supported broker
    - Create local Trade records
    - Link trades to positions when possible
    - Support for date range filtering
    
    Usage:
        service = TradeSyncService(user)
        result = service.sync(broker_account, limit=100)
    """
    
    SYNC_TYPE = 'trades'
    
    def sync(
        self,
        broker_account: BrokerAccount,
        limit: int = 100000,
        symbol: Optional[str] = None,
        since_days: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Sync trades from a broker.
        
        Args:
            broker_account: BrokerAccount to sync from
            limit: Maximum number of trades to fetch
            symbol: Optional symbol filter
            since_days: Only sync trades from last N days
            **kwargs: Additional parameters
            
        Returns:
            Dict with sync results
        """
        self._log_start(
            f"Starting trade sync for {broker_account.broker.name}",
            broker=broker_account.broker.name,
            limit=limit,
            symbol=symbol,
        )
        
        try:
            # Get broker instance
            credentials = self._get_credentials(broker_account)
            broker_type = broker_account.get_broker_type()
            broker = BrokerFactory.create_broker(broker_type, self.user, credentials)
            
            # Authenticate
            if not broker.authenticate():
                raise SyncAuthenticationError(
                    sync_type=self.SYNC_TYPE,
                    broker_type=broker_type,
                )
            
            # Fetch trades from broker
            broker_trades = broker.get_trades(
                symbol=symbol,
                limit=limit,
            )
            
            self.logger.info(
                f"Retrieved {len(broker_trades)} trades from {broker_type}"
            )
            
            # Filter by date if specified
            if since_days:
                cutoff_date = timezone.now() - timedelta(days=since_days)
                broker_trades = self._filter_trades_by_date(broker_trades, cutoff_date)
            
            # Sync trades to database
            with transaction.atomic():
                result = self._sync_trades(
                    broker_account=broker_account,
                    broker_trades=broker_trades,
                )
            
            # Log completion
            self._log_complete(
                created=result.get('created', 0),
                updated=result.get('updated', 0),
                broker=broker_account.broker.name
            )
            
            # Create sync log
            self._create_sync_log(
                broker_account=broker_account,
                status='success' if not self._errors else 'partial',
                records_synced=result.get('created', 0) + result.get('updated', 0),
                details=result,
            )
            
            return result
            
        except SyncException:
            raise
        except Exception as e:
            self._log_error("Trade sync failed", error=e)
            
            self._create_sync_log(
                broker_account=broker_account,
                status='error',
                error_message=str(e),
            )
            
            raise SyncException(
                message=f"Trade sync failed: {str(e)}",
                sync_type=self.SYNC_TYPE,
            )
    
    def _sync_trades(
        self,
        broker_account: BrokerAccount,
        broker_trades: List[BrokerTrade],
    ) -> Dict[str, Any]:
        """
        Sync trades to database.
        
        Args:
            broker_account: BrokerAccount being synced
            broker_trades: List of trades from broker
            
        Returns:
            Dict with sync statistics
        """
        created = 0
        updated = 0
        skipped = 0
        
        for broker_trade in broker_trades:
            try:
                result = self._sync_single_trade(
                    broker_account=broker_account,
                    broker_trade=broker_trade,
                )
                
                if result.get('created'):
                    created += 1
                elif result.get('updated'):
                    updated += 1
                elif result.get('skipped'):
                    skipped += 1
                    
            except Exception as e:
                self._log_error(
                    f"Failed to sync trade {broker_trade.broker_trade_id or broker_trade.symbol}",
                    error=e,
                    symbol=broker_trade.symbol
                )
        
        return self._build_result(
            success=len(self._errors) == 0,
            created=created,
            updated=updated,
            skipped=skipped,
        )
    
    def _sync_single_trade(
        self,
        broker_account: BrokerAccount,
        broker_trade: BrokerTrade,
    ) -> Dict[str, Any]:
        """
        Sync a single trade.
        
        Args:
            broker_account: BrokerAccount being synced
            broker_trade: Trade data from broker
            
        Returns:
            Dict with result info
        """
        # Check if trade already exists
        if broker_trade.broker_trade_id:
            existing = Trade.objects.filter(
                broker_trade_id=broker_trade.broker_trade_id,
                broker=broker_account.broker,
                user=self.user,
            ).first()
            
            if existing:
                return {'skipped': True, 'trade_id': existing.id}
        
        # Find or create AllAsset (source de vérité unique)
        # Extraire l'UIC et l'asset_type depuis raw_data si disponible
        raw_data = broker_trade.raw_data or {}
        uic = raw_data.get('uic')
        asset_type = raw_data.get('asset_type')
        
        # Récupérer l'instance du broker pour pouvoir appeler get_asset_by_uic si nécessaire
        broker_instance = None
        if broker_account.get_broker_type() == 'SAXO':
            credentials = self._get_credentials(broker_account)
            broker_instance = BrokerFactory.create_broker(
                broker_account.get_broker_type(),
                self.user,
                credentials
            )
            # S'assurer que le broker est authentifié
            if not broker_instance.is_connected:
                broker_instance.authenticate()
        
        all_asset = self._get_or_create_all_asset(
            symbol=broker_trade.symbol,
            broker_type=broker_account.get_broker_type(),
            uic=uic,
            asset_type=asset_type,
            broker_instance=broker_instance,
        )
        
        if not all_asset:
            raise ValueError(f"Could not find or create AllAsset: {broker_trade.symbol}")
        
        # Try to find related position (utilise all_asset maintenant)
        position = self._find_related_position(
            broker_account=broker_account,
            all_asset=all_asset,
            trade_type=broker_trade.trade_type,
        )
        
        # Parse executed_at
        executed_at = None
        if broker_trade.executed_at:
            try:
                if isinstance(broker_trade.executed_at, str):
                    executed_at = datetime.fromisoformat(
                        broker_trade.executed_at.replace('Z', '+00:00')
                    )
                else:
                    executed_at = broker_trade.executed_at
            except (ValueError, TypeError):
                executed_at = timezone.now()
        else:
            executed_at = timezone.now()
        
        # Create trade (utilise all_asset directement)
        trade = Trade.objects.create(
            user=self.user,
            broker=broker_account.broker,
            all_asset=all_asset,  # Utiliser AllAssets directement
            position=position,
            trade_type=broker_trade.trade_type,
            quantity=broker_trade.quantity,
            price=broker_trade.price,
            fees=broker_trade.fees,
            executed_at=executed_at,
            broker_trade_id=broker_trade.broker_trade_id,
        )
        
        return {
            'created': True,
            'trade_id': trade.id,
        }
    
    def _find_related_position(
        self,
        broker_account: BrokerAccount,
        all_asset: AllAssets,
        trade_type: str,
    ) -> Optional[Position]:
        """
        Find a related position for a trade.
        
        Args:
            broker_account: BrokerAccount
            all_asset: AllAssets for the trade
            trade_type: 'BUY' or 'SELL'
            
        Returns:
            Position or None
        """
        # Find open position for this all_asset
        position = Position.objects.filter(
            user=self.user,
            broker=broker_account.broker,
            all_asset=all_asset,  # Utiliser all_asset directement
            is_open=True,
        ).first()
        
        return position
    
    def _get_or_create_all_asset(
        self,
        symbol: str,
        broker_type: str,
        uic: Optional[int] = None,
        asset_type: Optional[str] = None,
        broker_instance: Optional[BrokerBase] = None,
    ) -> Optional[AllAssets]:
        """
        Get or create an AllAsset for the given symbol.
        
        AllAssets est la source de vérité unique. Si l'asset n'existe pas,
        on essaie de le récupérer depuis l'API du broker (si UIC disponible)
        avant de créer un AllAsset minimal.
        
        Args:
            symbol: Asset symbol (peut être "UIC_xxxx" si symbole réel non disponible)
            broker_type: Type of broker (SAXO, BINANCE, etc.)
            uic: UIC de l'asset (optionnel, pour Saxo)
            asset_type: Type d'asset (optionnel, pour améliorer la recherche)
            broker_instance: Instance du broker (optionnel, pour appeler l'API)
            
        Returns:
            AllAssets instance or None
        """
        platform = broker_type.upper()
        
        # 1. Chercher dans AllAssets avec (symbol, platform) unique
        all_asset = AllAssets.objects.filter(
            symbol=symbol,
            platform=platform,
        ).first()
        
        if all_asset:
            # Si l'AllAsset existe mais n'a pas d'UIC alors qu'on en a un, le mettre à jour
            if platform == 'SAXO' and uic and not all_asset.saxo_uic:
                all_asset.saxo_uic = uic
                all_asset.save(update_fields=['saxo_uic'])
                self.logger.debug(f"Updated saxo_uic for {symbol}: {uic}")
            return all_asset
        
        # 2. Si symbol = "UIC_xxxx" et UIC disponible, chercher par UIC
        if symbol.startswith('UIC_') and uic:
            try:
                extracted_uic = int(symbol.replace('UIC_', ''))
                if extracted_uic == uic:
                    # Chercher par saxo_uic
                    all_asset = AllAssets.objects.filter(
                        saxo_uic=uic,
                        platform=platform,
                    ).first()
                    
                    if all_asset:
                        self.logger.info(
                            f"Found AllAsset by UIC {uic}: {all_asset.symbol} "
                            f"(was looking for {symbol})"
                        )
                        return all_asset
            except ValueError:
                pass
        
        # 3. Si toujours pas trouvé et UIC disponible, essayer de récupérer depuis l'API
        if platform == 'SAXO' and uic and broker_instance:
            try:
                from ...brokers.saxo import SaxoBroker
                if isinstance(broker_instance, SaxoBroker):
                    broker_asset = broker_instance.get_asset_by_uic(
                        uic=uic,
                        asset_type=asset_type or 'Stock'
                    )
                    
                    if broker_asset:
                        raw_data = broker_asset.raw_data or {}
                        
                        # Utiliser get_or_create pour éviter les doublons
                        defaults = {
                            'name': broker_asset.name,
                            'asset_type': broker_asset.asset_type or asset_type or 'UNKNOWN',
                            'market': raw_data.get('country_code', ''),
                            'currency': broker_asset.currency or 'USD',
                            'exchange': broker_asset.exchange or raw_data.get('exchange_id', ''),
                            'is_tradable': broker_asset.is_tradable,
                            # Champs spécifiques Saxo
                            'saxo_uic': uic,
                            'saxo_exchange_id': raw_data.get('exchange_id', ''),
                            'saxo_country_code': raw_data.get('country_code', ''),
                        }
                        
                        try:
                            all_asset, created = AllAssets.objects.get_or_create(
                                symbol=broker_asset.symbol,  # Le vrai symbole, pas "UIC_xxxx"
                                platform=platform,
                                defaults=defaults
                            )
                            
                            if not created:
                                # Mettre à jour l'asset existant avec les nouvelles données
                                update_fields = []
                                for field, value in defaults.items():
                                    current_value = getattr(all_asset, field, None)
                                    # Mettre à jour si la valeur actuelle est vide/None ou si la nouvelle valeur est meilleure
                                    if value and (not current_value or (isinstance(value, str) and value and not current_value)):
                                        setattr(all_asset, field, value)
                                        update_fields.append(field)
                                
                                if update_fields:
                                    all_asset.save(update_fields=update_fields)
                                    self.logger.info(
                                        f"Updated existing AllAsset from API for UIC {uic}: "
                                        f"{broker_asset.symbol} ({broker_asset.name}) - fields: {update_fields}"
                                    )
                            else:
                                self.logger.info(
                                    f"Created AllAsset from API for UIC {uic}: "
                                    f"{broker_asset.symbol} ({broker_asset.name})"
                                )
                            
                            return all_asset
                        except Exception as create_error:
                            # En cas d'erreur (race condition), essayer de récupérer l'asset existant
                            self.logger.warning(
                                f"Error during get_or_create for {broker_asset.symbol} ({platform}): {create_error}. "
                                f"Trying to get existing asset."
                            )
                            all_asset = AllAssets.objects.filter(
                                symbol=broker_asset.symbol,
                                platform=platform,
                            ).first()
                            
                            if all_asset:
                                # Mettre à jour avec les nouvelles données
                                update_fields = []
                                for field, value in defaults.items():
                                    current_value = getattr(all_asset, field, None)
                                    if value and (not current_value or (isinstance(value, str) and value and not current_value)):
                                        setattr(all_asset, field, value)
                                        update_fields.append(field)
                                
                                if update_fields:
                                    all_asset.save(update_fields=update_fields)
                                return all_asset
                            raise
            except Exception as e:
                self.logger.warning(
                    f"Failed to retrieve asset from API for UIC {uic}: {e}. "
                    f"Creating minimal AllAsset."
                )
        
        # 4. Si pas trouvé, créer un AllAsset minimal
        # L'utilisateur devra lancer une sync AllAssets pour enrichir les données
        self.logger.warning(
            f"AllAsset not found for {symbol} ({platform}). "
            f"Creating minimal AllAsset. Consider running asset sync first."
        )
        
        try:
            defaults = {
                'name': symbol,  # Nom par défaut = symbol
                'asset_type': asset_type or 'UNKNOWN',
                'market': '',
                'currency': 'USD',
                'is_tradable': True,
            }
            
            # Ajouter l'UIC si disponible (même si symbol = "UIC_xxxx")
            if platform == 'SAXO' and uic:
                defaults['saxo_uic'] = uic
            
            try:
                all_asset, created = AllAssets.objects.get_or_create(
                    symbol=symbol,
                    platform=platform,
                    defaults=defaults
                )
                
                if not created:
                    # Mettre à jour l'asset existant si nécessaire
                    update_fields = []
                    for field, value in defaults.items():
                        current_value = getattr(all_asset, field, None)
                        if value and (not current_value or (isinstance(value, str) and value and not current_value)):
                            setattr(all_asset, field, value)
                            update_fields.append(field)
                    
                    if update_fields:
                        all_asset.save(update_fields=update_fields)
                        self.logger.info(f"Updated existing minimal AllAsset for {symbol} ({platform})")
                else:
                    self.logger.info(f"Created minimal AllAsset for {symbol} ({platform})")
                
                return all_asset
            except Exception as create_error:
                # En cas d'erreur (race condition), essayer de récupérer l'asset existant
                self.logger.warning(
                    f"Error during get_or_create for {symbol} ({platform}): {create_error}. "
                    f"Trying to get existing asset."
                )
                all_asset = AllAssets.objects.filter(
                    symbol=symbol,
                    platform=platform,
                ).first()
                
                if all_asset:
                    # Mettre à jour avec les nouvelles données
                    update_fields = []
                    for field, value in defaults.items():
                        current_value = getattr(all_asset, field, None)
                        if value and (not current_value or (isinstance(value, str) and value and not current_value)):
                            setattr(all_asset, field, value)
                            update_fields.append(field)
                    
                    if update_fields:
                        all_asset.save(update_fields=update_fields)
                    return all_asset
                raise
        except Exception as e:
            self.logger.error(
                f"Failed to create/get AllAsset for {symbol} ({platform}): {str(e)}",
                exc_info=True
            )
            return None
    
    def _filter_trades_by_date(
        self,
        trades: List[BrokerTrade],
        cutoff_date: datetime,
    ) -> List[BrokerTrade]:
        """
        Filter trades by date.
        
        Args:
            trades: List of trades
            cutoff_date: Only include trades after this date
            
        Returns:
            Filtered list of trades
        """
        filtered = []
        
        for trade in trades:
            if trade.executed_at:
                try:
                    if isinstance(trade.executed_at, str):
                        trade_date = datetime.fromisoformat(
                            trade.executed_at.replace('Z', '+00:00')
                        )
                    else:
                        trade_date = trade.executed_at
                    
                    if trade_date >= cutoff_date:
                        filtered.append(trade)
                except (ValueError, TypeError):
                    # Include trades with invalid dates
                    filtered.append(trade)
            else:
                # Include trades without date
                filtered.append(trade)
        
        return filtered
    
    def _get_credentials(self, broker_account: BrokerAccount) -> Dict[str, Any]:
        """
        Get credentials from broker account.
        Utilise la méthode get_credentials_dict() du modèle.
        """
        # Utiliser la méthode du modèle qui gère déjà tout
        credentials = broker_account.get_credentials_dict()
        
        # Ajouter des informations supplémentaires si nécessaire
        credentials['user_id'] = broker_account.user.id
        if broker_account.account_id:
            credentials['account_id'] = broker_account.account_id
        
        return credentials
    
    def sync_recent(
        self,
        broker_account: BrokerAccount,
        hours: int = 24,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Sync only recent trades.
        
        Args:
            broker_account: BrokerAccount to sync from
            hours: Only sync trades from last N hours
            **kwargs: Additional parameters
            
        Returns:
            Dict with sync results
        """
        # Convert hours to days for since_days parameter
        since_days = max(1, hours // 24)
        
        return self.sync(
            broker_account=broker_account,
            since_days=since_days,
            **kwargs
        )

