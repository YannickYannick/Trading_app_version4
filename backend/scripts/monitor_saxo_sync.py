"""
Script de monitoring pour la synchronisation Saxo Bank

Fichier: backend/scripts/monitor_saxo_sync.py
Usage:
    python manage.py shell < scripts/monitor_saxo_sync.py
    OU
    python scripts/monitor_saxo_sync.py (depuis le dossier backend)
"""
import os
import sys
import django

# Configuration Django
if __name__ == '__main__':
    # Ajouter le chemin du projet
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config_django.settings.development')
    django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from apps.trading.models import Position, Trade, BrokerAccount, Broker
from apps.trading.services.sync.position_sync_service import PositionSyncService
from apps.trading.services.sync.trade_sync_service import TradeSyncService
import logging

logger = logging.getLogger(__name__)


def check_saxo_sync_health():
    """Vérifie la santé de la synchronisation Saxo"""

    

    print("\n" + "="*60)

    print("🔍 MONITORING SYNCHRONISATION SAXO BANK")

    print("="*60 + "\n")

    

    # 1. Vérifier les comptes Saxo actifs

    print("📊 1. COMPTES SAXO ACTIFS")

    print("-" * 40)

    

    saxo_broker = Broker.objects.filter(broker_type='SAXO').first()

    if not saxo_broker:

        print("❌ Broker Saxo non trouvé dans la base")

        return

    

    saxo_accounts = BrokerAccount.objects.filter(

        broker=saxo_broker,

        is_active=True

    )

    

    print(f"Comptes actifs: {saxo_accounts.count()}")

    for account in saxo_accounts:

        print(f"  - User: {account.user.username}")

        print(f"    Broker: {account.broker.name if account.broker else 'N/A'}")

        print(f"    Account ID: {account.account_id or 'N/A'}")

        print(f"    Is Active: {account.is_active}")

        print()

    

    # 2. Vérifier les positions ouvertes

    print("\n📈 2. POSITIONS OUVERTES")

    print("-" * 40)

    

    for account in saxo_accounts:

        positions = Position.objects.filter(

            user=account.user,

            broker=saxo_broker,

            is_open=True

        )

        

        print(f"User: {account.user.username}")

        print(f"Positions ouvertes: {positions.count()}")

        

        if positions.exists():

            for pos in positions:

                pnl_sign = "+" if pos.pnl >= 0 else ""

                print(f"  - {pos.asset.symbol:8} {pos.side:5} "

                      f"qty={pos.quantity:8} "

                      f"entry={pos.entry_price:8.2f} "

                      f"current={pos.current_price:8.2f} "

                      f"PnL={pnl_sign}{pos.pnl:.2f} ({pnl_sign}{pos.pnl_percent:.2f}%)")

        else:

            print("  Aucune position ouverte")

        print()

    

    # 3. Vérifier les trades récents

    print("\n💼 3. TRADES RÉCENTS (7 derniers jours)")

    print("-" * 40)

    

    seven_days_ago = timezone.now() - timedelta(days=7)

    

    for account in saxo_accounts:

        trades = Trade.objects.filter(

            user=account.user,

            broker=saxo_broker,

            executed_at__gte=seven_days_ago

        ).order_by('-executed_at')

        

        print(f"User: {account.user.username}")

        print(f"Trades (7j): {trades.count()}")

        

        if trades.exists():

            for trade in trades[:10]:  # Afficher max 10

                print(f"  - {trade.executed_at.strftime('%Y-%m-%d %H:%M')} "

                      f"{trade.trade_type:4} {trade.quantity:8} "

                      f"{trade.asset.symbol:8} @ {trade.price:8.2f} "

                      f"fees={trade.fees:.2f}")

        else:

            print("  Aucun trade récent")

        print()

    

    # 4. Vérifier les erreurs de synchronisation

    print("\n⚠️  4. VALIDATION DES DONNÉES")

    print("-" * 40)

    

    for account in saxo_accounts:

        # Positions avec side invalide

        invalid_sides = Position.objects.filter(

            user=account.user,

            broker=saxo_broker,

            is_open=True

        ).exclude(side__in=['LONG', 'SHORT'])

        

        if invalid_sides.exists():

            print(f"❌ User {account.user.username}: {invalid_sides.count()} positions avec side invalide")

            for pos in invalid_sides:

                print(f"   - Position {pos.id}: side={pos.side}")

        else:

            print(f"✅ User {account.user.username}: Tous les sides sont valides")

        

        # Positions avec prix à 0

        zero_price = Position.objects.filter(

            user=account.user,

            broker=saxo_broker,

            is_open=True,

            entry_price=0

        )

        

        if zero_price.exists():

            print(f"⚠️  User {account.user.username}: {zero_price.count()} positions avec entry_price=0")

        

        # Trades avec type invalide

        invalid_trades = Trade.objects.filter(

            user=account.user,

            broker=saxo_broker

        ).exclude(trade_type__in=['BUY', 'SELL'])

        

        if invalid_trades.exists():

            print(f"❌ User {account.user.username}: {invalid_trades.count()} trades avec type invalide")

        

        print()

    

    # 5. Statistiques globales

    print("\n📊 5. STATISTIQUES GLOBALES")

    print("-" * 40)

    

    total_positions = Position.objects.filter(

        broker=saxo_broker,

        is_open=True

    ).count()

    

    total_trades = Trade.objects.filter(

        broker=saxo_broker

    ).count()

    

    recent_trades = Trade.objects.filter(

        broker=saxo_broker,

        executed_at__gte=seven_days_ago

    ).count()

    

    print(f"Total positions ouvertes: {total_positions}")

    print(f"Total trades (historique): {total_trades}")

    print(f"Trades récents (7j): {recent_trades}")

    

    # 6. Test de synchronisation

    print("\n\n🔄 6. TEST DE SYNCHRONISATION")

    print("-" * 40)

    

    for account in saxo_accounts:

        print(f"\nTest sync pour: {account.user.username}")

        

        try:

            # Test sync positions

            pos_service = PositionSyncService(user=account.user)

            result = pos_service.sync(broker_account=account)

            

            print(f"✅ Positions sync: {result.get('created', 0)} created, {result.get('updated', 0)} updated")

            

            # Test sync trades

            trade_service = TradeSyncService(user=account.user)

            result = trade_service.sync(broker_account=account)

            

            print(f"✅ Trades sync: {result.get('created', 0)} created, {result.get('updated', 0)} updated")

            

        except Exception as e:

            print(f"❌ Erreur de sync: {str(e)}")

    

    print("\n" + "="*60)

    print("✅ MONITORING TERMINÉ")

    print("="*60 + "\n")


def validate_broker_position_fields():
    """Valide que BrokerPosition utilise les bons champs"""
    from apps.trading.brokers.base import BrokerPosition
    from decimal import Decimal

    

    print("\n" + "="*60)

    print("🔍 VALIDATION DES CHAMPS BrokerPosition")

    print("="*60 + "\n")

    

    try:

        # Test avec les bons paramètres

        position = BrokerPosition(

            symbol='AAPL',

            quantity=Decimal('100'),

            entry_price=Decimal('150.50'),

            current_price=Decimal('155.00'),

            side='LONG',

            pnl=Decimal('450.00'),

            pnl_percent=Decimal('2.99'),

            broker_position_id='TEST123',

            raw_data={'currency': 'USD'}

        )

        print("✅ BrokerPosition créé avec succès")

        print(f"   Symbol: {position.symbol}")

        print(f"   Side: {position.side}")

        print(f"   Entry Price: {position.entry_price}")

        print(f"   PnL: {position.pnl}")

        

    except TypeError as e:

        print(f"❌ Erreur BrokerPosition: {e}")

    

    print()


def validate_broker_trade_fields():
    """Valide que BrokerTrade utilise les bons champs"""
    from apps.trading.brokers.base import BrokerTrade
    from decimal import Decimal

    

    print("\n" + "="*60)

    print("🔍 VALIDATION DES CHAMPS BrokerTrade")

    print("="*60 + "\n")

    

    try:

        # Test avec les bons paramètres

        trade = BrokerTrade(

            symbol='AAPL',

            trade_type='BUY',

            quantity=Decimal('100'),

            price=Decimal('150.50'),

            fees=Decimal('2.50'),

            executed_at='2025-12-29T10:30:00Z',

            broker_trade_id='TRD123',

            raw_data={'order_id': 'ORD456'}

        )

        print("✅ BrokerTrade créé avec succès")

        print(f"   Symbol: {trade.symbol}")

        print(f"   Type: {trade.trade_type}")

        print(f"   Price: {trade.price}")

        print(f"   Fees: {trade.fees}")

        print(f"   Executed At: {trade.executed_at}")

        

    except TypeError as e:

        print(f"❌ Erreur BrokerTrade: {e}")

    

    print()


if __name__ == '__main__':

    # Valider les dataclasses

    validate_broker_position_fields()

    validate_broker_trade_fields()

    

    # Vérifier la santé de la sync

    check_saxo_sync_health()

