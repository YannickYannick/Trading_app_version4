# 🗄️ Modèles de données

## Architecture

Les modèles sont divisés en modules pour faciliter la maintenance :

```
models/
├── base.py         # Modèle abstrait de base
├── assets.py       # Assets et prix
├── trading.py      # Positions, trades, ordres
├── strategies.py   # Stratégies de trading
├── brokers.py      # Brokers et comptes
└── automation.py   # Tâches automatisées
```

## `base.py` - Modèle de base

```python
from django.db import models

class TimeStampedModel(models.Model):
    """Modèle abstrait avec created_at et updated_at."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']

BROKER_CHOICES = [
    ('SAXO', 'Saxo Bank'),
    ('BINANCE', 'Binance'),
    ('YAHOO', 'Yahoo Finance'),
    ('OTHER', 'Autre'),
]
```

## `assets.py` - Assets

### AllAssets (Catalogue universel)

```python
class AllAssets(TimeStampedModel):
    """Catalogue universel d'actifs depuis les APIs brokers."""
    symbol = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    platform = models.CharField(max_length=20, choices=BROKER_CHOICES)
    asset_type = models.CharField(max_length=50)
    market = models.CharField(max_length=50)
    currency = models.CharField(max_length=10, default='USD')
    exchange = models.CharField(max_length=100, blank=True)
    is_tradable = models.BooleanField(default=True)
    
    # Champs Saxo
    saxo_uic = models.IntegerField(null=True, blank=True)
    saxo_exchange_id = models.CharField(max_length=20, blank=True)
    
    # Champs Binance
    binance_base_asset = models.CharField(max_length=20, blank=True)
    binance_quote_asset = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = ['symbol', 'platform']
```

### Asset (Enrichi)

```python
class Asset(TimeStampedModel):
    """Asset avec données enrichies (Yahoo Finance, etc.)."""
    all_asset = models.ForeignKey(AllAssets, on_delete=models.SET_NULL, null=True)
    symbol = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    asset_type = models.CharField(max_length=50)
    currency = models.CharField(max_length=10, default='USD')
    
    # Données enrichies
    sector = models.CharField(max_length=100, blank=True)
    industry = models.CharField(max_length=100, blank=True)
    market_cap = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    pe_ratio = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    # Prix actuel
    current_price = models.DecimalField(max_digits=20, decimal_places=8, null=True)
    price_updated_at = models.DateTimeField(null=True)
    is_active = models.BooleanField(default=True)
```

### AssetPrice (Historique)

```python
class AssetPrice(TimeStampedModel):
    """Historique des prix OHLCV."""
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    date = models.DateField()
    open_price = models.DecimalField(max_digits=20, decimal_places=8)
    high_price = models.DecimalField(max_digits=20, decimal_places=8)
    low_price = models.DecimalField(max_digits=20, decimal_places=8)
    close_price = models.DecimalField(max_digits=20, decimal_places=8)
    volume = models.BigIntegerField(null=True)

    class Meta:
        unique_together = ['asset', 'date']
```

## `trading.py` - Trading

### Position

```python
class Position(TimeStampedModel):
    """Position de trading."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    broker = models.ForeignKey(Broker, on_delete=models.CASCADE)
    strategy = models.ForeignKey(Strategy, on_delete=models.SET_NULL, null=True)
    
    side = models.CharField(max_length=10, choices=[('LONG', 'Long'), ('SHORT', 'Short')])
    quantity = models.DecimalField(max_digits=20, decimal_places=8)
    entry_price = models.DecimalField(max_digits=20, decimal_places=8)
    current_price = models.DecimalField(max_digits=20, decimal_places=8, null=True)
    stop_loss = models.DecimalField(max_digits=20, decimal_places=8, null=True)
    take_profit = models.DecimalField(max_digits=20, decimal_places=8, null=True)
    
    is_open = models.BooleanField(default=True)
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True)

    @property
    def pnl(self):
        """Calcule le P&L."""
        if not self.current_price:
            return Decimal('0')
        diff = self.current_price - self.entry_price
        if self.side == 'SHORT':
            diff = -diff
        return diff * self.quantity
```

### Trade

```python
class Trade(TimeStampedModel):
    """Trade exécuté."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    broker = models.ForeignKey(Broker, on_delete=models.CASCADE)
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True)
    
    trade_type = models.CharField(max_length=10, choices=[('BUY', 'Achat'), ('SELL', 'Vente')])
    quantity = models.DecimalField(max_digits=20, decimal_places=8)
    price = models.DecimalField(max_digits=20, decimal_places=8)
    fees = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    executed_at = models.DateTimeField()

    @property
    def total_value(self):
        return self.quantity * self.price
```

### Order

```python
class Order(TimeStampedModel):
    """Ordre en attente."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    broker = models.ForeignKey(Broker, on_delete=models.CASCADE)
    
    ORDER_TYPES = [('MARKET', 'Market'), ('LIMIT', 'Limit'), ('STOP', 'Stop')]
    STATUS_CHOICES = [('PENDING', 'En attente'), ('FILLED', 'Exécuté'), ('CANCELLED', 'Annulé')]
    
    order_type = models.CharField(max_length=20, choices=ORDER_TYPES)
    side = models.CharField(max_length=10, choices=[('BUY', 'Achat'), ('SELL', 'Vente')])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    quantity = models.DecimalField(max_digits=20, decimal_places=8)
    price = models.DecimalField(max_digits=20, decimal_places=8, null=True)
    stop_price = models.DecimalField(max_digits=20, decimal_places=8, null=True)
    filled_quantity = models.DecimalField(max_digits=20, decimal_places=8, default=0)
```

## `strategies.py` - Stratégies

```python
class Strategy(TimeStampedModel):
    """Stratégie de trading."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    risk_level = models.CharField(max_length=20, choices=[
        ('LOW', 'Faible'), ('MEDIUM', 'Moyen'), ('HIGH', 'Élevé')
    ])
    max_position_size = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    max_daily_loss = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    parameters = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    is_automated = models.BooleanField(default=False)
```

## `brokers.py` - Brokers

```python
class Broker(TimeStampedModel):
    """Broker supporté."""
    name = models.CharField(max_length=100)
    broker_type = models.CharField(max_length=20, choices=BROKER_CHOICES)
    api_base_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    supports_stocks = models.BooleanField(default=False)
    supports_crypto = models.BooleanField(default=False)


class BrokerAccount(TimeStampedModel):
    """Compte broker d'un utilisateur."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    broker = models.ForeignKey(Broker, on_delete=models.CASCADE)
    account_id = models.CharField(max_length=100)
    account_name = models.CharField(max_length=100)
    access_token = models.TextField(blank=True)  # Chiffré en prod
    refresh_token = models.TextField(blank=True)
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='USD')
    is_active = models.BooleanField(default=True)
    is_demo = models.BooleanField(default=False)
```

## Diagramme des relations

```
User
 ├── BrokerAccount (1:N)
 │    └── Broker
 ├── Strategy (1:N)
 ├── Position (1:N)
 │    ├── Asset → AllAssets
 │    ├── Broker
 │    └── Strategy
 ├── Trade (1:N)
 │    ├── Asset
 │    ├── Broker
 │    └── Position
 └── Order (1:N)
      ├── Asset
      └── Broker

AllAssets ← Asset (1:N enrichi)
Asset ← AssetPrice (1:N historique)
```

