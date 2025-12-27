"""
Tests for BrokerService.

Tests the high-level service that manages broker interactions.
These are simplified tests that focus on the core functionality.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

from apps.trading.models import Broker, BrokerAccount


class BrokerServiceBasicTestCase(TestCase):
    """Basic tests for BrokerService initialization."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create broker
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
            account_name='Saxo Test Account',
            client_id='test_client_id',
            client_secret='test_secret',
            access_token='test_token',
            is_sandbox=True,
            is_active=True
        )
        
        self.binance_account = BrokerAccount.objects.create(
            user=self.user,
            broker=self.binance_broker,
            account_id='binance-456',
            account_name='Binance Test Account',
            api_key='test_api_key',
            api_secret='test_api_secret',
            is_sandbox=True,
            is_active=True
        )
    
    def test_broker_service_import(self):
        """Test that BrokerService can be imported."""
        from apps.trading.services.broker_service import BrokerService
        self.assertIsNotNone(BrokerService)
    
    def test_broker_service_init(self):
        """Test service initialization."""
        from apps.trading.services.broker_service import BrokerService
        service = BrokerService(self.user)
        self.assertEqual(service.user, self.user)
    
    def test_broker_factory_import(self):
        """Test that BrokerFactory can be imported."""
        from apps.trading.brokers.factory import BrokerFactory
        self.assertIsNotNone(BrokerFactory)
    
    def test_broker_factory_get_supported_brokers(self):
        """Test getting list of supported brokers."""
        from apps.trading.brokers.factory import BrokerFactory
        brokers = BrokerFactory.get_supported_brokers()
        # Factory returns class names like 'Saxo Bank', 'Binance'
        self.assertTrue(any('Saxo' in b for b in brokers))
        self.assertTrue(any('Binance' in b for b in brokers))
    
    @patch('apps.trading.brokers.factory.BrokerFactory.create_broker')
    def test_get_broker_instance_creates_broker(self, mock_create):
        """Test that get_broker_instance calls factory."""
        from apps.trading.services.broker_service import BrokerService
        
        mock_broker = MagicMock()
        mock_create.return_value = mock_broker
        
        service = BrokerService(self.user)
        result = service.get_broker_instance(self.saxo_account)
        
        mock_create.assert_called_once()
        self.assertEqual(result, mock_broker)


class BrokerModelTestCase(TestCase):
    """Tests for Broker and BrokerAccount models."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='modeluser',
            password='testpass123'
        )
    
    def test_broker_creation(self):
        """Test creating a Broker."""
        broker = Broker.objects.create(
            name='Test Broker',
            broker_type=Broker.BrokerType.SAXO,
            is_active=True
        )
        self.assertEqual(str(broker), 'Test Broker')
    
    def test_broker_account_creation(self):
        """Test creating a BrokerAccount."""
        broker = Broker.objects.create(
            name='Saxo Bank',
            broker_type=Broker.BrokerType.SAXO
        )
        
        account = BrokerAccount.objects.create(
            user=self.user,
            broker=broker,
            account_id='test-123',
            account_name='Test Account',
            api_key='key123',
            api_secret='secret456',
            is_active=True
        )
        
        self.assertEqual(account.user, self.user)
        self.assertEqual(account.broker, broker)
        self.assertEqual(account.account_id, 'test-123')
    
    def test_broker_account_str(self):
        """Test BrokerAccount string representation."""
        broker = Broker.objects.create(
            name='Binance',
            broker_type=Broker.BrokerType.BINANCE
        )
        
        account = BrokerAccount.objects.create(
            user=self.user,
            broker=broker,
            account_id='binance-789'
        )
        
        expected = f"{self.user.username} - Binance (binance-789)"
        self.assertEqual(str(account), expected)
    
    def test_broker_account_extra_credentials(self):
        """Test BrokerAccount extra_credentials JSON field."""
        broker = Broker.objects.create(
            name='Custom Broker',
            broker_type=Broker.BrokerType.OTHER
        )
        
        account = BrokerAccount.objects.create(
            user=self.user,
            broker=broker,
            account_id='custom-123',
            extra_credentials={'custom_field': 'custom_value'}
        )
        
        self.assertEqual(account.extra_credentials['custom_field'], 'custom_value')

