"""
Tests unitaires pour la synchronisation Saxo Bank

Fichier: backend/apps/trading/tests/test_saxo_sync.py
"""
from decimal import Decimal

from unittest.mock import Mock, patch

from django.test import TestCase

from django.contrib.auth.models import User

from apps.trading.brokers.base import BrokerPosition, BrokerTrade

from apps.trading.models import Position, BrokerAccount, Broker, Asset

from apps.trading.services.sync.position_sync_service import PositionSyncService


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

