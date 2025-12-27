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
from ...brokers.base import BrokerTrade
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
        limit: int = 50,
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
                broker_account=broker_account,
            ).first()
            
            if existing:
                return {'skipped': True, 'trade_id': existing.id}
        
        # Find or create asset
        asset = self._get_or_create_asset(
            symbol=broker_trade.symbol,
            broker_type=broker_account.get_broker_type(),
        )
        
        if not asset:
            raise ValueError(f"Could not find or create asset: {broker_trade.symbol}")
        
        # Try to find related position
        position = self._find_related_position(
            broker_account=broker_account,
            asset=asset,
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
        
        # Create trade
        trade = Trade.objects.create(
            user=self.user,
            broker_account=broker_account,
            broker=broker_account.broker,
            asset=asset,
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
        asset: Asset,
        trade_type: str,
    ) -> Optional[Position]:
        """
        Find a related position for a trade.
        
        Args:
            broker_account: BrokerAccount
            asset: Asset for the trade
            trade_type: 'BUY' or 'SELL'
            
        Returns:
            Position or None
        """
        # Find open position for this asset
        position = Position.objects.filter(
            user=self.user,
            broker_account=broker_account,
            asset=asset,
            is_open=True,
        ).first()
        
        return position
    
    def _get_or_create_asset(
        self,
        symbol: str,
        broker_type: str,
    ) -> Optional[Asset]:
        """
        Get or create an asset for the given symbol.
        
        Args:
            symbol: Asset symbol
            broker_type: Type of broker
            
        Returns:
            Asset instance or None
        """
        # First try to find existing asset
        asset = Asset.objects.filter(symbol=symbol).first()
        if asset:
            return asset
        
        # Try to find in AllAssets
        platform = broker_type.upper()
        all_asset = AllAssets.objects.filter(
            symbol=symbol,
            platform=platform,
        ).first()
        
        if all_asset:
            asset = Asset.objects.create(
                all_asset=all_asset,
                symbol=all_asset.symbol,
                name=all_asset.name,
                asset_type=all_asset.asset_type,
                currency=all_asset.currency,
            )
            return asset
        
        # Create basic asset
        asset = Asset.objects.create(
            symbol=symbol,
            name=symbol,
            asset_type='UNKNOWN',
            currency='USD',
        )
        
        return asset
    
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

