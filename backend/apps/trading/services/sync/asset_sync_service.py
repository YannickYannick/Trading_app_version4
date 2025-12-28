"""
Asset Synchronization Service.

This service handles synchronization of assets from brokers
to the local AllAssets catalog.
"""
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from ...brokers.factory import BrokerFactory
from ...brokers.base import BrokerAsset
from ...models import BrokerAccount, BrokerSyncLog, AllAssets, Asset

logger = logging.getLogger('trading.services.sync.assets')


class AssetSyncService:
    """
    Service for synchronizing assets from brokers.
    
    This service fetches assets from broker APIs and stores them
    in the AllAssets catalog for universal asset lookup.
    
    Usage:
        service = AssetSyncService(user)
        result = service.sync_assets(broker_account, asset_type='Stock')
    """
    
    def __init__(self, user: User):
        """
        Initialize the asset sync service.
        
        Args:
            user: Django User instance
        """
        self.user = user
    
    @transaction.atomic
    def sync_assets(
        self,
        broker_account: BrokerAccount,
        asset_type: str = 'Stock',
        keywords: str = '',
        limit: int = 1000,
        update_existing: bool = True
    ) -> Dict[str, Any]:
        """
        Sync assets from a broker to the database.
        
        Args:
            broker_account: BrokerAccount model instance
            asset_type: Type of asset to sync
            keywords: Search keywords (optional)
            limit: Maximum number of assets to sync
            update_existing: Whether to update existing assets
            
        Returns:
            Dict with sync results
        """
        sync_log = None
        try:
            # Get broker instance
            credentials = self._get_credentials(broker_account)
            broker_type = broker_account.get_broker_type()
            broker = BrokerFactory.create_broker(broker_type, self.user, credentials)
            
            # Authenticate
            if not broker.authenticate():
                error_msg = broker.last_error or "Authentication failed"
                self._log_sync(broker_account, 'assets', 'error', error_message=error_msg)
                return {
                    'success': False,
                    'message': error_msg,
                    'created': 0,
                    'updated': 0,
                    'errors': [],
                }
            
            # Fetch assets from broker
            broker_assets = broker.get_assets(
                asset_type=asset_type,
                keywords=keywords,
                limit=limit
            )
            
            if not broker_assets:
                self._log_sync(
                    broker_account, 'assets', 'success',
                    details={'message': 'No assets found'}
                )
                return {
                    'success': True,
                    'message': 'No assets found in broker',
                    'created': 0,
                    'updated': 0,
                    'errors': [],
                }
            
            # Process assets
            created = 0
            updated = 0
            errors = []
            platform = broker_account.get_broker_type().upper()
            
            for broker_asset in broker_assets:
                try:
                    result = self._process_asset(broker_asset, platform, update_existing)
                    if result == 'created':
                        created += 1
                    elif result == 'updated':
                        updated += 1
                except Exception as e:
                    errors.append({
                        'symbol': broker_asset.symbol,
                        'error': str(e),
                    })
                    logger.warning(f"Error processing asset {broker_asset.symbol}: {e}")
            
            # Log the sync
            self._log_sync(
                broker_account, 'assets', 'success',
                records_synced=created + updated,
                details={
                    'asset_type': asset_type,
                    'created': created,
                    'updated': updated,
                    'errors_count': len(errors),
                }
            )
            
            return {
                'success': True,
                'message': f'Synced {created + updated} assets ({created} created, {updated} updated)',
                'created': created,
                'updated': updated,
                'errors': errors,
            }
            
        except Exception as e:
            logger.exception(f"Error syncing assets: {e}")
            self._log_sync(broker_account, 'assets', 'error', error_message=str(e))
            return {
                'success': False,
                'message': str(e),
                'created': 0,
                'updated': 0,
                'errors': [{'error': str(e)}],
            }
    
    def _process_asset(
        self,
        broker_asset: BrokerAsset,
        platform: str,
        update_existing: bool
    ) -> str:
        """
        Process a single asset.
        
        Args:
            broker_asset: BrokerAsset from broker
            platform: Platform identifier
            update_existing: Whether to update if exists
            
        Returns:
            'created', 'updated', or 'skipped'
        """
        defaults = {
            'name': broker_asset.name,
            'asset_type': broker_asset.asset_type,
            'exchange': broker_asset.exchange,
            'currency': broker_asset.currency,
            'is_tradable': broker_asset.is_tradable,
        }
        
        # Add broker-specific fields
        if platform == 'SAXO' and broker_asset.broker_id:
            try:
                defaults['saxo_uic'] = int(broker_asset.broker_id)
            except (ValueError, TypeError):
                pass
        
        # Check if exists
        existing = AllAssets.objects.filter(
            symbol=broker_asset.symbol,
            platform=platform
        ).first()
        
        if existing:
            if update_existing:
                for key, value in defaults.items():
                    setattr(existing, key, value)
                existing.save()
                return 'updated'
            return 'skipped'
        else:
            AllAssets.objects.create(
                symbol=broker_asset.symbol,
                platform=platform,
                **defaults
            )
            return 'created'
    
    @transaction.atomic
    def sync_all_asset_types(
        self,
        broker_account: BrokerAccount,
        limit_per_type: int = 500
    ) -> Dict[str, Any]:
        """
        Sync all asset types from a broker.
        
        Args:
            broker_account: BrokerAccount model instance
            limit_per_type: Max assets per type
            
        Returns:
            Dict with aggregated sync results
        """
        broker_type = broker_account.get_broker_type().upper()
        
        # Define asset types based on broker
        if broker_type == 'SAXO':
            asset_types = ['Stock', 'ETF', 'FX', 'CFD']
        elif broker_type == 'BINANCE':
            asset_types = ['Crypto']
        else:
            asset_types = ['Stock']
        
        total_created = 0
        total_updated = 0
        all_errors = []
        results_by_type = {}
        
        for asset_type in asset_types:
            result = self.sync_assets(
                broker_account,
                asset_type=asset_type,
                limit=limit_per_type
            )
            
            total_created += result.get('created', 0)
            total_updated += result.get('updated', 0)
            all_errors.extend(result.get('errors', []))
            results_by_type[asset_type] = result
        
        return {
            'success': True,
            'message': f'Synced {total_created + total_updated} assets across {len(asset_types)} types',
            'total_created': total_created,
            'total_updated': total_updated,
            'errors': all_errors,
            'by_type': results_by_type,
        }
    
    def search_and_sync(
        self,
        broker_account: BrokerAccount,
        keywords: str,
        asset_type: str = 'Stock',
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Search for assets and sync matching ones.
        
        Args:
            broker_account: BrokerAccount model instance
            keywords: Search keywords
            asset_type: Type of asset
            limit: Max results
            
        Returns:
            Dict with sync results and matched assets
        """
        result = self.sync_assets(
            broker_account,
            asset_type=asset_type,
            keywords=keywords,
            limit=limit
        )
        
        # Get the synced assets from database
        platform = broker_account.get_broker_type().upper()
        synced_assets = AllAssets.objects.filter(
            platform=platform,
            symbol__icontains=keywords
        )[:limit]
        
        result['synced_assets'] = list(synced_assets.values(
            'id', 'symbol', 'name', 'asset_type', 'currency'
        ))
        
        return result
    
    def _get_credentials(self, broker_account: BrokerAccount) -> Dict[str, Any]:
        """Get credentials from broker account."""
        credentials = {}
        
        if broker_account.api_key:
            credentials['api_key'] = broker_account.api_key
        if broker_account.api_secret:
            credentials['api_secret'] = broker_account.api_secret
        if broker_account.client_id:
            credentials['client_id'] = broker_account.client_id
        if broker_account.client_secret:
            credentials['client_secret'] = broker_account.client_secret
        if broker_account.access_token:
            credentials['access_token'] = broker_account.access_token
        if broker_account.refresh_token:
            credentials['refresh_token'] = broker_account.refresh_token
        if broker_account.token_expires_at:
            credentials['token_expires_at'] = broker_account.token_expires_at.isoformat()
        if broker_account.extra_credentials:
            credentials.update(broker_account.extra_credentials)
        
        # Environment settings
        broker_type = broker_account.get_broker_type().upper()
        if broker_type == 'SAXO':
            credentials['environment'] = 'simulation' if broker_account.is_sandbox else 'live'
        elif broker_type == 'BINANCE':
            credentials['testnet'] = broker_account.is_sandbox
        
        return credentials
    
    def _log_sync(
        self,
        broker_account: BrokerAccount,
        sync_type: str,
        status: str,
        records_synced: int = 0,
        error_message: str = '',
        details: Optional[Dict] = None
    ) -> BrokerSyncLog:
        """Log a sync operation."""
        return BrokerSyncLog.objects.create(
            broker_account=broker_account,
            sync_type=sync_type,
            status=status,
            records_synced=records_synced,
            error_message=error_message,
            details=details or {},
        )

