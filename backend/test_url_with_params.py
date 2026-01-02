"""
Test de l'URL avec query params
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config_django.settings.development')
django.setup()

import requests
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken

BASE_URL = "http://localhost:8000"
ASSET_ID = 101173

def test_urls():
    """Test les différentes URLs"""
    user = User.objects.first()
    if not user:
        print("❌ Aucun utilisateur trouvé")
        return
    
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    
    urls_to_test = [
        f"{BASE_URL}/api/all-assets/{ASSET_ID}/prices/",
        f"{BASE_URL}/api/all-assets/{ASSET_ID}/prices/?days=365",
        f"{BASE_URL}/api/all-assets/{ASSET_ID}/prices/?days=365&output_format=list",
        f"{BASE_URL}/api/all-assets/{ASSET_ID}/prices/?days=365&format=list",  # Ancien format pour compatibilité
    ]
    
    for url in urls_to_test:
        print(f"\n{'='*70}")
        print(f"Test: {url}")
        print(f"{'='*70}")
        try:
            response = requests.get(url, headers=headers, timeout=5)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Succès - Count: {data.get('count', 0)}")
            else:
                print(f"❌ Erreur {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error: {error_data.get('error', 'N/A')}")
                    print(f"Message: {error_data.get('message', 'N/A')}")
                except:
                    print(f"Response text: {response.text[:200]}")
        except requests.exceptions.ConnectionError:
            print(f"❌ Erreur de connexion - Serveur non démarré")
        except Exception as e:
            print(f"❌ Exception: {e}")

if __name__ == '__main__':
    test_urls()
