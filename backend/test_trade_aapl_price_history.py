"""
Script de test pour vérifier l'historique des prix d'AAPL depuis les Trades
"""
import os
import sys
import django
from datetime import datetime

# Configuration Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config_django.settings.development')
django.setup()

from apps.trading.models import AllAssets, Trade
from apps.trading.api.views import AllAssetsViewSet
from rest_framework.test import APIRequestFactory
from rest_framework.request import Request
from django.contrib.auth.models import User
import json

def test_trade_aapl_price_history():
    """Test l'historique des prix pour AAPL depuis les trades"""
    print(f"\n{'='*70}")
    print(f"Test de l'historique des prix pour AAPL depuis les Trades")
    print(f"{'='*70}\n")
    
    # 1. Chercher les trades avec AAPL
    print("🔍 Recherche des trades avec AAPL...")
    trades_with_aapl = Trade.objects.filter(
        all_asset__symbol__icontains='AAPL'
    ).select_related('all_asset')[:5]
    
    if not trades_with_aapl.exists():
        print("   ⚠️  Aucun trade trouvé avec AAPL")
        # Chercher dans AllAssets directement
        print("\n   🔍 Recherche directe dans AllAssets...")
        aapl_assets = AllAssets.objects.filter(
            symbol__icontains='AAPL'
        )[:5]
        
        if not aapl_assets.exists():
            print("   ❌ Aucun AllAsset AAPL trouvé")
            return
        
        print(f"   ✅ Trouvé {aapl_assets.count()} AllAsset(s) AAPL")
        for asset in aapl_assets:
            test_allasset_directly(asset)
        return
    
    print(f"   ✅ Trouvé {trades_with_aapl.count()} trade(s) avec AAPL\n")
    
    # 2. Pour chaque trade, extraire l'AllAsset et tester
    for i, trade in enumerate(trades_with_aapl, 1):
        print(f"{'─'*70}")
        print(f"Trade #{i} (ID: {trade.id})")
        print(f"{'─'*70}\n")
        
        print(f"📋 Informations du Trade:")
        print(f"   - Trade ID: {trade.id}")
        print(f"   - Date: {trade.executed_at}")
        print(f"   - Type: {trade.trade_type}")
        print(f"   - Prix: {trade.price}")
        print(f"   - Quantité: {trade.quantity}")
        
        # Extraire l'AllAsset
        all_asset = trade.all_asset
        if not all_asset:
            print(f"   ⚠️  Ce trade n'a pas d'AllAsset associé")
            continue
        
        print(f"\n📦 AllAsset associé:")
        print(f"   - ID: {all_asset.id}")
        print(f"   - Symbol: {all_asset.symbol}")
        print(f"   - Platform: {all_asset.platform}")
        print(f"   - Name: {all_asset.name}")
        print(f"   - Symbole Yahoo: {all_asset.symbole_yahoo}")
        
        # Tester l'AllAsset
        test_allasset_directly(all_asset)
        print()

def test_allasset_directly(all_asset: AllAssets):
    """Test un AllAsset directement"""
    print(f"\n📊 Historique des prix disponible:")
    print(f"   - has_price_history: {all_asset.has_price_history}")
    print(f"   - price_history_json est None: {all_asset.price_history_json is None}")
    
    price_history = all_asset.price_history_json or {}
    print(f"   - price_history_json est dict vide: {price_history == {}}")
    print(f"   - price_history_days: {all_asset.price_history_days}")
    print(f"   - price_history_updated_at: {all_asset.price_history_updated_at}")
    
    if price_history:
        print(f"   - Type: {type(price_history)}")
        print(f"   - Nombre de dates: {len(price_history)}")
        
        # Afficher les dates disponibles
        dates = sorted(price_history.keys(), reverse=True)
        print(f"\n   📅 Période disponible:")
        if dates:
            print(f"      - Date la plus récente: {dates[0]}")
            print(f"      - Date la plus ancienne: {dates[-1]}")
            print(f"      - Nombre total de jours: {len(dates)}")
            
            # Afficher quelques exemples
            print(f"\n   📈 Exemples de données (5 plus récentes):")
            for date in dates[:5]:
                price_data = price_history[date]
                close = price_data.get('close')
                open_price = price_data.get('open')
                source = price_data.get('source', 'UNKNOWN')
                print(f"      * {date}: close={close}, open={open_price}, source={source}")
        
        # Tester avec différents nombres de jours
        print(f"\n🔌 Test de l'endpoint API avec différents nombres de jours:")
        
        test_days = [1, 30, 100, 365]
        
        for days in test_days:
            print(f"\n   📊 Test avec {days} jours:")
            result = test_api_endpoint(all_asset.id, days)
            if result:
                print(f"      ✅ Status: {result['status']}")
                print(f"      ✅ Count: {result['count']}")
                if result['count'] > 0:
                    print(f"      ✅ Premier résultat: {result['first_result']}")
                else:
                    print(f"      ⚠️  Aucun résultat")
                    if result.get('message'):
                        print(f"      - Message: {result['message']}")
            else:
                print(f"      ❌ Erreur lors de l'appel API")
    else:
        print(f"   ⚠️  Aucun historique de prix disponible")
        print(f"   💡 Vous devez synchroniser l'historique pour cet asset")

def test_api_endpoint(asset_id: int, days: int = 365):
    """Test l'endpoint API prices pour un AllAsset"""
    try:
        # Créer une requête mock avec DRF
        factory = APIRequestFactory()
        request = factory.get(
            f'/api/all-assets/{asset_id}/prices/',
            {'days': days, 'format': 'list'}
        )
        
        # Récupérer un utilisateur
        user = User.objects.first()
        if not user:
            user = User.objects.create_user('test_user', 'test@example.com', 'testpass')
        
        # Envelopper dans un Request DRF
        drf_request = Request(request)
        drf_request.user = user
        
        # Appeler la vue
        viewset = AllAssetsViewSet()
        viewset.request = drf_request
        viewset.format_kwarg = None
        viewset.kwargs = {'pk': str(asset_id)}
        
        response = viewset.prices(drf_request, pk=str(asset_id))
        
        if hasattr(response, 'data'):
            data = response.data
            first_result = None
            if data.get('results') and len(data['results']) > 0:
                first_result = {
                    'date': data['results'][0].get('date'),
                    'close': data['results'][0].get('close'),
                    'source': data['results'][0].get('source')
                }
            
            return {
                'status': response.status_code,
                'count': data.get('count', 0),
                'message': data.get('message'),
                'first_result': first_result
            }
        else:
            return {
                'status': response.status_code,
                'count': 0,
                'message': 'No data in response'
            }
    except Exception as e:
        print(f"      ❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    try:
        test_trade_aapl_price_history()
    except Exception as e:
        print(f"\n❌ Erreur globale: {e}")
        import traceback
        traceback.print_exc()

