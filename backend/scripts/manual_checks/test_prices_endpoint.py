"""
Script de test pour vérifier l'endpoint /api/all-assets/{id}/prices/
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

from django.contrib.auth.models import User
from apps.trading.models import AllAssets
from apps.trading.api.views import AllAssetsViewSet
from rest_framework.test import APIRequestFactory
from rest_framework.response import Response

def test_prices_endpoint(asset_id):
    """Test l'endpoint prices pour un AllAsset"""
    print(f"\n{'='*70}")
    print(f"Test de l'endpoint /api/all-assets/{asset_id}/prices/")
    print(f"{'='*70}\n")
    
    # 1. Vérifier si l'AllAsset existe
    print("🔍 Vérification de l'existence de l'AllAsset dans la base de données...")
    try:
        all_asset = AllAssets.objects.get(id=asset_id)
        print(f"✅ AllAsset trouvé dans la base de données:")
        print(f"   - ID: {all_asset.id}")
        print(f"   - Symbol: {all_asset.symbol}")
        print(f"   - Name: {all_asset.name}")
        print(f"   - Platform: {all_asset.platform}")
        print(f"   - Asset Type: {all_asset.asset_type}")
        print(f"   - Currency: {all_asset.currency}")
        print(f"   - Symbole Yahoo: {all_asset.symbole_yahoo}")
        print(f"   - has_price_history: {all_asset.has_price_history}")
        
        if all_asset.has_price_history:
            count = all_asset.get_price_history_count()
            print(f"   - Nombre de jours d'historique: {count}")
            dates = all_asset.get_price_history_dates()
            if dates:
                print(f"   - Période: {dates[-1]} → {dates[0]}")
                print(f"   - 5 dernières dates: {dates[:5]}")
        else:
            print(f"   ⚠️  Aucun historique de prix disponible")
            print(f"   - price_history_json est None: {all_asset.price_history_json is None}")
            if all_asset.price_history_json:
                print(f"   - price_history_json est vide: {len(all_asset.price_history_json) == 0}")
    except AllAssets.DoesNotExist:
        print(f"❌ AllAsset {asset_id} n'existe PAS dans la base de données")
        print(f"\n📋 Vérification des AllAssets disponibles...")
        total = AllAssets.objects.count()
        print(f"   - Total d'AllAssets dans la base: {total}")
        
        if total > 0:
            print(f"\n   Exemples d'AllAssets disponibles:")
            for aa in AllAssets.objects.all()[:5]:
                print(f"     - ID: {aa.id}, Symbol: {aa.symbol}, Platform: {aa.platform}")
        return
    except Exception as e:
        print(f"❌ Erreur lors de la récupération de l'AllAsset: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 2. Tester l'endpoint API
    print(f"\n📡 Test de l'endpoint API...")
    factory = APIRequestFactory()
    user = User.objects.first()
    if not user:
        print("❌ Aucun utilisateur trouvé dans la base de données")
        return
    
    print(f"   Utilisateur: {user.username} (ID: {user.id})")
    
    # Simuler une requête GET
    request = factory.get(f'/api/all-assets/{asset_id}/prices/?days=365&format=list')
    request.user = user
    
    viewset = AllAssetsViewSet()
    viewset.request = request
    viewset.format_kwarg = None
    viewset.kwargs = {'pk': str(asset_id)}
    
    try:
        print(f"   Appel de viewset.prices()...")
        response = viewset.prices(request, pk=str(asset_id))
        print(f"\n📊 Réponse de l'endpoint:")
        print(f"   - Status Code: {response.status_code}")
        
        if hasattr(response, 'data'):
            data = response.data
            print(f"   - Count: {data.get('count', 0)}")
            print(f"   - All Asset Symbol: {data.get('all_asset_symbol', 'N/A')}")
            print(f"   - Message: {data.get('message', 'N/A')}")
            
            if response.status_code == 200:
                results = data.get('results', [])
                if results:
                    print(f"   ✅ {len(results)} résultats retournés")
                    print(f"\n   - 5 premiers résultats:")
                    for i, result in enumerate(results[:5], 1):
                        print(f"     {i}. Date: {result.get('date')}, Close: {result.get('close')}, Volume: {result.get('volume')}")
                else:
                    print(f"   ⚠️  Aucun résultat dans la réponse")
            else:
                print(f"   ❌ Erreur HTTP {response.status_code}")
                print(f"   - Error: {data.get('error', 'N/A')}")
                print(f"   - Message: {data.get('message', 'N/A')}")
        else:
            print(f"   ❌ Pas de données dans la réponse")
            
    except Exception as e:
        print(f"\n❌ Exception lors de l'appel de l'endpoint:")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # Tester avec l'ID mentionné dans l'erreur
    test_prices_endpoint(101173)
    
    print(f"\n{'='*70}")
    print("Test avec le premier AllAsset disponible ayant un historique...")
    print(f"{'='*70}")
    first_asset_with_history = AllAssets.objects.filter(price_history_json__isnull=False).exclude(price_history_json={}).first()
    if first_asset_with_history:
        test_prices_endpoint(first_asset_with_history.id)
    else:
        print("Aucun AllAsset avec historique trouvé")



