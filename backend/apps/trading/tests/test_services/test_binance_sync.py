"""
Tests for Binance synchronization services.

Tests position and trade synchronization specifically for Binance broker.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone

from apps.trading.models import Broker, BrokerAccount, Asset, Position, Trade, AllAssets
from apps.trading.services.sync.position_sync_service import PositionSyncService
from apps.trading.services.sync.trade_sync_service import TradeSyncService
from apps.trading.brokers.base import BrokerPosition, BrokerTrade


class BinancePositionSyncTestCase(TestCase):
    """Tests for Binance position synchronization."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create Binance broker
        self.binance_broker = Broker.objects.create(
            name='Binance',
            broker_type=Broker.BrokerType.BINANCE,
            is_active=True
        )
        
        # Create Binance account
        self.binance_account = BrokerAccount.objects.create(
            user=self.user,
            broker=self.binance_broker,
            account_id='binance-123',
            account_name='Binance Test Account',
            api_key='test_api_key',
            api_secret='test_api_secret',
            is_sandbox=True,
            is_active=True
        )
        
        # Create test assets
        self.btc_asset = Asset.objects.create(
            symbol='BTC',
            name='Bitcoin',
            asset_type='CRYPTO',
            currency='USDT'
        )
        
        self.eth_asset = Asset.objects.create(
            symbol='ETH',
            name='Ethereum',
            asset_type='CRYPTO',
            currency='USDT'
        )
        
        # Create AllAssets entries for Binance
        AllAssets.objects.create(
            symbol='BTC',
            name='Bitcoin',
            platform='BINANCE',
            asset_type='CRYPTO',
            currency='USDT',
            is_tradable=True
        )
        
        AllAssets.objects.create(
            symbol='ETH',
            name='Ethereum',
            platform='BINANCE',
            asset_type='CRYPTO',
            currency='USDT',
            is_tradable=True
        )
    
    @patch('apps.trading.brokers.factory.BrokerFactory.create_broker')
    def test_sync_positions_success(self, mock_create_broker):
        """Test successful position synchronization."""
        # Mock broker instance
        mock_broker = MagicMock()
        mock_broker.authenticate.return_value = True
        
        # Mock positions from Binance
        mock_positions = [
            BrokerPosition(
                symbol='BTC',
                quantity=Decimal('0.5'),
                entry_price=Decimal('50000'),  # Current price used as entry for spot
                current_price=Decimal('50000'),
                side='LONG',
                pnl=Decimal('0'),
                pnl_percent=Decimal('0'),
                broker_position_id='BTC',
                raw_data={'asset': 'BTC', 'free': '0.5', 'locked': '0'}
            ),
            BrokerPosition(
                symbol='ETH',
                quantity=Decimal('10'),
                entry_price=Decimal('3000'),
                current_price=Decimal('3000'),
                side='LONG',
                pnl=Decimal('0'),
                pnl_percent=Decimal('0'),
                broker_position_id='ETH',
                raw_data={'asset': 'ETH', 'free': '10', 'locked': '0'}
            ),
        ]
        mock_broker.get_positions.return_value = mock_positions
        mock_create_broker.return_value = mock_broker
        
        # Sync positions
        service = PositionSyncService(self.user)
        result = service.sync(self.binance_account)
        
        # Verify results
        self.assertTrue(result.get('success'))
        self.assertEqual(result.get('created'), 2)
        self.assertEqual(result.get('updated'), 0)
        
        # Verify positions were created
        positions = Position.objects.filter(
            user=self.user,
            broker=self.binance_broker,
            is_open=True
        )
        self.assertEqual(positions.count(), 2)
        
        btc_position = positions.get(asset__symbol='BTC')
        self.assertEqual(btc_position.quantity, Decimal('0.5'))
        self.assertEqual(btc_position.entry_price, Decimal('50000'))
        self.assertEqual(btc_position.current_price, Decimal('50000'))
        self.assertEqual(btc_position.side, 'LONG')
    
    @patch('apps.trading.brokers.factory.BrokerFactory.create_broker')
    def test_sync_positions_with_zero_entry_price(self, mock_create_broker):
        """Test position sync when entry_price is 0 (Binance spot balances)."""
        # Mock broker instance
        mock_broker = MagicMock()
        mock_broker.authenticate.return_value = True
        
        # Mock position with entry_price = 0 (typical for Binance spot)
        mock_positions = [
            BrokerPosition(
                symbol='BTC',
                quantity=Decimal('0.5'),
                entry_price=Decimal('0'),  # Zero entry price
                current_price=Decimal('50000'),  # But we have current price
                side='LONG',
                pnl=Decimal('0'),
                pnl_percent=Decimal('0'),
                broker_position_id='BTC',
                raw_data={'asset': 'BTC', 'free': '0.5', 'locked': '0'}
            ),
        ]
        mock_broker.get_positions.return_value = mock_positions
        mock_create_broker.return_value = mock_broker
        
        # Sync positions
        service = PositionSyncService(self.user)
        result = service.sync(self.binance_account)
        
        # Verify position was created with current_price as entry_price
        position = Position.objects.get(
            user=self.user,
            broker=self.binance_broker,
            asset__symbol='BTC',
            is_open=True
        )
        # Entry price should be set to current_price when entry_price is 0
        self.assertEqual(position.entry_price, Decimal('50000'))
        self.assertEqual(position.current_price, Decimal('50000'))
    
    @patch('apps.trading.brokers.factory.BrokerFactory.create_broker')
    def test_sync_positions_update_existing(self, mock_create_broker):
        """Test updating existing positions."""
        # Create existing position
        existing_position = Position.objects.create(
            user=self.user,
            broker=self.binance_broker,
            asset=self.btc_asset,
            quantity=Decimal('0.3'),
            entry_price=Decimal('45000'),
            current_price=Decimal('45000'),
            side='LONG',
            is_open=True
        )
        
        # Mock broker instance
        mock_broker = MagicMock()
        mock_broker.authenticate.return_value = True
        
        # Mock updated position
        mock_positions = [
            BrokerPosition(
                symbol='BTC',
                quantity=Decimal('0.5'),  # Updated quantity
                entry_price=Decimal('50000'),  # Updated price
                current_price=Decimal('50000'),
                side='LONG',
                pnl=Decimal('0'),
                pnl_percent=Decimal('0'),
                broker_position_id='BTC',
                raw_data={'asset': 'BTC', 'free': '0.5', 'locked': '0'}
            ),
        ]
        mock_broker.get_positions.return_value = mock_positions
        mock_create_broker.return_value = mock_broker
        
        # Sync positions
        service = PositionSyncService(self.user)
        result = service.sync(self.binance_account)
        
        # Verify position was updated
        self.assertEqual(result.get('updated'), 1)
        
        existing_position.refresh_from_db()
        self.assertEqual(existing_position.quantity, Decimal('0.5'))
        self.assertEqual(existing_position.entry_price, Decimal('50000'))
        self.assertEqual(existing_position.current_price, Decimal('50000'))


class BinanceTradeSyncTestCase(TestCase):
    """Tests for Binance trade synchronization."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create Binance broker
        self.binance_broker = Broker.objects.create(
            name='Binance',
            broker_type=Broker.BrokerType.BINANCE,
            is_active=True
        )
        
        # Create Binance account
        self.binance_account = BrokerAccount.objects.create(
            user=self.user,
            broker=self.binance_broker,
            account_id='binance-123',
            account_name='Binance Test Account',
            api_key='test_api_key',
            api_secret='test_api_secret',
            is_sandbox=True,
            is_active=True
        )
        
        # Create test assets
        self.btc_asset = Asset.objects.create(
            symbol='BTCUSDT',
            name='Bitcoin/USDT',
            asset_type='CRYPTO',
            currency='USDT'
        )
        
        self.eth_asset = Asset.objects.create(
            symbol='ETHEUR',
            name='Ethereum/EUR',
            asset_type='CRYPTO',
            currency='EUR'
        )
    
    @patch('apps.trading.brokers.factory.BrokerFactory.create_broker')
    def test_sync_trades_success(self, mock_create_broker):
        """Test successful trade synchronization."""
        # Mock broker instance
        mock_broker = MagicMock()
        mock_broker.authenticate.return_value = True
        
        # Mock trades from Binance
        executed_at = timezone.now() - timedelta(days=1)
        mock_trades = [
            BrokerTrade(
                symbol='BTCUSDT',
                side='buy',
                quantity=Decimal('0.1'),
                price=Decimal('50000'),
                fees=Decimal('5'),
                executed_at=executed_at,
                broker_trade_id='123456',
                raw_data={}
            ),
            BrokerTrade(
                symbol='ETHEUR',
                side='sell',
                quantity=Decimal('2'),
                price=Decimal('3000'),
                fees=Decimal('6'),
                executed_at=executed_at - timedelta(hours=2),
                broker_trade_id='123457',
                raw_data={}
            ),
        ]
        mock_broker.get_trades.return_value = mock_trades
        mock_create_broker.return_value = mock_broker
        
        # Sync trades
        service = TradeSyncService(self.user)
        result = service.sync(self.binance_account, limit=100)
        
        # Verify results
        self.assertTrue(result.get('success'))
        self.assertEqual(result.get('created'), 2)
        
        # Verify trades were created
        trades = Trade.objects.filter(
            user=self.user,
            broker=self.binance_broker
        )
        self.assertEqual(trades.count(), 2)
        
        btc_trade = trades.get(asset__symbol='BTCUSDT')
        self.assertEqual(btc_trade.trade_type, 'BUY')
        self.assertEqual(btc_trade.quantity, Decimal('0.1'))
        self.assertEqual(btc_trade.price, Decimal('50000'))
        self.assertEqual(btc_trade.fees, Decimal('5'))
        self.assertEqual(btc_trade.broker_trade_id, '123456')
    
    @patch('apps.trading.brokers.factory.BrokerFactory.create_broker')
    def test_sync_trades_skip_duplicates(self, mock_create_broker):
        """Test that duplicate trades are skipped."""
        # Create existing trade
        existing_trade = Trade.objects.create(
            user=self.user,
            broker=self.binance_broker,
            asset=self.btc_asset,
            trade_type='BUY',
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            fees=Decimal('5'),
            executed_at=timezone.now() - timedelta(days=1),
            broker_trade_id='123456'
        )
        
        # Mock broker instance
        mock_broker = MagicMock()
        mock_broker.authenticate.return_value = True
        
        # Mock same trade from Binance
        executed_at = timezone.now() - timedelta(days=1)
        mock_trades = [
            BrokerTrade(
                symbol='BTCUSDT',
                side='buy',
                quantity=Decimal('0.1'),
                price=Decimal('50000'),
                fees=Decimal('5'),
                executed_at=executed_at,
                broker_trade_id='123456',  # Same ID
                raw_data={}
            ),
        ]
        mock_broker.get_trades.return_value = mock_trades
        mock_create_broker.return_value = mock_broker
        
        # Sync trades
        service = TradeSyncService(self.user)
        result = service.sync(self.binance_account, limit=100)
        
        # Verify trade was skipped
        self.assertEqual(result.get('skipped'), 1)
        self.assertEqual(result.get('created'), 0)
        
        # Verify only one trade exists
        trades = Trade.objects.filter(
            user=self.user,
            broker=self.binance_broker
        )
        self.assertEqual(trades.count(), 1)
    
    @patch('apps.trading.brokers.factory.BrokerFactory.create_broker')
    def test_sync_trades_with_limit(self, mock_create_broker):
        """Test trade sync with limit parameter."""
        # Mock broker instance
        mock_broker = MagicMock()
        mock_broker.authenticate.return_value = True
        
        # Mock many trades
        executed_at = timezone.now() - timedelta(days=1)
        mock_trades = [
            BrokerTrade(
                symbol='BTCUSDT',
                side='buy',
                quantity=Decimal('0.1'),
                price=Decimal('50000'),
                fees=Decimal('5'),
                executed_at=executed_at - timedelta(hours=i),
                broker_trade_id=f'12345{i}',
                raw_data={}
            )
            for i in range(100)
        ]
        mock_broker.get_trades.return_value = mock_trades
        mock_create_broker.return_value = mock_broker
        
        # Sync with limit
        service = TradeSyncService(self.user)
        result = service.sync(self.binance_account, limit=50)
        
        # Verify limit was respected
        self.assertEqual(result.get('created'), 50)
        
        # Verify only 50 trades were created
        trades = Trade.objects.filter(
            user=self.user,
            broker=self.binance_broker
        )
        self.assertEqual(trades.count(), 50)
    
    @patch('apps.trading.brokers.factory.BrokerFactory.create_broker')
    def test_sync_trades_authentication_failure(self, mock_create_broker):
        """Test trade sync when authentication fails."""
        # Mock broker instance with failed authentication
        mock_broker = MagicMock()
        mock_broker.authenticate.return_value = False
        mock_create_broker.return_value = mock_broker
        
        # Sync trades
        service = TradeSyncService(self.user)
        
        # Should raise authentication error
        from apps.trading.exceptions import SyncAuthenticationError
        with self.assertRaises(SyncAuthenticationError):
            service.sync(self.binance_account)

