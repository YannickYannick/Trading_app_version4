# 🔄 Services de Synchronisation - Documentation

## Vue d'ensemble

Les services de synchronisation gèrent la récupération et le stockage des données depuis les brokers vers la base de données locale.

## Architecture

```
apps/trading/services/
├── __init__.py
├── broker_service.py           # Service principal broker
└── sync/
    ├── __init__.py
    ├── asset_sync_service.py   # Synchronisation des actifs
    └── price_sync_service.py   # Synchronisation des prix
```

## AssetSyncService

**Fichier** : `apps/trading/services/sync/asset_sync_service.py`

### Description

Synchronise les actifs depuis les APIs des brokers vers le catalogue `AllAssets`.

### Méthodes principales

| Méthode | Description |
|---------|-------------|
| `sync_assets()` | Sync les actifs d'un type donné |
| `sync_all_asset_types()` | Sync tous les types d'actifs |
| `search_and_sync()` | Recherche et sync des actifs |

### Utilisation

```python
from apps.trading.services.sync.asset_sync_service import AssetSyncService

# Créer le service
service = AssetSyncService(user)

# Synchroniser les actions
result = service.sync_assets(
    broker_account,
    asset_type='Stock',
    keywords='',
    limit=1000
)

print(result)
# {
#     'success': True,
#     'message': 'Synced 150 assets (120 created, 30 updated)',
#     'created': 120,
#     'updated': 30,
#     'errors': []
# }
```

### Sync de tous les types

```python
# Synchroniser tous les types d'actifs
result = service.sync_all_asset_types(
    broker_account,
    limit_per_type=500
)

# Pour Saxo: Stock, ETF, FX, CFD
# Pour Binance: Crypto
```

### Recherche et synchronisation

```python
# Rechercher et synchroniser des actifs spécifiques
result = service.search_and_sync(
    broker_account,
    keywords='AAPL',
    asset_type='Stock',
    limit=50
)

# Retourne aussi les actifs synchronisés
print(result['synced_assets'])
# [{'id': 1, 'symbol': 'AAPL', 'name': 'Apple Inc.', ...}]
```

## PriceSyncService

**Fichier** : `apps/trading/services/sync/price_sync_service.py`

### Description

Synchronise les prix des actifs depuis les brokers.

### Méthodes principales

| Méthode | Description |
|---------|-------------|
| `sync_current_prices()` | Sync les prix actuels |
| `sync_single_price()` | Sync le prix d'un seul actif |
| `sync_historical_prices()` | Sync les prix historiques |
| `update_all_asset_prices()` | Met à jour tous les prix |
| `get_price_with_fallback()` | Prix avec fallback multi-broker |

### Utilisation

```python
from apps.trading.services.sync.price_sync_service import PriceSyncService

# Créer le service
service = PriceSyncService(user)

# Synchroniser les prix de plusieurs actifs
result = service.sync_current_prices(
    broker_account,
    symbols=['AAPL', 'GOOGL', 'MSFT']
)

print(result)
# {
#     'success': True,
#     'message': 'Updated 3 prices',
#     'updated': 3,
#     'prices': {'AAPL': '150.50', 'GOOGL': '140.25', 'MSFT': '380.00'}
# }
```

### Prix unique

```python
# Récupérer et mettre à jour le prix d'un seul actif
price = service.sync_single_price(broker_account, 'AAPL')
print(price)  # Decimal('150.50')
```

### Prix historiques (Binance)

```python
# Synchroniser les prix historiques (30 derniers jours)
result = service.sync_historical_prices(
    broker_account,
    symbol='BTCUSDT',
    days=30
)

# Stocke les données dans AssetPrice
print(result)
# {'success': True, 'message': 'Synced 30 historical prices', 'records': 30}
```

### Mise à jour globale

```python
# Mettre à jour tous les prix d'une plateforme
result = service.update_all_asset_prices(
    broker_account,
    batch_size=50  # Par lots de 50
)

print(result)
# {
#     'success': True,
#     'total_assets': 150,
#     'updated': 145,
#     'errors': [...]
# }
```

### Fallback multi-broker

```python
# Essayer plusieurs brokers pour obtenir un prix
accounts = BrokerAccount.objects.filter(user=user, is_active=True)
price = service.get_price_with_fallback('AAPL', list(accounts))
```

## Modèle AllAssets

**Fichier** : `apps/trading/models/assets.py`

Le catalogue universel des actifs :

```python
class AllAssets(models.Model):
    symbol = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    platform = models.CharField(max_length=20, choices=BROKER_CHOICES)
    asset_type = models.CharField(max_length=50)
    market = models.CharField(max_length=50)
    currency = models.CharField(max_length=10, default='USD')
    is_tradable = models.BooleanField(default=True)
    
    # Champs spécifiques Saxo
    saxo_uic = models.IntegerField(null=True, blank=True)
    
    # Champs spécifiques Binance
    binance_base_asset = models.CharField(max_length=20, blank=True)
    binance_quote_asset = models.CharField(max_length=20, blank=True)
    
    class Meta:
        unique_together = ['symbol', 'platform']
```

## Modèle Asset

Actifs enrichis avec prix actuels :

```python
class Asset(TimeStampedModel):
    all_asset = models.ForeignKey(AllAssets, null=True, blank=True)
    symbol = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    current_price = models.DecimalField(max_digits=20, decimal_places=8, null=True)
    price_updated_at = models.DateTimeField(null=True)
```

## Modèle AssetPrice

Historique des prix :

```python
class AssetPrice(TimeStampedModel):
    asset = models.ForeignKey(Asset, related_name='price_history')
    date = models.DateField()
    open_price = models.DecimalField(max_digits=20, decimal_places=8)
    high_price = models.DecimalField(max_digits=20, decimal_places=8)
    low_price = models.DecimalField(max_digits=20, decimal_places=8)
    close_price = models.DecimalField(max_digits=20, decimal_places=8)
    volume = models.BigIntegerField(null=True)
```

## Logs de synchronisation

Chaque synchronisation est enregistrée :

```python
class BrokerSyncLog(TimeStampedModel):
    broker_account = models.ForeignKey(BrokerAccount)
    sync_type = models.CharField(max_length=50)  # 'assets', 'prices'
    status = models.CharField(max_length=20)     # 'success', 'error'
    records_synced = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    details = models.JSONField(default=dict)
```

## Workflow de synchronisation

```
1. Créer BrokerAccount avec credentials
         ↓
2. AssetSyncService.sync_assets()
   - Authentification broker
   - Récupération des actifs
   - Stockage dans AllAssets
         ↓
3. Asset.create_from_all_asset()
   - Création des actifs enrichis
         ↓
4. PriceSyncService.sync_current_prices()
   - Mise à jour des prix actuels
         ↓
5. PriceSyncService.sync_historical_prices()
   - Stockage historique (optionnel)
```

## Résumé

| Service | Données | Stockage |
|---------|---------|----------|
| AssetSyncService | Actifs | AllAssets |
| PriceSyncService | Prix actuels | Asset.current_price |
| PriceSyncService | Prix historiques | AssetPrice |

