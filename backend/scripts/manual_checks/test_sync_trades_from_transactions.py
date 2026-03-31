"""
Script de test pour synchroniser les trades depuis les transactions Saxo
"""
import os
import sys
import django

# Configuration Django
if __name__ == '__main__':
    _BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if _BACKEND_ROOT not in sys.path:
        sys.path.insert(0, _BACKEND_ROOT)
    os.chdir(_BACKEND_ROOT)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config_django.settings.development')
    django.setup()

from django.contrib.auth.models import User
from apps.trading.models import BrokerAccount, Broker, Trade
from apps.trading.services.sync.trade_sync_service import TradeSyncService
from apps.trading.services.broker_service import BrokerService


def test_sync_trades():
    """Tester la synchronisation des trades depuis les transactions"""
    print("\n" + "="*60)
    print("TEST: Synchronisation des trades depuis transactions")
    print("="*60 + "\n")
    
    # Récupérer un compte Saxo
    saxo_broker = Broker.objects.filter(broker_type='SAXO').first()
    if not saxo_broker:
        print("❌ Aucun broker Saxo trouvé")
        return False
    
    accounts = BrokerAccount.objects.filter(
        broker=saxo_broker,
        is_active=True
    )
    
    if not accounts.exists():
        print("❌ Aucun compte Saxo actif trouvé")
        return False
    
    account = accounts.first()
    user = account.user
    
    print(f"✅ Compte trouvé: {account.name} (User: {user.username})")
    
    # Vérifier les trades existants avant
    trades_before = Trade.objects.filter(
        user=user,
        broker=saxo_broker
    ).count()
    print(f"📊 Trades avant synchronisation: {trades_before}")
    
    # Tester d'abord la récupération des trades depuis les transactions
    print("\n1️⃣ Test de récupération des trades depuis transactions...")
    try:
        service = BrokerService(user)
        broker = service.get_broker_instance(account, use_cache=False)
        
        if not broker.authenticate():
            print("❌ Échec de l'authentification")
            return False
        
        # Récupérer les trades (utilise maintenant les transactions)
        broker_trades = broker.get_trades(limit=50)
        print(f"   ✅ {len(broker_trades)} trade(s) récupéré(s) depuis les transactions")
        
        if broker_trades:
            print(f"\n   Exemple de trade:")
            t = broker_trades[0]
            print(f"   - Symbole: {t.symbol}")
            print(f"   - Type: {t.trade_type}")
            print(f"   - Quantité: {t.quantity}")
            print(f"   - Prix: {t.price}")
            print(f"   - ID: {t.broker_trade_id}")
            print(f"   - Date: {t.executed_at}")
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Tester la synchronisation complète
    print("\n2️⃣ Test de synchronisation complète...")
    try:
        sync_service = TradeSyncService(user)
        
        # Synchroniser les trades (utilise get_trades() qui utilise maintenant les transactions)
        result = sync_service.sync(
            broker_account=account,
            limit=100,
        )
        
        print(f"\n   ✅ Synchronisation terminée:")
        print(f"   - Créés: {result.get('created', 0)}")
        print(f"   - Mis à jour: {result.get('updated', 0)}")
        print(f"   - Ignorés: {result.get('skipped', 0)}")
        print(f"   - Succès: {result.get('success', False)}")
        
        # Vérifier les trades après
        trades_after = Trade.objects.filter(
            user=user,
            broker=saxo_broker
        ).count()
        print(f"\n📊 Trades après synchronisation: {trades_after}")
        print(f"   (+{trades_after - trades_before} nouveaux trades)")
        
        # Afficher quelques trades
        if trades_after > 0:
            print(f"\n   Derniers trades synchronisés:")
            recent_trades = Trade.objects.filter(
                user=user,
                broker=saxo_broker
            ).order_by('-executed_at')[:5]
            
            for trade in recent_trades:
                print(f"   - {trade.symbol} {trade.trade_type} {trade.quantity} @ {trade.price} le {trade.executed_at}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erreur lors de la synchronisation: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_sync_trades()
    print("\n" + "="*60)
    if success:
        print("✅ TEST RÉUSSI: Les trades sont maintenant synchronisés dans la base")
        print("   Vous pouvez les voir dans /admin/trading/trade/")
    else:
        print("❌ TEST ÉCHOUÉ")
    print("="*60 + "\n")
    sys.exit(0 if success else 1)











