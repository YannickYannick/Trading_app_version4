"""
Script de test pour vérifier l'endpoint saxo-transactions
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
from apps.trading.api.views import BrokerAccountViewSet
from rest_framework.test import APIRequestFactory
from rest_framework.test import force_authenticate


def test_saxo_transactions_endpoint():
    """Tester l'endpoint saxo-transactions"""
    print("\n" + "="*60)
    print("TEST: Endpoint saxo-transactions")
    print("="*60 + "\n")
    
    # Récupérer un compte Saxo
    saxo_broker = Broker.objects.filter(broker_type='SAXO').first()
    if not saxo_broker:
        print("❌ Aucun broker Saxo trouvé dans la base")
        return False
    
    saxo_accounts = BrokerAccount.objects.filter(
        broker=saxo_broker,
        is_active=True
    )
    
    if not saxo_accounts.exists():
        print("❌ Aucun compte Saxo actif trouvé")
        return False
    
    account = saxo_accounts.first()
    user = account.user
    
    print(f"✅ Compte Saxo trouvé:")
    print(f"   - ID: {account.id}")
    print(f"   - Nom: {account.name or account.account_name}")
    print(f"   - User: {user.username}")
    print()
    
    # Tester directement la méthode du ViewSet
    factory = APIRequestFactory()
    request = factory.get(
        f'/api/broker-accounts/{account.id}/saxo-transactions/',
        {
            'limit': 10,
        }
    )
    force_authenticate(request, user=user)
    
    viewset = BrokerAccountViewSet()
    viewset.kwargs = {'pk': account.id}
    viewset.request = request
    
    try:
        response = viewset.saxo_transactions(request, pk=account.id)
        
        print(f"✅ Endpoint appelé avec succès")
        print(f"   - Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.data
            print(f"   - Success: {data.get('success')}")
            print(f"   - Count: {data.get('count')}")
            print(f"   - Transactions: {len(data.get('transactions', []))} trouvée(s)")
            
            if data.get('transactions'):
                print(f"\n   Première transaction:")
                txn = data['transactions'][0]
                print(f"   - TradeId: {txn.get('TradeId')}")
                print(f"   - UIC: {txn.get('Uic')}")
                print(f"   - Type: {txn.get('TransactionType')}")
                print(f"   - ToOpenOrClose: {txn.get('ToOpenOrClose')}")
                print(f"   - Date: {txn.get('TradeDate')}")
            else:
                print(f"   ⚠️  Aucune transaction retournée")
                
            return True
        else:
            print(f"   ❌ Erreur: {response.data}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_saxo_transactions_endpoint()
    sys.exit(0 if success else 1)


