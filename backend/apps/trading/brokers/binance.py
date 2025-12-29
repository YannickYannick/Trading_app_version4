"""
Binance Broker Implementation.

This module provides integration with Binance API for cryptocurrency trading.
Supports both live and testnet environments.

Documentation: https://binance-docs.github.io/apidocs/spot/en/
"""
import requests
import hmac
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal
from urllib.parse import urlencode
import logging

from .base import (
    BrokerBase,
    BrokerAsset,
    BrokerPosition,
    BrokerTrade,
    BrokerOrder,
    OrderResult,
    BrokerError,
    AuthenticationError,
    RateLimitError,
    BrokerAPIError,
)

logger = logging.getLogger('trading.brokers.binance')


class BinanceBroker(BrokerBase):
    """
    Client for Binance API.
    
    Supports:
    - HMAC authentication
    - Spot trading
    - Position/balance management
    - Order placement and management
    
    Usage:
        broker = BinanceBroker(user, {
            'api_key': 'xxx',
            'api_secret': 'xxx',
            'testnet': False  # or True for testnet
        })
        broker.authenticate()
        assets = broker.get_assets(keywords='BTC')
    """
    
    BROKER_NAME = 'Binance'
    BROKER_TYPE = 'BINANCE'
    
    # Environment URLs
    LIVE_BASE_URL = "https://api.binance.com"
    TESTNET_BASE_URL = "https://testnet.binance.vision"
    
    # Asset type mapping
    ASSET_TYPE_MAP = {
        'Crypto': 'CRYPTO',
        'CRYPTO': 'CRYPTO',
        'crypto': 'CRYPTO',
        'Spot': 'SPOT',
        'spot': 'SPOT',
    }
    
    def __init__(self, user, credentials: Dict[str, Any]):
        """
        Initialize Binance broker.
        
        Args:
            user: Django User instance
            credentials: Dict containing:
                - api_key: Binance API key
                - api_secret: Binance API secret
                - testnet: Whether to use testnet (default: False)
        """
        super().__init__(user, credentials)
        
        self.api_key = credentials.get('api_key')
        self.api_secret = credentials.get('api_secret', '').encode('utf-8') if credentials.get('api_secret') else None
        self.is_testnet = credentials.get('testnet', False)
        
        self.base_url = self.TESTNET_BASE_URL if self.is_testnet else self.LIVE_BASE_URL
        
        # Cache for exchange info
        self._exchange_info: Optional[Dict] = None
        self._exchange_info_updated: Optional[datetime] = None
    
    # ============================================
    # AUTHENTICATION
    # ============================================
    
    def authenticate(self) -> bool:
        """Authenticate with Binance (test connection)."""
        try:
            self._clear_error()
            
            # Log des informations de connexion (sans les secrets)
            logger.debug(f"Authenticating Binance: api_key present={bool(self.api_key)}, testnet={self.is_testnet}, base_url={self.base_url}")
            
            if not self.api_key:
                self._set_error("API key is missing")
                logger.error("Binance API key is missing")
                return False
            
            if not self.api_secret:
                self._set_error("API secret is missing")
                logger.error("Binance API secret is missing")
                return False
            
            # Test connection with ping
            response = self._make_request('GET', '/api/v3/ping', signed=False)
            if response is not None:
                self._authenticated = True
                return True
            
            return False
            
        except Exception as e:
            self._set_error(f"Authentication error: {str(e)}")
            return False
    
    def is_authenticated(self) -> bool:
        """Check if authenticated."""
        return self._authenticated and bool(self.api_key) and bool(self.api_secret)
    
    def refresh_authentication(self) -> bool:
        """Refresh authentication (no-op for API key auth)."""
        # API key authentication doesn't need refresh
        return self.is_authenticated()
    
    # ============================================
    # API REQUESTS
    # ============================================
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        signed: bool = False,
        timeout: int = 30
    ) -> Optional[Dict]:
        """
        Make a request to Binance API.
        
        Args:
            method: HTTP method ('GET', 'POST', 'DELETE')
            endpoint: API endpoint
            params: Query parameters
            signed: Whether to sign the request
            timeout: Request timeout in seconds
            
        Returns:
            Response JSON or None on error
        """
        url = f"{self.base_url}{endpoint}"
        headers = {
            'X-MBX-APIKEY': self.api_key or '',
        }
        
        if params is None:
            params = {}
        
        if signed:
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._sign_params(params)
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, headers=headers, data=params, timeout=timeout)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, params=params, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = response.headers.get('Retry-After', 60)
                self._set_error(f"Rate limited. Retry after {retry_after} seconds")
                raise RateLimitError(f"Rate limited. Retry after {retry_after} seconds")
            
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error: {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_msg = f"{error_msg} - {error_data.get('msg', str(error_data))}"
            except:
                pass
            
            # Don't log "Invalid symbol" errors as critical - they're expected for some symbols
            if 'Invalid symbol' in error_msg:
                logger.debug(f"Binance: {error_msg}")
            else:
                self._set_error(error_msg)
            return None
        except requests.exceptions.RequestException as e:
            self._set_error(f"Request error: {str(e)}")
            return None
    
    def _sign_params(self, params: Dict) -> str:
        """Sign parameters with HMAC SHA256."""
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret,
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _get_exchange_info(self) -> Optional[Dict]:
        """Get and cache exchange information."""
        # Cache for 1 hour
        if (
            self._exchange_info and
            self._exchange_info_updated and
            (datetime.now() - self._exchange_info_updated).seconds < 3600
        ):
            return self._exchange_info
        
        response = self._make_request('GET', '/api/v3/exchangeInfo', signed=False)
        if response:
            self._exchange_info = response
            self._exchange_info_updated = datetime.now()
        
        return self._exchange_info
    
    # ============================================
    # ASSETS
    # ============================================
    
    def get_assets(
        self,
        asset_type: str = 'Crypto',
        keywords: str = '',
        limit: int = 100
    ) -> List[BrokerAsset]:
        """Get list of available trading pairs."""
        try:
            exchange_info = self._get_exchange_info()
            
            if not exchange_info:
                return []
            
            symbols = exchange_info.get('symbols', [])
            assets = []
            
            for item in symbols:
                symbol = item.get('symbol', '')
                base_asset = item.get('baseAsset', '')
                quote_asset = item.get('quoteAsset', '')
                
                # Filter by keywords
                if keywords:
                    keywords_upper = keywords.upper()
                    if keywords_upper not in symbol and keywords_upper not in base_asset:
                        continue
                
                # Skip non-trading pairs
                if item.get('status') != 'TRADING':
                    continue
                
                asset = BrokerAsset(
                    symbol=symbol,
                    name=f"{base_asset}/{quote_asset}",
                    asset_type='CRYPTO',
                    exchange='Binance',
                    currency=quote_asset,
                    is_tradable=item.get('isSpotTradingAllowed', True),
                    broker_id=symbol,
                    raw_data=item,
                )
                assets.append(asset)
                
                if len(assets) >= limit:
                    break
            
            return assets
            
        except Exception as e:
            self._set_error(f"Get assets error: {str(e)}")
            return []
    
    def get_asset_price(
        self,
        symbol: str,
        **kwargs
    ) -> Optional[Decimal]:
        """Get current price for a trading pair."""
        try:
            params = {'symbol': symbol.upper()}
            response = self._make_request('GET', '/api/v3/ticker/price', params=params, signed=False)
            
            if response and 'price' in response:
                return Decimal(response['price'])
            
            return None
            
        except Exception as e:
            self._set_error(f"Get asset price error: {str(e)}")
            return None
    
    def get_multiple_prices(
        self,
        symbols: List[str],
        **kwargs
    ) -> Dict[str, Optional[Decimal]]:
        """Get prices for multiple trading pairs (optimized)."""
        try:
            # Use the batch endpoint for efficiency
            response = self._make_request('GET', '/api/v3/ticker/price', signed=False)
            
            if not response:
                return {}
            
            prices = {}
            symbols_upper = [s.upper() for s in symbols]
            
            for item in response:
                symbol = item.get('symbol', '')
                if symbol in symbols_upper:
                    prices[symbol] = Decimal(item['price'])
            
            return prices
            
        except Exception as e:
            self._set_error(f"Get multiple prices error: {str(e)}")
            return {}
    
    def get_ticker_24h(self, symbol: str) -> Optional[Dict]:
        """
        Get 24h ticker statistics for a symbol.
        
        Returns:
            Dict with price change, volume, etc.
        """
        try:
            params = {'symbol': symbol.upper()}
            response = self._make_request('GET', '/api/v3/ticker/24hr', params=params, signed=False)
            
            if response:
                return {
                    'symbol': response.get('symbol'),
                    'price_change': Decimal(response.get('priceChange', '0')),
                    'price_change_percent': Decimal(response.get('priceChangePercent', '0')),
                    'last_price': Decimal(response.get('lastPrice', '0')),
                    'high_price': Decimal(response.get('highPrice', '0')),
                    'low_price': Decimal(response.get('lowPrice', '0')),
                    'volume': Decimal(response.get('volume', '0')),
                    'quote_volume': Decimal(response.get('quoteVolume', '0')),
                }
            
            return None
            
        except Exception as e:
            self._set_error(f"Get ticker 24h error: {str(e)}")
            return None
    
    def get_klines(
        self,
        symbol: str,
        interval: str = '1h',
        limit: int = 100
    ) -> List[Dict]:
        """
        Get candlestick/kline data.
        
        Args:
            symbol: Trading pair symbol
            interval: Kline interval (1m, 5m, 15m, 1h, 4h, 1d, etc.)
            limit: Number of klines to return (max 1000)
            
        Returns:
            List of kline dictionaries
        """
        try:
            params = {
                'symbol': symbol.upper(),
                'interval': interval,
                'limit': min(limit, 1000),
            }
            response = self._make_request('GET', '/api/v3/klines', params=params, signed=False)
            
            if not response:
                return []
            
            klines = []
            for k in response:
                klines.append({
                    'open_time': k[0],
                    'open': Decimal(k[1]),
                    'high': Decimal(k[2]),
                    'low': Decimal(k[3]),
                    'close': Decimal(k[4]),
                    'volume': Decimal(k[5]),
                    'close_time': k[6],
                    'quote_volume': Decimal(k[7]),
                    'trades': k[8],
                })
            
            return klines
            
        except Exception as e:
            self._set_error(f"Get klines error: {str(e)}")
            return []
    
    # ============================================
    # POSITIONS (BALANCES)
    # ============================================
    
    def get_positions(self) -> List[BrokerPosition]:
        """Get current balances (spot positions)."""
        try:
            response = self._make_request('GET', '/api/v3/account', signed=True)
            
            if not response:
                return []
            
            positions = []
            balances = response.get('balances', [])
            
            for balance in balances:
                free = Decimal(balance.get('free', '0'))
                locked = Decimal(balance.get('locked', '0'))
                total = free + locked
                
                # Skip zero balances
                if total == 0:
                    continue
                
                asset = balance.get('asset', '')
                
                # Get current price for value calculation
                # For stable coins, use 1:1 with USD
                if asset in ('USDT', 'USDC', 'BUSD', 'TUSD', 'DAI'):
                    current_price = Decimal('1')
                else:
                    # Try to get price in USDT
                    current_price = self.get_asset_price(f"{asset}USDT") or Decimal('0')
                
                # For spot positions, use current price as entry price
                # This allows P&L calculation based on current market value
                entry_price = current_price if current_price > 0 else Decimal('0')
                
                # Calculate unrealized P&L (value change from entry)
                # For spot, we consider entry as current price, so P&L is 0
                # But we track the value
                position_value = total * current_price
                
                position = BrokerPosition(
                    symbol=asset,
                    quantity=total,
                    entry_price=entry_price,  # Use current price for spot positions
                    current_price=current_price,
                    side='LONG',  # Spot is always long
                    pnl=Decimal('0'),  # Spot positions don't have unrealized P&L in traditional sense
                    pnl_percent=Decimal('0'),
                    broker_position_id=asset,
                    raw_data={
                        'asset': asset,
                        'free': str(free),
                        'locked': str(locked),
                        'total': str(total),
                        'value': str(position_value),
                    },
                )
                positions.append(position)
            
            return positions
            
        except Exception as e:
            self._set_error(f"Get positions error: {str(e)}")
            return []
    
    # ============================================
    # TRADES
    # ============================================
    
    def _get_trades_for_symbol(self, symbol: str, limit: int = 1000) -> List[BrokerTrade]:
        """
        Internal method to get trades for a specific symbol.
        This avoids recursion when called from get_trades().
        """
        try:
            params = {'symbol': symbol.upper(), 'limit': limit}
            # Clear previous error before making request
            self._clear_error()
            response = self._make_request('GET', '/api/v3/myTrades', params=params, signed=True)
            
            if not response:
                # Check if error is "Invalid symbol" - this is expected for some symbols
                error_msg = self.last_error or ''
                if 'Invalid symbol' in error_msg or '400' in error_msg:
                    logger.debug(f"Binance: Invalid symbol {symbol}, skipping")
                    return []
                # For other errors, return empty list but keep the error logged
                logger.warning(f"Binance: Failed to get trades for {symbol}: {error_msg}")
                return []
            
            trades = []
            for item in response:
                trade = BrokerTrade(
                    symbol=item.get('symbol', ''),
                    trade_type='BUY' if item.get('isBuyer') else 'SELL',
                    quantity=Decimal(str(item.get('qty', 0))),
                    price=Decimal(str(item.get('price', 0))),
                    fees=Decimal(str(item.get('commission', 0))),
                    executed_at=datetime.fromtimestamp(item.get('time', 0) / 1000).isoformat(),
                    broker_trade_id=str(item.get('id', '')),
                    raw_data=item,
                )
                trades.append(trade)
            
            return trades
        except Exception as e:
            logger.debug(f"Error getting trades for {symbol}: {e}")
            return []
    
    def get_trades(
        self,
        symbol: Optional[str] = None,
        limit: int = 100000,
        **kwargs
    ) -> List[BrokerTrade]:
        """
        Get trade history.
        
        If symbol is provided, returns trades for that symbol.
        If symbol is None, uses _get_traded_symbols() to find all symbols
        the user has traded and retrieves trades for each.
        """
        try:
            if symbol:
                # Get trades for specific symbol
                return self._get_trades_for_symbol(symbol, limit)
            else:
                # Get trades for all symbols (limited to recent)
                all_trades = []
                traded_symbols = self._get_traded_symbols()
                
                if not traded_symbols:
                    logger.warning("No traded symbols found. Cannot fetch trades without a symbol.")
                    return []
                
                logger.info(f"Fetching trades for {len(traded_symbols)} symbols")
                
                # Limit to prevent too many API calls (Binance rate limit is 1200/min for signed endpoints)
                # We'll process up to 20 symbols to stay safe
                symbols_to_check = traded_symbols[:20]
                
                for sym in symbols_to_check:
                    try:
                        # Use internal method to avoid recursion
                        # Use limit of 1000 per symbol to get all trades
                        trades = self._get_trades_for_symbol(sym, limit=1000)
                        if trades:
                            logger.debug(f"Found {len(trades)} trades for {sym}")
                            all_trades.extend(trades)
                        # Small delay to avoid rate limiting
                        time.sleep(0.1)
                    except Exception as e:
                        logger.debug(f"Error fetching trades for {sym}: {e}")
                        # Continue with other symbols
                        continue
                
                # Sort by time (most recent first)
                all_trades.sort(key=lambda x: x.executed_at or '', reverse=True)
                logger.info(f"Retrieved {len(all_trades)} total trades from {len(symbols_to_check)} symbols")
                return all_trades[:limit]
            
        except Exception as e:
            logger.error(f"Get trades error: {str(e)}", exc_info=True)
            self._set_error(f"Get trades error: {str(e)}")
            return []
    
    def _get_traded_symbols(self) -> List[str]:
        """
        Get list of symbols to check for trades.
        
        Method 2: Uses a predefined list of symbols.
        Simple and explicit approach with full control over which symbols to check.
        """
        # Predefined list of target assets to check for trades
        predefined_symbols = ['ETHEUR', 'BTCEUR', 'ADAEUR', 'AVAXEUR', 'SOLEUR', 'BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        logger.info(f"Using predefined list of {len(predefined_symbols)} symbols to check for trades")
        return predefined_symbols
    
    # ============================================
    # ORDERS
    # ============================================
    
    def get_orders(
        self,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 1000000
    ) -> List[BrokerOrder]:
        """Get orders."""
        try:
            if symbol:
                params = {'symbol': symbol.upper(), 'limit': limit}
                
                if status and status.upper() == 'PENDING':
                    # Get open orders
                    response = self._make_request('GET', '/api/v3/openOrders', params=params, signed=True)
                else:
                    # Get all orders
                    response = self._make_request('GET', '/api/v3/allOrders', params=params, signed=True)
            else:
                # Get open orders for all symbols
                response = self._make_request('GET', '/api/v3/openOrders', signed=True)
            
            if not response:
                return []
            
            orders = []
            for item in response:
                item_status = item.get('status', '')
                
                # Filter by status if specified
                if status and item_status != status.upper():
                    continue
                
                order = BrokerOrder(
                    symbol=item.get('symbol', ''),
                    order_type=item.get('type', 'MARKET'),
                    side=item.get('side', 'BUY'),
                    quantity=Decimal(str(item.get('origQty', 0))),
                    price=Decimal(str(item.get('price', 0))) if item.get('price') != '0.00000000' else None,
                    status=item_status,
                    filled_quantity=Decimal(str(item.get('executedQty', 0))),
                    broker_order_id=str(item.get('orderId', '')),
                    raw_data=item,
                )
                orders.append(order)
            
            return orders
            
        except Exception as e:
            self._set_error(f"Get orders error: {str(e)}")
            return []
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        order_type: str = 'MARKET',
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        time_in_force: str = 'GTC',
        **kwargs
    ) -> OrderResult:
        """Place an order."""
        try:
            if not self._ensure_authenticated():
                return OrderResult(
                    success=False,
                    error="Not authenticated"
                )
            
            params = {
                'symbol': symbol.upper(),
                'side': side.upper(),
                'type': order_type.upper(),
                'quantity': str(quantity),
            }
            
            if order_type.upper() == 'LIMIT':
                if not price:
                    return OrderResult(
                        success=False,
                        error="Limit orders require a price"
                    )
                params['price'] = str(price)
                params['timeInForce'] = time_in_force
            
            elif order_type.upper() == 'STOP_LIMIT':
                if not price or not stop_price:
                    return OrderResult(
                        success=False,
                        error="Stop limit orders require price and stop_price"
                    )
                params['price'] = str(price)
                params['stopPrice'] = str(stop_price)
                params['timeInForce'] = time_in_force
            
            elif order_type.upper() == 'STOP':
                if not stop_price:
                    return OrderResult(
                        success=False,
                        error="Stop orders require stop_price"
                    )
                params['stopPrice'] = str(stop_price)
                params['type'] = 'STOP_LOSS'
            
            response = self._make_request('POST', '/api/v3/order', params=params, signed=True)
            
            if response:
                return OrderResult(
                    success=True,
                    order_id=str(response.get('orderId', '')),
                    message=f"Order placed: {response.get('status', 'UNKNOWN')}",
                    raw_data=response,
                )
            else:
                return OrderResult(
                    success=False,
                    error=self.last_error or "Order placement failed"
                )
            
        except Exception as e:
            return OrderResult(
                success=False,
                error=str(e)
            )
    
    def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> OrderResult:
        """Cancel an order."""
        try:
            if not self._ensure_authenticated():
                return OrderResult(
                    success=False,
                    error="Not authenticated"
                )
            
            if not symbol:
                # Try to find the order to get its symbol
                orders = self.get_orders()
                for order in orders:
                    if order.broker_order_id == order_id:
                        symbol = order.symbol
                        break
            
            if not symbol:
                return OrderResult(
                    success=False,
                    error="Symbol is required to cancel order"
                )
            
            params = {
                'symbol': symbol.upper(),
                'orderId': int(order_id),
            }
            
            response = self._make_request('DELETE', '/api/v3/order', params=params, signed=True)
            
            if response:
                return OrderResult(
                    success=True,
                    order_id=order_id,
                    message="Order cancelled successfully",
                    raw_data=response,
                )
            else:
                return OrderResult(
                    success=False,
                    error=self.last_error or "Order cancellation failed"
                )
            
        except Exception as e:
            return OrderResult(
                success=False,
                error=str(e)
            )
    
    # ============================================
    # ACCOUNT
    # ============================================
    
    def get_account_balance(self) -> Dict[str, Decimal]:
        """Get account balances."""
        try:
            response = self._make_request('GET', '/api/v3/account', signed=True)
            
            if not response:
                return {}
            
            balances = {}
            for balance in response.get('balances', []):
                asset = balance.get('asset', '')
                free = Decimal(balance.get('free', '0'))
                locked = Decimal(balance.get('locked', '0'))
                total = free + locked
                
                if total > 0:
                    balances[asset] = total
                    balances[f'{asset}_free'] = free
                    balances[f'{asset}_locked'] = locked
            
            return balances
            
        except Exception as e:
            self._set_error(f"Get account balance error: {str(e)}")
            return {}
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information."""
        try:
            response = self._make_request('GET', '/api/v3/account', signed=True)
            
            if not response:
                return {}
            
            return {
                'broker': self.BROKER_NAME,
                'connected': self.is_connected,
                'can_trade': response.get('canTrade', False),
                'can_withdraw': response.get('canWithdraw', False),
                'can_deposit': response.get('canDeposit', False),
                'account_type': response.get('accountType', 'SPOT'),
                'balances': self.get_account_balance(),
            }
            
        except Exception as e:
            self._set_error(f"Get account info error: {str(e)}")
            return {'broker': self.BROKER_NAME, 'connected': False, 'error': str(e)}
    
    def get_server_time(self) -> Optional[int]:
        """Get Binance server time."""
        try:
            response = self._make_request('GET', '/api/v3/time', signed=False)
            if response:
                return response.get('serverTime')
            return None
        except:
            return None

