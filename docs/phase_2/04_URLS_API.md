# 🔗 URLs API

## Architecture

```
config_django/urls.py
    └── path('api/', include('apps.trading.urls'))
            └── apps/trading/urls.py
                    └── path('', include('apps.trading.api.urls'))
                            └── apps/trading/api/urls.py
                                    └── router.urls (ViewSets)
```

## Configuration principale (`config_django/urls.py`)

```python
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView
)

urlpatterns = [
    # Admin Django
    path('admin/', admin.site.urls),
    
    # API REST
    path('api/', include('apps.trading.urls')),
    
    # Authentification DRF (navigateur)
    path('api/auth/', include('rest_framework.urls', namespace='rest_framework')),
    
    # Documentation API
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
```

## URLs Trading (`apps/trading/urls.py`)

```python
from django.urls import path, include

app_name = 'trading'

urlpatterns = [
    path('', include('apps.trading.api.urls')),
]
```

## URLs API (`apps/trading/api/urls.py`)

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from . import views, auth_views

# Router pour les ViewSets
router = DefaultRouter()

# Catalogue
router.register(r'all-assets', views.AllAssetsViewSet, basename='all-asset')

# Assets
router.register(r'assets', views.AssetViewSet, basename='asset')

# Trading
router.register(r'positions', views.PositionViewSet, basename='position')
router.register(r'trades', views.TradeViewSet, basename='trade')
router.register(r'orders', views.OrderViewSet, basename='order')

# Stratégies
router.register(r'strategies', views.StrategyViewSet, basename='strategy')

# Brokers
router.register(r'brokers', views.BrokerViewSet, basename='broker')
router.register(r'broker-accounts', views.BrokerAccountViewSet, basename='broker-account')

urlpatterns = [
    # ViewSets
    path('', include(router.urls)),
    
    # Authentification Session
    path('auth/login/', auth_views.login_session, name='api-login'),
    path('auth/logout/', auth_views.logout_session, name='api-logout'),
    
    # Authentification JWT
    path('auth/jwt/login/', auth_views.login_jwt, name='jwt-login'),
    path('auth/jwt/logout/', auth_views.logout_jwt, name='jwt-logout'),
    path('auth/jwt/refresh/', TokenRefreshView.as_view(), name='jwt-refresh'),
    path('auth/jwt/verify/', TokenVerifyView.as_view(), name='jwt-verify'),
    
    # User
    path('auth/user/', auth_views.user_info, name='api-user'),
    path('auth/register/', auth_views.register, name='api-register'),
]
```

## Endpoints générés

### CRUD automatique (Router)

| Endpoint | Méthode | Action |
|----------|---------|--------|
| `/api/assets/` | GET | list |
| `/api/assets/` | POST | create |
| `/api/assets/{id}/` | GET | retrieve |
| `/api/assets/{id}/` | PUT | update |
| `/api/assets/{id}/` | PATCH | partial_update |
| `/api/assets/{id}/` | DELETE | destroy |

### Actions personnalisées

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/all-assets/saxo/` | GET | Assets Saxo |
| `/api/all-assets/stats/` | GET | Statistiques |
| `/api/assets/{id}/prices/` | GET | Historique prix |
| `/api/positions/open/` | GET | Positions ouvertes |
| `/api/positions/{id}/close/` | POST | Fermer position |
| `/api/trades/recent/` | GET | Trades récents |
| `/api/orders/pending/` | GET | Ordres en attente |
| `/api/orders/{id}/cancel/` | POST | Annuler ordre |

### Authentification

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/auth/login/` | POST | Login session |
| `/api/auth/logout/` | POST | Logout |
| `/api/auth/jwt/login/` | POST | Login JWT |
| `/api/auth/jwt/refresh/` | POST | Refresh token |
| `/api/auth/user/` | GET | Info utilisateur |
| `/api/auth/register/` | POST | Inscription |

## Vérification des routes

```bash
python -c "
from django.urls import get_resolver
resolver = get_resolver()
for pattern in resolver.url_patterns:
    print(pattern)
"
```

## Accès

- API Root : http://localhost:8000/api/
- Swagger : http://localhost:8000/api/docs/
- ReDoc : http://localhost:8000/api/redoc/

