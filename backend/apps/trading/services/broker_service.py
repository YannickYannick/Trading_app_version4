"""
Broker Service - High-level service for broker operations.

This service provides a unified interface for interacting with
different brokers through the factory pattern.
"""
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction

from ..brokers.factory import BrokerFactory
from ..brokers.base import (
    BrokerBase,
    BrokerAsset,
    BrokerPosition,
    BrokerTrade,
    BrokerOrder,
    OrderResult,
    BrokerError,
)
from ..models import (
    BrokerAccount,
    BrokerSyncLog,
    AllAssets,
    Asset,
    Position,
    Trade,
    Order,
)

logger = logging.getLogger('trading.services.broker')


class BrokerServiceError(Exception):
    """Base exception for broker service errors."""
    pass


class BrokerService:
    """
    High-level service for broker operations.
    
    This service provides a unified interface for:
    - Managing broker connections
    - Retrieving data from brokers
    - Placing and managing orders
    - Synchronizing broker data with local database
    
    Usage:
        service = BrokerService(user)
        
        # Test connection
        result = service.test_connection(broker_account)
        
        # Get assets
        assets = service.get_assets(broker_account, keywords='AAPL')
        
        # Place order
        result = service.place_order(broker_account, 'AAPL', 'BUY', 10)
    """
    
    def __init__(self, user: User):
        """
        Initialize the broker service.
        
        Args:
            user: Django User instance
        """
        self.user = user
        self._broker_cache: Dict[int, BrokerBase] = {}
    
    # ============================================
    # BROKER INSTANCE MANAGEMENT
    # ============================================
    
    def get_broker_instance(
        self,
        broker_account: BrokerAccount,
        use_cache: bool = True
    ) -> BrokerBase:
        """
        Get a broker instance for a broker account.
        
        Args:
            broker_account: BrokerAccount model instance
            use_cache: Whether to use cached instance
            
        Returns:
            BrokerBase instance
        """
        # Check cache
        if use_cache and broker_account.id in self._broker_cache:
            return self._broker_cache[broker_account.id]
        
        # Get credentials from broker account
        credentials = self._get_credentials_from_account(broker_account)
        
        # Get broker type - utiliser la méthode du modèle
        broker_type = broker_account.get_broker_type()
        
        # Normaliser en minuscules pour le factory (saxo, binance, etc.)
        broker_type_lower = broker_type.lower() if broker_type else None
        
        # Create broker instance
        broker = BrokerFactory.create_broker(broker_type_lower, self.user, credentials)
        
        # Cache the instance
        if use_cache:
            self._broker_cache[broker_account.id] = broker
        
        return broker
    
    def _get_credentials_from_account(self, broker_account: BrokerAccount) -> Dict[str, Any]:
        """
        Extract credentials from a broker account.
        
        Utilise la méthode get_credentials_dict() du modèle qui gère déjà
        tous les cas (Saxo, Binance, etc.) de manière cohérente.
        
        Args:
            broker_account: BrokerAccount model instance
            
        Returns:
            Dictionary of credentials
        """
        # Utiliser la méthode du modèle qui gère déjà tout
        credentials = broker_account.get_credentials_dict()
        
        # Ajouter des informations supplémentaires si nécessaire
        credentials['user_id'] = broker_account.user.id
        if broker_account.account_id:
            credentials['account_id'] = broker_account.account_id
        
        # S'assurer que l'environnement est défini
        if 'environment' not in credentials:
            credentials['environment'] = broker_account.environment or 'simulation'
        
        return credentials
    
    def clear_cache(self) -> None:
        """Clear the broker instance cache."""
        self._broker_cache.clear()
    
    # ============================================
    # CONNECTION TESTING
    # ============================================
    
    def test_connection(self, broker_account: BrokerAccount) -> Dict[str, Any]:
        """
        Test connection to a broker.
        
        Args:
            broker_account: BrokerAccount model instance
            
        Returns:
            Dict with 'success', 'message', and optional 'error'
        """
        try:
            broker = self.get_broker_instance(broker_account, use_cache=False)
            success = broker.test_connection()
            
            # Log the sync attempt
            self._log_sync(
                broker_account=broker_account,
                sync_type='connection_test',
                status='success' if success else 'error',
                error_message=broker.last_error if not success else '',
            )
            
            return {
                'success': success,
                'message': 'Connection successful' if success else 'Connection failed',
                'error': broker.last_error if not success else None,
                'broker_name': broker.BROKER_NAME,
            }
            
        except BrokerError as e:
            logger.error(f"Broker error testing connection: {e}")
            self._log_sync(
                broker_account=broker_account,
                sync_type='connection_test',
                status='error',
                error_message=str(e),
            )
            return {
                'success': False,
                'message': 'Connection failed',
                'error': str(e),
            }
        except Exception as e:
            logger.exception(f"Unexpected error testing connection: {e}")
            return {
                'success': False,
                'message': 'Unexpected error',
                'error': str(e),
            }
    
    # ============================================
    # ASSETS
    # ============================================
    
    def get_assets(
        self,
        broker_account: BrokerAccount,
        asset_type: str = 'Stock',
        keywords: str = '',
        limit: int = 100
    ) -> List[BrokerAsset]:
        """
        Get assets from a broker.
        
        Args:
            broker_account: BrokerAccount model instance
            asset_type: Type of asset to search for
            keywords: Search keywords
            limit: Maximum number of results
            
        Returns:
            List of BrokerAsset objects
        """
        try:
            broker = self.get_broker_instance(broker_account)
            
            if not broker.authenticate():
                logger.warning(f"Authentication failed for {broker.BROKER_NAME}")
                return []
            
            return broker.get_assets(
                asset_type=asset_type,
                keywords=keywords,
                limit=limit
            )
            
        except Exception as e:
            logger.error(f"Error getting assets: {e}")
            return []
    
    def get_asset_price(
        self,
        broker_account: BrokerAccount,
        symbol: str,
        **kwargs
    ) -> Optional[Decimal]:
        """
        Get current price for an asset.
        
        Args:
            broker_account: BrokerAccount model instance
            symbol: Asset symbol
            **kwargs: Additional parameters
            
        Returns:
            Current price or None
        """
        try:
            broker = self.get_broker_instance(broker_account)
            
            if not broker.authenticate():
                return None
            
            return broker.get_asset_price(symbol, **kwargs)
            
        except Exception as e:
            logger.error(f"Error getting asset price: {e}")
            return None
    
    def get_multiple_prices(
        self,
        broker_account: BrokerAccount,
        symbols: List[str]
    ) -> Dict[str, Optional[Decimal]]:
        """
        Get prices for multiple assets.
        
        Args:
            broker_account: BrokerAccount model instance
            symbols: List of asset symbols
            
        Returns:
            Dictionary mapping symbols to prices
        """
        try:
            broker = self.get_broker_instance(broker_account)
            
            if not broker.authenticate():
                return {}
            
            return broker.get_multiple_prices(symbols)
            
        except Exception as e:
            logger.error(f"Error getting multiple prices: {e}")
            return {}
    
    # ============================================
    # POSITIONS
    # ============================================
    
    def get_positions(self, broker_account: BrokerAccount) -> List[BrokerPosition]:
        """
        Get positions from a broker.
        
        Args:
            broker_account: BrokerAccount model instance
            
        Returns:
            List of BrokerPosition objects
        """
        try:
            broker = self.get_broker_instance(broker_account)
            
            if not broker.authenticate():
                return []
            
            return broker.get_positions()
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def get_position_by_symbol(
        self,
        broker_account: BrokerAccount,
        symbol: str
    ) -> Optional[BrokerPosition]:
        """
        Get position for a specific symbol.
        
        Args:
            broker_account: BrokerAccount model instance
            symbol: Asset symbol
            
        Returns:
            BrokerPosition or None
        """
        try:
            broker = self.get_broker_instance(broker_account)
            
            if not broker.authenticate():
                return None
            
            return broker.get_position_by_symbol(symbol)
            
        except Exception as e:
            logger.error(f"Error getting position: {e}")
            return None
    
    # ============================================
    # TRADES
    # ============================================
    
    def get_trades(
        self,
        broker_account: BrokerAccount,
        symbol: Optional[str] = None,
        limit: int = 50
    ) -> List[BrokerTrade]:
        """
        Get trades from a broker.
        
        Args:
            broker_account: BrokerAccount model instance
            symbol: Filter by symbol (optional)
            limit: Maximum number of results
            
        Returns:
            List of BrokerTrade objects
        """
        try:
            broker = self.get_broker_instance(broker_account)
            
            if not broker.authenticate():
                return []
            
            return broker.get_trades(symbol=symbol, limit=limit)
            
        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            return []
    
    # ============================================
    # ORDERS
    # ============================================
    
    def get_orders(
        self,
        broker_account: BrokerAccount,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 50
    ) -> List[BrokerOrder]:
        """
        Get orders from a broker.
        
        Args:
            broker_account: BrokerAccount model instance
            status: Filter by status
            symbol: Filter by symbol
            limit: Maximum number of results
            
        Returns:
            List of BrokerOrder objects
        """
        try:
            broker = self.get_broker_instance(broker_account)
            
            if not broker.authenticate():
                return []
            
            return broker.get_orders(status=status, symbol=symbol, limit=limit)
            
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []
    
    def place_order(
        self,
        broker_account: BrokerAccount,
        symbol: str,
        side: str,
        quantity: Decimal,
        order_type: str = 'MARKET',
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        **kwargs
    ) -> OrderResult:
        """
        Place an order through a broker.
        
        Args:
            broker_account: BrokerAccount model instance
            symbol: Asset symbol
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            order_type: 'MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT'
            price: Limit price
            stop_price: Stop price
            **kwargs: Additional parameters
            
        Returns:
            OrderResult with success status
        """
        try:
            broker = self.get_broker_instance(broker_account)
            
            if not broker.authenticate():
                return OrderResult(
                    success=False,
                    error="Authentication failed"
                )
            
            result = broker.place_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=order_type,
                price=price,
                stop_price=stop_price,
                **kwargs
            )
            
            # Log the order
            self._log_sync(
                broker_account=broker_account,
                sync_type='order_placed',
                status='success' if result.success else 'error',
                details={
                    'symbol': symbol,
                    'side': side,
                    'quantity': str(quantity),
                    'order_type': order_type,
                    'order_id': result.order_id,
                },
                error_message=result.error if not result.success else '',
            )
            
            return result
            
        except Exception as e:
            logger.exception(f"Error placing order: {e}")
            return OrderResult(
                success=False,
                error=str(e)
            )
    
    def cancel_order(
        self,
        broker_account: BrokerAccount,
        order_id: str,
        symbol: Optional[str] = None
    ) -> OrderResult:
        """
        Cancel an order.
        
        Args:
            broker_account: BrokerAccount model instance
            order_id: Order ID
            symbol: Asset symbol (required for some brokers)
            
        Returns:
            OrderResult with success status
        """
        try:
            broker = self.get_broker_instance(broker_account)
            
            if not broker.authenticate():
                return OrderResult(
                    success=False,
                    error="Authentication failed"
                )
            
            # Some brokers need symbol
            if hasattr(broker, 'cancel_order'):
                import inspect
                sig = inspect.signature(broker.cancel_order)
                if 'symbol' in sig.parameters:
                    result = broker.cancel_order(order_id, symbol=symbol)
                else:
                    result = broker.cancel_order(order_id)
            else:
                result = broker.cancel_order(order_id)
            
            # Log the cancellation
            self._log_sync(
                broker_account=broker_account,
                sync_type='order_cancelled',
                status='success' if result.success else 'error',
                details={'order_id': order_id},
                error_message=result.error if not result.success else '',
            )
            
            return result
            
        except Exception as e:
            logger.exception(f"Error cancelling order: {e}")
            return OrderResult(
                success=False,
                error=str(e)
            )
    
    # ============================================
    # ACCOUNT
    # ============================================
    
    def get_account_balance(self, broker_account: BrokerAccount) -> Dict[str, Decimal]:
        """
        Get account balance.
        
        Args:
            broker_account: BrokerAccount model instance
            
        Returns:
            Dictionary mapping currency to balance
        """
        try:
            # Récupérer les credentials pour logging
            credentials = self._get_credentials_from_account(broker_account)
            logger.info(f"Getting balance for account {broker_account.id} (type: {broker_account.get_broker_type()})")
            logger.debug(f"Credentials keys present: api_key={bool(credentials.get('api_key'))}, api_secret={bool(credentials.get('api_secret'))}, testnet={credentials.get('testnet', False)}")
            
            broker = self.get_broker_instance(broker_account)
            
            if not broker.authenticate():
                logger.error(f"Authentication failed for account {broker_account.id}")
                return {}
            
            return broker.get_account_balance()
            
        except Exception as e:
            logger.error(f"Error getting account balance: {e}", exc_info=True)
            return {}
    
    def get_account_info(self, broker_account: BrokerAccount) -> Dict[str, Any]:
        """
        Get account information.
        
        Args:
            broker_account: BrokerAccount model instance
            
        Returns:
            Dictionary with account info
        """
        try:
            broker = self.get_broker_instance(broker_account)
            
            if not broker.authenticate():
                return {'connected': False, 'error': 'Authentication failed'}
            
            return broker.get_account_info()
            
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {'connected': False, 'error': str(e)}
    
    # ============================================
    # SYNC LOGGING
    # ============================================
    
    def _log_sync(
        self,
        broker_account: BrokerAccount,
        sync_type: str,
        status: str,
        details: Optional[Dict] = None,
        error_message: Optional[str] = None,
        records_synced: int = 0
    ) -> BrokerSyncLog:
        """
        Log a sync operation.
        
        Args:
            broker_account: BrokerAccount model instance
            sync_type: Type of sync operation
            status: 'success', 'error', or 'warning'
            details: Additional details
            error_message: Error message if any
            records_synced: Number of records synced
            
        Returns:
            BrokerSyncLog instance
        """
        return BrokerSyncLog.objects.create(
            broker_account=broker_account,
            sync_type=sync_type,
            status=status,
            records_synced=records_synced,
            error_message=error_message or '',  # Utiliser chaîne vide au lieu de None
            details=details or {},
        )
    
    def get_sync_logs(
        self,
        broker_account: Optional[BrokerAccount] = None,
        sync_type: Optional[str] = None,
        limit: int = 50
    ) -> List[BrokerSyncLog]:
        """
        Get sync logs.
        
        Args:
            broker_account: Filter by broker account
            sync_type: Filter by sync type
            limit: Maximum number of results
            
        Returns:
            List of BrokerSyncLog instances
        """
        queryset = BrokerSyncLog.objects.filter(
            broker_account__user=self.user
        )
        
        if broker_account:
            queryset = queryset.filter(broker_account=broker_account)
        
        if sync_type:
            queryset = queryset.filter(sync_type=sync_type)
        
        return list(queryset.order_by('-created_at')[:limit])
    
    # ============================================
    # DATA SYNCHRONIZATION
    # ============================================
    
    @transaction.atomic
    def sync_assets_to_db(
        self,
        broker_account: BrokerAccount,
        asset_type: str = 'Stock',
        limit: int = 1000
    ) -> Dict[str, Any]:
        """
        Sync assets from broker to database.
        
        Args:
            broker_account: BrokerAccount model instance
            asset_type: Type of asset to sync
            limit: Maximum number of assets to sync
            
        Returns:
            Dict with sync results
        """
        try:
            broker_assets = self.get_assets(
                broker_account,
                asset_type=asset_type,
                limit=limit
            )
            
            if not broker_assets:
                return {
                    'success': False,
                    'message': 'No assets retrieved from broker',
                    'created': 0,
                    'updated': 0,
                }
            
            created = 0
            updated = 0
            platform = broker_account.get_broker_type().upper()
            
            for broker_asset in broker_assets:
                all_asset, was_created = AllAssets.objects.update_or_create(
                    symbol=broker_asset.symbol,
                    platform=platform,
                    defaults={
                        'name': broker_asset.name,
                        'asset_type': broker_asset.asset_type,
                        'exchange': broker_asset.exchange,
                        'currency': broker_asset.currency,
                        'is_tradable': broker_asset.is_tradable,
                        # Store broker-specific ID
                        'saxo_uic': int(broker_asset.broker_id) if platform == 'SAXO' and broker_asset.broker_id else None,
                    }
                )
                
                if was_created:
                    created += 1
                else:
                    updated += 1
            
            # Log the sync
            self._log_sync(
                broker_account=broker_account,
                sync_type='assets',
                status='success',
                records_synced=created + updated,
                details={
                    'asset_type': asset_type,
                    'created': created,
                    'updated': updated,
                },
            )
            
            return {
                'success': True,
                'message': f'Synced {created + updated} assets',
                'created': created,
                'updated': updated,
            }
            
        except Exception as e:
            logger.exception(f"Error syncing assets: {e}")
            self._log_sync(
                broker_account=broker_account,
                sync_type='assets',
                status='error',
                error_message=str(e),
            )
            return {
                'success': False,
                'message': str(e),
                'created': 0,
                'updated': 0,
            }
    
    @transaction.atomic
    def sync_positions_to_db(self, broker_account: BrokerAccount) -> Dict[str, Any]:
        """
        Sync positions from broker to database.
        
        Args:
            broker_account: BrokerAccount model instance
            
        Returns:
            Dict with sync results
        """
        try:
            broker_positions = self.get_positions(broker_account)
            
            if not broker_positions:
                return {
                    'success': True,
                    'message': 'No positions found',
                    'synced': 0,
                }
            
            synced = 0
            
            for broker_pos in broker_positions:
                # Find or create asset
                asset = Asset.objects.filter(symbol=broker_pos.symbol).first()
                
                if not asset:
                    # Try to find in AllAssets
                    all_asset = AllAssets.objects.filter(
                        symbol=broker_pos.symbol,
                        platform=broker_account.get_broker_type().upper()
                    ).first()
                    
                    if all_asset:
                        asset, _ = Asset.objects.get_or_create(
                            all_asset=all_asset,
                            defaults={
                                'symbol': all_asset.symbol,
                                'name': all_asset.name,
                                'asset_type': all_asset.asset_type,
                                'currency': all_asset.currency,
                            }
                        )
                
                if not asset:
                    continue
                
                # Update or create position
                position, _ = Position.objects.update_or_create(
                    user=self.user,
                    asset=asset,
                    broker=broker_account.broker,
                    broker_account=broker_account,
                    is_open=True,
                    defaults={
                        'quantity': broker_pos.quantity,
                        'entry_price': broker_pos.entry_price,
                        'current_price': broker_pos.current_price,
                        'side': 'BUY' if broker_pos.side == 'LONG' else 'SELL',
                    }
                )
                synced += 1
            
            # Log the sync
            self._log_sync(
                broker_account=broker_account,
                sync_type='positions',
                status='success',
                records_synced=synced,
            )
            
            return {
                'success': True,
                'message': f'Synced {synced} positions',
                'synced': synced,
            }
            
        except Exception as e:
            logger.exception(f"Error syncing positions: {e}")
            self._log_sync(
                broker_account=broker_account,
                sync_type='positions',
                status='error',
                error_message=str(e),
            )
            return {
                'success': False,
                'message': str(e),
                'synced': 0,
            }

