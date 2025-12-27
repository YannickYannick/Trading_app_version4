# 🧪 Tests des Services - Documentation

## Vue d'ensemble

Les tests des services vérifient le bon fonctionnement des brokers et des services de synchronisation en utilisant des mocks pour éviter les appels API réels.

## Structure des tests

```
apps/trading/tests/
├── __init__.py
├── test_api/                    # Tests API (Phase 2)
│   ├── __init__.py
│   ├── test_authentication.py
│   ├── test_assets.py
│   └── test_trading.py
├── test_brokers/                # Tests brokers (Phase 3)
│   ├── __init__.py
│   ├── test_saxo_broker.py
│   └── test_binance_broker.py
└── test_services/               # Tests services (Phase 3)
    ├── __init__.py
    ├── test_broker_service.py
    ├── test_asset_sync_service.py
    └── test_price_sync_service.py
```

## Tests des Brokers

### test_saxo_broker.py

Tests pour l'implémentation SaxoBroker :

```python
class SaxoBrokerTestCase(TestCase):
    def setUp(self):
        self.user = Mock()
        self.credentials = {
            'client_id': 'test_client_id',
            'client_secret': 'test_secret',
            'access_token': 'test_token',
        }
        self.broker = SaxoBroker(self.user, self.credentials)
    
    def test_is_authenticated_with_valid_token(self):
        """Test is_authenticated avec token valide"""
        future_time = (datetime.now() + timedelta(hours=1)).isoformat()
        self.broker.token_expires_at = future_time
        self.assertTrue(self.broker.is_authenticated())
    
    @patch.object(SaxoBroker, '_make_request')
    def test_get_assets_success(self, mock_request):
        """Test récupération des assets"""
        mock_request.return_value = {'Data': [
            {'Symbol': 'AAPL', 'Description': 'Apple Inc.'}
        ]}
        assets = self.broker.get_assets()
        self.assertEqual(len(assets), 1)
```

#### Tests couverts

| Test | Description |
|------|-------------|
| `test_init_sets_correct_environment` | Vérifie l'URL de base |
| `test_is_authenticated_*` | Vérifie l'état d'authentification |
| `test_refresh_token_*` | Vérifie le refresh du token |
| `test_get_assets_*` | Vérifie la récupération des assets |
| `test_get_asset_price_*` | Vérifie la récupération des prix |
| `test_get_positions_*` | Vérifie la récupération des positions |
| `test_place_order_*` | Vérifie le placement d'ordres |
| `test_get_account_balance_*` | Vérifie les balances du compte |

### test_binance_broker.py

Tests pour l'implémentation BinanceBroker :

```python
class BinanceBrokerTestCase(TestCase):
    def setUp(self):
        self.user = Mock()
        self.credentials = {
            'api_key': 'test_api_key',
            'api_secret': 'test_api_secret',
            'testnet': True,
        }
        self.broker = BinanceBroker(self.user, self.credentials)
    
    def test_signature_generation(self):
        """Test génération signature HMAC"""
        params = {'symbol': 'BTCUSDT', 'timestamp': 1234567890}
        signature = self.broker._sign_params(params)
        self.assertEqual(len(signature), 64)  # SHA256 hex
    
    @patch.object(BinanceBroker, '_make_request')
    def test_get_asset_price_success(self, mock_request):
        """Test récupération du prix"""
        mock_request.return_value = {'price': '50000.00'}
        price = self.broker.get_asset_price(symbol='BTCUSDT')
        self.assertEqual(price, Decimal('50000.00'))
```

## Tests des Services

### test_broker_service.py

Tests pour le service principal :

```python
class BrokerServiceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.broker = Broker.objects.create(
            name='Saxo Bank',
            broker_type='saxo'
        )
        self.account = BrokerAccount.objects.create(
            user=self.user,
            broker=self.broker,
            account_id='test-123'
        )
        self.service = BrokerService(self.user)
    
    @patch('apps.trading.services.broker_service.BrokerFactory.create_broker')
    def test_test_connection_success(self, mock_factory):
        """Test connexion réussie"""
        mock_broker = MagicMock()
        mock_broker.test_connection.return_value = True
        mock_factory.return_value = mock_broker
        
        result = self.service.test_connection(self.account)
        
        self.assertTrue(result['success'])
```

#### Tests couverts

| Test | Description |
|------|-------------|
| `test_get_broker_instance_*` | Création d'instance broker |
| `test_test_connection_*` | Test de connexion |
| `test_get_assets_*` | Récupération des assets |
| `test_get_positions_*` | Récupération des positions |
| `test_get_trades_*` | Récupération des trades |
| `test_place_order_*` | Placement d'ordres |

### test_asset_sync_service.py

Tests pour la synchronisation des assets :

```python
class AssetSyncServiceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(...)
        self.broker = Broker.objects.create(...)
        self.account = BrokerAccount.objects.create(...)
        self.service = AssetSyncService(self.user)
    
    @patch('apps.trading.services.sync.asset_sync_service.BrokerService')
    def test_sync_all_assets_from_saxo_success(self, mock_service):
        """Test sync réussie depuis Saxo"""
        mock_broker = MagicMock()
        mock_broker.authenticate.return_value = True
        mock_broker.get_assets.return_value = [
            {'Symbol': 'AAPL', 'Description': 'Apple Inc.'}
        ]
        # ...
        result = self.service.sync_all_assets_from_broker(self.account)
        self.assertTrue(result['success'])
```

#### Tests couverts

| Test | Description |
|------|-------------|
| `test_sync_all_assets_*` | Sync des AllAssets |
| `test_sync_user_assets_*` | Sync des Assets utilisateur |
| `test_map_*_asset` | Mapping des données broker |
| `test_sync_updates_existing` | Mise à jour vs création |

### test_price_sync_service.py

Tests pour la synchronisation des prix :

```python
class PriceSyncServiceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(...)
        self.all_asset = AllAssets.objects.create(...)
        self.asset = Asset.objects.create(...)
        self.service = PriceSyncService(self.user)
    
    @patch('apps.trading.services.sync.price_sync_service.BrokerService')
    def test_sync_asset_price_from_broker_success(self, mock_service):
        """Test sync prix via broker"""
        mock_broker = MagicMock()
        mock_broker.authenticate.return_value = True
        mock_broker.get_asset_price.return_value = Decimal('155.50')
        # ...
        result = self.service.sync_asset_price(self.asset)
        self.assertTrue(result['success'])
        self.assertEqual(result['price'], Decimal('155.50'))
```

## Utilisation des Mocks

### Mock simple
```python
from unittest.mock import Mock

mock_broker = Mock()
mock_broker.authenticate.return_value = True
```

### MagicMock (avec méthodes magiques)
```python
from unittest.mock import MagicMock

mock_broker = MagicMock()
mock_broker.get_assets.return_value = [{'symbol': 'AAPL'}]
```

### Patch d'un module
```python
from unittest.mock import patch

@patch('apps.trading.brokers.saxo.requests.get')
def test_method(self, mock_get):
    mock_get.return_value.json.return_value = {'data': 'value'}
```

### Patch d'une méthode
```python
@patch.object(SaxoBroker, '_make_request')
def test_method(self, mock_request):
    mock_request.return_value = {'Data': []}
```

### Side effect pour exceptions
```python
mock_broker.authenticate.side_effect = Exception("Network error")
```

## Lancer les tests

### Tous les tests
```bash
python manage.py test
```

### Tests des brokers uniquement
```bash
python manage.py test apps.trading.tests.test_brokers
```

### Tests des services uniquement
```bash
python manage.py test apps.trading.tests.test_services
```

### Un fichier de test spécifique
```bash
python manage.py test apps.trading.tests.test_brokers.test_saxo_broker
```

### Un test spécifique
```bash
python manage.py test apps.trading.tests.test_brokers.test_saxo_broker.SaxoBrokerTestCase.test_authenticate_success
```

### Avec verbosité
```bash
python manage.py test --verbosity=2
```

## Résumé des tests

| Catégorie | Fichier | Nombre de tests |
|-----------|---------|-----------------|
| Saxo Broker | `test_saxo_broker.py` | ~15 |
| Binance Broker | `test_binance_broker.py` | ~15 |
| Broker Service | `test_broker_service.py` | ~12 |
| Asset Sync | `test_asset_sync_service.py` | ~10 |
| Price Sync | `test_price_sync_service.py` | ~10 |

**Total approximatif : 60+ tests**

## Bonnes pratiques

1. **Utiliser setUp pour la configuration**
   ```python
   def setUp(self):
       self.user = User.objects.create_user(...)
   ```

2. **Tester les cas de succès ET d'échec**
   ```python
   def test_method_success(self):
   def test_method_failure(self):
   def test_method_exception(self):
   ```

3. **Nommer clairement les tests**
   ```python
   def test_get_assets_with_keyword_filter(self):
   def test_authenticate_with_expired_token(self):
   ```

4. **Mocker les dépendances externes**
   - Pas d'appels API réels
   - Tests rapides et fiables
   - Pas de dépendance réseau

5. **Vérifier les effets secondaires**
   ```python
   # Vérifier que l'asset a été créé
   self.assertTrue(Asset.objects.filter(symbol='AAPL').exists())
   ```

