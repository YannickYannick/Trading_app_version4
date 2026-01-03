"""
Script de test pour vérifier l'historique des prix d'un AllAsset
"""
import os
import sys
import django

# Configuration Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config_django.settings.development')
django.setup()

from apps.trading.models import AllAssets
from apps.trading.api.views import AllAssetsViewSet
from django.test import RequestFactory
from django.contrib.auth.models import User

def test_allasset_price_history(asset_id: int):
    """Test l'historique des prix pour un AllAsset"""
    print(f"\n{'='*60}")
    print(f"Test de l'historique des prix pour AllAsset {asset_id}")
    print(f"{'='*60}\n")
    
    try:
        # Récupérer l'asset
        asset = AllAssets.objects.get(id=asset_id)
        print(f"✅ AllAsset trouvé:")
        print(f"   - ID: {asset.id}")
        print(f"   - Symbol: {asset.symbol}")
        print(f"   - Platform: {asset.platform}")
        print(f"   - Name: {asset.name}")
        print(f"   - Symbole Yahoo: {asset.symbole_yahoo}")
        
        # Vérifier l'historique
        print(f"\n📊 Historique des prix:")
        print(f"   - has_price_history: {asset.has_price_history}")
        print(f"   - price_history_json est None: {asset.price_history_json is None}")
        print(f"   - price_history_json est dict vide: {asset.price_history_json == {}}")
        
        if asset.price_history_json:
            print(f"   - Type: {type(asset.price_history_json)}")
            print(f"   - Nombre de clés: {len(asset.price_history_json)}")
            print(f"   - price_history_days: {asset.price_history_days}")
            
            # Afficher quelques dates
            dates = sorted(asset.price_history_json.keys(), reverse=True)[:5]
            print(f"\n   - 5 premières dates (les plus récentes):")
            for date in dates:
                price_data = asset.price_history_json[date]
                print(f"     * {date}: close={price_data.get('close')}, open={price_data.get('open')}")
        else:
            print(f"   ⚠️  price_history_json est vide ou None")
        
        # Tester l'endpoint API
        print(f"\n🔌 Test de l'endpoint API /api/all-assets/{asset_id}/prices/")
        
        # Créer une requête mock
        factory = RequestFactory()
        request = factory.get(f'/api/all-assets/{asset_id}/prices/?days=365&format=list')
        
        # Récupérer un utilisateur (nécessaire pour les permissions)
        user = User.objects.first()
        if not user:
            print("   ⚠️  Aucun utilisateur trouvé, création d'un utilisateur de test...")
            user = User.objects.create_user('test_user', 'test@example.com', 'testpass')
        
        request.user = user
        
        # Appeler la vue
        viewset = AllAssetsViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        try:
            response = viewset.prices(request, pk=str(asset_id))
            print(f"   - Status code: {response.status_code}")
            
            if hasattr(response, 'data'):
                data = response.data
                print(f"   - Count: {data.get('count', 0)}")
                print(f"   - Results length: {len(data.get('results', []))}")
                
                if data.get('results'):
                    print(f"\n   - Premier résultat:")
                    first_result = data['results'][0]
                    print(f"     * Date: {first_result.get('date')}")
                    print(f"     * Close: {first_result.get('close')}")
                    print(f"     * Open: {first_result.get('open')}")
                    print(f"     * Source: {first_result.get('source')}")
                else:
                    print(f"   ⚠️  Aucun résultat retourné")
                    if data.get('message'):
                        print(f"   - Message: {data.get('message')}")
            else:
                print(f"   ⚠️  Pas de données dans la réponse")
                print(f"   - Response: {response}")
        except Exception as e:
            print(f"   ❌ Erreur lors de l'appel à l'API: {e}")
            import traceback
            traceback.print_exc()
        
    except AllAssets.DoesNotExist:
        print(f"❌ AllAsset {asset_id} non trouvé")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # Tester avec AAPL (chercher par symbol contenant AAPL)
    print("🔍 Recherche d'AllAssets contenant 'AAPL' dans le symbol...")
    aapl_assets = AllAssets.objects.filter(symbol__icontains='AAPL')
    print(f"   Trouvé {aapl_assets.count()} asset(s)")
    
    for asset in aapl_assets[:3]:  # Tester les 3 premiers
        test_allasset_price_history(asset.id)
        print()



