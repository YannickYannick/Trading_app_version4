"""
Yahoo Finance Data Provider.

This service provides market data from Yahoo Finance,
including current prices, historical data, and asset information.
"""
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime, date, timedelta
from django.db import transaction
from django.utils import timezone

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    yf = None

from ...models import Asset, AssetPrice, AllAssets

logger = logging.getLogger('trading.services.data_providers.yahoo')


class YahooFinanceService:
    """
    Service for fetching data from Yahoo Finance.
    
    This service provides:
    - Current stock/crypto prices
    - Historical OHLCV data
    - Company/asset information
    - Dividend and split data
    
    Usage:
        service = YahooFinanceService()
        price = service.get_current_price('AAPL')
        history = service.get_historical_data('AAPL', days=30)
    """
    
    def __init__(self):
        """Initialize the Yahoo Finance service."""
        if not YFINANCE_AVAILABLE:
            logger.warning("yfinance package not installed. Some features will be unavailable.")
    
    @property
    def is_available(self) -> bool:
        """Check if yfinance is available."""
        return YFINANCE_AVAILABLE
    
    def _get_ticker(self, symbol: str):
        """Get a yfinance Ticker object."""
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance package is not installed")
        return yf.Ticker(symbol)
    
    # ============================================
    # CURRENT PRICES
    # ============================================
    
    def get_current_price(self, symbol: str) -> Optional[Decimal]:
        """
        Get the current price for a symbol.
        
        Args:
            symbol: Stock/crypto symbol (e.g., 'AAPL', 'BTC-USD')
            
        Returns:
            Current price as Decimal or None
        """
        if not YFINANCE_AVAILABLE:
            return None
        
        try:
            ticker = self._get_ticker(symbol)
            info = ticker.fast_info
            
            # Try different price fields
            price = getattr(info, 'last_price', None)
            if price is None:
                price = getattr(info, 'regular_market_price', None)
            if price is None:
                # Fallback to history
                hist = ticker.history(period='1d')
                if not hist.empty:
                    price = hist['Close'].iloc[-1]
            
            if price is not None:
                return Decimal(str(price))
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return None
    
    def get_multiple_prices(self, symbols: List[str]) -> Dict[str, Optional[Decimal]]:
        """
        Get current prices for multiple symbols.
        
        Args:
            symbols: List of symbols
            
        Returns:
            Dict mapping symbols to prices
        """
        if not YFINANCE_AVAILABLE:
            return {}
        
        prices = {}
        
        try:
            # Use batch download for efficiency
            tickers_str = ' '.join(symbols)
            data = yf.download(tickers_str, period='1d', progress=False)
            
            if not data.empty:
                # Handle single vs multiple symbols
                if len(symbols) == 1:
                    if 'Close' in data.columns:
                        last_price = data['Close'].iloc[-1]
                        prices[symbols[0]] = Decimal(str(last_price)) if last_price else None
                else:
                    for symbol in symbols:
                        try:
                            if symbol in data['Close'].columns:
                                last_price = data['Close'][symbol].iloc[-1]
                                prices[symbol] = Decimal(str(last_price)) if last_price else None
                        except:
                            prices[symbol] = None
            
            # Fill missing with None
            for symbol in symbols:
                if symbol not in prices:
                    prices[symbol] = None
            
            return prices
            
        except Exception as e:
            logger.error(f"Error getting multiple prices: {e}")
            return {s: None for s in symbols}
    
    # ============================================
    # HISTORICAL DATA
    # ============================================
    
    def get_historical_data(
        self,
        symbol: str,
        days: int = 30,
        interval: str = '1d'
    ) -> List[Dict[str, Any]]:
        """
        Get historical OHLCV data.
        
        Args:
            symbol: Stock/crypto symbol
            days: Number of days of history
            interval: Data interval ('1d', '1h', '5m', etc.)
            
        Returns:
            List of dicts with date, open, high, low, close, volume
        """
        if not YFINANCE_AVAILABLE:
            return []
        
        try:
            ticker = self._get_ticker(symbol)
            
            # Calculate period
            if days <= 7:
                period = '1wk'
            elif days <= 30:
                period = '1mo'
            elif days <= 90:
                period = '3mo'
            elif days <= 180:
                period = '6mo'
            elif days <= 365:
                period = '1y'
            else:
                period = '2y'
            
            hist = ticker.history(period=period, interval=interval)
            
            if hist.empty:
                return []
            
            result = []
            for idx, row in hist.iterrows():
                result.append({
                    'date': idx.strftime('%Y-%m-%d') if interval == '1d' else idx.isoformat(),
                    'open': Decimal(str(row['Open'])),
                    'high': Decimal(str(row['High'])),
                    'low': Decimal(str(row['Low'])),
                    'close': Decimal(str(row['Close'])),
                    'volume': int(row['Volume']) if row['Volume'] else 0,
                })
            
            return result[-days:] if len(result) > days else result
            
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return []
    
    @transaction.atomic
    def sync_historical_prices(
        self,
        asset: Asset,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Sync historical prices to database.
        
        Args:
            asset: Asset model instance
            days: Number of days to sync
            
        Returns:
            Dict with sync results
        """
        try:
            data = self.get_historical_data(asset.symbol, days=days)
            
            if not data:
                return {'success': False, 'message': 'No data available', 'records': 0}
            
            records = 0
            for item in data:
                price_date = datetime.strptime(item['date'], '%Y-%m-%d').date()
                
                AssetPrice.objects.update_or_create(
                    asset=asset,
                    date=price_date,
                    defaults={
                        'open_price': item['open'],
                        'high_price': item['high'],
                        'low_price': item['low'],
                        'close_price': item['close'],
                        'volume': item['volume'],
                    }
                )
                records += 1
            
            # Update asset's current price
            if data:
                asset.current_price = data[-1]['close']
                asset.price_updated_at = timezone.now()
                asset.save()
            
            return {
                'success': True,
                'message': f'Synced {records} price records',
                'records': records,
            }
            
        except Exception as e:
            logger.exception(f"Error syncing historical prices: {e}")
            return {'success': False, 'message': str(e), 'records': 0}
    
    # ============================================
    # ASSET INFORMATION
    # ============================================
    
    def get_asset_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed asset information.
        
        Args:
            symbol: Stock/crypto symbol
            
        Returns:
            Dict with asset details
        """
        if not YFINANCE_AVAILABLE:
            return None
        
        try:
            ticker = self._get_ticker(symbol)
            info = ticker.info
            
            if not info:
                return None
            
            return {
                'symbol': symbol,
                'name': info.get('longName') or info.get('shortName', symbol),
                'currency': info.get('currency', 'USD'),
                'exchange': info.get('exchange', ''),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'country': info.get('country', ''),
                'description': info.get('longBusinessSummary', ''),
                'website': info.get('website', ''),
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'dividend_yield': info.get('dividendYield'),
                '52w_high': info.get('fiftyTwoWeekHigh'),
                '52w_low': info.get('fiftyTwoWeekLow'),
            }
            
        except Exception as e:
            logger.error(f"Error getting info for {symbol}: {e}")
            return None
    
    def enrich_asset(self, asset: Asset) -> bool:
        """
        Enrich an asset with Yahoo Finance data.
        
        Args:
            asset: Asset model instance
            
        Returns:
            True if enriched successfully
        """
        try:
            info = self.get_asset_info(asset.symbol)
            
            if not info:
                return False
            
            # Update asset fields
            if info.get('name'):
                asset.name = info['name']
            if info.get('currency'):
                asset.currency = info['currency']
            if info.get('sector'):
                asset.sector = info['sector']
            if info.get('industry'):
                asset.industry = info['industry']
            
            # Get current price
            price = self.get_current_price(asset.symbol)
            if price:
                asset.current_price = price
                asset.price_updated_at = timezone.now()
            
            asset.save()
            return True
            
        except Exception as e:
            logger.error(f"Error enriching asset {asset.symbol}: {e}")
            return False
    
    def search_assets(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for assets on Yahoo Finance.
        
        Note: Yahoo Finance doesn't have a direct search API,
        so this tries the symbol directly.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching assets
        """
        if not YFINANCE_AVAILABLE:
            return []
        
        results = []
        
        # Try the query as a direct symbol
        symbols_to_try = [
            query.upper(),
            f"{query.upper()}-USD",  # Crypto format
        ]
        
        for symbol in symbols_to_try[:limit]:
            try:
                info = self.get_asset_info(symbol)
                if info and info.get('name'):
                    results.append(info)
            except:
                continue
        
        return results
    
    # ============================================
    # DIVIDENDS AND SPLITS
    # ============================================
    
    def get_dividends(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get dividend history for a stock.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            List of dividend records
        """
        if not YFINANCE_AVAILABLE:
            return []
        
        try:
            ticker = self._get_ticker(symbol)
            dividends = ticker.dividends
            
            if dividends.empty:
                return []
            
            result = []
            for date_idx, amount in dividends.items():
                result.append({
                    'date': date_idx.strftime('%Y-%m-%d'),
                    'amount': Decimal(str(amount)),
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting dividends for {symbol}: {e}")
            return []
    
    def get_splits(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get stock split history.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            List of split records
        """
        if not YFINANCE_AVAILABLE:
            return []
        
        try:
            ticker = self._get_ticker(symbol)
            splits = ticker.splits
            
            if splits.empty:
                return []
            
            result = []
            for date_idx, ratio in splits.items():
                result.append({
                    'date': date_idx.strftime('%Y-%m-%d'),
                    'ratio': str(ratio),
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting splits for {symbol}: {e}")
            return []
    
    # ============================================
    # BATCH OPERATIONS
    # ============================================
    
    def update_all_prices(
        self,
        assets: List[Asset],
        batch_size: int = 50
    ) -> Dict[str, Any]:
        """
        Update prices for multiple assets.
        
        Args:
            assets: List of Asset model instances
            batch_size: Number of assets per batch
            
        Returns:
            Dict with update results
        """
        if not YFINANCE_AVAILABLE:
            return {'success': False, 'message': 'yfinance not available', 'updated': 0}
        
        symbols = [a.symbol for a in assets]
        updated = 0
        errors = []
        
        # Process in batches
        for i in range(0, len(symbols), batch_size):
            batch_symbols = symbols[i:i + batch_size]
            
            try:
                prices = self.get_multiple_prices(batch_symbols)
                
                for asset in assets:
                    if asset.symbol in prices and prices[asset.symbol] is not None:
                        asset.current_price = prices[asset.symbol]
                        asset.price_updated_at = timezone.now()
                        asset.save(update_fields=['current_price', 'price_updated_at'])
                        updated += 1
                        
            except Exception as e:
                errors.append({
                    'batch': i // batch_size,
                    'error': str(e),
                })
        
        return {
            'success': True,
            'message': f'Updated {updated} of {len(assets)} prices',
            'updated': updated,
            'total': len(assets),
            'errors': errors,
        }

