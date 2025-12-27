"""
Tests for BinanceBroker implementation.

Basic tests for imports and broker initialization.
"""
from django.test import TestCase
from unittest.mock import Mock
from decimal import Decimal


class BinanceBrokerImportTestCase(TestCase):
    """Tests for BinanceBroker imports and basic functionality."""
    
    def test_binance_broker_import(self):
        """Test that BinanceBroker can be imported."""
        from apps.trading.brokers.binance import BinanceBroker
        self.assertIsNotNone(BinanceBroker)
    
    def test_broker_factory_includes_binance(self):
        """Test that factory includes Binance."""
        from apps.trading.brokers.factory import BrokerFactory
        brokers = BrokerFactory.get_supported_brokers()
        self.assertTrue(any('Binance' in b for b in brokers))


class BinanceBrokerInstanceTestCase(TestCase):
    """Tests for BinanceBroker instance creation."""
    
    def test_binance_broker_init_testnet(self):
        """Test BinanceBroker initialization with testnet."""
        from apps.trading.brokers.binance import BinanceBroker
        
        user = Mock()
        user.id = 1
        
        credentials = {
            'api_key': 'test_api_key',
            'api_secret': 'test_api_secret',
            'testnet': True,
        }
        
        broker = BinanceBroker(user, credentials)
        self.assertIsNotNone(broker)
        self.assertEqual(broker.base_url, BinanceBroker.TESTNET_BASE_URL)
    
    def test_binance_broker_init_live(self):
        """Test BinanceBroker initialization with live environment."""
        from apps.trading.brokers.binance import BinanceBroker
        
        user = Mock()
        credentials = {
            'api_key': 'test_api_key',
            'api_secret': 'test_api_secret',
            'testnet': False,
        }
        
        broker = BinanceBroker(user, credentials)
        self.assertEqual(broker.base_url, BinanceBroker.LIVE_BASE_URL)
    
    def test_binance_broker_signature_generation(self):
        """Test HMAC signature generation."""
        from apps.trading.brokers.binance import BinanceBroker
        
        user = Mock()
        credentials = {
            'api_key': 'test_key',
            'api_secret': 'test_secret',
        }
        
        broker = BinanceBroker(user, credentials)
        params = {'symbol': 'BTCUSDT', 'timestamp': 1234567890}
        signature = broker._sign_params(params)
        
        self.assertIsNotNone(signature)
        self.assertEqual(len(signature), 64)  # SHA256 hex digest
    
    def test_binance_broker_has_required_methods(self):
        """Test BinanceBroker has all required methods."""
        from apps.trading.brokers.binance import BinanceBroker
        
        user = Mock()
        broker = BinanceBroker(user, {'api_key': 'key', 'api_secret': 'secret'})
        
        self.assertTrue(hasattr(broker, 'authenticate'))
        self.assertTrue(hasattr(broker, 'is_authenticated'))
        self.assertTrue(hasattr(broker, 'get_assets'))
        self.assertTrue(hasattr(broker, 'get_asset_price'))
        self.assertTrue(hasattr(broker, 'get_positions'))
        self.assertTrue(hasattr(broker, 'place_order'))
