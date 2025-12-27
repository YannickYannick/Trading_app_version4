# ⚠️ Gestion d'Erreurs Unifiée - Documentation

## Vue d'ensemble

La gestion d'erreurs unifiée permet de capturer, logger et retourner des erreurs de manière cohérente à travers toute l'application.

## Architecture

```
apps/trading/
├── exceptions/
│   ├── __init__.py
│   └── broker_exceptions.py    # Exceptions personnalisées
├── middleware/
│   ├── __init__.py
│   └── error_middleware.py     # Middleware de gestion d'erreurs
└── utils/
    ├── __init__.py
    └── error_utils.py          # Décorateurs et utilitaires
```

## Exceptions Personnalisées

**Fichier** : `apps/trading/exceptions/broker_exceptions.py`

### Hiérarchie des exceptions

```python
# Exception de base
class TradingAppException(Exception):
    """Exception de base pour l'application trading."""
    def __init__(self, message: str, code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code or 'TRADING_ERROR'
        self.details = details or {}

# Exceptions Broker
class BrokerException(TradingAppException):
    """Exception liée aux brokers."""
    pass

class BrokerAuthenticationError(BrokerException):
    """Erreur d'authentification broker."""
    def __init__(self, broker_name: str, message: str = None):
        super().__init__(
            message or f"Authentification échouée pour {broker_name}",
            code='BROKER_AUTH_ERROR',
            details={'broker': broker_name}
        )

class BrokerConnectionError(BrokerException):
    """Erreur de connexion broker."""
    pass

class BrokerRateLimitError(BrokerException):
    """Rate limit dépassé."""
    pass

class BrokerAPIError(BrokerException):
    """Erreur API broker générique."""
    pass

# Exceptions Sync
class SyncException(TradingAppException):
    """Exception de synchronisation."""
    pass

class AssetSyncError(SyncException):
    """Erreur de synchronisation des actifs."""
    pass

class PriceSyncError(SyncException):
    """Erreur de synchronisation des prix."""
    pass

# Exceptions Trading
class TradingException(TradingAppException):
    """Exception de trading."""
    pass

class InsufficientFundsError(TradingException):
    """Fonds insuffisants."""
    pass

class OrderValidationError(TradingException):
    """Erreur de validation d'ordre."""
    pass

class PositionNotFoundError(TradingException):
    """Position non trouvée."""
    pass
```

## Middleware de Gestion d'Erreurs

**Fichier** : `apps/trading/middleware/error_middleware.py`

### ErrorHandlingMiddleware

```python
class ErrorHandlingMiddleware:
    """Middleware pour capturer et formater les erreurs."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except TradingAppException as e:
            return self._handle_trading_exception(e)
        except Exception as e:
            return self._handle_unexpected_exception(e, request)
    
    def _handle_trading_exception(self, exception):
        """Gérer les exceptions de l'application."""
        logger.warning(f"Trading exception: {exception.code} - {exception.message}")
        
        return JsonResponse({
            'success': False,
            'error': {
                'code': exception.code,
                'message': exception.message,
                'details': exception.details,
            }
        }, status=400)
    
    def _handle_unexpected_exception(self, exception, request):
        """Gérer les exceptions inattendues."""
        logger.exception(f"Unexpected error: {exception}")
        
        return JsonResponse({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Une erreur inattendue est survenue',
            }
        }, status=500)
```

### Configuration

```python
# settings/base.py
MIDDLEWARE = [
    # ... autres middlewares
    'apps.trading.middleware.ErrorHandlingMiddleware',
]
```

## Utilitaires d'Erreurs

**Fichier** : `apps/trading/utils/error_utils.py`

### Décorateur handle_broker_errors

```python
def handle_broker_errors(func):
    """Décorateur pour gérer les erreurs broker."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.Timeout:
            raise BrokerConnectionError("Timeout de connexion")
        except requests.exceptions.ConnectionError:
            raise BrokerConnectionError("Impossible de se connecter au broker")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise BrokerAuthenticationError("Token expiré ou invalide")
            elif e.response.status_code == 429:
                raise BrokerRateLimitError("Trop de requêtes")
            raise BrokerAPIError(str(e))
    return wrapper
```

### Décorateur retry_on_error

```python
def retry_on_error(max_retries=3, delay=1, exceptions=(Exception,)):
    """Décorateur pour réessayer en cas d'erreur."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    logger.warning(f"Tentative {attempt + 1}/{max_retries} échouée: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
            raise last_exception
        return wrapper
    return decorator
```

### Décorateur log_execution_time

```python
def log_execution_time(func):
    """Décorateur pour logger le temps d'exécution."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        logger.info(f"{func.__name__} exécuté en {duration:.2f}s")
        return result
    return wrapper
```

## Exception Handler DRF

**Fichier** : `apps/trading/utils/error_utils.py`

```python
from rest_framework.views import exception_handler

def custom_exception_handler(exc, context):
    """Handler personnalisé pour DRF."""
    response = exception_handler(exc, context)
    
    if response is not None:
        response.data['success'] = False
        response.data['error'] = {
            'code': getattr(exc, 'code', 'API_ERROR'),
            'message': str(exc),
            'details': getattr(exc, 'details', {}),
        }
    
    return response
```

### Configuration DRF

```python
# settings/base.py
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'apps.trading.utils.error_utils.custom_exception_handler',
}
```

## Utilisation dans le code

### Dans les brokers

```python
class SaxoBroker(BrokerBase):
    @handle_broker_errors
    def authenticate(self):
        response = requests.post(self.auth_url, data=self.credentials)
        response.raise_for_status()
        return True
    
    @retry_on_error(max_retries=3, exceptions=(BrokerConnectionError,))
    @handle_broker_errors
    def get_assets(self, **kwargs):
        response = self._make_request('GET', '/ref/v1/instruments')
        return response.json()
```

### Dans les services

```python
class AssetSyncService:
    def sync_assets(self, broker_account):
        try:
            broker = self._get_broker(broker_account)
            assets = broker.get_assets()
            # ... process assets
        except BrokerAuthenticationError as e:
            logger.error(f"Auth error: {e}")
            return {'success': False, 'error': str(e)}
        except BrokerAPIError as e:
            logger.error(f"API error: {e}")
            raise AssetSyncError(f"Sync failed: {e}")
```

### Dans les views

```python
class AssetViewSet(viewsets.ModelViewSet):
    def sync(self, request, pk=None):
        try:
            result = self.sync_service.sync_assets(broker_account)
            return Response(result)
        except AssetSyncError as e:
            return Response({
                'success': False,
                'error': {'code': e.code, 'message': e.message}
            }, status=400)
```

## Format de réponse d'erreur

### Erreur métier (400)

```json
{
    "success": false,
    "error": {
        "code": "BROKER_AUTH_ERROR",
        "message": "Authentification échouée pour Saxo Bank",
        "details": {
            "broker": "Saxo Bank"
        }
    }
}
```

### Erreur serveur (500)

```json
{
    "success": false,
    "error": {
        "code": "INTERNAL_ERROR",
        "message": "Une erreur inattendue est survenue"
    }
}
```

## Résumé

| Composant | Rôle |
|-----------|------|
| `TradingAppException` | Classe de base pour toutes les exceptions |
| `ErrorHandlingMiddleware` | Capture globale des erreurs |
| `handle_broker_errors` | Décorateur pour les appels broker |
| `retry_on_error` | Retry automatique |
| `custom_exception_handler` | Handler DRF |

La gestion d'erreurs unifiée assure :
- ✅ Messages d'erreur cohérents
- ✅ Logging automatique
- ✅ Retry intelligent
- ✅ Format de réponse standard

