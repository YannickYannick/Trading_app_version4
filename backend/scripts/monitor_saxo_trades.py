"""
Script de monitoring pour l'historique des trades Saxo Bank

Fichier: backend/scripts/monitor_saxo_trades.py
Usage:
    python scripts/monitor_saxo_trades.py (depuis le dossier backend)
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
from django.db.models import Q, Sum, Count, Avg, Max, Min
from datetime import timedelta
from decimal import Decimal
from apps.trading.models import Trade, BrokerAccount, Broker, Asset, Position
from apps.trading.services.sync.trade_sync_service import TradeSyncService
from apps.trading.brokers.base import BrokerTrade
import logging

logger = logging.getLogger(__name__)


def check_saxo_trades_health():
    """Vérifie la santé de l'historique des trades Saxo"""

    print("\n" + "="*60)
    print("🔍 MONITORING HISTORIQUE TRADES SAXO BANK")
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
        print()

    # 2. Statistiques globales des trades
    print("\n📊 2. STATISTIQUES GLOBALES")
    print("-" * 40)

    for account in saxo_accounts:
        all_trades = Trade.objects.filter(
            user=account.user,
            broker=saxo_broker
        )

        # Trades par période
        today = timezone.now().date()
        seven_days_ago = timezone.now() - timedelta(days=7)
        thirty_days_ago = timezone.now() - timedelta(days=30)

        trades_today = all_trades.filter(executed_at__date=today).count()
        trades_7d = all_trades.filter(executed_at__gte=seven_days_ago).count()
        trades_30d = all_trades.filter(executed_at__gte=thirty_days_ago).count()
        total_trades = all_trades.count()

        # Trades par type
        buy_trades = all_trades.filter(trade_type='BUY').count()
        sell_trades = all_trades.filter(trade_type='SELL').count()

        print(f"User: {account.user.username}")
        print(f"  Total trades: {total_trades}")
        print(f"  Trades aujourd'hui: {trades_today}")
        print(f"  Trades (7j): {trades_7d}")
        print(f"  Trades (30j): {trades_30d}")
        print(f"  Achat (BUY): {buy_trades}")
        print(f"  Vente (SELL): {sell_trades}")
        print()

    # 3. Trades récents détaillés
    print("\n💼 3. TRADES RÉCENTS (10 derniers)")
    print("-" * 40)

    seven_days_ago = timezone.now() - timedelta(days=7)

    for account in saxo_accounts:
        trades = Trade.objects.filter(
            user=account.user,
            broker=saxo_broker,
            executed_at__gte=seven_days_ago
        ).order_by('-executed_at')[:10]

        print(f"User: {account.user.username}")
        print(f"Trades récents: {trades.count()}")

        if trades.exists():
            print(f"\n{'Date':<20} {'Type':<6} {'Symbol':<10} {'Qty':<10} {'Price':<12} {'Fees':<10} {'Total':<12}")
            print("-" * 90)
            for trade in trades:
                total_value = trade.total_value
                print(f"{trade.executed_at.strftime('%Y-%m-%d %H:%M'):<20} "
                      f"{trade.trade_type:<6} "
                      f"{trade.asset.symbol:<10} "
                      f"{trade.quantity:<10} "
                      f"{trade.price:<12.2f} "
                      f"{trade.fees:<10.2f} "
                      f"{total_value:<12.2f}")
        else:
            print("  Aucun trade récent")
        print()

    # 4. Analyse par symbole
    print("\n📈 4. ANALYSE PAR SYMBOLE (Top 10)")
    print("-" * 40)

    for account in saxo_accounts:
        trades = Trade.objects.filter(
            user=account.user,
            broker=saxo_broker
        )

        # Grouper par symbole
        symbol_stats = trades.values('asset__symbol').annotate(
            total_trades=Count('id'),
            total_quantity=Sum('quantity'),
            avg_price=Avg('price'),
            total_fees=Sum('fees'),
            buy_count=Count('id', filter=Q(trade_type='BUY')),
            sell_count=Count('id', filter=Q(trade_type='SELL'))
        ).order_by('-total_trades')[:10]

        print(f"User: {account.user.username}")
        if symbol_stats:
            print(f"\n{'Symbol':<12} {'Trades':<8} {'Qty Totale':<12} {'Prix Moyen':<12} {'Fees Totales':<12} {'BUY':<6} {'SELL':<6}")
            print("-" * 90)
            for stat in symbol_stats:
                print(f"{stat['asset__symbol']:<12} "
                      f"{stat['total_trades']:<8} "
                      f"{stat['total_quantity'] or 0:<12.2f} "
                      f"{stat['avg_price'] or 0:<12.2f} "
                      f"{stat['total_fees'] or 0:<12.2f} "
                      f"{stat['buy_count']:<6} "
                      f"{stat['sell_count']:<6}")
        else:
            print("  Aucune statistique disponible")
        print()

    # 5. Validation des données
    print("\n⚠️  5. VALIDATION DES DONNÉES")
    print("-" * 40)

    for account in saxo_accounts:
        # Trades avec type invalide
        invalid_trades = Trade.objects.filter(
            user=account.user,
            broker=saxo_broker
        ).exclude(trade_type__in=['BUY', 'SELL'])

        if invalid_trades.exists():
            print(f"❌ User {account.user.username}: {invalid_trades.count()} trades avec type invalide")
            for trade in invalid_trades[:5]:
                print(f"   - Trade {trade.id}: type={trade.trade_type}")
        else:
            print(f"✅ User {account.user.username}: Tous les types de trades sont valides")

        # Trades sans symbole/asset
        trades_no_asset = Trade.objects.filter(
            user=account.user,
            broker=saxo_broker,
            asset__isnull=True
        )

        if trades_no_asset.exists():
            print(f"⚠️  User {account.user.username}: {trades_no_asset.count()} trades sans asset")

        # Trades avec prix à zéro
        zero_price_trades = Trade.objects.filter(
            user=account.user,
            broker=saxo_broker,
            price=0
        )

        if zero_price_trades.exists():
            print(f"⚠️  User {account.user.username}: {zero_price_trades.count()} trades avec prix=0")

        # Trades sans broker_trade_id (doublons potentiels)
        trades_no_broker_id = Trade.objects.filter(
            user=account.user,
            broker=saxo_broker,
            broker_trade_id=''
        )

        if trades_no_broker_id.exists():
            print(f"⚠️  User {account.user.username}: {trades_no_broker_id.count()} trades sans broker_trade_id")

        # Trades dupliqués (même broker_trade_id)
        duplicate_trades = Trade.objects.filter(
            user=account.user,
            broker=saxo_broker
        ).exclude(broker_trade_id='').values('broker_trade_id').annotate(
            count=Count('id')
        ).filter(count__gt=1)

        if duplicate_trades.exists():
            print(f"❌ User {account.user.username}: {duplicate_trades.count()} broker_trade_id dupliqués détectés")
            for dup in duplicate_trades[:5]:
                trades_with_id = Trade.objects.filter(
                    user=account.user,
                    broker=saxo_broker,
                    broker_trade_id=dup['broker_trade_id']
                )
                print(f"   - broker_trade_id={dup['broker_trade_id']}: {dup['count']} occurrences")

        print()

    # 6. Test de synchronisation
    print("\n🔄 6. TEST DE SYNCHRONISATION")
    print("-" * 40)

    for account in saxo_accounts:
        print(f"\nTest sync pour: {account.user.username}")

        try:
            # Compter les trades avant sync
            trades_before = Trade.objects.filter(
                user=account.user,
                broker=saxo_broker
            ).count()

            # Test sync trades
            trade_service = TradeSyncService(user=account.user)
            result = trade_service.sync(broker_account=account, limit=100)

            # Compter les trades après sync
            trades_after = Trade.objects.filter(
                user=account.user,
                broker=saxo_broker
            ).count()

            created = result.get('created', 0)
            updated = result.get('updated', 0)
            skipped = result.get('skipped', 0)

            print(f"✅ Sync terminé:")
            print(f"   - Trades avant: {trades_before}")
            print(f"   - Trades après: {trades_after}")
            print(f"   - Créés: {created}")
            print(f"   - Mis à jour: {updated}")
            print(f"   - Ignorés (doublons): {skipped}")
            print(f"   - Nouveaux: {trades_after - trades_before}")

        except Exception as e:
            print(f"❌ Erreur de sync: {str(e)}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*60)
    print("✅ MONITORING TERMINÉ")
    print("="*60 + "\n")


def validate_broker_trade_creation():
    """Valide la création correcte de BrokerTrade"""
    from apps.trading.brokers.base import BrokerTrade

    print("\n" + "="*60)
    print("🔍 VALIDATION CRÉATION BrokerTrade")
    print("="*60 + "\n")

    try:
        # Test avec tous les paramètres
        trade = BrokerTrade(
            symbol='AAPL',
            trade_type='BUY',
            quantity=Decimal('100'),
            price=Decimal('150.50'),
            fees=Decimal('2.50'),
            executed_at='2025-12-29T10:30:00Z',
            broker_trade_id='TRD_TEST_123',
            raw_data={'order_id': 'ORD456'}
        )

        print("✅ BrokerTrade créé avec succès")
        print(f"   Symbol: {trade.symbol}")
        print(f"   Type: {trade.trade_type}")
        print(f"   Quantity: {trade.quantity}")
        print(f"   Price: {trade.price}")
        print(f"   Fees: {trade.fees}")
        print(f"   Executed At: {trade.executed_at}")
        print(f"   Broker Trade ID: {trade.broker_trade_id}")

        # Test avec paramètres minimaux
        trade_min = BrokerTrade(
            symbol='GOOGL',
            trade_type='SELL',
            quantity=Decimal('50'),
            price=Decimal('2800.00')
        )

        print("\n✅ BrokerTrade créé avec paramètres minimaux")
        print(f"   Symbol: {trade_min.symbol}")
        print(f"   Type: {trade_min.trade_type}")
        print(f"   Fees (par défaut): {trade_min.fees}")

    except Exception as e:
        print(f"❌ Erreur BrokerTrade: {e}")
        import traceback
        traceback.print_exc()

    print()


def analyze_trade_performance():
    """Analyse la performance des trades"""
    print("\n" + "="*60)
    print("📊 ANALYSE DE PERFORMANCE DES TRADES")
    print("="*60 + "\n")

    saxo_broker = Broker.objects.filter(broker_type='SAXO').first()
    if not saxo_broker:
        print("❌ Broker Saxo non trouvé")
        return

    saxo_accounts = BrokerAccount.objects.filter(
        broker=saxo_broker,
        is_active=True
    )

    for account in saxo_accounts:
        trades = Trade.objects.filter(
            user=account.user,
            broker=saxo_broker
        )

        if not trades.exists():
            print(f"User {account.user.username}: Aucun trade trouvé")
            continue

        stats = trades.aggregate(
            total_trades=Count('id'),
            total_volume=Sum('quantity'),
            total_fees=Sum('fees'),
            avg_price=Avg('price'),
            max_price=Max('price'),
            min_price=Min('price'),
            buy_count=Count('id', filter=Q(trade_type='BUY')),
            sell_count=Count('id', filter=Q(trade_type='SELL'))
        )

        print(f"User: {account.user.username}")
        print(f"  Total trades: {stats['total_trades']}")
        print(f"  Volume total: {stats['total_volume'] or 0:.2f}")
        print(f"  Fees totales: {stats['total_fees'] or 0:.2f}")
        print(f"  Prix moyen: {stats['avg_price'] or 0:.2f}")
        print(f"  Prix max: {stats['max_price'] or 0:.2f}")
        print(f"  Prix min: {stats['min_price'] or 0:.2f}")
        print(f"  Achat (BUY): {stats['buy_count']}")
        print(f"  Vente (SELL): {stats['sell_count']}")
        print()


if __name__ == '__main__':
    # Valider la création de BrokerTrade
    validate_broker_trade_creation()

    # Vérifier la santé de l'historique
    check_saxo_trades_health()

    # Analyser la performance
    analyze_trade_performance()

