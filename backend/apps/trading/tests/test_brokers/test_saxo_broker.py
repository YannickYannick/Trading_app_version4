"""
Tests for SaxoBroker implementation.

Basic tests for imports and broker initialization.
"""
from django.test import TestCase
from unittest.mock import Mock
from decimal import Decimal
from datetime import datetime, timedelta


class SaxoBrokerImportTestCase(TestCase):
    """Tests for SaxoBroker imports and basic functionality."""
    
    def test_saxo_broker_import(self):
        """Test that SaxoBroker can be imported."""
        from apps.trading.brokers.saxo import SaxoBroker
        self.assertIsNotNone(SaxoBroker)
    
    def test_broker_base_import(self):
        """Test that BrokerBase can be imported."""
        from apps.trading.brokers.base import BrokerBase, BrokerAsset, BrokerPosition, OrderResult
        self.assertIsNotNone(BrokerBase)
        self.assertIsNotNone(BrokerAsset)
        self.assertIsNotNone(BrokerPosition)
        self.assertIsNotNone(OrderResult)
    
    def test_broker_factory_includes_saxo(self):
        """Test that factory includes Saxo."""
        from apps.trading.brokers.factory import BrokerFactory
        brokers = BrokerFactory.get_supported_brokers()
        self.assertTrue(any('Saxo' in b for b in brokers))


class SaxoBrokerInstanceTestCase(TestCase):
    """Tests for SaxoBroker instance creation."""
    
    def test_saxo_broker_init(self):
        """Test SaxoBroker initialization."""
        from apps.trading.brokers.saxo import SaxoBroker
        
        user = Mock()
        user.id = 1
        
        credentials = {
            'client_id': 'test_client_id',
            'client_secret': 'test_secret',
            'environment': 'simulation',
            'access_token': 'test_token',
        }
        
        broker = SaxoBroker(user, credentials)
        self.assertIsNotNone(broker)
        self.assertEqual(broker.base_url, SaxoBroker.SIM_BASE_URL)
    
    def test_saxo_broker_live_url(self):
        """Test SaxoBroker with live environment."""
        from apps.trading.brokers.saxo import SaxoBroker
        
        user = Mock()
        credentials = {
            'environment': 'live',
        }
        
        broker = SaxoBroker(user, credentials)
        self.assertEqual(broker.base_url, SaxoBroker.LIVE_BASE_URL)
    
    def test_saxo_broker_is_authenticated_no_token(self):
        """Test is_authenticated without token."""
        from apps.trading.brokers.saxo import SaxoBroker
        
        user = Mock()
        broker = SaxoBroker(user, {})
        self.assertFalse(broker.is_authenticated())
    
    def test_saxo_broker_has_required_methods(self):
        """Test SaxoBroker has all required methods."""
        from apps.trading.brokers.saxo import SaxoBroker
        
        user = Mock()
        broker = SaxoBroker(user, {})
        
        self.assertTrue(hasattr(broker, 'authenticate'))
        self.assertTrue(hasattr(broker, 'is_authenticated'))
        self.assertTrue(hasattr(broker, 'get_assets'))
        self.assertTrue(hasattr(broker, 'get_asset_price'))
        self.assertTrue(hasattr(broker, 'get_positions'))
        self.assertTrue(hasattr(broker, 'place_order'))
