# 🌐 Phase 2 : API REST

## Objectif

Créer une API REST complète avec Django REST Framework pour exposer les données et fonctionnalités de l'application.

## ✅ Checklist

| Tâche | Statut | Documentation |
|-------|--------|---------------|
| DRF installé et configuré | ✅ | [01_DRF_INSTALLATION.md](01_DRF_INSTALLATION.md) |
| Serializers créés | ✅ | [02_SERIALIZERS.md](02_SERIALIZERS.md) |
| ViewSets créés | ✅ | [03_VIEWSETS.md](03_VIEWSETS.md) |
| URLs API configurées | ✅ | [04_URLS_API.md](04_URLS_API.md) |
| CORS configuré | ✅ | [05_CORS.md](05_CORS.md) |
| Authentification (Session + JWT) | ✅ | [06_AUTHENTIFICATION.md](06_AUTHENTIFICATION.md) |
| Tests API de base | ✅ | [07_TESTS_API.md](07_TESTS_API.md) |

## 📊 Endpoints créés

### Catalogue (AllAssets)
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/all-assets/` | Liste le catalogue |
| GET | `/api/all-assets/{id}/` | Détails d'un asset |
| GET | `/api/all-assets/saxo/` | Assets Saxo |
| GET | `/api/all-assets/binance/` | Assets Binance |
| GET | `/api/all-assets/stats/` | Statistiques |
| GET | `/api/all-assets/search/?q=...` | Recherche |

### Assets
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| CRUD | `/api/assets/` | CRUD complet |
| GET | `/api/assets/{id}/prices/` | Historique prix |
| GET | `/api/assets/{id}/positions/` | Positions |
| GET | `/api/assets/{id}/trades/` | Trades |
| GET | `/api/assets/{id}/summary/` | Résumé |

### Trading
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| CRUD | `/api/positions/` | Gestion positions |
| GET | `/api/positions/open/` | Positions ouvertes |
| GET | `/api/positions/summary/` | Résumé portfolio |
| POST | `/api/positions/{id}/close/` | Fermer position |
| CRUD | `/api/trades/` | Gestion trades |
| GET | `/api/trades/recent/` | Trades récents |
| GET | `/api/trades/stats/` | Statistiques |
| CRUD | `/api/orders/` | Gestion ordres |
| GET | `/api/orders/pending/` | Ordres en attente |
| POST | `/api/orders/{id}/cancel/` | Annuler ordre |

### Stratégies
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| CRUD | `/api/strategies/` | Gestion stratégies |
| GET | `/api/strategies/{id}/performance/` | Performance |
| POST | `/api/strategies/{id}/activate/` | Activer |
| POST | `/api/strategies/{id}/deactivate/` | Désactiver |

### Brokers
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/brokers/` | Liste brokers |
| CRUD | `/api/broker-accounts/` | Comptes utilisateur |
| GET | `/api/broker-accounts/{id}/sync_status/` | Statut sync |

### Authentification
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/auth/login/` | Login session |
| POST | `/api/auth/logout/` | Logout |
| POST | `/api/auth/jwt/login/` | Login JWT |
| POST | `/api/auth/jwt/refresh/` | Refresh token |
| POST | `/api/auth/register/` | Inscription |
| GET | `/api/auth/user/` | Info utilisateur |

### Documentation
| URL | Description |
|-----|-------------|
| `/api/docs/` | Swagger UI |
| `/api/redoc/` | ReDoc |
| `/api/schema/` | OpenAPI JSON |

## 🔧 Technologies

| Package | Version | Utilisation |
|---------|---------|-------------|
| `djangorestframework` | 3.x | API REST |
| `djangorestframework-simplejwt` | 5.x | JWT Auth |
| `django-cors-headers` | 4.x | CORS |
| `django-filter` | 23.x | Filtrage |
| `drf-spectacular` | 0.27.x | Documentation |

## 🧪 Tests

51 tests API créés couvrant :
- Authentification (16 tests)
- Assets API (17 tests)
- Trading API (18 tests)

```bash
python manage.py test apps.trading.tests
# Ran 51 tests in 40s - OK
```

## 🚀 Utilisation

### Session (Navigateur)

```javascript
// Login
const response = await fetch('/api/auth/login/', {
  method: 'POST',
  credentials: 'include',
  body: JSON.stringify({ username, password })
});

// API calls
const assets = await fetch('/api/assets/', {
  credentials: 'include'
});
```

### JWT (Apps)

```javascript
// Login
const { access, refresh } = await fetch('/api/auth/jwt/login/', {
  method: 'POST',
  body: JSON.stringify({ username, password })
}).then(r => r.json());

// API calls
const assets = await fetch('/api/assets/', {
  headers: { 'Authorization': `Bearer ${access}` }
});
```

