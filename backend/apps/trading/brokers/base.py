"""
Base class for all broker implementations.

This abstract class defines the interface that all broker implementations
must follow, ensuring consistency across different broker APIs.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger('trading.brokers')


class OrderSide(Enum):
    """Order side enumeration."""
    BUY = 'BUY'
    SELL = 'SELL'


class OrderType(Enum):
    """Order type enumeration."""
    MARKET = 'MARKET'
    LIMIT = 'LIMIT'
    STOP = 'STOP'
    STOP_LIMIT = 'STOP_LIMIT'


@dataclass
class BrokerAsset:
    """Standardized asset representation from brokers."""
    symbol: str
    name: str
    asset_type: str
    exchange: str = ''
    currency: str = 'USD'
    is_tradable: bool = True
    # Broker-specific identifiers
    broker_id: Optional[str] = None
    raw_data: Optional[Dict] = None


@dataclass
class BrokerPosition:
    """Standardized position representation from brokers."""
    symbol: str
    quantity: Decimal
    entry_price: Decimal
    current_price: Decimal
    side: str  # 'LONG' or 'SHORT'
    pnl: Decimal = Decimal('0')
    pnl_percent: Decimal = Decimal('0')
    broker_position_id: Optional[str] = None
    raw_data: Optional[Dict] = None


@dataclass
class BrokerTrade:
    """Standardized trade representation from brokers."""
    symbol: str
    trade_type: str  # 'BUY' or 'SELL'
    quantity: Decimal
    price: Decimal
    fees: Decimal = Decimal('0')
    executed_at: Optional[str] = None
    broker_trade_id: Optional[str] = None
    raw_data: Optional[Dict] = None


@dataclass
class BrokerOrder:
    """Standardized order representation from brokers."""
    symbol: str
    order_type: str
    side: str
    quantity: Decimal
    price: Optional[Decimal] = None
    status: str = 'PENDING'
    filled_quantity: Decimal = Decimal('0')
    broker_order_id: Optional[str] = None
    raw_data: Optional[Dict] = None


@dataclass
class OrderResult:
    """Result of an order placement."""
    success: bool
    order_id: Optional[str] = None
    message: str = ''
    error: Optional[str] = None
    raw_data: Optional[Dict] = None


class BrokerError(Exception):
    """Base exception for broker errors."""
    pass


class AuthenticationError(BrokerError):
    """Authentication failed."""
    pass


class RateLimitError(BrokerError):
    """Rate limit exceeded."""
    pass


class InsufficientFundsError(BrokerError):
    """Insufficient funds for operation."""
    pass


class APIError(BrokerError):
    """API request error."""
    pass


# Aliases for compatibility
BrokerAuthenticationError = AuthenticationError
BrokerRateLimitError = RateLimitError
BrokerAPIError = APIError


class BrokerBase(ABC):
    """
    Abstract base class for all broker implementations.
    
    Each broker (Saxo, Binance, etc.) must implement all abstract methods
    to provide a consistent interface.
    
    Usage:
        class MyBroker(BrokerBase):
            def authenticate(self) -> bool:
                # Implementation
                pass
    """
    
    # Broker identification
    BROKER_NAME: str = 'unknown'
    BROKER_TYPE: str = 'unknown'
    
    def __init__(self, user, credentials: Dict[str, Any]):
        """
        Initialize the broker with user and credentials.
        
        Args:
            user: Django User instance
            credentials: Dictionary containing API keys and tokens
        """
        self.user = user
        self.credentials = credentials
        self._authenticated = False
        self._last_error: Optional[str] = None
    
    @property
    def is_connected(self) -> bool:
        """Check if broker is connected and authenticated."""
        return self._authenticated
    
    @property
    def last_error(self) -> Optional[str]:
        """Get the last error message."""
        return self._last_error
    
    def _set_error(self, error: str) -> None:
        """Set the last error message."""
        self._last_error = error
        logger.error(f"[{self.BROKER_NAME}] {error}")
    
    def _clear_error(self) -> None:
        """Clear the last error."""
        self._last_error = None
    
    # ============================================
    # AUTHENTICATION
    # ============================================
    
    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the broker.
        
        Returns:
            True if authentication successful, False otherwise
        """
        pass
    
    @abstractmethod
    def is_authenticated(self) -> bool:
        """
        Check if currently authenticated.
        
        Returns:
            True if authenticated, False otherwise
        """
        pass
    
    @abstractmethod
    def refresh_authentication(self) -> bool:
        """
        Refresh authentication tokens if needed.
        
        Returns:
            True if refresh successful, False otherwise
        """
        pass
    
    def test_connection(self) -> bool:
        """
        Test the connection to the broker.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self._clear_error()
            return self.authenticate()
        except Exception as e:
            self._set_error(f"Connection test failed: {str(e)}")
            return False
    
    # ============================================
    # ASSETS
    # ============================================
    
    @abstractmethod
    def get_assets(
        self,
        asset_type: str = 'Stock',
        keywords: str = '',
        limit: int = 100
    ) -> List[BrokerAsset]:
        """
        Get list of available assets.
        
        Args:
            asset_type: Type of asset ('Stock', 'Crypto', 'ETF', etc.)
            keywords: Search keywords
            limit: Maximum number of results
            
        Returns:
            List of BrokerAsset objects
        """
        pass
    
    @abstractmethod
    def get_asset_price(
        self,
        symbol: str,
        **kwargs
    ) -> Optional[Decimal]:
        """
        Get current price for an asset.
        
        Args:
            symbol: Asset symbol
            **kwargs: Additional broker-specific parameters
            
        Returns:
            Current price as Decimal, or None if not available
        """
        pass
    
    def get_multiple_prices(
        self,
        symbols: List[str],
        **kwargs
    ) -> Dict[str, Optional[Decimal]]:
        """
        Get prices for multiple assets.
        
        Args:
            symbols: List of asset symbols
            **kwargs: Additional broker-specific parameters
            
        Returns:
            Dictionary mapping symbols to prices
        """
        prices = {}
        for symbol in symbols:
            prices[symbol] = self.get_asset_price(symbol, **kwargs)
        return prices
    
    # ============================================
    # POSITIONS
    # ============================================
    
    @abstractmethod
    def get_positions(self) -> List[BrokerPosition]:
        """
        Get current open positions.
        
        Returns:
            List of BrokerPosition objects
        """
        pass
    
    def get_position_by_symbol(self, symbol: str) -> Optional[BrokerPosition]:
        """
        Get position for a specific symbol.
        
        Args:
            symbol: Asset symbol
            
        Returns:
            BrokerPosition if found, None otherwise
        """
        positions = self.get_positions()
        for pos in positions:
            if pos.symbol == symbol:
                return pos
        return None
    
    # ============================================
    # TRADES
    # ============================================
    
    @abstractmethod
    def get_trades(
        self,
        symbol: Optional[str] = None,
        limit: int = 50,
        **kwargs
    ) -> List[BrokerTrade]:
        """
        Get trade history.
        
        Args:
            symbol: Filter by symbol (optional)
            limit: Maximum number of results
            **kwargs: Additional broker-specific parameters
            
        Returns:
            List of BrokerTrade objects
        """
        pass
    
    # ============================================
    # ORDERS
    # ============================================
    
    @abstractmethod
    def get_orders(
        self,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 50
    ) -> List[BrokerOrder]:
        """
        Get orders.
        
        Args:
            status: Filter by status ('PENDING', 'FILLED', etc.)
            symbol: Filter by symbol
            limit: Maximum number of results
            
        Returns:
            List of BrokerOrder objects
        """
        pass
    
    @abstractmethod
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        order_type: str = 'MARKET',
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        **kwargs
    ) -> OrderResult:
        """
        Place an order.
        
        Args:
            symbol: Asset symbol
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            order_type: 'MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT'
            price: Limit price (for LIMIT orders)
            stop_price: Stop price (for STOP orders)
            **kwargs: Additional broker-specific parameters
            
        Returns:
            OrderResult with success status and order details
        """
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> OrderResult:
        """
        Cancel an order.
        
        Args:
            order_id: Broker order ID
            
        Returns:
            OrderResult with success status
        """
        pass
    
    # ============================================
    # ACCOUNT
    # ============================================
    
    @abstractmethod
    def get_account_balance(self) -> Dict[str, Decimal]:
        """
        Get account balances.
        
        Returns:
            Dictionary mapping currency to balance
        """
        pass
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information.
        
        Returns:
            Dictionary with account details
        """
        return {
            'broker': self.BROKER_NAME,
            'connected': self.is_connected,
            'balances': self.get_account_balance(),
        }
    
    # ============================================
    # UTILITY
    # ============================================
    
    def _ensure_authenticated(self) -> bool:
        """
        Ensure the broker is authenticated, attempting authentication if needed.
        
        Returns:
            True if authenticated, False otherwise
        """
        if self.is_authenticated():
            return True
        return self.authenticate()

