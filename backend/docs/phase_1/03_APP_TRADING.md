# 📦 App Trading

## Description

L'app `trading` est l'application principale qui gère toute la logique de trading : assets, positions, trades, ordres, stratégies et intégration brokers.

## Structure

```
apps/trading/
├── __init__.py
├── apps.py                 # Configuration de l'app
├── admin.py               # Interface admin Django
├── models/                # Modèles de données
│   ├── __init__.py        # Exports des modèles
│   ├── base.py            # TimeStampedModel
│   ├── assets.py          # AllAssets, Asset, AssetPrice
│   ├── trading.py         # Position, Trade, Order
│   ├── strategies.py      # Strategy, StrategyPerformance
│   ├── brokers.py         # Broker, BrokerAccount, BrokerSyncLog
│   └── automation.py      # ScheduledTask, TaskExecutionLog
├── api/                   # API REST
│   ├── __init__.py
│   ├── serializers.py     # Serializers DRF
│   ├── views.py           # ViewSets
│   ├── urls.py            # Routes API
│   └── auth_views.py      # Authentification
├── tests/                 # Tests
│   ├── __init__.py
│   └── test_api/          # Tests API
├── urls.py                # URLs de l'app
└── migrations/            # Migrations Django
```

## Configuration (`apps.py`)

```python
from django.apps import AppConfig

class TradingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.trading'
    verbose_name = 'Trading'
```

## Enregistrement dans Django

Dans `config_django/settings/base.py` :

```python
INSTALLED_APPS = [
    # ...
    'apps.trading',
]
```

## Modèles exportés (`models/__init__.py`)

```python
from .base import TimeStampedModel, BROKER_CHOICES
from .assets import AllAssets, Asset, AssetPrice
from .trading import Position, Trade, Order
from .strategies import Strategy, StrategyPerformance
from .brokers import Broker, BrokerAccount, BrokerSyncLog
from .automation import ScheduledTask, TaskExecutionLog

__all__ = [
    'TimeStampedModel', 'BROKER_CHOICES',
    'AllAssets', 'Asset', 'AssetPrice',
    'Position', 'Trade', 'Order',
    'Strategy', 'StrategyPerformance',
    'Broker', 'BrokerAccount', 'BrokerSyncLog',
    'ScheduledTask', 'TaskExecutionLog',
]
```

## URLs (`urls.py`)

```python
from django.urls import path, include

app_name = 'trading'

urlpatterns = [
    path('', include('apps.trading.api.urls')),
]
```

## Fonctionnalités

### Gestion des Assets
- Catalogue universel (AllAssets) avec données Saxo/Binance
- Assets enrichis avec données Yahoo Finance
- Historique des prix

### Trading
- Positions longues/courtes avec P&L calculé
- Historique des trades
- Ordres en attente (limit, stop, etc.)

### Stratégies
- Stratégies de trading personnalisées
- Suivi de performance quotidien
- Support pour l'automatisation

### Brokers
- Multi-brokers (Saxo, Binance, Yahoo)
- Comptes utilisateur avec tokens
- Synchronisation automatique

### Automatisation
- Tâches planifiées
- Logs d'exécution

