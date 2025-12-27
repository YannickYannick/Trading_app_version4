# 🧪 Tests API

## Structure

```
apps/trading/tests/
├── __init__.py
└── test_api/
    ├── __init__.py
    ├── test_authentication.py  # Tests auth (16 tests)
    ├── test_assets.py          # Tests assets (17 tests)
    └── test_trading.py         # Tests trading (18 tests)
```

## Total : 51 tests

## Tests d'authentification

### SessionAuthenticationTests

```python
class SessionAuthenticationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_login_with_valid_credentials(self):
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123',
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
    
    def test_login_with_invalid_password(self):
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'wrongpassword',
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
```

### JWTAuthenticationTests

```python
class JWTAuthenticationTests(APITestCase):
    def test_jwt_login_returns_tokens(self):
        response = self.client.post('/api/auth/jwt/login/', {
            'username': 'testuser',
            'password': 'testpass123',
        }, format='json')
        
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
    
    def test_jwt_access_protected_endpoint(self):
        # Login
        login_response = self.client.post('/api/auth/jwt/login/', {...})
        access_token = login_response.data['access']
        
        # Utiliser le token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = self.client.get('/api/auth/user/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
```

### ProtectedEndpointsTests

```python
class ProtectedEndpointsTests(APITestCase):
    def test_assets_requires_authentication(self):
        response = self.client.get('/api/assets/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_positions_requires_authentication(self):
        response = self.client.get('/api/positions/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
```

## Tests Assets

### AllAssetsAPITests

```python
class AllAssetsAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(...)
        self.client.force_authenticate(user=self.user)
        
        self.saxo_asset = AllAssets.objects.create(
            symbol='AAPL',
            platform='SAXO',
            ...
        )
    
    def test_list_all_assets(self):
        response = self.client.get('/api/all-assets/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_filter_by_platform(self):
        response = self.client.get('/api/all-assets/?platform=SAXO')
        self.assertEqual(response.data['count'], 1)
    
    def test_stats_action(self):
        response = self.client.get('/api/all-assets/stats/')
        self.assertIn('total', response.data)
```

### AssetAPITests

```python
class AssetAPITests(APITestCase):
    def test_create_asset(self):
        data = {'symbol': 'TSLA', 'name': 'Tesla', ...}
        response = self.client.post('/api/assets/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_update_asset(self):
        response = self.client.put(f'/api/assets/{self.asset.id}/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_summary_action(self):
        response = self.client.get(f'/api/assets/{self.asset.id}/summary/')
        self.assertIn('positions', response.data)
```

## Tests Trading

### PositionAPITests

```python
class PositionAPITests(APITestCase):
    def test_list_positions_filtered_by_user(self):
        # Chaque utilisateur voit seulement ses positions
        response = self.client.get('/api/positions/')
        self.assertEqual(response.data['count'], 1)  # Seulement sa position
    
    def test_open_positions_action(self):
        response = self.client.get('/api/positions/open/')
        for pos in response.data:
            self.assertTrue(pos['is_open'])
    
    def test_close_position_action(self):
        response = self.client.post(f'/api/positions/{self.position.id}/close/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.position.refresh_from_db()
        self.assertFalse(self.position.is_open)
    
    def test_cannot_access_other_user_position(self):
        response = self.client.get(f'/api/positions/{self.other_position.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
```

### OrderAPITests

```python
class OrderAPITests(APITestCase):
    def test_cancel_order_action(self):
        response = self.client.post(f'/api/orders/{self.pending_order.id}/cancel/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.pending_order.refresh_from_db()
        self.assertEqual(self.pending_order.status, 'CANCELLED')
    
    def test_cannot_cancel_filled_order(self):
        response = self.client.post(f'/api/orders/{self.filled_order.id}/cancel/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
```

## Exécuter les tests

```bash
# Tous les tests
python manage.py test apps.trading.tests

# Tests spécifiques
python manage.py test apps.trading.tests.test_api.test_authentication
python manage.py test apps.trading.tests.test_api.test_assets
python manage.py test apps.trading.tests.test_api.test_trading

# Avec verbosité
python manage.py test --verbosity=2

# Un test spécifique
python manage.py test apps.trading.tests.test_api.test_assets.AssetAPITests.test_create_asset
```

## Résultat

```
$ python manage.py test apps.trading.tests
Found 51 test(s).
Creating test database...
...................................................
----------------------------------------------------------------------
Ran 51 tests in 40s

OK
```

## Utilitaires de test

### force_authenticate

```python
self.client.force_authenticate(user=self.user)
```

### credentials (JWT)

```python
self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
```

### format='json'

```python
response = self.client.post('/api/assets/', data, format='json')
```

## Bonnes pratiques

1. **setUp()** pour la configuration commune
2. Noms descriptifs (`test_create_asset_returns_201`)
3. Un test = une assertion principale
4. Tester les cas d'erreur
5. Tester les permissions

