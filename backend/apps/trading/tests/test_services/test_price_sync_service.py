"""
Tests for PriceSyncService.

Basic tests for imports and service initialization.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal

from apps.trading.models import Broker, BrokerAccount, AllAssets, Asset


class PriceSyncServiceImportTestCase(TestCase):
    """Tests for PriceSyncService imports."""
    
    def test_price_sync_service_import(self):
        """Test that PriceSyncService can be imported."""
        from apps.trading.services.sync.price_sync_service import PriceSyncService
        self.assertIsNotNone(PriceSyncService)
    
    def test_services_init_import(self):
        """Test that services __init__ exports correctly."""
        from apps.trading.services import PriceSyncService
        self.assertIsNotNone(PriceSyncService)
    
    def test_yahoo_finance_import(self):
        """Test that YahooFinanceService can be imported."""
        from apps.trading.services.data_providers.yahoo_finance import YahooFinanceService
        self.assertIsNotNone(YahooFinanceService)


class PriceSyncServiceTestCase(TestCase):
    """Tests for PriceSyncService."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create brokers
        self.saxo_broker = Broker.objects.create(
            name='Saxo Bank',
            broker_type=Broker.BrokerType.SAXO,
            is_active=True
        )
        
        self.binance_broker = Broker.objects.create(
            name='Binance',
            broker_type=Broker.BrokerType.BINANCE,
            is_active=True
        )
        
        # Create broker accounts
        self.saxo_account = BrokerAccount.objects.create(
            user=self.user,
            broker=self.saxo_broker,
            account_id='saxo-123',
            is_active=True
        )
        
        # Create AllAssets
        self.saxo_all_asset = AllAssets.objects.create(
            symbol='AAPL',
            name='Apple Inc.',
            platform='SAXO',
            asset_type='Stock',
            market='NASDAQ',
            currency='USD',
            is_tradable=True,
            saxo_uic=211
        )
        
        self.binance_all_asset = AllAssets.objects.create(
            symbol='BTCUSDT',
            name='BTC/USDT',
            platform='BINANCE',
            asset_type='CRYPTO',
            market='TRADING',
            currency='USDT',
            is_tradable=True
        )
        
        # Create Assets
        self.saxo_asset = Asset.objects.create(
            all_asset=self.saxo_all_asset,
            symbol='AAPL',
            name='Apple Inc.',
            asset_type='STOCK',
            currency='USD',
            current_price=Decimal('150.00')
        )
    
    def test_init(self):
        """Test service initialization."""
        from apps.trading.services.sync.price_sync_service import PriceSyncService
        
        service = PriceSyncService(self.user)
        self.assertEqual(service.user, self.user)
    
    def test_init_without_user(self):
        """Test service initialization without user."""
        from apps.trading.services.sync.price_sync_service import PriceSyncService
        
        service = PriceSyncService()
        self.assertIsNone(service.user)
    
    def test_service_has_required_methods(self):
        """Test service has required methods."""
        from apps.trading.services.sync.price_sync_service import PriceSyncService
        
        service = PriceSyncService(self.user)
        
        self.assertTrue(hasattr(service, 'sync_current_prices'))
        self.assertTrue(hasattr(service, 'sync_single_price'))
        self.assertTrue(hasattr(service, 'sync_historical_prices'))
        self.assertTrue(hasattr(service, 'update_all_asset_prices'))
        self.assertTrue(callable(service.sync_current_prices))
    
    def test_get_credentials(self):
        """Test getting credentials from broker account."""
        from apps.trading.services.sync.price_sync_service import PriceSyncService
        
        self.saxo_account.client_id = 'test_id'
        self.saxo_account.client_secret = 'test_secret'
        self.saxo_account.save()
        
        service = PriceSyncService(self.user)
        credentials = service._get_credentials(self.saxo_account)
        
        self.assertEqual(credentials['client_id'], 'test_id')
        self.assertEqual(credentials['environment'], 'simulation')


class YahooFinanceServiceTestCase(TestCase):
    """Tests for YahooFinanceService."""
    
    def test_yahoo_finance_service_init(self):
        """Test YahooFinanceService initialization."""
        from apps.trading.services.data_providers.yahoo_finance import YahooFinanceService
        service = YahooFinanceService()
        self.assertIsNotNone(service)
    
    def test_yahoo_finance_service_has_methods(self):
        """Test YahooFinanceService has required methods."""
        from apps.trading.services.data_providers.yahoo_finance import YahooFinanceService
        service = YahooFinanceService()
        
        self.assertTrue(hasattr(service, 'get_current_price'))
        self.assertTrue(hasattr(service, 'get_historical_data'))
        self.assertTrue(callable(service.get_current_price))
        self.assertTrue(callable(service.get_historical_data))


class AssetModelTestCase(TestCase):
    """Tests for Asset model."""
    
    def test_asset_creation(self):
        """Test creating an Asset."""
        all_asset = AllAssets.objects.create(
            symbol='GOOGL',
            name='Alphabet Inc.',
            platform='SAXO',
            asset_type='Stock',
            market='NASDAQ',
        )
        
        asset = Asset.objects.create(
            all_asset=all_asset,
            symbol='GOOGL',
            name='Alphabet Inc.',
            asset_type='STOCK',
            current_price=Decimal('100.00')
        )
        
        self.assertEqual(asset.symbol, 'GOOGL')
        self.assertEqual(asset.all_asset, all_asset)
    
    def test_asset_create_from_all_asset(self):
        """Test creating Asset from AllAssets."""
        all_asset = AllAssets.objects.create(
            symbol='MSFT',
            name='Microsoft Corporation',
            platform='SAXO',
            asset_type='Stock',
            market='NASDAQ',
            currency='USD',
            exchange='XNAS',
        )
        
        asset = Asset.create_from_all_asset(all_asset)
        
        self.assertEqual(asset.symbol, 'MSFT')
        self.assertEqual(asset.name, 'Microsoft Corporation')
        self.assertEqual(asset.all_asset, all_asset)
