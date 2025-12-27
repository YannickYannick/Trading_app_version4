# 🔌 Services Brokers - Documentation

## Vue d'ensemble

Les services brokers permettent l'interaction avec différentes APIs de courtiers (Saxo Bank, Binance) via une interface unifiée.

## Architecture

```
apps/trading/
├── brokers/
│   ├── __init__.py         # Exports
│   ├── base.py             # BrokerBase (classe abstraite)
│   ├── saxo.py             # SaxoBroker (OAuth2)
│   ├── binance.py          # BinanceBroker (HMAC)
│   └── factory.py          # BrokerFactory (Pattern Factory)
└── services/
    └── broker_service.py   # Service de haut niveau
```

## Classe de Base : BrokerBase

**Fichier** : `apps/trading/brokers/base.py`

### Dataclasses standardisées

```python
@dataclass
class BrokerAsset:
    """Asset standardisé."""
    symbol: str
    name: str
    asset_type: str
    exchange: str = ''
    currency: str = 'USD'
    is_tradable: bool = True
    broker_id: Optional[str] = None

@dataclass
class BrokerPosition:
    """Position standardisée."""
    symbol: str
    quantity: Decimal
    entry_price: Decimal
    current_price: Decimal
    side: str  # 'LONG' ou 'SHORT'
    pnl: Decimal = Decimal('0')

@dataclass
class OrderResult:
    """Résultat d'un ordre."""
    success: bool
    order_id: Optional[str] = None
    message: str = ''
    error: Optional[str] = None
```

### Méthodes abstraites

| Méthode | Description |
|---------|-------------|
| `authenticate()` | Authentification avec le broker |
| `is_authenticated()` | Vérifier l'état d'authentification |
| `get_assets()` | Récupérer les actifs disponibles |
| `get_asset_price()` | Récupérer le prix d'un actif |
| `get_positions()` | Récupérer les positions ouvertes |
| `get_trades()` | Récupérer l'historique des trades |
| `place_order()` | Placer un ordre |
| `cancel_order()` | Annuler un ordre |
| `get_account_balance()` | Récupérer les balances |

## SaxoBroker (OAuth2)

**Fichier** : `apps/trading/brokers/saxo.py`

### Authentification OAuth2

```python
class SaxoBroker(BrokerBase):
    SIM_BASE_URL = "https://gateway.saxobank.com/sim/openapi"
    LIVE_BASE_URL = "https://gateway.saxobank.com/openapi"
    
    def __init__(self, user, credentials):
        super().__init__(user, credentials)
        self.client_id = credentials.get('client_id')
        self.client_secret = credentials.get('client_secret')
        self.access_token = credentials.get('access_token')
        self.refresh_token = credentials.get('refresh_token')
        
        # Environnement (simulation ou live)
        env = credentials.get('environment', 'simulation')
        self.base_url = self.LIVE_BASE_URL if env == 'live' else self.SIM_BASE_URL
```

### Refresh automatique du token

```python
def _refresh_token(self) -> bool:
    """Rafraîchir le token OAuth2."""
    response = requests.post(
        f"{self.base_url}/token",
        data={
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }
    )
    # ... mise à jour des tokens
```

## BinanceBroker (HMAC SHA256)

**Fichier** : `apps/trading/brokers/binance.py`

### Signature HMAC

```python
class BinanceBroker(BrokerBase):
    LIVE_BASE_URL = "https://api.binance.com"
    TESTNET_BASE_URL = "https://testnet.binance.vision"
    
    def _sign_params(self, params: Dict) -> str:
        """Générer la signature HMAC SHA256."""
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
```

### Requêtes signées

```python
def _make_signed_request(self, method, endpoint, params=None):
    params = params or {}
    params['timestamp'] = int(time.time() * 1000)
    params['signature'] = self._sign_params(params)
    
    headers = {'X-MBX-APIKEY': self.api_key}
    # ... envoi de la requête
```

## BrokerFactory

**Fichier** : `apps/trading/brokers/factory.py`

```python
class BrokerFactory:
    """Factory pour créer des instances de brokers."""
    
    _brokers = {
        'saxo': SaxoBroker,
        'binance': BinanceBroker,
    }
    
    @staticmethod
    def create_broker(broker_type: str, user, credentials) -> BrokerBase:
        broker_class = BrokerFactory._brokers.get(broker_type.lower())
        if not broker_class:
            raise ValueError(f"Broker '{broker_type}' non supporté")
        return broker_class(user, credentials)
    
    @staticmethod
    def get_supported_brokers() -> List[str]:
        return list(BrokerFactory._brokers.keys())
```

## BrokerService

**Fichier** : `apps/trading/services/broker_service.py`

Service de haut niveau qui gère les interactions avec les brokers.

```python
class BrokerService:
    def __init__(self, user: User):
        self.user = user
    
    def get_broker_instance(self, broker_account: BrokerAccount) -> BrokerBase:
        """Obtenir une instance de broker."""
        credentials = self._get_credentials(broker_account)
        return BrokerFactory.create_broker(
            broker_account.broker.broker_type,
            self.user,
            credentials
        )
    
    def test_connection(self, broker_account: BrokerAccount) -> Dict:
        """Tester la connexion à un broker."""
        broker = self.get_broker_instance(broker_account)
        success = broker.test_connection()
        return {
            'success': success,
            'message': 'Connexion réussie' if success else 'Connexion échouée'
        }
```

## Modèle BrokerAccount

**Fichier** : `apps/trading/models/brokers.py`

```python
class BrokerAccount(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    broker = models.ForeignKey(Broker, on_delete=models.CASCADE)
    account_id = models.CharField(max_length=100)
    
    # API Keys (Binance)
    api_key = models.CharField(max_length=255, blank=True)
    api_secret = models.CharField(max_length=255, blank=True)
    
    # OAuth (Saxo)
    client_id = models.CharField(max_length=255, blank=True)
    client_secret = models.CharField(max_length=255, blank=True)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    
    # Configuration
    is_sandbox = models.BooleanField(default=True)
    extra_credentials = models.JSONField(default=dict, blank=True)
```

## Utilisation

```python
from apps.trading.services.broker_service import BrokerService
from apps.trading.models import BrokerAccount

# Récupérer le compte broker
broker_account = BrokerAccount.objects.get(user=user, broker__broker_type='SAXO')

# Créer le service
service = BrokerService(user)

# Tester la connexion
result = service.test_connection(broker_account)

# Récupérer les assets
assets = service.get_assets(broker_account, asset_type='Stock', keywords='AAPL')

# Récupérer les positions
positions = service.get_positions(broker_account)

# Placer un ordre
order = service.place_order(
    broker_account,
    symbol='AAPL',
    side='BUY',
    size=10,
    price=150.0
)
```

## Résumé

| Broker | Authentification | Endpoints |
|--------|------------------|-----------|
| Saxo | OAuth2 (tokens) | gateway.saxobank.com |
| Binance | HMAC SHA256 | api.binance.com |

Les brokers sont accessibles via le `BrokerFactory` et le `BrokerService` fournit une interface simplifiée pour les opérations courantes.

