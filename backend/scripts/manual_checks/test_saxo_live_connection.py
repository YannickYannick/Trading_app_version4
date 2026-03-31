"""
Script de test pour vérifier la connexion à l'API Saxo Bank LIVE.

Ce script teste la connexion et l'accès aux prix pour diagnostiquer
les problèmes de NoAccess.

Usage (depuis n’importe quel répertoire) :
    python scripts/manual_checks/test_saxo_live_connection.py
"""

import os
import sys
import requests

# Essayer d'importer dotenv (optionnel)
try:
    from dotenv import load_dotenv
    import os
    _backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    # Racine du dépôt (parent de backend)
    project_root = os.path.dirname(_backend_root)
    env_path = os.path.join(project_root, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"✅ Fichier .env chargé depuis: {env_path}")
    else:
        backend_env = os.path.join(_backend_root, '.env')
        if os.path.exists(backend_env):
            load_dotenv(backend_env)
            print(f"✅ Fichier .env chargé depuis: {backend_env}")
        else:
            load_dotenv()  # Essayer le .env par défaut
except ImportError:
    # Si dotenv n'est pas installé, on utilise les variables d'environnement directement
    print("⚠️  python-dotenv non installé, utilisation des variables d'environnement système uniquement")
except Exception as e:
    print(f"⚠️  Erreur lors du chargement du .env: {e}")

# Essayer d'importer Django (optionnel - pas nécessaire pour ce test simple)
django_available = False
try:
    import django
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    os.chdir(backend_dir)
    # Essayer différents modules de settings
    settings_modules = ['config_django.settings.development', 'config_django.settings.base', 'trading_app.settings']
    for settings_module in settings_modules:
        try:
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)
            django.setup()
            django_available = True
            break
        except Exception:
            continue
except (ImportError, Exception) as e:
    # Si Django n'est pas disponible, on continue sans (le test fonctionne aussi sans)
    print(f"⚠️  Django non disponible: {e}")
    print("   Le test continuera sans Django (variables d'environnement uniquement)\n")


def test_saxo_live_connection():
    """Test la connexion à l'API Saxo LIVE"""
    
    base_url = "https://gateway.saxobank.com/openapi"  # ✅ LIVE
    token = os.getenv('SAXO_ACCESS_TOKEN')
    
    # Si le token n'est pas dans l'environnement, essayer de le récupérer depuis Django
    if not token and django_available:
        try:
            from apps.trading.models import BrokerAccount
            # Récupérer le premier compte Saxo disponible
            saxo_account = BrokerAccount.objects.filter(broker_type='saxo').first()
            if saxo_account and hasattr(saxo_account, 'saxo_access_token') and saxo_account.saxo_access_token:
                token = saxo_account.saxo_access_token
                print("ℹ️  Token récupéré depuis la base de données Django")
                print(f"   Compte: {saxo_account.name or saxo_account.id}")
        except Exception as e:
            print(f"⚠️  Erreur lors de la récupération du token depuis Django: {e}")
            pass  # Si Django n'est pas disponible ou erreur, on continue
    
    if not token:
        print("❌ SAXO_ACCESS_TOKEN not found in environment or database")
        print("   Set it in your .env file, export it, or ensure a Saxo account exists in the database")
        return
    
    print(f"🔍 Testing Saxo LIVE connection...")
    print(f"   Base URL: {base_url}")
    print(f"   Token preview: {token[:20]}...{token[-10:] if len(token) > 30 else ''}")
    print()
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    
    # Test 1: Client info
    print("=" * 80)
    print("🔍 Test 1: Client info (GET /port/v1/clients/me)")
    print("=" * 80)
    try:
        r = requests.get(
            f"{base_url}/port/v1/clients/me",
            headers=headers,
            timeout=10
        )
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            print("✅ Connection OK!")
            client_data = r.json()
            print(f"   Client Key: {client_data.get('ClientKey', 'N/A')}")
            print(f"   Account Key: {client_data.get('AccountKey', 'N/A')}")
            print(f"   Name: {client_data.get('Name', 'N/A')}")
        elif r.status_code == 401:
            print("❌ Unauthorized (401)")
            print("   ⚠️ This usually means:")
            print("      - The token is expired")
            print("      - The token is for SIM environment but using LIVE URL")
            print("      - The token is invalid")
            print(f"   Error: {r.text[:200]}")
        else:
            print(f"❌ Error: {r.status_code}")
            print(f"   {r.text[:500]}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    print()
    
    # Test 2: Prix d'un instrument FX (EURUSD)
    print("=" * 80)
    print("🔍 Test 2: Fetching FX price (EURUSD, UIC 21)")
    print("=" * 80)
    try:
        r = requests.get(
            f"{base_url}/trade/v1/infoprices",
            params={
                "Uic": 21,  # EURUSD
                "AssetType": "FxSpot",
                "FieldGroups": "Quote,PriceInfo"
            },
            headers=headers,
            timeout=10
        )
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            quote = data.get('Quote', {}) if 'Quote' in data else {}
            if 'Data' in data and data['Data']:
                quote = data['Data'][0].get('Quote', {})
            
            print(f"✅ Price data received!")
            print(f"   Quote structure: {list(quote.keys()) if quote else 'No Quote'}")
            
            # Vérifier NoAccess
            price_type_ask = quote.get('PriceTypeAsk', 'N/A')
            price_type_bid = quote.get('PriceTypeBid', 'N/A')
            
            if price_type_ask == 'NoAccess' or price_type_bid == 'NoAccess':
                print(f"   ⚠️  NoAccess detected!")
                print(f"      PriceTypeAsk: {price_type_ask}")
                print(f"      PriceTypeBid: {price_type_bid}")
                print(f"   💡 Possible causes:")
                print(f"      1. Market Data subscription not activated in SaxoTraderGO")
                print(f"      2. Token is for SIM environment (check token generation)")
                print(f"      3. Instrument not available for this account")
            else:
                print(f"   ✅ Access granted!")
                print(f"      PriceTypeAsk: {price_type_ask}")
                print(f"      PriceTypeBid: {price_type_bid}")
                mid = quote.get('Mid')
                bid = quote.get('Bid')
                ask = quote.get('Ask')
                if mid or bid or ask:
                    print(f"      Mid: {mid}")
                    print(f"      Bid: {bid}")
                    print(f"      Ask: {ask}")
        elif r.status_code == 401:
            print(f"❌ Unauthorized (401)")
            print(f"   Token is not valid for LIVE environment")
        else:
            print(f"❌ Error: {r.status_code}")
            print(f"   {r.text[:500]}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    print()
    
    # Test 3: Stock price (Apple)
    print("=" * 80)
    print("🔍 Test 3: Fetching stock price (AAPL, UIC 211)")
    print("=" * 80)
    try:
        r = requests.get(
            f"{base_url}/trade/v1/infoprices",
            params={
                "Uic": 211,  # AAPL
                "AssetType": "Stock",
                "FieldGroups": "Quote,PriceInfo"
            },
            headers=headers,
            timeout=10
        )
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            quote = data.get('Quote', {}) if 'Quote' in data else {}
            if 'Data' in data and data['Data']:
                quote = data['Data'][0].get('Quote', {})
            
            price_type_ask = quote.get('PriceTypeAsk', 'N/A')
            price_type_bid = quote.get('PriceTypeBid', 'N/A')
            
            if price_type_ask == 'NoAccess' or price_type_bid == 'NoAccess':
                print(f"   ⚠️  NoAccess detected!")
                print(f"      PriceTypeAsk: {price_type_ask}")
                print(f"      PriceTypeBid: {price_type_bid}")
                print(f"   💡 Check Market Data subscription for US stocks")
            else:
                print(f"   ✅ Access granted!")
                mid = quote.get('Mid')
                bid = quote.get('Bid')
                ask = quote.get('Ask')
                if mid or bid or ask:
                    print(f"      Mid: {mid}")
                    print(f"      Bid: {bid}")
                    print(f"      Ask: {ask}")
        elif r.status_code == 401:
            print(f"❌ Unauthorized (401)")
        else:
            print(f"❌ Error: {r.status_code}")
            print(f"   {r.text[:500]}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    print()
    print("=" * 80)
    print("📋 DIAGNOSTIC RÉSUMÉ")
    print("=" * 80)
    print("""
Si vous voyez des erreurs 401:
   → Le token n'est pas valide pour l'environnement LIVE
   → Vérifiez que le token a été généré avec l'URL LIVE
   → Vérifiez que SAXO_CLIENT_ID et SAXO_CLIENT_SECRET sont pour LIVE

Si vous voyez des NoAccess:
   → Le token est valide mais les permissions Market Data ne sont pas activées
   → Connectez-vous à SaxoTraderGO
   → Allez dans Settings → Market Data
   → Activez les flux de données pour les marchés concernés

Si tout fonctionne:
   → ✅ Votre configuration LIVE est correcte!
   → Vous pouvez utiliser la validation Yahoo Finance
    """)


if __name__ == "__main__":
    test_saxo_live_connection()

