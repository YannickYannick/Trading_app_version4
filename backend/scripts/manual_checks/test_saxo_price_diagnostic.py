#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de diagnostic pour comprendre pourquoi les prix Saxo ne sont pas récupérés.

Ce script teste en détail :
1. Configuration du compte (environnement, URLs)
2. Token et authentification
3. Requête API directe pour voir la réponse complète
4. Comparaison SIM vs LIVE
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
_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)
os.chdir(_BACKEND_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config_django.settings.base')
django.setup()

import requests
import json
import logging
from apps.trading.models import BrokerAccount
from apps.trading.services.broker_service import BrokerService

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def print_section(title):
    """Affiche une section."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def test_account_configuration():
    """Test 1: Vérifier la configuration du compte."""
    print_section("TEST 1: Configuration du compte Saxo")
    
    saxo_account = BrokerAccount.objects.filter(
        broker__broker_type='SAXO'
    ).first()
    
    if not saxo_account:
        print("❌ Aucun compte Saxo trouvé")
        return None
    
    print(f"✅ Compte trouvé:")
    print(f"   ID: {saxo_account.id}")
    print(f"   Nom: {saxo_account.name}")
    print(f"   User: {saxo_account.user.username}")
    print(f"   Environment: {saxo_account.environment}")
    print(f"   Saxo Environment: {saxo_account.saxo_environment}")
    print(f"   Is Sandbox: {saxo_account.is_sandbox}")
    if hasattr(saxo_account, 'api_base_url'):
        print(f"   API Base URL: {saxo_account.api_base_url or 'Non défini'}")
    
    # ⚠️ DÉTECTION D'INCOHÉRENCE
    if saxo_account.environment == 'live' and saxo_account.saxo_environment == 'simulation':
        print(f"\n   ⚠️  INCOHÉRENCE DÉTECTÉE:")
        print(f"      environment='live' mais saxo_environment='simulation'")
        print(f"      → Le code utilise probablement saxo_environment, donc SIM sera utilisé !")
    if saxo_account.is_sandbox and saxo_account.environment == 'live':
        print(f"\n   ⚠️  INCOHÉRENCE DÉTECTÉE:")
        print(f"      is_sandbox=True mais environment='live'")
    print(f"   Client ID présent: {bool(saxo_account.saxo_client_id)}")
    print(f"   Client Secret présent: {bool(saxo_account.saxo_client_secret)}")
    print(f"   Access Token présent: {bool(saxo_account.saxo_access_token)}")
    print(f"   Refresh Token présent: {bool(saxo_account.saxo_refresh_token)}")
    
    if saxo_account.saxo_access_token:
        token_preview = saxo_account.saxo_access_token[:50] + "..."
        print(f"   Access Token preview: {token_preview}")
    
    return saxo_account


def test_broker_instance_configuration(account):
    """Test 2: Vérifier la configuration du broker instance."""
    print_section("TEST 2: Configuration du Broker Instance")
    
    try:
        broker_service = BrokerService(account.user)
        broker = broker_service.get_broker_instance(account, use_cache=False)
        
        print(f"✅ Broker instance créée:")
        print(f"   Base URL: {broker.base_url}")
        print(f"   Auth URL: {broker.auth_url}")
        print(f"   Client ID: {broker.client_id[:20]}..." if broker.client_id else "   Client ID: None")
        print(f"   Redirect URI: {broker.redirect_uri}")
        
        # Vérifier si c'est SIM ou LIVE
        if 'sim/openapi' in broker.base_url:
            print("\n   ⚠️  ATTENTION: L'URL contient 'sim/openapi' - Configuration SIM détectée !")
            print("   → Vérifiez que account.environment = 'live'")
        elif 'openapi' in broker.base_url and 'sim' not in broker.base_url:
            print("\n   ✅ Configuration LIVE correcte")
        else:
            print("\n   ⚠️  URL inattendue")
        
        if 'sim.logonvalidation' in broker.auth_url:
            print("\n   ⚠️  ATTENTION: Auth URL contient 'sim.logonvalidation' - Configuration SIM !")
        elif 'live.logonvalidation' in broker.auth_url:
            print("\n   ✅ Auth URL LIVE correcte")
        
        return broker
        
    except Exception as e:
        print(f"❌ Erreur lors de la création du broker: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_authentication(broker):
    """Test 3: Tester l'authentification."""
    print_section("TEST 3: Authentification")
    
    if not broker:
        print("❌ Broker non disponible")
        return False
    
    print("Tentative d'authentification...")
    
    try:
        # Vérifier l'état actuel
        is_authenticated_before = broker.is_authenticated()
        print(f"   Authentifié avant: {is_authenticated_before}")
        
        if broker.access_token:
            print(f"   Token existant: {broker.access_token[:30]}...")
        
        # Authentifier
        result = broker.authenticate()
        
        print(f"   Résultat authentification: {result}")
        print(f"   Authentifié après: {broker.is_authenticated()}")
        
        if result:
            print(f"   ✅ Nouveau token: {broker.access_token[:50]}...")
            print(f"   Expires at: {broker.token_expires_at}")
            print(f"   Base URL utilisée: {broker.base_url}")
            return True
        else:
            print(f"   ❌ Erreur d'authentification: {broker.last_error}")
            return False
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_direct_api_request(broker, uic=21, asset_type="FxSpot"):
    """Test 4: Faire une requête API directe pour voir la réponse complète."""
    print_section(f"TEST 4: Requête API directe (UIC: {uic}, Type: {asset_type})")
    
    if not broker or not broker.is_authenticated():
        print("❌ Broker non authentifié")
        return None
    
    print(f"URL utilisée: {broker.base_url}")
    print(f"Token utilisé: {broker.access_token[:30]}...")
    
    # Test avec différentes configurations de FieldGroups
    test_configs = [
        {"FieldGroups": "Quote"},
        {"FieldGroups": "PriceInfo,Quote"},
        {},  # Sans FieldGroups
    ]
    
    for i, params_base in enumerate(test_configs, 1):
        print(f"\n--- Test {i}: FieldGroups = {params_base.get('FieldGroups', 'Aucun')} ---")
        
        params = {
            "Uic": uic,
            "AssetType": asset_type,
            **params_base
        }
        
        headers = {
            "Authorization": f"Bearer {broker.access_token}",
            "Accept": "application/json"
        }
        
        url = f"{broker.base_url}/trade/v1/infoprices"
        
        print(f"   URL complète: {url}")
        print(f"   Paramètres: {params}")
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Réponse reçue:")
                print(f"   {json.dumps(data, indent=6)[:1000]}")  # Premiers 1000 caractères
                
                # Analyser la structure
                if "Data" in data:
                    print(f"\n   📊 Structure: Tableau 'Data' avec {len(data.get('Data', []))} élément(s)")
                    if data.get('Data'):
                        first = data['Data'][0]
                        print(f"   📊 Premier élément keys: {list(first.keys())}")
                        if 'Quote' in first:
                            quote = first['Quote']
                            print(f"   📊 Quote keys: {list(quote.keys())}")
                            print(f"   📊 Quote values: Amount={quote.get('Amount')}, PriceTypeAsk={quote.get('PriceTypeAsk')}, PriceTypeBid={quote.get('PriceTypeBid')}")
                else:
                    print(f"\n   📊 Structure: Pas de 'Data', keys racine: {list(data.keys())}")
                    if 'Quote' in data:
                        quote = data['Quote']
                        print(f"   📊 Quote keys: {list(quote.keys())}")
                        print(f"   📊 Quote values: Amount={quote.get('Amount')}, PriceTypeAsk={quote.get('PriceTypeAsk')}, PriceTypeBid={quote.get('PriceTypeBid')}")
                
                # Vérifier si c'est un problème de permissions
                if 'Quote' in data or (isinstance(data.get('Data'), list) and data.get('Data') and 'Quote' in data['Data'][0]):
                    quote = data.get('Quote') or (data.get('Data', [{}])[0].get('Quote', {}))
                    amount = quote.get('Amount', 0)
                    price_type_ask = quote.get('PriceTypeAsk', '')
                    price_type_bid = quote.get('PriceTypeBid', '')
                    
                    if amount == 0 and price_type_ask == "NoAccess":
                        print(f"\n   ❌ PROBLÈME IDENTIFIÉ: NoAccess détecté")
                        print(f"   → Le compte n'a pas les permissions pour accéder aux prix")
                        print(f"   → Vérifiez dans SaxoTraderGO: Market Data doit être activé")
                        print(f"   → Vérifiez que le token est bien généré pour l'environnement LIVE")
                
                return data
                
            elif response.status_code == 401:
                print(f"   ❌ 401 Unauthorized - Token invalide ou expiré")
                print(f"   → Le token est peut-être un token SIM qui ne fonctionne pas avec LIVE")
                print(f"   → Ou le token a expiré et doit être rafraîchi")
                
            else:
                print(f"   ❌ Erreur HTTP {response.status_code}")
                print(f"   Réponse: {response.text[:500]}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            import traceback
            traceback.print_exc()
    
    return None


def test_multiple_uics(broker):
    """Test 5: Tester plusieurs UICs pour voir si certains fonctionnent."""
    print_section("TEST 5: Test avec plusieurs UICs")
    
    if not broker or not broker.is_authenticated():
        print("❌ Broker non authentifié")
        return
    
    # UICs de test courants
    test_uics = [
        (21, "FxSpot", "EURUSD"),
        (1422226, "Stock", "AMD"),
        (712, "Stock", "UNH"),
    ]
    
    print("Test de plusieurs instruments:")
    
    for uic, asset_type, symbol in test_uics:
        print(f"\n   📊 {symbol} (UIC: {uic}, Type: {asset_type})")
        
        params = {
            "Uic": uic,
            "AssetType": asset_type,
            "FieldGroups": "Quote"
        }
        
        headers = {
            "Authorization": f"Bearer {broker.access_token}",
            "Accept": "application/json"
        }
        
        try:
            response = requests.get(
                f"{broker.base_url}/trade/v1/infoprices",
                params=params,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                quote = data.get('Quote') or (data.get('Data', [{}])[0].get('Quote', {}))
                amount = quote.get('Amount', 0)
                price_type_ask = quote.get('PriceTypeAsk', '')
                
                if amount > 0:
                    print(f"      ✅ Prix disponible: {amount}")
                elif price_type_ask == "NoAccess":
                    print(f"      ❌ NoAccess - Permissions manquantes")
                else:
                    print(f"      ⚠️  Pas de prix (Amount={amount}, PriceTypeAsk={price_type_ask})")
            else:
                print(f"      ❌ Erreur {response.status_code}")
                
        except Exception as e:
            print(f"      ❌ Exception: {e}")


def check_token_origin(account, broker):
    """Test 6: Vérifier si le token provient de SIM ou LIVE."""
    print_section("TEST 6: Vérification de l'origine du token")
    
    if not broker or not broker.access_token:
        print("❌ Pas de token disponible")
        return
    
    print(f"Token actuel: {broker.access_token[:100]}...")
    print(f"Base URL: {broker.base_url}")
    
    # Vérifier si le token a été généré avec SIM ou LIVE
    # Les tokens SIM ne fonctionnent généralement pas avec LIVE et vice versa
    
    print("\n⚠️  IMPORTANT:")
    print("   Si le compte a été migré vers LIVE mais que le token est ancien,")
    print("   il faut régénérer le token avec l'environnement LIVE.")
    print("   Les tokens SIM ne fonctionnent pas avec l'API LIVE.")
    
    print("\n   Pour régénérer le token:")
    print("   1. Aller sur http://localhost:3000/brokers")
    print("   2. Cliquer sur '🔄 Refresh Token' pour votre compte Saxo")
    print("   3. Ou déconnecter et reconnecter le compte")


def main():
    """Exécuter tous les tests de diagnostic."""
    print("\n" + "="*70)
    print("  DIAGNOSTIC COMPLET - Pourquoi les prix Saxo ne sont pas obtenus")
    print("="*70)
    
    # Test 1: Configuration du compte
    account = test_account_configuration()
    if not account:
        return
    
    # Test 2: Configuration du broker
    broker = test_broker_instance_configuration(account)
    if not broker:
        return
    
    # Test 3: Authentification
    auth_success = test_authentication(broker)
    
    # Test 4: Requête API directe
    if auth_success:
        test_direct_api_request(broker, uic=21, asset_type="FxSpot")
    
    # Test 5: Plusieurs UICs
    if auth_success:
        test_multiple_uics(broker)
    
    # Test 6: Vérification token
    if auth_success:
        check_token_origin(account, broker)
    
    # Résumé et recommandations
    print_section("RÉSUMÉ ET RECOMMANDATIONS")
    
    print("Vérifications à faire:")
    print("  1. ✅ Le compte utilise-t-il environment='live' ?")
    print(f"     → Actuel: {account.environment}")
    print("  2. ✅ Le broker instance utilise-t-il l'URL LIVE ?")
    print(f"     → Actuel: {broker.base_url if broker else 'N/A'}")
    print("  3. ✅ Le token a-t-il été généré avec LIVE ?")
    print("     → Si ancien token SIM, il faut le régénérer")
    print("  4. ✅ Les permissions Market Data sont-elles activées ?")
    print("     → Vérifier dans SaxoTraderGO")
    
    print("\nActions recommandées:")
    print("  1. Exécuter: python manage.py migrate_saxo_to_live")
    print("  2. Régénérer le token via l'interface web ou API")
    print("  3. Activer 'Market Data' dans SaxoTraderGO si nécessaire")
    print("  4. Relancer ce script pour vérifier")


if __name__ == '__main__':
    main()

