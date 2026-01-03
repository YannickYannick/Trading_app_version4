"""
Exemple d'utilisation de la reconstruction de positions depuis les transactions.

Ce script montre comment utiliser le système de reconstruction pour remplacer
complètement l'usage de hist/v3/positions.
"""
import os
import sys
import django

# Configuration Django
if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config_django.settings.development')
    django.setup()

from django.contrib.auth.models import User
from apps.trading.models import BrokerAccount, Broker
from apps.trading.services.saxo_historical_positions import SaxoHistoricalPositionsService
from apps.trading.services.saxo_position_reconstructor import PositionReconstructor


def example_simple_reconstruction():
    """Exemple simple de reconstruction"""
    print("\n" + "="*60)
    print("📝 EXEMPLE 1: Reconstruction Simple")
    print("="*60 + "\n")
    
    # Transactions d'exemple (format Saxo API)
    transactions = [
        {
            'TradeId': 'TRADE_EXAMPLE_001',
            'Uic': 211,
            'TransactionType': 'Trade',
            'ToOpenOrClose': 'Open',
            'TradeDate': '2025-01-01T10:00:00Z',
            'Amount': 100,
            'Price': 150.50,
            'AmountAccountValue': 15050.00,
        },
        {
            'TradeId': 'TRADE_EXAMPLE_001',
            'Uic': 211,
            'TransactionType': 'Commission',
            'FundingSubType': 'Commission',
            'AmountAccountValue': -2.50,
        },
        {
            'TradeId': 'TRADE_EXAMPLE_001',
            'Uic': 211,
            'TransactionType': 'Trade',
            'ToOpenOrClose': 'Close',
            'TradeDate': '2025-01-02T15:00:00Z',
            'Amount': -100,
            'Price': 155.00,
            'AmountAccountValue': -15500.00,
        },
        {
            'TradeId': 'TRADE_EXAMPLE_001',
            'Uic': 211,
            'TransactionType': 'Commission',
            'FundingSubType': 'Commission',
            'AmountAccountValue': -2.50,
        },
    ]
    
    # Reconstruire
    reconstructor = PositionReconstructor(transactions)
    positions = reconstructor.reconstruct()
    
    print(f"Nombre de positions reconstruites: {len(positions)}\n")
    
    for pos in positions:
        print(f"Position {pos.trade_id} (UIC: {pos.uic}):")
        print(f"  Direction: {pos.direction}")
        print(f"  Quantité: {pos.quantity}")
        print(f"  Ouverture: {pos.open_date} @ {pos.open_price}")
        print(f"  Fermeture: {pos.close_date} @ {pos.close_price}")
        print(f"  P&L Brut: {pos.gross_pnl}")
        print(f"  Frais: {pos.total_fees}")
        print(f"  Funding: {pos.total_funding}")
        print(f"  P&L Net: {pos.net_pnl}")
        print(f"  Fermée: {pos.is_closed}")
        print()


def example_partial_close():
    """Exemple avec clôture partielle"""
    print("\n" + "="*60)
    print("📝 EXEMPLE 2: Clôture Partielle")
    print("="*60 + "\n")
    
    transactions = [
        # Ouverture
        {
            'TradeId': 'TRADE_PARTIAL_001',
            'Uic': 212,
            'TransactionType': 'Trade',
            'ToOpenOrClose': 'Open',
            'TradeDate': '2025-01-01T10:00:00Z',
            'Amount': 100,
            'Price': 100.00,
        },
        # Fermeture partielle (50%)
        {
            'TradeId': 'TRADE_PARTIAL_001',
            'Uic': 212,
            'TransactionType': 'Trade',
            'ToOpenOrClose': 'Close',
            'TradeDate': '2025-01-02T10:00:00Z',
            'Amount': -50,
            'Price': 105.00,
        },
        # Fermeture finale (50%)
        {
            'TradeId': 'TRADE_PARTIAL_001',
            'Uic': 212,
            'TransactionType': 'Trade',
            'ToOpenOrClose': 'Close',
            'TradeDate': '2025-01-03T10:00:00Z',
            'Amount': -50,
            'Price': 110.00,
        },
    ]
    
    reconstructor = PositionReconstructor(transactions)
    positions = reconstructor.reconstruct()
    
    pos = positions[0]
    print(f"Position avec clôture partielle:")
    print(f"  Nombre de clôtures: {pos.partial_closes}")
    print(f"  Quantité fermée: 100 (50 + 50)")
    print(f"  Prix moyen de fermeture: {pos.close_price}")
    print(f"  P&L Brut: {pos.gross_pnl}")
    print()


def example_with_service():
    """Exemple d'utilisation avec le service complet"""
    print("\n" + "="*60)
    print("📝 EXEMPLE 3: Utilisation avec Service")
    print("="*60 + "\n")
    
    # Récupérer le compte Saxo
    saxo_broker = Broker.objects.filter(broker_type='SAXO').first()
    if not saxo_broker:
        print("❌ Aucun compte Saxo trouvé")
        return
    
    accounts = BrokerAccount.objects.filter(
        broker=saxo_broker,
        is_active=True
    )
    
    if not accounts.exists():
        print("❌ Aucun compte Saxo actif trouvé")
        return
    
    account = accounts.first()
    user = account.user
    
    print(f"Utilisation du compte: {user.username}\n")
    
    # Créer le service
    service = SaxoHistoricalPositionsService(user=user)
    
    try:
        # Récupérer les positions fermées
        print("Récupération des positions fermées depuis les transactions...")
        closed_positions = service.get_closed_positions(
            broker_account=account,
            from_date='2025-01-01',
            limit=100
        )
        
        print(f"✅ {len(closed_positions)} positions fermées reconstruites\n")
        
        # Afficher les 5 premières
        for i, pos in enumerate(closed_positions[:5], 1):
            print(f"{i}. Trade {pos.trade_id} (UIC: {pos.uic}):")
            print(f"   {pos.direction} {pos.quantity} - P&L Net: {pos.net_pnl}")
        
        # Calculer les métriques de performance
        print("\n📊 Calcul des métriques de performance...")
        metrics = service.get_performance_metrics(
            broker_account=account,
            from_date='2025-01-01'
        )
        
        print(f"\nMétriques de performance:")
        print(f"  Total trades: {metrics['total_trades']}")
        print(f"  Winrate: {metrics['winrate']:.2f}%")
        print(f"  Trades gagnants: {metrics['winning_trades']}")
        print(f"  Trades perdants: {metrics['losing_trades']}")
        print(f"  P&L Net Total: {metrics['total_net_pnl']:.2f}")
        print(f"  Frais totaux: {metrics['total_fees']:.2f}")
        print(f"  Funding total: {metrics['total_funding']:.2f}")
        print(f"  P&L moyen par trade: {metrics['avg_net_pnl_per_trade']:.2f}")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    # Exemple 1: Reconstruction simple
    example_simple_reconstruction()
    
    # Exemple 2: Clôture partielle
    example_partial_close()
    
    # Exemple 3: Utilisation avec service (nécessite un compte Saxo configuré)
    example_with_service()
    
    print("\n" + "="*60)
    print("✅ EXEMPLES TERMINÉS")
    print("="*60 + "\n")











