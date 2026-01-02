"""
AllAsset Price History Synchronization Service.

This service handles synchronization of price history for AllAssets
from external data providers (Yahoo Finance, brokers, etc.).

Only synchronizes AllAssets that are used in the system (referenced
in Asset, Trade, or Position) and have a validated Yahoo symbol.
"""
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime, date
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from django.db.models import Q

from ...models import (
    AllAssets, AllAssetPriceHistory, Asset, Trade, Position
)
from ..data_providers.yahoo_finance import YahooFinanceService

logger = logging.getLogger('trading.services.sync.all_asset_prices')


class AllAssetPriceSyncService:
    """
    Service for synchronizing price history for AllAssets.
    
    This service identifies AllAssets that need price history synchronization
    and fetches historical data from various sources (Yahoo Finance, brokers, etc.).
    
    Usage:
        service = AllAssetPriceSyncService()
        result = service.sync_all_asset_price_history(days=30)
    """
    
    def __init__(self, user: Optional[User] = None):
        """
        Initialize the AllAsset price sync service.
        
        Args:
            user: Django User instance (optional)
        """
        self.user = user
        self.yahoo_service = YahooFinanceService()
    
    def get_all_assets_to_sync(self) -> List[AllAssets]:
        """
        Identify AllAssets that should have their price history synchronized.
        
        An AllAsset is eligible for synchronization if:
        1. It is referenced in at least one Asset, Trade, or Position
        2. It has a validated Yahoo symbol (not 'Not_searched', 'not_found', 'manual')
        
        Returns:
            List of AllAssets to synchronize
        """
        # Get AllAsset IDs referenced in Asset, Trade, or Position
        asset_all_asset_ids = Asset.objects.filter(
            all_asset__isnull=False
        ).values_list('all_asset_id', flat=True).distinct()
        
        trade_all_asset_ids = Trade.objects.values_list(
            'all_asset_id', flat=True
        ).distinct()
        
        position_all_asset_ids = Position.objects.values_list(
            'all_asset_id', flat=True
        ).distinct()
        
        # Combine all IDs
        all_asset_ids = set(asset_all_asset_ids) | set(trade_all_asset_ids) | set(position_all_asset_ids)
        
        # Filter AllAssets that are used AND have validated Yahoo symbol
        all_assets = AllAssets.objects.filter(
            id__in=all_asset_ids,
            symbole_yahoo__not_in=['Not_searched', 'not_found', 'manual']
        ).exclude(symbole_yahoo='').distinct()
        
        logger.info(f"Found {all_assets.count()} AllAssets eligible for price history sync")
        return list(all_assets)
    
    def sync_from_yahoo_finance(
        self,
        all_asset: AllAssets,
        days: int = 30,
        interval: str = '1d'
    ) -> Dict[str, Any]:
        """
        Sync price history from Yahoo Finance for a specific AllAsset.
        
        Args:
            all_asset: AllAssets instance to sync
            days: Number of days of history to fetch
            interval: Yahoo Finance interval ('1d', '1wk', '1mo')
            
        Returns:
            Dict with sync results
        """
        if not all_asset.symbole_yahoo or all_asset.symbole_yahoo in ['Not_searched', 'not_found', 'manual']:
            return {
                'success': False,
                'message': f'No validated Yahoo symbol for {all_asset.symbol}',
                'records': 0
            }
        
        try:
            # Get historical data from Yahoo Finance
            yahoo_symbol = all_asset.symbole_yahoo
            historical_data = self.yahoo_service.get_historical_data(
                yahoo_symbol,
                days=days,
                interval=interval
            )
            
            if not historical_data:
                return {
                    'success': False,
                    'message': f'No historical data available for {yahoo_symbol}',
                    'records': 0
                }
            
            # Construire le dictionnaire JSON pour stockage JSONB
            # Format: {'YYYY-MM-DD': {'open': x, 'high': y, 'low': z, 'close': w, 'volume': v, 'source': 'YAHOO'}, ...}
            price_dict = {}
            records = 0
            
            for item in historical_data:
                try:
                    # Normaliser la date au format 'YYYY-MM-DD'
                    if isinstance(item['date'], str):
                        try:
                            price_date = datetime.strptime(item['date'], '%Y-%m-%d').date()
                        except ValueError:
                            price_date = datetime.fromisoformat(item['date'].replace('Z', '+00:00')).date()
                    else:
                        price_date = item['date']
                    
                    date_str = price_date.strftime('%Y-%m-%d')
                    
                    # Construire l'objet de prix pour cette date
                    price_dict[date_str] = {
                        'open': float(item['open']),
                        'high': float(item['high']),
                        'low': float(item['low']),
                        'close': float(item['close']),
                        'volume': int(item.get('volume', 0) or 0),
                        'source': 'YAHOO'
                    }
                    records += 1
                except (ValueError, KeyError) as e:
                    logger.warning(f"Error processing price data for {all_asset.symbol} on {item.get('date', 'unknown')}: {e}")
                    continue
            
            # Fusionner avec l'historique existant (garder les données existantes si pas de doublon)
            existing_history = all_asset.price_history_json or {}
            existing_history.update(price_dict)  # Les nouvelles données écrasent les anciennes pour les mêmes dates
            
            # Sauvegarder dans le champ JSONB
            with transaction.atomic():
                all_asset.price_history_json = existing_history
                all_asset.price_history_days = len(existing_history)
                all_asset.price_history_updated_at = timezone.now()
                all_asset.save(update_fields=['price_history_json', 'price_history_days', 'price_history_updated_at'])
            
            logger.info(
                f"Synced {records} price records for {all_asset.symbol} "
                f"(Yahoo: {yahoo_symbol}, Total days: {len(existing_history)})"
            )
            
            return {
                'success': True,
                'message': f'Synced {records} price records (Total: {len(existing_history)} days)',
                'records': records,
                'total_days': len(existing_history),
                'yahoo_symbol': yahoo_symbol
            }
            
        except Exception as e:
            logger.exception(f"Error syncing price history for {all_asset.symbol}: {e}")
            return {
                'success': False,
                'message': str(e),
                'records': 0
            }
    
    def sync_from_broker(
        self,
        all_asset: AllAssets,
        broker_account_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Sync price history from a broker for a specific AllAsset.
        
        Args:
            all_asset: AllAssets instance to sync
            broker_account_id: Optional broker account ID
            days: Number of days of history to fetch
            
        Returns:
            Dict with sync results
        """
        # TODO: Implement broker-based price history sync
        # This would require broker-specific implementations
        # (e.g., Saxo historical prices, Binance klines, etc.)
        
        logger.warning(
            f"Broker-based price history sync not yet implemented for {all_asset.symbol}"
        )
        
        return {
            'success': False,
            'message': 'Broker-based sync not yet implemented',
            'records': 0
        }
    
    def sync_all_asset_price_history(
        self,
        days: int = 30,
        source: str = 'YAHOO',
        all_asset_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Sync price history for AllAssets.
        
        Args:
            days: Number of days of history to fetch
            source: Source to sync from ('YAHOO', 'SAXO', 'BINANCE', etc.)
            all_asset_id: Optional specific AllAsset ID to sync (if None, syncs all eligible)
            
        Returns:
            Dict with sync results
        """
        try:
            if all_asset_id:
                # Sync specific AllAsset
                try:
                    all_asset = AllAssets.objects.get(id=all_asset_id)
                    all_assets = [all_asset]
                except AllAssets.DoesNotExist:
                    return {
                        'success': False,
                        'message': f'AllAsset {all_asset_id} not found',
                        'synced': 0,
                        'failed': 0,
                        'total_records': 0
                    }
            else:
                # Get all eligible AllAssets
                all_assets = self.get_all_assets_to_sync()
            
            if not all_assets:
                return {
                    'success': True,
                    'message': 'No AllAssets to sync',
                    'synced': 0,
                    'failed': 0,
                    'total_records': 0
                }
            
            synced_count = 0
            failed_count = 0
            total_records = 0
            failed_assets = []
            
            for all_asset in all_assets:
                if source == 'YAHOO':
                    result = self.sync_from_yahoo_finance(all_asset, days=days)
                else:
                    result = self.sync_from_broker(all_asset, days=days)
                
                if result['success']:
                    synced_count += 1
                    total_records += result.get('records', 0)
                else:
                    failed_count += 1
                    failed_assets.append({
                        'id': all_asset.id,
                        'symbol': all_asset.symbol,
                        'error': result.get('message', 'Unknown error')
                    })
            
            logger.info(
                f"Price history sync completed: {synced_count} synced, "
                f"{failed_count} failed, {total_records} total records"
            )
            
            return {
                'success': True,
                'message': f'Synced {synced_count} AllAssets, {failed_count} failed',
                'synced': synced_count,
                'failed': failed_count,
                'total_records': total_records,
                'failed_assets': failed_assets
            }
            
        except Exception as e:
            logger.exception(f"Error in sync_all_asset_price_history: {e}")
            return {
                'success': False,
                'message': str(e),
                'synced': 0,
                'failed': 0,
                'total_records': 0
            }

