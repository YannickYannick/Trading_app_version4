"""
Tests for Broker Account Sync API endpoints.

Tests the synchronization endpoints for assets, prices, positions, and trades.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from apps.trading.models import Broker, BrokerAccount, BrokerSyncLog


class BrokerSyncAPITestCase(TestCase):
    """Tests for broker synchronization API endpoints."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
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
            broker_type='SAXO',
            name='Test Saxo Account',
            account_id='TEST123',
            environment='simulation',
            is_sandbox=True,
            saxo_client_id='test_client_id',
            saxo_client_secret='test_client_secret',
            saxo_redirect_uri='https://test.com/callback',
            saxo_environment='simulation',
        )
        
        self.binance_account = BrokerAccount.objects.create(
            user=self.user,
            broker=self.binance_broker,
            broker_type='BINANCE',
            name='Test Binance Account',
            account_id='TEST456',
            environment='simulation',
            is_sandbox=True,
            binance_api_key='test_api_key',
            binance_api_secret='test_api_secret',
            binance_testnet=True,
        )
    
    def test_sync_assets_invalid_type(self):
        """Test sync with invalid sync type."""
        response = self.client.post(
            f'/api/broker-accounts/{self.saxo_account.id}/sync/',
            {'sync_type': 'INVALID'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('invalide', response.data.get('error', '').lower())
    
    def test_sync_assets_saxo(self):
        """Test syncing assets from Saxo account."""
        response = self.client.post(
            f'/api/broker-accounts/{self.saxo_account.id}/sync/',
            {'sync_type': 'ASSETS'},
            format='json'
        )
        
        # Should create a sync log even if sync fails (auth issue)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('sync_log', response.data)
        
        # Check that a sync log was created
        sync_log = BrokerSyncLog.objects.filter(
            broker_account=self.saxo_account,
            sync_type='ASSETS'
        ).first()
        self.assertIsNotNone(sync_log)
        self.assertIsNotNone(sync_log.started_at)
        # error_message should always be a string, never None
        self.assertIsInstance(sync_log.error_message, str)
    
    def test_sync_prices_binance(self):
        """Test syncing prices from Binance account."""
        response = self.client.post(
            f'/api/broker-accounts/{self.binance_account.id}/sync/',
            {'sync_type': 'PRICES'},
            format='json'
        )
        
        # Should create a sync log even if sync fails (auth issue)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('sync_log', response.data)
        
        # Check that a sync log was created
        sync_log = BrokerSyncLog.objects.filter(
            broker_account=self.binance_account,
            sync_type='PRICES'
        ).first()
        self.assertIsNotNone(sync_log)
        # error_message should always be a string, never None
        self.assertIsInstance(sync_log.error_message, str)
    
    def test_sync_positions(self):
        """Test syncing positions."""
        response = self.client.post(
            f'/api/broker-accounts/{self.saxo_account.id}/sync/',
            {'sync_type': 'POSITIONS'},
            format='json'
        )
        
        # Should create a sync log
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('sync_log', response.data)
        
        sync_log = BrokerSyncLog.objects.filter(
            broker_account=self.saxo_account,
            sync_type='POSITIONS'
        ).first()
        self.assertIsNotNone(sync_log)
        self.assertIsInstance(sync_log.error_message, str)
    
    def test_sync_trades(self):
        """Test syncing trades."""
        response = self.client.post(
            f'/api/broker-accounts/{self.binance_account.id}/sync/',
            {'sync_type': 'TRADES'},
            format='json'
        )
        
        # Should create a sync log
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('sync_log', response.data)
        
        sync_log = BrokerSyncLog.objects.filter(
            broker_account=self.binance_account,
            sync_type='TRADES'
        ).first()
        self.assertIsNotNone(sync_log)
        self.assertIsInstance(sync_log.error_message, str)
    
    def test_sync_error_message_never_none(self):
        """Test that error_message is never None in sync logs."""
        # Test successful sync (should have empty string)
        response = self.client.post(
            f'/api/broker-accounts/{self.saxo_account.id}/sync/',
            {'sync_type': 'ASSETS'},
            format='json'
        )
        
        sync_log = BrokerSyncLog.objects.filter(
            broker_account=self.saxo_account,
            sync_type='ASSETS'
        ).order_by('-created_at').first()
        
        self.assertIsNotNone(sync_log)
        # error_message should be a string, never None
        self.assertIsInstance(sync_log.error_message, str)
        if sync_log.status == 'SUCCESS':
            self.assertEqual(sync_log.error_message, '')
    
    def test_sync_requires_authentication(self):
        """Test that sync requires authentication."""
        self.client.force_authenticate(user=None)
        
        response = self.client.post(
            f'/api/broker-accounts/{self.saxo_account.id}/sync/',
            {'sync_type': 'ASSETS'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_sync_updates_last_sync(self):
        """Test that sync updates the account's last_sync timestamp."""
        initial_sync = self.saxo_account.last_sync
        
        response = self.client.post(
            f'/api/broker-accounts/{self.saxo_account.id}/sync/',
            {'sync_type': 'ASSETS'},
            format='json'
        )
        
        self.saxo_account.refresh_from_db()
        
        # last_sync should be updated (even if sync fails)
        if response.status_code == status.HTTP_200_OK:
            self.assertIsNotNone(self.saxo_account.last_sync)
            if initial_sync:
                self.assertGreater(self.saxo_account.last_sync, initial_sync)

