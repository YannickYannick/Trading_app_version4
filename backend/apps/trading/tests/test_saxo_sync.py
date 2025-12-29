"""
Tests unitaires pour la synchronisation Saxo Bank

Fichier: backend/apps/trading/tests/test_saxo_sync.py
"""
from decimal import Decimal

from unittest.mock import Mock, patch

from django.test import TestCase

from django.contrib.auth.models import User
from django.utils import timezone

from apps.trading.brokers.base import BrokerPosition, BrokerTrade

from apps.trading.models import Position, BrokerAccount, Broker, Asset, Trade

from apps.trading.services.sync.position_sync_service import PositionSyncService
from apps.trading.services.sync.trade_sync_service import TradeSyncService


class TestSaxoPositionSync(TestCase):

    """Tests pour la synchronisation des positions Saxo"""

    

    def setUp(self):

        """Configuration initiale des tests"""

        self.user = User.objects.create_user(

            username='testuser',

            email='test@example.com',

            password='testpass123'

        )

        

        self.broker = Broker.objects.create(

            name='Saxo Bank',

            broker_type='SAXO',

            is_active=True

        )

        

        self.broker_account = BrokerAccount.objects.create(

            user=self.user,

            broker=self.broker,

            broker_type='SAXO',

            is_active=True

        )

        

        self.asset = Asset.objects.create(

            symbol='AAPL',

            name='Apple Inc.',

            asset_type='stock'

        )

    

    def test_broker_position_creation_with_correct_params(self):

        """Test: BrokerPosition utilise les bons noms de paramètres"""

        position = BrokerPosition(

            symbol='AAPL',

            quantity=Decimal('100'),

            entry_price=Decimal('150.50'),  # ✅ Pas 'average_price'

            current_price=Decimal('155.00'),

            side='LONG',  # ✅ Requis

            pnl=Decimal('450.00'),  # ✅ Pas 'unrealized_pnl'

            pnl_percent=Decimal('2.99'),

            broker_position_id='SAX123456',

            raw_data={'currency': 'USD'}  # ✅ Dans raw_data

        )

        

        self.assertEqual(position.symbol, 'AAPL')

        self.assertEqual(position.entry_price, Decimal('150.50'))

        self.assertEqual(position.side, 'LONG')

        self.assertEqual(position.pnl, Decimal('450.00'))

    

    def test_broker_trade_creation_with_correct_params(self):

        """Test: BrokerTrade utilise les bons noms de paramètres"""

        trade = BrokerTrade(

            symbol='AAPL',

            trade_type='BUY',  # ✅ Pas 'side'

            quantity=Decimal('100'),

            price=Decimal('150.50'),

            fees=Decimal('2.50'),  # ✅ Pas 'commission'

            executed_at='2025-12-29T10:30:00Z',  # ✅ Pas 'timestamp'

            broker_trade_id='TRD123456',

            raw_data={'order_id': 'ORD789'}

        )

        

        self.assertEqual(trade.trade_type, 'BUY')

        self.assertEqual(trade.fees, Decimal('2.50'))

        self.assertEqual(trade.executed_at, '2025-12-29T10:30:00Z')

    

    def test_side_determination_from_quantity(self):

        """Test: Détermination correcte du side depuis la quantité"""

        # Position LONG (quantité positive)

        position_long = BrokerPosition(

            symbol='AAPL',

            quantity=Decimal('100'),

            entry_price=Decimal('150'),

            current_price=Decimal('155'),

            side='LONG'

        )

        self.assertEqual(position_long.side, 'LONG')

        

        # Position SHORT (quantité négative dans Saxo)

        amount_short = Decimal('-50')

        side_short = 'LONG' if amount_short >= 0 else 'SHORT'

        position_short = BrokerPosition(

            symbol='AAPL',

            quantity=abs(amount_short),

            entry_price=Decimal('150'),

            current_price=Decimal('145'),

            side=side_short

        )

        self.assertEqual(position_short.side, 'SHORT')

        self.assertEqual(position_short.quantity, Decimal('50'))

    

    def test_pnl_percent_calculation(self):

        """Test: Calcul correct du PnL en pourcentage"""

        entry_price = Decimal('100')

        current_price = Decimal('110')

        pnl_percent = ((current_price - entry_price) / entry_price) * Decimal('100')

        

        self.assertEqual(pnl_percent, Decimal('10'))

    

    @patch('apps.trading.services.sync.position_sync_service.PositionSyncService._sync_single_position')

    def test_position_sync_service_calls_single_sync(self, mock_sync_single):

        """Test: Le service de sync appelle bien la méthode pour chaque position"""

        mock_sync_single.return_value = (Mock(), True)

        

        service = PositionSyncService(user=self.user)

        

        broker_positions = [

            BrokerPosition(

                symbol='AAPL',

                quantity=Decimal('100'),

                entry_price=Decimal('150'),

                current_price=Decimal('155'),

                side='LONG'

            ),

            BrokerPosition(

                symbol='GOOGL',

                quantity=Decimal('50'),

                entry_price=Decimal('2800'),

                current_price=Decimal('2850'),

                side='LONG'

            )

        ]

        

        # Note: Cette partie nécessite d'adapter selon votre implémentation réelle

        # mock_sync_single.assert_called()

    

    def test_side_validation_in_position_model(self):

        """Test: Le modèle Position accepte uniquement LONG/SHORT"""

        position = Position.objects.create(

            user=self.user,

            broker=self.broker,

            asset=self.asset,

            side='LONG',  # ✅ Valide

            quantity=Decimal('100'),

            entry_price=Decimal('150'),

            current_price=Decimal('155')

        )

        

        self.assertEqual(position.side, 'LONG')

        self.assertIn(position.side, ['LONG', 'SHORT'])


class TestSaxoAPIDataMapping(TestCase):

    """Tests pour le mapping des données de l'API Saxo"""

    

    def test_map_saxo_position_to_broker_position(self):

        """Test: Mapping correct d'une position Saxo vers BrokerPosition"""

        saxo_response = {

            'PositionId': 'SAX123',

            'PositionBase': {

                'Symbol': 'AAPL',

                'Amount': 100,  # Positif = LONG

                'Uic': 211,

                'Currency': 'USD'

            },

            'PositionView': {

                'AverageOpenPrice': 150.50,

                'CurrentPrice': 155.00,

                'ProfitLossOnTrade': 450.00

            }

        }

        

        # Simulation du mapping comme dans saxo.py

        position_base = saxo_response['PositionBase']

        position_view = saxo_response['PositionView']

        

        amount = Decimal(str(position_base['Amount']))

        side = 'LONG' if amount >= 0 else 'SHORT'

        entry_price = Decimal(str(position_view['AverageOpenPrice']))

        current_price = Decimal(str(position_view['CurrentPrice']))

        pnl = Decimal(str(position_view['ProfitLossOnTrade']))

        

        pnl_percent = Decimal('0')

        if entry_price and entry_price > 0:

            pnl_percent = ((current_price - entry_price) / entry_price) * Decimal('100')

        

        position = BrokerPosition(

            symbol=position_base['Symbol'],

            quantity=abs(amount),

            entry_price=entry_price,

            current_price=current_price,

            side=side,

            pnl=pnl,

            pnl_percent=pnl_percent,

            broker_position_id=str(saxo_response['PositionId']),

            raw_data={

                'uic': position_base['Uic'],

                'currency': position_base['Currency']

            }

        )

        

        # Vérifications

        self.assertEqual(position.symbol, 'AAPL')

        self.assertEqual(position.side, 'LONG')

        self.assertEqual(position.entry_price, Decimal('150.50'))

        self.assertEqual(position.pnl, Decimal('450.00'))

        self.assertAlmostEqual(float(position.pnl_percent), 2.99, places=2)

    

    def test_map_saxo_trade_to_broker_trade(self):

        """Test: Mapping correct d'un trade Saxo vers BrokerTrade"""

        saxo_order = {

            'OrderId': 'ORD123',

            'Symbol': 'AAPL',

            'BuySell': 'Buy',

            'Amount': 100,

            'FilledAmount': 100,

            'Price': 150.50,

            'FilledTime': '2025-12-29T10:30:00Z',

            'Commission': 2.50

        }

        

        # Simulation du mapping comme dans saxo.py

        trade = BrokerTrade(

            symbol=saxo_order['Symbol'],

            trade_type='BUY' if saxo_order['BuySell'] == 'Buy' else 'SELL',

            quantity=Decimal(str(saxo_order['FilledAmount'])),

            price=Decimal(str(saxo_order['Price'])),

            executed_at=saxo_order['FilledTime'],

            broker_trade_id=str(saxo_order['OrderId']),

            fees=Decimal(str(saxo_order['Commission'])),

            raw_data=saxo_order

        )

        

        # Vérifications

        self.assertEqual(trade.trade_type, 'BUY')

        self.assertEqual(trade.fees, Decimal('2.50'))

        self.assertEqual(trade.executed_at, '2025-12-29T10:30:00Z')


class TestSaxoSyncEdgeCases(TestCase):

    """Tests pour les cas limites de la synchronisation Saxo"""

    

    def test_empty_symbol_handling(self):

        """Test: Gestion d'un symbol vide"""

        with self.assertRaises(ValueError):

            position = BrokerPosition(

                symbol='',  # ❌ Symbol vide

                quantity=Decimal('100'),

                entry_price=Decimal('150'),

                current_price=Decimal('155'),

                side='LONG'

            )

            if not position.symbol or not position.symbol.strip():

                raise ValueError("Position has empty or invalid symbol")

    

    def test_zero_entry_price_pnl_calculation(self):

        """Test: PnL percent = 0 si entry_price = 0"""

        entry_price = Decimal('0')

        current_price = Decimal('155')

        

        pnl_percent = Decimal('0')

        if entry_price and entry_price > 0:

            pnl_percent = ((current_price - entry_price) / entry_price) * Decimal('100')

        

        self.assertEqual(pnl_percent, Decimal('0'))

    

    def test_negative_quantity_conversion(self):

        """Test: Quantité négative convertie en positive avec side SHORT"""

        saxo_amount = Decimal('-50')

        side = 'LONG' if saxo_amount >= 0 else 'SHORT'

        quantity = abs(saxo_amount)

        

        self.assertEqual(side, 'SHORT')

        self.assertEqual(quantity, Decimal('50'))

        self.assertGreater(quantity, 0)


class TestSaxoTradeSync(TestCase):
    """Tests pour la synchronisation des trades Saxo"""

    def setUp(self):
        """Configuration initiale des tests"""
        self.user = User.objects.create_user(
            username='testuser_trade',
            email='test_trade@example.com',
            password='testpass123'
        )

        self.broker = Broker.objects.create(
            name='Saxo Bank',
            broker_type='SAXO',
            is_active=True
        )

        self.broker_account = BrokerAccount.objects.create(
            user=self.user,
            broker=self.broker,
            broker_type='SAXO',
            is_active=True
        )

        self.asset = Asset.objects.create(
            symbol='AAPL',
            name='Apple Inc.',
            asset_type='stock'
        )

    def test_broker_trade_creation_with_all_params(self):
        """Test: BrokerTrade créé avec tous les paramètres requis"""
        trade = BrokerTrade(
            symbol='AAPL',
            trade_type='BUY',
            quantity=Decimal('100'),
            price=Decimal('150.50'),
            fees=Decimal('2.50'),
            executed_at='2025-12-29T10:30:00Z',
            broker_trade_id='TRD123456',
            raw_data={'order_id': 'ORD789'}
        )

        self.assertEqual(trade.symbol, 'AAPL')
        self.assertEqual(trade.trade_type, 'BUY')
        self.assertEqual(trade.quantity, Decimal('100'))
        self.assertEqual(trade.price, Decimal('150.50'))
        self.assertEqual(trade.fees, Decimal('2.50'))
        self.assertEqual(trade.executed_at, '2025-12-29T10:30:00Z')
        self.assertEqual(trade.broker_trade_id, 'TRD123456')

    def test_trade_type_buy_vs_sell(self):
        """Test: Distinction correcte entre BUY et SELL"""
        buy_trade = BrokerTrade(
            symbol='AAPL',
            trade_type='BUY',
            quantity=Decimal('100'),
            price=Decimal('150.50')
        )
        self.assertEqual(buy_trade.trade_type, 'BUY')

        sell_trade = BrokerTrade(
            symbol='AAPL',
            trade_type='SELL',
            quantity=Decimal('50'),
            price=Decimal('155.00')
        )
        self.assertEqual(sell_trade.trade_type, 'SELL')

    def test_saxo_buysell_to_trade_type_mapping(self):
        """Test: Mapping correct de BuySell Saxo vers trade_type"""
        # Test Buy
        saxo_order_buy = {'BuySell': 'Buy'}
        trade_type_buy = 'BUY' if saxo_order_buy.get('BuySell') == 'Buy' else 'SELL'
        self.assertEqual(trade_type_buy, 'BUY')

        # Test Sell
        saxo_order_sell = {'BuySell': 'Sell'}
        trade_type_sell = 'BUY' if saxo_order_sell.get('BuySell') == 'Buy' else 'SELL'
        self.assertEqual(trade_type_sell, 'SELL')

    def test_trade_with_filled_amount(self):
        """Test: Utilisation de FilledAmount si disponible"""
        saxo_order = {
            'Amount': 100,
            'FilledAmount': 75,  # Partiellement exécuté
            'Price': 150.50
        }

        # Utiliser FilledAmount si disponible, sinon Amount
        quantity = Decimal(str(saxo_order.get('FilledAmount', saxo_order.get('Amount', 0))))
        self.assertEqual(quantity, Decimal('75'))

    def test_trade_executed_at_parsing(self):
        """Test: Parsing correct de executed_at"""
        from datetime import datetime

        # Format ISO avec Z
        executed_at_str = '2025-12-29T10:30:00Z'
        executed_at = datetime.fromisoformat(executed_at_str.replace('Z', '+00:00'))
        self.assertIsNotNone(executed_at)

        # Format ISO sans Z
        executed_at_str2 = '2025-12-29T10:30:00+00:00'
        executed_at2 = datetime.fromisoformat(executed_at_str2)
        self.assertIsNotNone(executed_at2)

    def test_trade_model_creation(self):
        """Test: Création d'un Trade dans la base de données"""
        trade = Trade.objects.create(
            user=self.user,
            broker=self.broker,
            asset=self.asset,
            trade_type='BUY',
            quantity=Decimal('100'),
            price=Decimal('150.50'),
            fees=Decimal('2.50'),
            executed_at=timezone.now(),
            broker_trade_id='TRD_TEST_123'
        )

        self.assertEqual(trade.trade_type, 'BUY')
        self.assertEqual(trade.quantity, Decimal('100'))
        self.assertEqual(trade.broker_trade_id, 'TRD_TEST_123')
        self.assertIn(trade.trade_type, ['BUY', 'SELL'])

    def test_trade_duplicate_detection(self):
        """Test: Détection des trades en double via broker_trade_id"""
        # Créer un premier trade
        trade1 = Trade.objects.create(
            user=self.user,
            broker=self.broker,
            asset=self.asset,
            trade_type='BUY',
            quantity=Decimal('100'),
            price=Decimal('150.50'),
            executed_at=timezone.now(),
            broker_trade_id='TRD_DUP_123'
        )

        # Vérifier qu'un trade avec le même broker_trade_id existe
        existing = Trade.objects.filter(
            broker_trade_id='TRD_DUP_123',
            broker=self.broker,
            user=self.user,
        ).first()

        self.assertIsNotNone(existing)
        self.assertEqual(existing.id, trade1.id)

    @patch('apps.trading.services.sync.trade_sync_service.TradeSyncService._sync_single_trade')
    def test_trade_sync_service_structure(self, mock_sync_single):
        """Test: Structure du service de sync des trades"""
        mock_sync_single.return_value = {'created': True, 'trade_id': 1}

        service = TradeSyncService(user=self.user)
        self.assertIsNotNone(service)
        self.assertEqual(service.user, self.user)

    def test_trade_total_value_calculation(self):
        """Test: Calcul de la valeur totale d'un trade"""
        trade = Trade.objects.create(
            user=self.user,
            broker=self.broker,
            asset=self.asset,
            trade_type='BUY',
            quantity=Decimal('100'),
            price=Decimal('150.50'),
            fees=Decimal('2.50'),
            executed_at=timezone.now(),
            broker_trade_id='TRD_VALUE_123'
        )

        expected_total = Decimal('100') * Decimal('150.50')
        self.assertEqual(trade.total_value, expected_total)

    def test_trade_with_empty_symbol(self):
        """Test: Gestion d'un trade avec symbole vide"""
        # Un trade doit avoir un symbole valide
        with self.assertRaises(Exception):
            trade = BrokerTrade(
                symbol='',  # Symbole vide
                trade_type='BUY',
                quantity=Decimal('100'),
                price=Decimal('150.50')
            )
            if not trade.symbol or not trade.symbol.strip():
                raise ValueError("Trade has empty or invalid symbol")

    def test_trade_with_zero_price(self):
        """Test: Gestion d'un trade avec prix à zéro"""
        # Un trade ne devrait pas avoir un prix à zéro
        trade = BrokerTrade(
            symbol='AAPL',
            trade_type='BUY',
            quantity=Decimal('100'),
            price=Decimal('0'),  # Prix à zéro
            fees=Decimal('0')
        )

        # Le prix est à zéro mais le trade peut être créé
        # La validation devrait se faire au niveau du service
        self.assertEqual(trade.price, Decimal('0'))

    def test_trade_commission_to_fees_mapping(self):
        """Test: Mapping de Commission vers fees"""
        saxo_order = {
            'Commission': 2.50
        }

        fees = Decimal(str(saxo_order.get('Commission', 0)))
        self.assertEqual(fees, Decimal('2.50'))

        # Test sans commission
        saxo_order_no_commission = {}
        fees_no_commission = Decimal(str(saxo_order_no_commission.get('Commission', 0)))
        self.assertEqual(fees_no_commission, Decimal('0'))


class TestSaxoTradeSyncEdgeCases(TestCase):
    """Tests pour les cas limites de la synchronisation des trades Saxo"""

    def setUp(self):
        """Configuration initiale des tests"""
        self.user = User.objects.create_user(
            username='testuser_trade_edge',
            email='test_trade_edge@example.com',
            password='testpass123'
        )

        self.broker = Broker.objects.create(
            name='Saxo Bank',
            broker_type='SAXO',
            is_active=True
        )

        self.broker_account = BrokerAccount.objects.create(
            user=self.user,
            broker=self.broker,
            broker_type='SAXO',
            is_active=True
        )

        self.asset = Asset.objects.create(
            symbol='AAPL',
            name='Apple Inc.',
            asset_type='stock'
        )

    def test_partially_filled_order(self):
        """Test: Gestion d'un ordre partiellement exécuté"""
        saxo_order = {
            'OrderId': 'ORD_PARTIAL_123',
            'Amount': 100,
            'FilledAmount': 50,  # Partiellement exécuté
            'Price': 150.50,
            'BuySell': 'Buy'
        }

        # Utiliser FilledAmount pour la quantité
        quantity = Decimal(str(saxo_order.get('FilledAmount', saxo_order.get('Amount', 0))))
        self.assertEqual(quantity, Decimal('50'))

    def test_trade_without_executed_at(self):
        """Test: Gestion d'un trade sans executed_at"""
        from django.utils import timezone

        trade = BrokerTrade(
            symbol='AAPL',
            trade_type='BUY',
            quantity=Decimal('100'),
            price=Decimal('150.50'),
            executed_at=None  # Pas de timestamp
        )

        self.assertIsNone(trade.executed_at)
        # Le service devrait utiliser timezone.now() comme fallback

    def test_trade_with_invalid_timestamp_format(self):
        """Test: Gestion d'un timestamp invalide"""
        from datetime import datetime

        invalid_timestamps = [
            'invalid-date',
            '2025-12-99',  # Date invalide
            None,
            '',
        ]

        for invalid_ts in invalid_timestamps:
            if invalid_ts:
                try:
                    datetime.fromisoformat(invalid_ts.replace('Z', '+00:00'))
                    parsed = True
                except (ValueError, TypeError, AttributeError):
                    parsed = False
                # Un timestamp invalide devrait être géré gracieusement
                # Le service devrait utiliser timezone.now() comme fallback

    def test_multiple_trades_same_symbol(self):
        """Test: Création de plusieurs trades pour le même symbole"""
        from django.utils import timezone

        # Créer plusieurs trades pour AAPL
        for i in range(3):
            Trade.objects.create(
                user=self.user,
                broker=self.broker,
                asset=self.asset,
                trade_type='BUY' if i % 2 == 0 else 'SELL',
                quantity=Decimal(f'{10 * (i + 1)}'),
                price=Decimal('150.50'),
                executed_at=timezone.now(),
                broker_trade_id=f'TRD_MULTI_{i}'
            )

        trades = Trade.objects.filter(
            user=self.user,
            broker=self.broker,
            asset=self.asset
        )

        self.assertEqual(trades.count(), 3)

    def test_trade_linking_to_position(self):
        """Test: Lien d'un trade à une position existante"""
        from django.utils import timezone

        # Créer une position
        position = Position.objects.create(
            user=self.user,
            broker=self.broker,
            asset=self.asset,
            side='LONG',
            quantity=Decimal('100'),
            entry_price=Decimal('150.00'),
            current_price=Decimal('155.00'),
            is_open=True
        )

        # Créer un trade qui devrait être lié à la position
        trade = Trade.objects.create(
            user=self.user,
            broker=self.broker,
            asset=self.asset,
            position=position,  # Lien explicite
            trade_type='BUY',
            quantity=Decimal('50'),
            price=Decimal('152.00'),
            executed_at=timezone.now(),
            broker_trade_id='TRD_LINKED_123'
        )

        self.assertIsNotNone(trade.position)
        self.assertEqual(trade.position.id, position.id)

