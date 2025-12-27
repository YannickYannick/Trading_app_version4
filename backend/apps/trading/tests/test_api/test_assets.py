"""
Tests pour l'API Assets.

Teste les endpoints :
- GET /api/all-assets/
- GET /api/assets/
- Actions personnalisées
"""
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal

from apps.trading.models import AllAssets, Asset


class AllAssetsAPITests(APITestCase):
    """Tests pour le catalogue AllAssets."""
    
    def setUp(self):
        """Configuration avant chaque test."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Créer des assets de test
        self.saxo_asset = AllAssets.objects.create(
            symbol='AAPL',
            name='Apple Inc.',
            platform='SAXO',
            asset_type='STOCK',
            market='NASDAQ',
            currency='USD',
            is_tradable=True,
            saxo_uic=12345
        )
        
        self.binance_asset = AllAssets.objects.create(
            symbol='BTCUSDT',
            name='Bitcoin / USDT',
            platform='BINANCE',
            asset_type='CRYPTO',
            market='CRYPTO',
            currency='USDT',
            is_tradable=True,
            binance_base_asset='BTC',
            binance_quote_asset='USDT'
        )
    
    def test_list_all_assets(self):
        """Test GET /api/all-assets/"""
        response = self.client.get('/api/all-assets/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
    
    def test_retrieve_all_asset(self):
        """Test GET /api/all-assets/{id}/"""
        response = self.client.get(f'/api/all-assets/{self.saxo_asset.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['symbol'], 'AAPL')
        self.assertEqual(response.data['platform'], 'SAXO')
    
    def test_filter_by_platform(self):
        """Test GET /api/all-assets/?platform=SAXO"""
        response = self.client.get('/api/all-assets/?platform=SAXO')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['symbol'], 'AAPL')
    
    def test_saxo_action(self):
        """Test GET /api/all-assets/saxo/"""
        response = self.client.get('/api/all-assets/saxo/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Vérifier que seuls les assets Saxo sont retournés
        for asset in response.data.get('results', response.data):
            self.assertEqual(asset['platform'], 'SAXO')
    
    def test_binance_action(self):
        """Test GET /api/all-assets/binance/"""
        response = self.client.get('/api/all-assets/binance/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_stats_action(self):
        """Test GET /api/all-assets/stats/"""
        response = self.client.get('/api/all-assets/stats/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total', response.data)
        self.assertIn('by_platform', response.data)
        self.assertEqual(response.data['total'], 2)
    
    def test_search_action(self):
        """Test GET /api/all-assets/search/?q=AAPL"""
        response = self.client.get('/api/all-assets/search/?q=AAPL')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_search_requires_min_length(self):
        """Test que la recherche nécessite au moins 2 caractères."""
        response = self.client.get('/api/all-assets/search/?q=A')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AssetAPITests(APITestCase):
    """Tests pour les assets enrichis."""
    
    def setUp(self):
        """Configuration avant chaque test."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Créer un AllAsset et un Asset lié
        self.all_asset = AllAssets.objects.create(
            symbol='AAPL',
            name='Apple Inc.',
            platform='SAXO',
            asset_type='STOCK',
            market='NASDAQ'
        )
        
        self.asset = Asset.objects.create(
            all_asset=self.all_asset,
            symbol='AAPL',
            name='Apple Inc.',
            asset_type='STOCK',
            currency='USD',
            current_price=Decimal('150.50'),
            sector='Technology',
            industry='Consumer Electronics',
            is_active=True
        )
    
    def test_list_assets(self):
        """Test GET /api/assets/"""
        response = self.client.get('/api/assets/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
    
    def test_retrieve_asset(self):
        """Test GET /api/assets/{id}/"""
        response = self.client.get(f'/api/assets/{self.asset.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['symbol'], 'AAPL')
        self.assertAlmostEqual(float(response.data['current_price']), 150.50)
    
    def test_create_asset(self):
        """Test POST /api/assets/"""
        data = {
            'symbol': 'TSLA',
            'name': 'Tesla Inc.',
            'asset_type': 'STOCK',
            'currency': 'USD',
            'current_price': '250.00',
        }
        
        response = self.client.post('/api/assets/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['symbol'], 'TSLA')
        self.assertEqual(Asset.objects.count(), 2)
    
    def test_update_asset(self):
        """Test PUT /api/assets/{id}/"""
        data = {
            'symbol': 'AAPL',
            'name': 'Apple Inc. (Updated)',
            'asset_type': 'STOCK',
            'currency': 'USD',
            'current_price': '160.00',
        }
        
        response = self.client.put(f'/api/assets/{self.asset.id}/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Apple Inc. (Updated)')
    
    def test_partial_update_asset(self):
        """Test PATCH /api/assets/{id}/"""
        data = {'current_price': '155.00'}
        
        response = self.client.patch(f'/api/assets/{self.asset.id}/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertAlmostEqual(float(response.data['current_price']), 155.00)
    
    def test_delete_asset(self):
        """Test DELETE /api/assets/{id}/"""
        response = self.client.delete(f'/api/assets/{self.asset.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Asset.objects.count(), 0)
    
    def test_prices_action(self):
        """Test GET /api/assets/{id}/prices/"""
        response = self.client.get(f'/api/assets/{self.asset.id}/prices/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Liste vide car pas de prix enregistrés
        self.assertEqual(len(response.data), 0)
    
    def test_summary_action(self):
        """Test GET /api/assets/{id}/summary/"""
        response = self.client.get(f'/api/assets/{self.asset.id}/summary/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('asset', response.data)
        self.assertIn('positions', response.data)
        self.assertIn('trades', response.data)
    
    def test_filter_by_asset_type(self):
        """Test GET /api/assets/?asset_type=STOCK"""
        response = self.client.get('/api/assets/?asset_type=STOCK')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

