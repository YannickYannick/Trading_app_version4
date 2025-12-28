"""
Position Synchronization Service.

This service synchronizes positions from brokers to the local database.
"""
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from .base_sync_service import BaseSyncService
from ...brokers.factory import BrokerFactory
from ...brokers.base import BrokerPosition
from ...models import BrokerAccount, Position, Asset, AllAssets, Broker
from ...exceptions import SyncException, SyncAuthenticationError

logger = logging.getLogger('trading.services.sync.positions')


class PositionSyncService(BaseSyncService):
    """
    Service for synchronizing positions from brokers.
    
    Features:
    - Sync positions from any supported broker
    - Create/update local Position records
    - Close positions that no longer exist on broker
    - Calculate P&L for synced positions
    
    Usage:
        service = PositionSyncService(user)
        result = service.sync(broker_account)
    """
    
    SYNC_TYPE = 'positions'
    
    def sync(
        self,
        broker_account: BrokerAccount,
        close_missing: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Sync positions from a broker.
        
        Args:
            broker_account: BrokerAccount to sync from
            close_missing: Whether to close positions not found on broker
            **kwargs: Additional parameters
            
        Returns:
            Dict with sync results
        """
        self._log_start(
            f"Starting position sync for {broker_account.broker.name}",
            broker=broker_account.broker.name
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
            
            # Fetch positions from broker
            broker_positions = broker.get_positions()
            
            self.logger.info(
                f"Retrieved {len(broker_positions)} positions from {broker_type}"
            )
            
            # Sync positions to database
            with transaction.atomic():
                result = self._sync_positions(
                    broker_account=broker_account,
                    broker_positions=broker_positions,
                    close_missing=close_missing,
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
            self._log_error("Position sync failed", error=e)
            
            self._create_sync_log(
                broker_account=broker_account,
                status='error',
                error_message=str(e),
            )
            
            raise SyncException(
                message=f"Position sync failed: {str(e)}",
                sync_type=self.SYNC_TYPE,
            )
    
    def _sync_positions(
        self,
        broker_account: BrokerAccount,
        broker_positions: List[BrokerPosition],
        close_missing: bool = True,
    ) -> Dict[str, Any]:
        """
        Sync positions to database.
        
        Args:
            broker_account: BrokerAccount being synced
            broker_positions: List of positions from broker
            close_missing: Whether to close missing positions
            
        Returns:
            Dict with sync statistics
        """
        created = 0
        updated = 0
        closed = 0
        
        # Track which positions we've seen
        seen_position_ids = set()
        
        for broker_pos in broker_positions:
            try:
                result = self._sync_single_position(
                    broker_account=broker_account,
                    broker_position=broker_pos,
                )
                
                if result.get('created'):
                    created += 1
                elif result.get('updated'):
                    updated += 1
                
                if result.get('position_id'):
                    seen_position_ids.add(result['position_id'])
                    
            except Exception as e:
                self._log_error(
                    f"Failed to sync position {broker_pos.symbol}",
                    error=e,
                    symbol=broker_pos.symbol
                )
        
        # Close positions that no longer exist on broker
        if close_missing:
            closed = self._close_missing_positions(
                broker_account=broker_account,
                seen_position_ids=seen_position_ids,
            )
        
        return self._build_result(
            success=len(self._errors) == 0,
            created=created,
            updated=updated,
            deleted=closed,
            closed=closed,
        )
    
    def _sync_single_position(
        self,
        broker_account: BrokerAccount,
        broker_position: BrokerPosition,
    ) -> Dict[str, Any]:
        """
        Sync a single position.
        
        Args:
            broker_account: BrokerAccount being synced
            broker_position: Position data from broker
            
        Returns:
            Dict with result info
        """
        # Find or create asset
        asset = self._get_or_create_asset(
            symbol=broker_position.symbol,
            broker_type=broker_account.get_broker_type(),
        )
        
        if not asset:
            raise ValueError(f"Could not find or create asset: {broker_position.symbol}")
        
        # Determine broker position ID
        broker_position_id = broker_position.broker_position_id or f"{broker_account.get_broker_type()}_{broker_position.symbol}"
        
        # Convert side
        side = 'BUY' if broker_position.side == 'LONG' else 'SELL'
        
        # Create or update position
        position, created = Position.objects.update_or_create(
            user=self.user,
            broker=broker_account.broker,
            asset=asset,
            is_open=True,
            defaults={
                'quantity': broker_position.quantity,
                'entry_price': broker_position.entry_price,
                'current_price': broker_position.current_price,
                'side': side,
            }
        )
        
        # Update calculated fields
        position.current_price = broker_position.current_price
        position.unrealized_pnl = broker_position.pnl
        position.save()
        
        return {
            'created': created,
            'updated': not created,
            'position_id': position.id,
        }
    
    def _close_missing_positions(
        self,
        broker_account: BrokerAccount,
        seen_position_ids: set,
    ) -> int:
        """
        Close positions that no longer exist on broker.
        
        Args:
            broker_account: BrokerAccount being synced
            seen_position_ids: Set of position IDs that still exist
            
        Returns:
            Number of positions closed
        """
        # Get open positions for this broker account
        open_positions = Position.objects.filter(
            user=self.user,
            broker=broker_account.broker,
            is_open=True,
        ).exclude(id__in=seen_position_ids)
        
        count = open_positions.count()
        
        if count > 0:
            # Mark as closed
            open_positions.update(
                is_open=False,
                closed_at=timezone.now(),
            )
            
            self._log_warning(
                f"Closed {count} positions not found on broker",
                count=count
            )
        
        return count
    
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
            # Create Asset from AllAssets
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
    
    def sync_for_all_accounts(self) -> Dict[str, Any]:
        """
        Sync positions for all user's broker accounts.
        
        Returns:
            Dict with aggregated results
        """
        accounts = BrokerAccount.objects.filter(
            user=self.user,
            is_active=True,
        )
        
        total_created = 0
        total_updated = 0
        total_closed = 0
        account_results = {}
        
        for account in accounts:
            try:
                result = self.sync(account)
                account_results[account.account_name or account.account_id] = result
                
                total_created += result.get('created', 0)
                total_updated += result.get('updated', 0)
                total_closed += result.get('closed', 0)
                
            except Exception as e:
                self._log_error(
                    f"Failed to sync account {account.account_id}",
                    error=e
                )
                account_results[account.account_name or account.account_id] = {
                    'success': False,
                    'error': str(e),
                }
        
        return {
            'success': len(self._errors) == 0,
            'total_created': total_created,
            'total_updated': total_updated,
            'total_closed': total_closed,
            'accounts': len(accounts),
            'results': account_results,
        }

