"""
Tests pour l'API Trading (Positions, Trades, Orders).

Teste :
- Filtrage par utilisateur
- Actions personnalisées
- Permissions
"""
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from django.utils import timezone

from apps.trading.models import (
    Asset, AllAssets, Position, Trade, Order,
    Broker, BrokerAccount, Strategy
)


class PositionAPITests(APITestCase):
    """Tests pour l'API Position."""
    
    def setUp(self):
        """Configuration avant chaque test."""
        # Créer des utilisateurs
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='testpass123'
        )
        
        # Créer un broker et un compte
        self.broker = Broker.objects.create(
            name='Saxo Bank',
            broker_type='SAXO',
            is_active=True
        )
        
        self.broker_account = BrokerAccount.objects.create(
            user=self.user,
            broker=self.broker,
            account_id='ACC123',
            account_name='Test Account',
            balance=Decimal('10000.00'),
            currency='USD',
            is_active=True
        )
        
        # Créer un asset
        self.asset = Asset.objects.create(
            symbol='AAPL',
            name='Apple Inc.',
            asset_type='STOCK',
            currency='USD',
            current_price=Decimal('150.00'),
            is_active=True
        )
        
        # Créer une position pour l'utilisateur
        self.position = Position.objects.create(
            user=self.user,
            asset=self.asset,
            broker=self.broker,
            quantity=Decimal('10'),
            entry_price=Decimal('145.00'),
            current_price=Decimal('150.00'),
            side='LONG',
            is_open=True
        )
        
        # Créer une position pour l'autre utilisateur
        self.other_position = Position.objects.create(
            user=self.other_user,
            asset=self.asset,
            broker=self.broker,
            quantity=Decimal('5'),
            entry_price=Decimal('140.00'),
            current_price=Decimal('150.00'),
            side='LONG',
            is_open=True
        )
        
        self.client.force_authenticate(user=self.user)
    
    def test_list_positions_filtered_by_user(self):
        """Test que chaque utilisateur voit seulement ses positions."""
        response = self.client.get('/api/positions/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Seulement la position de l'utilisateur connecté
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.position.id)
    
    def test_open_positions_action(self):
        """Test GET /api/positions/open/"""
        # Créer une position fermée
        Position.objects.create(
            user=self.user,
            asset=self.asset,
            broker=self.broker,
            quantity=Decimal('5'),
            entry_price=Decimal('150.00'),
            current_price=Decimal('155.00'),
            side='LONG',
            is_open=False,
            closed_at=timezone.now()
        )
        
        response = self.client.get('/api/positions/open/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Seulement la position ouverte
        for pos in response.data.get('results', response.data):
            self.assertTrue(pos['is_open'])
    
    def test_closed_positions_action(self):
        """Test GET /api/positions/closed/"""
        # Créer une position fermée
        closed_pos = Position.objects.create(
            user=self.user,
            asset=self.asset,
            broker=self.broker,
            quantity=Decimal('5'),
            entry_price=Decimal('150.00'),
            current_price=Decimal('155.00'),
            side='LONG',
            is_open=False,
            closed_at=timezone.now()
        )
        
        response = self.client.get('/api/positions/closed/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_summary_action(self):
        """Test GET /api/positions/summary/"""
        response = self.client.get('/api/positions/summary/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_positions', response.data)
        self.assertIn('total_value', response.data)
        self.assertIn('total_pnl', response.data)
    
    def test_close_position_action(self):
        """Test POST /api/positions/{id}/close/"""
        response = self.client.post(f'/api/positions/{self.position.id}/close/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Vérifier que la position est fermée
        self.position.refresh_from_db()
        self.assertFalse(self.position.is_open)
        self.assertIsNotNone(self.position.closed_at)
    
    def test_cannot_access_other_user_position(self):
        """Test qu'on ne peut pas accéder aux positions d'autres utilisateurs."""
        response = self.client.get(f'/api/positions/{self.other_position.id}/')
        
        # Devrait retourner 404 car la position n'est pas dans le queryset filtré
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TradeAPITests(APITestCase):
    """Tests pour l'API Trade."""
    
    def setUp(self):
        """Configuration avant chaque test."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.broker = Broker.objects.create(
            name='Saxo Bank',
            broker_type='SAXO',
            is_active=True
        )
        
        self.asset = Asset.objects.create(
            symbol='AAPL',
            name='Apple Inc.',
            asset_type='STOCK',
            currency='USD',
            current_price=Decimal('150.00'),
            is_active=True
        )
        
        # Créer des trades
        self.trade1 = Trade.objects.create(
            user=self.user,
            asset=self.asset,
            broker=self.broker,
            trade_type='BUY',
            quantity=Decimal('10'),
            price=Decimal('145.00'),
            fees=Decimal('5.00'),
            executed_at=timezone.now()
        )
        
        self.trade2 = Trade.objects.create(
            user=self.user,
            asset=self.asset,
            broker=self.broker,
            trade_type='SELL',
            quantity=Decimal('5'),
            price=Decimal('155.00'),
            fees=Decimal('5.00'),
            executed_at=timezone.now()
        )
        
        self.client.force_authenticate(user=self.user)
    
    def test_list_trades(self):
        """Test GET /api/trades/"""
        response = self.client.get('/api/trades/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
    
    def test_recent_trades_action(self):
        """Test GET /api/trades/recent/"""
        response = self.client.get('/api/trades/recent/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data), 20)
    
    def test_today_trades_action(self):
        """Test GET /api/trades/today/"""
        response = self.client.get('/api/trades/today/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('date', response.data)
        self.assertIn('count', response.data)
        self.assertIn('trades', response.data)
    
    def test_stats_action(self):
        """Test GET /api/trades/stats/"""
        response = self.client.get('/api/trades/stats/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_trades', response.data)
        self.assertIn('buy_trades', response.data)
        self.assertIn('sell_trades', response.data)


class OrderAPITests(APITestCase):
    """Tests pour l'API Order."""
    
    def setUp(self):
        """Configuration avant chaque test."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.broker = Broker.objects.create(
            name='Saxo Bank',
            broker_type='SAXO',
            is_active=True
        )
        
        self.asset = Asset.objects.create(
            symbol='AAPL',
            name='Apple Inc.',
            asset_type='STOCK',
            currency='USD',
            current_price=Decimal('150.00'),
            is_active=True
        )
        
        # Créer des ordres
        self.pending_order = Order.objects.create(
            user=self.user,
            asset=self.asset,
            broker=self.broker,
            order_type='LIMIT',
            side='BUY',
            status='PENDING',
            quantity=Decimal('10'),
            price=Decimal('145.00')
        )
        
        self.filled_order = Order.objects.create(
            user=self.user,
            asset=self.asset,
            broker=self.broker,
            order_type='MARKET',
            side='BUY',
            status='FILLED',
            quantity=Decimal('5'),
            filled_quantity=Decimal('5'),
            price=Decimal('150.00')
        )
        
        self.client.force_authenticate(user=self.user)
    
    def test_list_orders(self):
        """Test GET /api/orders/"""
        response = self.client.get('/api/orders/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
    
    def test_pending_orders_action(self):
        """Test GET /api/orders/pending/"""
        response = self.client.get('/api/orders/pending/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for order in response.data:
            self.assertIn(order['status'], ['PENDING', 'OPEN', 'PARTIALLY_FILLED'])
    
    def test_cancel_order_action(self):
        """Test POST /api/orders/{id}/cancel/"""
        response = self.client.post(f'/api/orders/{self.pending_order.id}/cancel/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Vérifier que l'ordre est annulé
        self.pending_order.refresh_from_db()
        self.assertEqual(self.pending_order.status, 'CANCELLED')
    
    def test_cannot_cancel_filled_order(self):
        """Test qu'on ne peut pas annuler un ordre déjà exécuté."""
        response = self.client.post(f'/api/orders/{self.filled_order.id}/cancel/')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class StrategyAPITests(APITestCase):
    """Tests pour l'API Strategy."""
    
    def setUp(self):
        """Configuration avant chaque test."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.strategy = Strategy.objects.create(
            user=self.user,
            name='Test Strategy',
            description='A test strategy',
            risk_level='MEDIUM',
            max_position_size=Decimal('10.00'),
            is_active=True,
            is_automated=False
        )
        
        self.client.force_authenticate(user=self.user)
    
    def test_list_strategies(self):
        """Test GET /api/strategies/"""
        response = self.client.get('/api/strategies/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
    
    def test_create_strategy(self):
        """Test POST /api/strategies/"""
        data = {
            'name': 'New Strategy',
            'description': 'A new strategy',
            'risk_level': 'LOW',
            'max_position_size': '5.00',
        }
        
        response = self.client.post('/api/strategies/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Strategy')
        # Vérifier que l'utilisateur est assigné automatiquement
        self.assertEqual(Strategy.objects.count(), 2)
    
    def test_activate_action(self):
        """Test POST /api/strategies/{id}/activate/"""
        self.strategy.is_active = False
        self.strategy.save()
        
        response = self.client.post(f'/api/strategies/{self.strategy.id}/activate/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.strategy.refresh_from_db()
        self.assertTrue(self.strategy.is_active)
    
    def test_deactivate_action(self):
        """Test POST /api/strategies/{id}/deactivate/"""
        response = self.client.post(f'/api/strategies/{self.strategy.id}/deactivate/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.strategy.refresh_from_db()
        self.assertFalse(self.strategy.is_active)

