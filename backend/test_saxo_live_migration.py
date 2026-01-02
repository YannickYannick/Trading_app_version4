#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de test pour valider la migration Saxo SIM → LIVE.

Ce script teste :
1. Configuration de l'environnement LIVE
2. Récupération d'un prix via l'API LIVE
3. Vérification que les URLs sont correctes
"""
import os
import sys
import django

# Forcer UTF-8 pour Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config_django.settings.base')
django.setup()

import requests
import logging
from apps.trading.models import BrokerAccount
from apps.trading.services.broker_service import BrokerService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_live_configuration():
    """Test 1: Vérifier que la configuration utilise LIVE."""
    print("\n" + "="*60)
    print("TEST 1: Configuration LIVE")
    print("="*60)
    
    # Trouver un compte Saxo
    saxo_account = BrokerAccount.objects.filter(
        broker__broker_type='SAXO'
    ).first()
    
    if not saxo_account:
        print("❌ Aucun compte Saxo trouvé")
        return False
    
    print(f"✅ Compte trouvé: {saxo_account.name}")
    print(f"   Environment: {saxo_account.environment}")
    print(f"   Saxo Environment: {saxo_account.saxo_environment}")
    print(f"   API Base URL: {saxo_account.api_base_url or 'Non défini'}")
    
    # Vérifier via BrokerService
    try:
        broker_service = BrokerService(saxo_account.user)
        broker = broker_service.get_broker_instance(saxo_account, use_cache=False)
        
        print(f"\n   Configuration broker:")
        print(f"   Base URL: {broker.base_url}")
        print(f"   Auth URL: {broker.auth_url}")
        
        # Vérifier que c'est LIVE
        if 'sim/openapi' in broker.base_url or 'sim.logonvalidation' in broker.auth_url:
            print("   ❌ ERREUR: L'URL contient encore 'sim' - La migration n'a pas fonctionné !")
            return False
        elif 'openapi' in broker.base_url and 'sim' not in broker.base_url:
            print("   ✅ URL LIVE correcte")
            return True
        else:
            print("   ⚠️  URL inattendue")
            return False
            
    except Exception as e:
        print(f"   ❌ Erreur lors de la récupération du broker: {e}")
        return False


def test_live_authentication():
    """Test 2: Vérifier l'authentification avec LIVE."""
    print("\n" + "="*60)
    print("TEST 2: Authentification LIVE")
    print("="*60)
    
    saxo_account = BrokerAccount.objects.filter(
        broker__broker_type='SAXO'
    ).first()
    
    if not saxo_account:
        print("❌ Aucun compte Saxo trouvé")
        return False
    
    try:
        broker_service = BrokerService(saxo_account.user)
        broker = broker_service.get_broker_instance(saxo_account, use_cache=False)
        
        # Authentifier
        print("Authentification en cours...")
        if broker.authenticate():
            print("✅ Authentification réussie")
            print(f"   Token: {broker.access_token[:30]}...")
            print(f"   Expires at: {broker.token_expires_at}")
            return True
        else:
            print(f"❌ Authentification échouée: {broker.last_error}")
            print("\n⚠️  Vérifiez que:")
            print("   - Les credentials (CLIENT_ID, CLIENT_SECRET) sont ceux du compte LIVE")
            print("   - Le refresh_token est valide pour l'environnement LIVE")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_live_price_retrieval():
    """Test 3: Récupérer un prix via l'API LIVE."""
    print("\n" + "="*60)
    print("TEST 3: Récupération de prix LIVE")
    print("="*60)
    
    saxo_account = BrokerAccount.objects.filter(
        broker__broker_type='SAXO'
    ).first()
    
    if not saxo_account:
        print("❌ Aucun compte Saxo trouvé")
        return False
    
    try:
        broker_service = BrokerService(saxo_account.user)
        broker = broker_service.get_broker_instance(saxo_account, use_cache=False)
        
        if not broker.authenticate():
            print(f"❌ Authentification échouée: {broker.last_error}")
            return False
        
        # Tester avec EURUSD (UIC généralement 21 pour FxSpot)
        print("Test avec EURUSD (UIC: 21, AssetType: FxSpot)...")
        
        price = broker.get_asset_price(
            symbol='EURUSD',
            uic=21,
            asset_type='FxSpot'
        )
        
        if price:
            print(f"✅ Prix récupéré avec succès: {price}")
            return True
        else:
            print("❌ Aucun prix récupéré")
            
            # Essayer une requête directe pour voir la réponse
            print("\nTentative de requête directe pour diagnostic...")
            headers = {
                "Authorization": f"Bearer {broker.access_token}",
                "Accept": "application/json"
            }
            
            response = requests.get(
                f"{broker.base_url}/trade/v1/infoprices",
                params={
                    "Uic": 21,
                    "AssetType": "FxSpot",
                    "FieldGroups": "Quote"
                },
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Réponse API: {data}")
                
                if "Quote" in data:
                    quote = data.get("Quote", {})
                    amount = quote.get("Amount", 0)
                    price_type_ask = quote.get("PriceTypeAsk", "")
                    price_type_bid = quote.get("PriceTypeBid", "")
                    
                    if amount == 0 and price_type_ask == "NoAccess":
                        print("\n❌ ERREUR: 'NoAccess' détecté - Les permissions du compte LIVE ne permettent pas d'accéder aux prix")
                        print("   Actions recommandées:")
                        print("   1. Activer 'Market Data' dans SaxoTraderGO")
                        print("   2. Vérifier les permissions du compte LIVE")
                        print("   3. Confirmer que le token est bien généré pour LIVE")
            else:
                print(f"   Erreur HTTP {response.status_code}: {response.text[:200]}")
            
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Exécuter tous les tests."""
    print("\n" + "="*60)
    print("TEST DE VALIDATION - Migration Saxo SIM → LIVE")
    print("="*60)
    
    results = []
    
    # Test 1: Configuration
    results.append(("Configuration LIVE", test_live_configuration()))
    
    # Test 2: Authentification
    results.append(("Authentification LIVE", test_live_authentication()))
    
    # Test 3: Récupération de prix
    results.append(("Récupération de prix LIVE", test_live_price_retrieval()))
    
    # Résumé
    print("\n" + "="*60)
    print("RÉSUMÉ DES TESTS")
    print("="*60)
    
    for test_name, result in results:
        status = "✅ RÉUSSI" if result else "❌ ÉCHOUÉ"
        print(f"{status} - {test_name}")
    
    success_count = sum(1 for _, result in results if result)
    total_count = len(results)
    
    print(f"\nTotal: {success_count}/{total_count} test(s) réussi(s)")
    
    if success_count == total_count:
        print("\n🎉 Tous les tests sont passés ! La migration est réussie.")
    else:
        print("\n⚠️  Certains tests ont échoué. Vérifiez les points ci-dessus.")


if __name__ == '__main__':
    main()








