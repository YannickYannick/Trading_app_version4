"""
AllAsset Price History Synchronization Service.

This service handles synchronization of price history for AllAssets
from external data providers (Yahoo Finance, brokers, etc.).

Only synchronizes AllAssets that are used in the system (referenced
in Asset, Trade, or Position) and have a validated Yahoo symbol.
"""
import logging
import math
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime, date
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from django.db.models import Q

from ...models import (
    AllAssets, AllAssetPriceHistory, Asset, Trade, Position, BrokerAccount
)
from ...brokers.factory import BrokerFactory
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
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """
        Convert value to float, handling None, NaN, and invalid values.
        Returns None if value cannot be converted to a valid float.
        
        Args:
            value: Value to convert (Decimal, int, str, float, None)
            
        Returns:
            Valid float or None if invalid
        """
        if value is None:
            return None
        try:
            # Convert to float (handles Decimal, int, str, etc.)
            f = float(value)
            # Check if it's NaN or infinity
            if math.isnan(f) or math.isinf(f):
                return None
            return f
        except (ValueError, TypeError):
            return None
    
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
        interval: str = '1d',
        fallback_to_broker: bool = True
    ) -> Dict[str, Any]:
        """
        Sync price history from Yahoo Finance for a specific AllAsset.
        If Yahoo fails and fallback_to_broker is True, tries broker (Saxo) as fallback.
        
        Args:
            all_asset: AllAssets instance to sync
            days: Number of days of history to fetch
            interval: Yahoo Finance interval ('1d', '1wk', '1mo')
            fallback_to_broker: If True, try broker if Yahoo fails
            
        Returns:
            Dict with sync results
        """
        # Si pas de symbole Yahoo valide, essayer directement le broker si c'est SAXO
        if not all_asset.symbole_yahoo or all_asset.symbole_yahoo in ['Not_searched', 'not_found', 'manual']:
            if fallback_to_broker and all_asset.platform == 'SAXO' and all_asset.saxo_uic:
                logger.info(f"No Yahoo symbol for {all_asset.symbol}, trying Saxo fallback directly...")
                return self.sync_from_saxo(all_asset, days=days)
            
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
                    # Filtrer les valeurs NaN/None avant stockage
                    open_price = self._safe_float(item['open'])
                    high_price = self._safe_float(item['high'])
                    low_price = self._safe_float(item['low'])
                    close_price = self._safe_float(item['close'])
                    volume = int(item.get('volume', 0) or 0)
                    
                    # Skip si tous les prix sont None/NaN (données invalides)
                    if all(p is None for p in [open_price, high_price, low_price, close_price]):
                        logger.warning(
                            f"Skipping invalid price data for {all_asset.symbol} on {date_str}: "
                            f"all prices are None/NaN"
                        )
                        continue
                    
                    price_dict[date_str] = {
                        'open': open_price,
                        'high': high_price,
                        'low': low_price,
                        'close': close_price,
                        'volume': volume,
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
            
            # Si Yahoo a échoué et que fallback est activé, essayer Saxo
            if fallback_to_broker and all_asset.platform == 'SAXO' and all_asset.saxo_uic:
                logger.info(f"Yahoo failed for {all_asset.symbol}, trying Saxo fallback...")
                try:
                    return self.sync_from_saxo(all_asset, days=days)
                except Exception as fallback_error:
                    logger.exception(f"Saxo fallback also failed for {all_asset.symbol}: {fallback_error}")
                    return {
                        'success': False,
                        'message': f'Yahoo failed: {str(e)}. Saxo fallback failed: {str(fallback_error)}',
                        'records': 0
                    }
            
            return {
                'success': False,
                'message': str(e),
                'records': 0
            }
    
    def sync_from_saxo(
        self,
        all_asset: AllAssets,
        days: int = 30,
        broker_account_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Sync price history from Saxo Bank for a specific AllAsset.
        
        Args:
            all_asset: AllAssets instance to sync (must have saxo_uic)
            days: Number of days of history to fetch
            broker_account_id: Optional broker account ID (if None, uses first active SAXO account)
            
        Returns:
            Dict with sync results
        """
        if all_asset.platform != 'SAXO':
            return {
                'success': False,
                'message': f'Asset {all_asset.symbol} is not a SAXO asset',
                'records': 0
            }
        
        if not all_asset.saxo_uic:
            return {
                'success': False,
                'message': f'No saxo_uic for {all_asset.symbol}',
                'records': 0
            }
        
        try:
            # Récupérer un BrokerAccount Saxo actif
            if broker_account_id:
                try:
                    broker_account = BrokerAccount.objects.get(
                        id=broker_account_id,
                        broker_type='SAXO',
                        is_active=True
                    )
                except BrokerAccount.DoesNotExist:
                    return {
                        'success': False,
                        'message': f'BrokerAccount {broker_account_id} not found or not active',
                        'records': 0
                    }
            else:
                # Chercher le premier compte SAXO actif pour l'utilisateur
                if not self.user:
                    return {
                        'success': False,
                        'message': 'No user specified and no broker_account_id provided',
                        'records': 0
                    }
                
                broker_account = BrokerAccount.objects.filter(
                    broker_type='SAXO',
                    user=self.user,
                    is_active=True
                ).first()
                
                if not broker_account:
                    return {
                        'success': False,
                        'message': f'No active SAXO account found for user {self.user.username}',
                        'records': 0
                    }
            
            # Créer une instance SaxoBroker
            from ...brokers.saxo import SaxoBroker
            
            credentials = broker_account.get_credentials()
            broker = BrokerFactory.create_broker('SAXO', self.user or broker_account.user, credentials)
            
            # S'assurer que le broker est authentifié
            if not broker.is_connected:
                if not broker.authenticate():
                    return {
                        'success': False,
                        'message': 'Failed to authenticate with Saxo Bank',
                        'records': 0
                    }
            
            # Récupérer l'historique des prix
            asset_type = all_asset.asset_type or 'Stock'
            historical_data = broker.get_historical_prices(
                uic=all_asset.saxo_uic,
                asset_type=asset_type,
                days=days,
                horizon=1  # Daily
            )
            
            if not historical_data:
                return {
                    'success': False,
                    'message': f'No historical data available from Saxo for UIC {all_asset.saxo_uic}',
                    'records': 0
                }
            
            # Construire le dictionnaire JSON pour stockage JSONB
            price_dict = {}
            records = 0
            
            for item in historical_data:
                try:
                    # Normaliser la date au format 'YYYY-MM-DD'
                    date_str = item['date']
                    if isinstance(date_str, str) and 'T' in date_str:
                        date_str = date_str.split('T')[0]
                    
                    # Convertir Decimal en float (ou None) pour JSONB
                    open_price = self._safe_float(item.get('open'))
                    high_price = self._safe_float(item.get('high'))
                    low_price = self._safe_float(item.get('low'))
                    close_price = self._safe_float(item.get('close'))
                    volume = int(item.get('volume', 0) or 0)
                    
                    # Skip si tous les prix sont None/NaN
                    if all(p is None for p in [open_price, high_price, low_price, close_price]):
                        logger.warning(
                            f"Skipping invalid Saxo price data for {all_asset.symbol} on {date_str}"
                        )
                        continue
                    
                    price_dict[date_str] = {
                        'open': open_price,
                        'high': high_price,
                        'low': low_price,
                        'close': close_price,
                        'volume': volume,
                        'source': 'SAXO'
                    }
                    records += 1
                except (ValueError, KeyError) as e:
                    logger.warning(f"Error processing Saxo price data for {all_asset.symbol} on {item.get('date', 'unknown')}: {e}")
                    continue
            
            if not price_dict:
                return {
                    'success': False,
                    'message': 'No valid price data retrieved from Saxo',
                    'records': 0
                }
            
            # Fusionner avec l'historique existant
            existing_history = all_asset.price_history_json or {}
            existing_history.update(price_dict)  # Les nouvelles données écrasent les anciennes
            
            # Sauvegarder dans le champ JSONB
            with transaction.atomic():
                all_asset.price_history_json = existing_history
                all_asset.price_history_days = len(existing_history)
                all_asset.price_history_updated_at = timezone.now()
                all_asset.save(update_fields=['price_history_json', 'price_history_days', 'price_history_updated_at'])
            
            logger.info(
                f"Synced {records} price records from Saxo for {all_asset.symbol} "
                f"(UIC: {all_asset.saxo_uic}, Total days: {len(existing_history)})"
            )
            
            return {
                'success': True,
                'message': f'Synced {records} price records from Saxo (Total: {len(existing_history)} days)',
                'records': records,
                'total_days': len(existing_history),
                'source': 'SAXO'
            }
            
        except Exception as e:
            logger.exception(f"Error syncing price history from Saxo for {all_asset.symbol}: {e}")
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
        # Pour SAXO, utiliser sync_from_saxo
        if all_asset.platform == 'SAXO':
            return self.sync_from_saxo(all_asset, days=days, broker_account_id=broker_account_id)
        
        # TODO: Implement other brokers (Binance, IB, etc.)
        logger.warning(
            f"Broker-based price history sync not yet implemented for {all_asset.platform}"
        )
        
        return {
            'success': False,
            'message': f'Broker sync not yet implemented for {all_asset.platform}',
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

