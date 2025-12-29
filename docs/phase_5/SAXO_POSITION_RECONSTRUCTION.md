# 🔧 Reconstruction des Positions Saxo depuis les Transactions

## 📋 Vue d'ensemble

Ce document décrit le système de reconstruction des positions Saxo Bank à partir des transactions brutes (`hist/v1/transactions`), remplaçant complètement l'usage de `hist/v3/positions`.

**Date** : 2025-12-29  
**Version** : 1.0

---

## 🎯 Objectif

Reconstruire des positions (open → close) à partir des transactions brutes, offrant :
- **Niveau de détail supérieur** à celui fourni par Saxo
- **Granularité fine** : chaque transaction est prise en compte
- **Gestion complète** : frais, funding, clôtures partielles, scaling
- **Source de vérité unique** : basée uniquement sur les transactions

---

## 📊 Structure des Données

### Transaction Saxo (hist/v1/transactions)

```python
{
    "TransactionId": "123456",
    "TradeId": "TRADE_001",           # ✅ Clé de regroupement
    "Uic": 211,                        # ✅ Clé de regroupement
    "TransactionType": "Trade",        # Trade, Commission, Funding, etc.
    "ToOpenOrClose": "Open",           # ✅ Open ou Close
    "TradeDate": "2025-01-01T10:00:00Z",
    "Amount": 100,                     # ✅ Quantité
    "Price": 150.50,                   # ✅ Prix d'exécution
    "AmountAccountValue": 15050.00,    # Valeur en compte
    "FundingSubType": "Commission",    # ✅ Pour distinguer fees/funding
    # ... autres champs
}
```

### Position Reconstruite

```python
@dataclass
class ReconstructedPosition:
    # Identifiants
    trade_id: str              # TradeId Saxo
    uic: int                   # UIC de l'instrument
    instrument_symbol: Optional[str]
    
    # Direction et quantité
    direction: str             # 'LONG' ou 'SHORT'
    quantity: Decimal          # Quantité finale
    
    # Dates et prix
    open_date: Optional[datetime]
    open_price: Decimal        # Prix moyen pondéré d'ouverture
    close_date: Optional[datetime]
    close_price: Decimal       # Prix moyen pondéré de fermeture
    
    # P&L
    gross_pnl: Decimal         # P&L brut
    total_fees: Decimal        # Frais totaux
    total_funding: Decimal     # Funding total
    net_pnl: Decimal           # P&L net = brut - frais - funding
    
    # Détails
    is_closed: bool
    partial_closes: int        # Nombre de clôtures partielles
    scaling_in_count: int      # Nombre d'ajouts à la position
```

---

## 🔄 Algorithme de Reconstruction

### Étape 1 : Récupération des Transactions

```python
# Depuis SaxoBroker
transactions = broker.get_transactions(
    from_date='2025-01-01',
    to_date='2025-12-31',
    limit=10000
)
```

### Étape 2 : Regroupement par TradeId et Uic

```python
grouped = {}
for txn in transactions:
    key = (txn['TradeId'], txn['Uic'])
    grouped[key].append(txn)
```

**Règle** : Une position = toutes les transactions avec le même `(TradeId, Uic)`

### Étape 3 : Classification des Transactions

Pour chaque groupe, séparer en 4 catégories :

1. **Open** : `ToOpenOrClose == 'Open'`
2. **Close** : `ToOpenOrClose == 'Close'`
3. **Fees** : `FundingSubType` dans `['Commission', 'BrokerCommission', ...]`
4. **Funding** : `FundingSubType` dans `['Funding', 'Interest', ...]`

### Étape 4 : Calcul de la Direction et Quantité

```python
# Quantité nette d'ouverture
open_amount = sum(txn['Amount'] for txn in open_transactions)

# Quantité nette de fermeture
close_amount = sum(abs(txn['Amount']) for txn in close_transactions)

# Quantité finale
final_quantity = open_amount - close_amount

# Direction
if final_quantity > 0:
    direction = 'LONG'
elif final_quantity < 0:
    direction = 'SHORT'
else:
    direction = 'LONG' if open_amount > 0 else 'SHORT'  # Position fermée
```

### Étape 5 : Calcul des Prix Moyens

**Prix moyen d'ouverture** (pondéré par quantité) :
```python
total_value = sum(txn['Amount'] * txn['Price'] for txn in open_transactions)
total_qty = sum(txn['Amount'] for txn in open_transactions)
open_price = total_value / total_qty
```

**Prix moyen de fermeture** (pondéré par quantité) :
```python
total_value = sum(abs(txn['Amount']) * txn['Price'] for txn in close_transactions)
total_qty = sum(abs(txn['Amount']) for txn in close_transactions)
close_price = total_value / total_qty
```

### Étape 6 : Calcul des Frais et Funding

```python
# Frais totaux (valeur absolue)
total_fees = sum(abs(txn['AmountAccountValue']) for txn in fee_transactions)

# Funding total (peut être positif ou négatif)
total_funding = sum(txn['AmountAccountValue'] for txn in funding_transactions)
```

### Étape 7 : Calcul du P&L

**Pour LONG** :
```python
if position.is_closed:
    gross_pnl = (close_price - open_price) * quantity
```

**Pour SHORT** :
```python
if position.is_closed:
    gross_pnl = (open_price - close_price) * quantity
```

**P&L Net** :
```python
net_pnl = gross_pnl - total_fees - total_funding
```

---

## 📝 Exemple Complet

### Transaction Input

```python
transactions = [
    # Ouverture
    {
        'TradeId': 'TRADE_001',
        'Uic': 211,
        'TransactionType': 'Trade',
        'ToOpenOrClose': 'Open',
        'TradeDate': '2025-01-01T10:00:00Z',
        'Amount': 100,
        'Price': 150.50,
    },
    # Commission d'ouverture
    {
        'TradeId': 'TRADE_001',
        'Uic': 211,
        'TransactionType': 'Commission',
        'FundingSubType': 'Commission',
        'AmountAccountValue': -2.50,
    },
    # Ajout à la position (scaling in)
    {
        'TradeId': 'TRADE_001',
        'Uic': 211,
        'TransactionType': 'Trade',
        'ToOpenOrClose': 'Open',
        'TradeDate': '2025-01-02T10:00:00Z',
        'Amount': 50,
        'Price': 152.00,
    },
    # Fermeture partielle
    {
        'TradeId': 'TRADE_001',
        'Uic': 211,
        'TransactionType': 'Trade',
        'ToOpenOrClose': 'Close',
        'TradeDate': '2025-01-03T10:00:00Z',
        'Amount': -75,
        'Price': 155.00,
    },
    # Commission de fermeture
    {
        'TradeId': 'TRADE_001',
        'Uic': 211,
        'TransactionType': 'Commission',
        'FundingSubType': 'Commission',
        'AmountAccountValue': -1.88,
    },
    # Fermeture finale
    {
        'TradeId': 'TRADE_001',
        'Uic': 211,
        'TransactionType': 'Trade',
        'ToOpenOrClose': 'Close',
        'TradeDate': '2025-01-04T10:00:00Z',
        'Amount': -75,
        'Price': 156.00,
    },
    # Commission finale
    {
        'TradeId': 'TRADE_001',
        'Uic': 211,
        'TransactionType': 'Commission',
        'FundingSubType': 'Commission',
        'AmountAccountValue': -1.88,
    },
]
```

### Position Reconstruite

```python
ReconstructedPosition(
    trade_id='TRADE_001',
    uic=211,
    direction='LONG',
    quantity=Decimal('0'),  # Fermée
    
    # Prix moyen d'ouverture = (100*150.50 + 50*152.00) / 150 = 151.00
    open_price=Decimal('151.00'),
    open_date=datetime(2025, 1, 1),
    
    # Prix moyen de fermeture = (75*155.00 + 75*156.00) / 150 = 155.50
    close_price=Decimal('155.50'),
    close_date=datetime(2025, 1, 4),
    
    # P&L brut = (155.50 - 151.00) * 150 = 675.00
    gross_pnl=Decimal('675.00'),
    
    # Frais = 2.50 + 1.88 + 1.88 = 6.26
    total_fees=Decimal('6.26'),
    
    total_funding=Decimal('0'),
    
    # P&L net = 675.00 - 6.26 = 668.74
    net_pnl=Decimal('668.74'),
    
    is_closed=True,
    partial_closes=2,
    scaling_in_count=1,
)
```

---

## 🚀 Utilisation

### Service Principal

```python
from apps.trading.services.saxo_historical_positions import SaxoHistoricalPositionsService

service = SaxoHistoricalPositionsService(user=user)

# Récupérer les positions fermées
closed_positions = service.get_closed_positions(
    broker_account=account,
    from_date='2025-01-01',
    to_date='2025-12-31'
)

# Récupérer toutes les positions
all_positions = service.get_all_positions(
    broker_account=account,
    from_date='2025-01-01'
)

# Calculer les métriques de performance
metrics = service.get_performance_metrics(
    broker_account=account,
    from_date='2025-01-01'
)

print(f"Winrate: {metrics['winrate']:.2f}%")
print(f"P&L Net Total: {metrics['total_net_pnl']:.2f}")
```

### Reconstruction Directe

```python
from apps.trading.services.saxo_position_reconstructor import PositionReconstructor

# Transactions depuis l'API
transactions = broker.get_transactions(...)

# Reconstruire
reconstructor = PositionReconstructor(transactions)
positions = reconstructor.reconstruct()

for pos in positions:
    print(f"Trade {pos.trade_id}: {pos.direction} {pos.quantity} @ {pos.open_price}")
    print(f"  P&L Net: {pos.net_pnl}")
```

---

## 🎯 Avantages vs hist/v3/positions

| Aspect | hist/v3/positions | hist/v1/transactions (Reconstruction) |
|--------|------------------|--------------------------------------|
| **Granularité** | Agrégé par position | Transaction par transaction |
| **Frais** | Parfois inclus | Détail complet |
| **Funding** | Limité | Détail complet |
| **Clôtures partielles** | Moyennées | Chaque clôture séparée |
| **Scaling** | Moyenné | Chaque ajout séparé |
| **Historique** | Limité | Complet |
| **Fiabilité** | Dépend de Saxo | Source de vérité |

---

## 📚 Fichiers

- **Service** : `backend/apps/trading/services/saxo_position_reconstructor.py`
- **Intégration** : `backend/apps/trading/services/saxo_historical_positions.py`
- **Broker** : `backend/apps/trading/brokers/saxo.py` (méthode `get_transactions()`)
- **Tests** : `backend/apps/trading/tests/test_saxo_position_reconstruction.py`

---

## ✅ Statut

- ✅ Reconstruction de base implémentée
- ✅ Gestion des frais et funding
- ✅ Clôtures partielles
- ✅ Scaling in/out
- ✅ Calcul du P&L
- ✅ Tests unitaires
- ✅ Service d'intégration
- ✅ Documentation

**Date de création** : 2025-12-29


