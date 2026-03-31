"""
Test de l'endpoint prices avec authentification (comme le frontend)
"""
import os
import sys
import django

_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)
os.chdir(_BACKEND_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config_django.settings.development')
django.setup()

import requests
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken

# Configuration
BASE_URL = "http://localhost:8000"
ASSET_ID = 101173

def test_prices_endpoint_with_auth():
    """Test l'endpoint avec authentification JWT comme le frontend"""
    print(f"\n{'='*70}")
    print(f"Test de l'endpoint avec authentification (comme le frontend)")
    print(f"{'='*70}\n")
    
    # Récupérer un utilisateur
    user = User.objects.first()
    if not user:
        print("❌ Aucun utilisateur trouvé")
        return
    
    print(f"Utilisateur: {user.username} (ID: {user.id})")
    
    # Générer un token JWT
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    
    print(f"Token généré: {access_token[:20]}...")
    
    # Faire la requête comme le frontend
    url = f"{BASE_URL}/api/all-assets/{ASSET_ID}/prices/?days=365&format=list"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    
    print(f"\n📡 Requête HTTP:")
    print(f"   URL: {url}")
    print(f"   Method: GET")
    print(f"   Headers: Authorization: Bearer ...")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        print(f"\n📊 Réponse:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Succès!")
            print(f"   - Count: {data.get('count', 0)}")
            print(f"   - All Asset Symbol: {data.get('all_asset_symbol', 'N/A')}")
            if data.get('results'):
                print(f"   - Premiers résultats: {len(data['results'])}")
        else:
            print(f"   ❌ Erreur HTTP {response.status_code}")
            try:
                error_data = response.json()
                print(f"   - Error: {error_data.get('error', 'N/A')}")
                print(f"   - Message: {error_data.get('message', 'N/A')}")
            except:
                print(f"   - Response text: {response.text[:200]}")
                
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Erreur de connexion")
        print(f"   Le serveur Django n'est probablement pas démarré sur {BASE_URL}")
        print(f"   Démarrez le serveur avec: python manage.py runserver")
    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_prices_endpoint_with_auth()



