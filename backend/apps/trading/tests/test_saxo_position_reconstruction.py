"""
Tests pour la reconstruction des positions Saxo à partir des transactions.
"""
from decimal import Decimal
from datetime import datetime
from django.test import TestCase
from django.contrib.auth.models import User

from apps.trading.services.saxo_position_reconstructor import (
    PositionReconstructor,
    ReconstructedPosition
)


class TestPositionReconstruction(TestCase):
    """Tests pour la reconstruction des positions"""

    def setUp(self):
        """Configuration des tests"""
        self.user = User.objects.create_user(
            username='test_reconstruct',
            email='test@example.com',
            password='testpass'
        )

    def test_simple_long_position_reconstruction(self):
        """Test: Reconstruction d'une position LONG simple (open → close)"""
        transactions = [
            {
                'TradeId': 'TRADE_001',
                'Uic': 211,
                'TransactionType': 'Trade',
                'ToOpenOrClose': 'Open',
                'TradeDate': '2025-01-01T10:00:00Z',
                'Amount': 100,
                'Price': 150.50,
                'AmountAccountValue': 15050.00,
            },
            {
                'TradeId': 'TRADE_001',
                'Uic': 211,
                'TransactionType': 'Commission',
                'FundingSubType': 'Commission',
                'AmountAccountValue': -2.50,
            },
            {
                'TradeId': 'TRADE_001',
                'Uic': 211,
                'TransactionType': 'Trade',
                'ToOpenOrClose': 'Close',
                'TradeDate': '2025-01-02T15:00:00Z',
                'Amount': -100,
                'Price': 155.00,
                'AmountAccountValue': -15500.00,
            },
            {
                'TradeId': 'TRADE_001',
                'Uic': 211,
                'TransactionType': 'Commission',
                'FundingSubType': 'Commission',
                'AmountAccountValue': -2.50,
            },
        ]

        reconstructor = PositionReconstructor(transactions)
        positions = reconstructor.reconstruct()

        self.assertEqual(len(positions), 1)
        pos = positions[0]

        self.assertEqual(pos.trade_id, 'TRADE_001')
        self.assertEqual(pos.uic, 211)
        self.assertEqual(pos.direction, 'LONG')
        self.assertEqual(pos.quantity, Decimal('0'))  # Position fermée
        self.assertTrue(pos.is_closed)
        self.assertEqual(pos.open_price, Decimal('150.50'))
        self.assertEqual(pos.close_price, Decimal('155.00'))
        self.assertEqual(pos.total_fees, Decimal('5.00'))  # 2.50 + 2.50

        # P&L brut = (155 - 150.50) * 100 = 450
        # (on utilise la quantité fermée, pas la quantité finale)
        expected_gross_pnl = (Decimal('155.00') - Decimal('150.50')) * Decimal('100')
        self.assertEqual(pos.gross_pnl, expected_gross_pnl)

        # P&L net = brut - frais = 450 - 5 = 445
        expected_net_pnl = expected_gross_pnl - Decimal('5.00')
        self.assertAlmostEqual(float(pos.net_pnl), float(expected_net_pnl), places=2)

    def test_short_position_reconstruction(self):
        """Test: Reconstruction d'une position SHORT"""
        transactions = [
            {
                'TradeId': 'TRADE_002',
                'Uic': 212,
                'TransactionType': 'Trade',
                'ToOpenOrClose': 'Open',
                'TradeDate': '2025-01-01T10:00:00Z',
                'Amount': -50,  # Négatif = SHORT
                'Price': 200.00,
                'AmountAccountValue': -10000.00,
            },
            {
                'TradeId': 'TRADE_002',
                'Uic': 212,
                'TransactionType': 'Trade',
                'ToOpenOrClose': 'Close',
                'TradeDate': '2025-01-02T15:00:00Z',
                'Amount': 50,
                'Price': 195.00,
                'AmountAccountValue': 9750.00,
            },
        ]

        reconstructor = PositionReconstructor(transactions)
        positions = reconstructor.reconstruct()

        self.assertEqual(len(positions), 1)
        pos = positions[0]

        self.assertEqual(pos.direction, 'SHORT')
        self.assertEqual(pos.quantity, Decimal('0'))
        self.assertTrue(pos.is_closed)

        # Pour SHORT: P&L = (open - close) * qty_fermée = (200 - 195) * 50 = 250
        # La quantité fermée est 50 (abs(50))
        expected_gross_pnl = (Decimal('200.00') - Decimal('195.00')) * Decimal('50')
        self.assertEqual(pos.gross_pnl, expected_gross_pnl)
        
        # Pour un SHORT fermé, la quantité finale devrait être 0
        # Mais dans le test, on ferme 50 alors qu'on avait ouvert -50
        # La quantité ouverte est -50 (négatif = SHORT)
        # La quantité fermée est 50
        # Donc quantité finale = abs(-50) - 50 = 0
        # Le test vérifie que la position est bien fermée (quantity = 0)
        # Mais le P&L se calcule sur la quantité fermée (50)
        if pos.is_closed:
            self.assertEqual(pos.quantity, Decimal('0'))

    def test_partial_close_reconstruction(self):
        """Test: Reconstruction avec clôture partielle"""
        transactions = [
            {
                'TradeId': 'TRADE_003',
                'Uic': 213,
                'TransactionType': 'Trade',
                'ToOpenOrClose': 'Open',
                'TradeDate': '2025-01-01T10:00:00Z',
                'Amount': 100,
                'Price': 100.00,
            },
            {
                'TradeId': 'TRADE_003',
                'Uic': 213,
                'TransactionType': 'Trade',
                'ToOpenOrClose': 'Close',
                'TradeDate': '2025-01-02T10:00:00Z',
                'Amount': -50,  # Fermeture partielle
                'Price': 105.00,
            },
            {
                'TradeId': 'TRADE_003',
                'Uic': 213,
                'TransactionType': 'Trade',
                'ToOpenOrClose': 'Close',
                'TradeDate': '2025-01-03T10:00:00Z',
                'Amount': -50,  # Fermeture complète
                'Price': 110.00,
            },
        ]

        reconstructor = PositionReconstructor(transactions)
        positions = reconstructor.reconstruct()

        self.assertEqual(len(positions), 1)
        pos = positions[0]

        self.assertEqual(pos.partial_closes, 2)
        self.assertEqual(pos.quantity, Decimal('0'))
        self.assertTrue(pos.is_closed)

        # Prix moyen de fermeture = (50*105 + 50*110) / 100 = 107.50
        expected_close_price = (Decimal('50') * Decimal('105') + Decimal('50') * Decimal('110')) / Decimal('100')
        self.assertEqual(pos.close_price, expected_close_price)

    def test_scaling_in_reconstruction(self):
        """Test: Reconstruction avec scaling in (ajouts multiples)"""
        transactions = [
            {
                'TradeId': 'TRADE_004',
                'Uic': 214,
                'TransactionType': 'Trade',
                'ToOpenOrClose': 'Open',
                'TradeDate': '2025-01-01T10:00:00Z',
                'Amount': 50,
                'Price': 100.00,
            },
            {
                'TradeId': 'TRADE_004',
                'Uic': 214,
                'TransactionType': 'Trade',
                'ToOpenOrClose': 'Open',
                'TradeDate': '2025-01-02T10:00:00Z',
                'Amount': 50,
                'Price': 102.00,  # Prix différent
            },
            {
                'TradeId': 'TRADE_004',
                'Uic': 214,
                'TransactionType': 'Trade',
                'ToOpenOrClose': 'Close',
                'TradeDate': '2025-01-03T10:00:00Z',
                'Amount': -100,
                'Price': 105.00,
            },
        ]

        reconstructor = PositionReconstructor(transactions)
        positions = reconstructor.reconstruct()

        self.assertEqual(len(positions), 1)
        pos = positions[0]

        self.assertEqual(pos.scaling_in_count, 1)  # Un ajout après l'ouverture initiale
        self.assertEqual(len(pos.open_transactions), 2)

        # Prix moyen d'ouverture = (50*100 + 50*102) / 100 = 101.00
        expected_open_price = (Decimal('50') * Decimal('100') + Decimal('50') * Decimal('102')) / Decimal('100')
        self.assertEqual(pos.open_price, expected_open_price)

    def test_fees_and_funding_calculation(self):
        """Test: Calcul correct des frais et funding"""
        transactions = [
            {
                'TradeId': 'TRADE_005',
                'Uic': 215,
                'TransactionType': 'Trade',
                'ToOpenOrClose': 'Open',
                'TradeDate': '2025-01-01T10:00:00Z',
                'Amount': 100,
                'Price': 100.00,
            },
            {
                'TradeId': 'TRADE_005',
                'Uic': 215,
                'TransactionType': 'Commission',
                'FundingSubType': 'Commission',
                'AmountAccountValue': -5.00,
            },
            {
                'TradeId': 'TRADE_005',
                'Uic': 215,
                'TransactionType': 'Funding',
                'FundingSubType': 'Funding',
                'AmountAccountValue': -10.00,  # Funding négatif (coût)
            },
            {
                'TradeId': 'TRADE_005',
                'Uic': 215,
                'TransactionType': 'Trade',
                'ToOpenOrClose': 'Close',
                'TradeDate': '2025-01-02T10:00:00Z',
                'Amount': -100,
                'Price': 110.00,
            },
            {
                'TradeId': 'TRADE_005',
                'Uic': 215,
                'TransactionType': 'Commission',
                'FundingSubType': 'Commission',
                'AmountAccountValue': -5.00,
            },
        ]

        reconstructor = PositionReconstructor(transactions)
        positions = reconstructor.reconstruct()

        self.assertEqual(len(positions), 1)
        pos = positions[0]

        # Frais totaux = 5 + 5 = 10
        self.assertEqual(pos.total_fees, Decimal('10.00'))

        # Funding total = -10
        self.assertEqual(pos.total_funding, Decimal('-10.00'))

        # P&L brut = (110 - 100) * 100 = 1000
        # (quantité fermée = 100)
        expected_gross_pnl = (Decimal('110') - Decimal('100')) * Decimal('100')
        self.assertEqual(pos.gross_pnl, expected_gross_pnl)

        # P&L net = 1000 - 10 - (-10) = 1000 - 10 + 10 = 1000
        expected_net_pnl = expected_gross_pnl - pos.total_fees - pos.total_funding
        self.assertAlmostEqual(float(pos.net_pnl), float(expected_net_pnl), places=2)

    def test_multiple_positions_grouping(self):
        """Test: Regroupement correct de plusieurs positions"""
        transactions = [
            # Position 1
            {
                'TradeId': 'TRADE_A',
                'Uic': 100,
                'TransactionType': 'Trade',
                'ToOpenOrClose': 'Open',
                'Amount': 50,
                'Price': 100.00,
            },
            {
                'TradeId': 'TRADE_A',
                'Uic': 100,
                'TransactionType': 'Trade',
                'ToOpenOrClose': 'Close',
                'Amount': -50,
                'Price': 105.00,
            },
            # Position 2
            {
                'TradeId': 'TRADE_B',
                'Uic': 200,
                'TransactionType': 'Trade',
                'ToOpenOrClose': 'Open',
                'Amount': 100,
                'Price': 200.00,
            },
            {
                'TradeId': 'TRADE_B',
                'Uic': 200,
                'TransactionType': 'Trade',
                'ToOpenOrClose': 'Close',
                'Amount': -100,
                'Price': 210.00,
            },
        ]

        reconstructor = PositionReconstructor(transactions)
        positions = reconstructor.reconstruct()

        self.assertEqual(len(positions), 2)

        # Vérifier que les positions sont bien séparées
        trade_ids = {pos.trade_id for pos in positions}
        self.assertEqual(trade_ids, {'TRADE_A', 'TRADE_B'})

        uics = {pos.uic for pos in positions}
        self.assertEqual(uics, {100, 200})


class TestReconstructedPosition(TestCase):
    """Tests pour la structure ReconstructedPosition"""

    def test_to_dict_serialization(self):
        """Test: Sérialisation en dictionnaire"""
        from datetime import datetime

        position = ReconstructedPosition(
            trade_id='TEST_001',
            uic=211,
            instrument_symbol='AAPL',
            direction='LONG',
            quantity=Decimal('0'),
            open_date=datetime(2025, 1, 1),
            open_price=Decimal('100.00'),
            close_date=datetime(2025, 1, 2),
            close_price=Decimal('110.00'),
            gross_pnl=Decimal('1000.00'),
            total_fees=Decimal('10.00'),
            total_funding=Decimal('-5.00'),
            net_pnl=Decimal('995.00'),
            is_closed=True,
        )

        result = position.to_dict()

        self.assertEqual(result['trade_id'], 'TEST_001')
        self.assertEqual(result['uic'], 211)
        self.assertEqual(result['direction'], 'LONG')
        self.assertEqual(result['gross_pnl'], 1000.0)
        self.assertEqual(result['net_pnl'], 995.0)
        self.assertTrue(result['is_closed'])

