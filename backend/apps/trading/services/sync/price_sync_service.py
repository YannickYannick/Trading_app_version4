"""
Price Synchronization Service.

This service handles synchronization of asset prices from brokers
and external data providers (Yahoo Finance, etc.).
"""
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime, date, timedelta
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from ...brokers.factory import BrokerFactory
from ...models import BrokerAccount, BrokerSyncLog, Asset, AssetPrice, AllAssets

logger = logging.getLogger('trading.services.sync.prices')


class PriceSyncService:
    """
    Service for synchronizing asset prices.
    
    This service fetches current and historical prices from brokers
    and external data sources, storing them in the database.
    
    Usage:
        service = PriceSyncService(user)
        result = service.sync_current_prices(broker_account, ['AAPL', 'GOOGL'])
    """
    
    def __init__(self, user: Optional[User] = None):
        """
        Initialize the price sync service.
        
        Args:
            user: Django User instance (optional for price-only operations)
        """
        self.user = user
    
    def sync_current_prices(
        self,
        broker_account: BrokerAccount,
        symbols: Optional[List[str]] = None,
        asset_type: str = 'Stock'
    ) -> Dict[str, Any]:
        """
        Sync current prices from a broker.
        
        Args:
            broker_account: BrokerAccount model instance
            symbols: List of symbols to update (None = all assets)
            asset_type: Type of asset
            
        Returns:
            Dict with sync results
        """
        try:
            # Get broker instance
            credentials = self._get_credentials(broker_account)
            broker_type = broker_account.broker.broker_type
            broker = BrokerFactory.create_broker(broker_type, self.user, credentials)
            
            if not broker.authenticate():
                error_msg = broker.last_error or "Authentication failed"
                return {'success': False, 'message': error_msg, 'updated': 0}
            
            # Get symbols to update
            if symbols is None:
                platform = broker_account.broker.broker_type.upper()
                assets = Asset.objects.filter(
                    all_asset__platform=platform
                ).values_list('symbol', flat=True)
                symbols = list(assets[:100])  # Limit to 100 at a time
            
            if not symbols:
                return {'success': True, 'message': 'No symbols to update', 'updated': 0}
            
            # Get prices
            prices = broker.get_multiple_prices(symbols)
            
            # Update assets
            updated = 0
            for symbol, price in prices.items():
                if price is not None:
                    Asset.objects.filter(symbol=symbol).update(
                        current_price=price,
                        price_updated_at=timezone.now()
                    )
                    updated += 1
            
            # Log the sync
            self._log_sync(
                broker_account, 'prices', 'success',
                records_synced=updated,
                details={'symbols_requested': len(symbols), 'symbols_updated': updated}
            )
            
            return {
                'success': True,
                'message': f'Updated {updated} prices',
                'updated': updated,
                'prices': {k: str(v) for k, v in prices.items() if v is not None},
            }
            
        except Exception as e:
            logger.exception(f"Error syncing prices: {e}")
            return {'success': False, 'message': str(e), 'updated': 0}
    
    def sync_single_price(
        self,
        broker_account: BrokerAccount,
        symbol: str,
        **kwargs
    ) -> Optional[Decimal]:
        """
        Get and sync price for a single asset.
        
        Args:
            broker_account: BrokerAccount model instance
            symbol: Asset symbol
            **kwargs: Additional parameters
            
        Returns:
            Current price or None
        """
        try:
            credentials = self._get_credentials(broker_account)
            broker_type = broker_account.broker.broker_type
            broker = BrokerFactory.create_broker(broker_type, self.user, credentials)
            
            if not broker.authenticate():
                return None
            
            price = broker.get_asset_price(symbol, **kwargs)
            
            if price is not None:
                Asset.objects.filter(symbol=symbol).update(
                    current_price=price,
                    price_updated_at=timezone.now()
                )
            
            return price
            
        except Exception as e:
            logger.error(f"Error syncing single price: {e}")
            return None
    
    @transaction.atomic
    def sync_historical_prices(
        self,
        broker_account: BrokerAccount,
        symbol: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Sync historical prices for an asset.
        
        Note: This requires broker support for historical data.
        For Binance, this uses the klines endpoint.
        
        Args:
            broker_account: BrokerAccount model instance
            symbol: Asset symbol
            days: Number of days of history
            
        Returns:
            Dict with sync results
        """
        try:
            credentials = self._get_credentials(broker_account)
            broker_type = broker_account.broker.broker_type
            broker = BrokerFactory.create_broker(broker_type, self.user, credentials)
            
            if not broker.authenticate():
                return {'success': False, 'message': 'Authentication failed', 'records': 0}
            
            # Get asset
            asset = Asset.objects.filter(symbol=symbol).first()
            if not asset:
                return {'success': False, 'message': f'Asset not found: {symbol}', 'records': 0}
            
            # Get historical data (Binance-specific for now)
            if broker_type.upper() == 'BINANCE' and hasattr(broker, 'get_klines'):
                klines = broker.get_klines(symbol, interval='1d', limit=days)
                
                if not klines:
                    return {'success': False, 'message': 'No historical data', 'records': 0}
                
                records = 0
                for kline in klines:
                    price_date = datetime.fromtimestamp(kline['open_time'] / 1000).date()
                    
                    AssetPrice.objects.update_or_create(
                        asset=asset,
                        date=price_date,
                        defaults={
                            'open_price': kline['open'],
                            'high_price': kline['high'],
                            'low_price': kline['low'],
                            'close_price': kline['close'],
                            'volume': kline['volume'],
                        }
                    )
                    records += 1
                
                return {
                    'success': True,
                    'message': f'Synced {records} historical prices',
                    'records': records,
                }
            
            return {
                'success': False,
                'message': f'Historical data not supported for {broker_type}',
                'records': 0,
            }
            
        except Exception as e:
            logger.exception(f"Error syncing historical prices: {e}")
            return {'success': False, 'message': str(e), 'records': 0}
    
    def update_all_asset_prices(
        self,
        broker_account: BrokerAccount,
        batch_size: int = 50
    ) -> Dict[str, Any]:
        """
        Update prices for all assets associated with a broker.
        
        Args:
            broker_account: BrokerAccount model instance
            batch_size: Number of assets to update per batch
            
        Returns:
            Dict with sync results
        """
        platform = broker_account.broker.broker_type.upper()
        
        # Get all assets for this platform
        assets = Asset.objects.filter(
            all_asset__platform=platform
        ).values_list('symbol', flat=True)
        
        all_symbols = list(assets)
        total_updated = 0
        errors = []
        
        # Process in batches
        for i in range(0, len(all_symbols), batch_size):
            batch = all_symbols[i:i + batch_size]
            result = self.sync_current_prices(broker_account, symbols=batch)
            
            if result.get('success'):
                total_updated += result.get('updated', 0)
            else:
                errors.append({
                    'batch': i // batch_size,
                    'error': result.get('message'),
                })
        
        return {
            'success': len(errors) == 0,
            'message': f'Updated {total_updated} of {len(all_symbols)} assets',
            'total_assets': len(all_symbols),
            'updated': total_updated,
            'errors': errors,
        }
    
    def get_price_with_fallback(
        self,
        symbol: str,
        broker_accounts: List[BrokerAccount]
    ) -> Optional[Decimal]:
        """
        Get price trying multiple broker accounts as fallback.
        
        Args:
            symbol: Asset symbol
            broker_accounts: List of broker accounts to try
            
        Returns:
            Price from first successful broker
        """
        for broker_account in broker_accounts:
            try:
                price = self.sync_single_price(broker_account, symbol)
                if price is not None:
                    return price
            except Exception as e:
                logger.warning(f"Failed to get price from {broker_account.broker.name}: {e}")
                continue
        
        return None
    
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
        
        broker_type = broker_account.broker.broker_type.upper()
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

