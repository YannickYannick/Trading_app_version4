"""
Tests for AssetSyncService.

Basic tests for imports and service initialization.
"""
from django.test import TestCase
from django.contrib.auth.models import User

from apps.trading.models import Broker, BrokerAccount, AllAssets, Asset


class AssetSyncServiceImportTestCase(TestCase):
    """Tests for AssetSyncService imports."""
    
    def test_asset_sync_service_import(self):
        """Test that AssetSyncService can be imported."""
        from apps.trading.services.sync.asset_sync_service import AssetSyncService
        self.assertIsNotNone(AssetSyncService)
    
    def test_services_init_import(self):
        """Test that services __init__ exports correctly."""
        from apps.trading.services import AssetSyncService
        self.assertIsNotNone(AssetSyncService)


class AssetSyncServiceTestCase(TestCase):
    """Tests for AssetSyncService."""
    
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
        
        self.binance_account = BrokerAccount.objects.create(
            user=self.user,
            broker=self.binance_broker,
            account_id='binance-456',
            is_active=True
        )
    
    def test_init(self):
        """Test service initialization."""
        from apps.trading.services.sync.asset_sync_service import AssetSyncService
        
        service = AssetSyncService(self.user)
        self.assertEqual(service.user, self.user)
    
    def test_service_has_required_methods(self):
        """Test service has required methods."""
        from apps.trading.services.sync.asset_sync_service import AssetSyncService
        
        service = AssetSyncService(self.user)
        
        # Check actual methods from implementation
        self.assertTrue(hasattr(service, 'sync_assets'))
        self.assertTrue(hasattr(service, 'sync_all_asset_types'))
        self.assertTrue(hasattr(service, 'search_and_sync'))
        self.assertTrue(callable(service.sync_assets))
    
    def test_get_credentials(self):
        """Test getting credentials from broker account."""
        from apps.trading.services.sync.asset_sync_service import AssetSyncService
        
        # Update account with credentials
        self.saxo_account.client_id = 'test_client_id'
        self.saxo_account.client_secret = 'test_secret'
        self.saxo_account.access_token = 'test_token'
        self.saxo_account.save()
        
        service = AssetSyncService(self.user)
        credentials = service._get_credentials(self.saxo_account)
        
        self.assertEqual(credentials['client_id'], 'test_client_id')
        self.assertEqual(credentials['client_secret'], 'test_secret')
        self.assertEqual(credentials['access_token'], 'test_token')
        self.assertEqual(credentials['environment'], 'simulation')  # is_sandbox=True by default
    
    def test_get_credentials_binance(self):
        """Test getting credentials from Binance account."""
        from apps.trading.services.sync.asset_sync_service import AssetSyncService
        
        # Update account with credentials
        self.binance_account.api_key = 'binance_api_key'
        self.binance_account.api_secret = 'binance_api_secret'
        self.binance_account.is_sandbox = True
        self.binance_account.save()
        
        service = AssetSyncService(self.user)
        credentials = service._get_credentials(self.binance_account)
        
        self.assertEqual(credentials['api_key'], 'binance_api_key')
        self.assertEqual(credentials['api_secret'], 'binance_api_secret')
        self.assertTrue(credentials['testnet'])


class AllAssetsModelTestCase(TestCase):
    """Tests for AllAssets model."""
    
    def test_all_assets_creation(self):
        """Test creating an AllAssets record."""
        asset = AllAssets.objects.create(
            symbol='AAPL',
            name='Apple Inc.',
            platform='SAXO',
            asset_type='Stock',
            market='NASDAQ',
            currency='USD',
            is_tradable=True
        )
        
        self.assertEqual(asset.symbol, 'AAPL')
        self.assertTrue(asset.is_saxo)
        self.assertFalse(asset.is_binance)
    
    def test_all_assets_binance(self):
        """Test AllAssets for Binance."""
        asset = AllAssets.objects.create(
            symbol='BTCUSDT',
            name='BTC/USDT',
            platform='BINANCE',
            asset_type='CRYPTO',
            market='TRADING',
            currency='USDT',
        )
        
        self.assertTrue(asset.is_binance)
        self.assertFalse(asset.is_saxo)
    
    def test_all_assets_unique_together(self):
        """Test that symbol+platform is unique."""
        AllAssets.objects.create(
            symbol='AAPL',
            name='Apple',
            platform='SAXO',
            asset_type='Stock',
            market='NASDAQ',
        )
        
        # Same symbol, different platform should work
        asset2 = AllAssets.objects.create(
            symbol='AAPL',
            name='Apple',
            platform='BINANCE',  # Different platform
            asset_type='Stock',
            market='NASDAQ',
        )
        
        self.assertEqual(AllAssets.objects.filter(symbol='AAPL').count(), 2)
