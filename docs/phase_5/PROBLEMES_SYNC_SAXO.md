# 🔧 Problèmes de Synchronisation Saxo Bank - Positions et Trades

## 📋 Résumé

Ce document décrit les problèmes rencontrés lors de la synchronisation des positions et trades depuis Saxo Bank, ainsi que les solutions appliquées.

**Date** : 2025-12-29  
**Version** : 4.0  
**Statut** : ✅ Résolu

---

## ❌ Problème 1 : Erreur `BrokerPosition.__init__()` - Argument inattendu `average_price`

### Symptômes

```
TypeError: BrokerPosition.__init__() got an unexpected keyword argument 'average_price'
```

**Erreur complète** :
```
[ERROR] Saxo get_positions error: BrokerPosition.__init__() got an unexpected keyword argument 'average_price'
[ERROR] Position sync failed: Failed to get positions: BrokerPosition.__init__() got an unexpected keyword argument 'average_price'
```

### Cause

Le code dans `saxo.py` utilisait des noms de paramètres incorrects lors de la création des objets `BrokerPosition` :

- ❌ `average_price` au lieu de `entry_price`
- ❌ `unrealized_pnl` au lieu de `pnl`
- ❌ `currency` (champ qui n'existe pas dans `BrokerPosition`)
- ❌ `side` manquant (requis par le modèle)

### Solution

**Fichier** : `backend/apps/trading/brokers/saxo.py`

**Correction appliquée** :

```python
# Avant (INCORRECT)
position = BrokerPosition(
    symbol=position_base.get('Symbol', ''),
    quantity=Decimal(str(position_base.get('Amount', 0))),
    average_price=Decimal(str(position_view.get('AverageOpenPrice', 0))),  # ❌
    current_price=Decimal(str(position_view.get('CurrentPrice', 0))),
    unrealized_pnl=Decimal(str(position_view.get('ProfitLossOnTrade', 0))),  # ❌
    currency=position_base.get('Currency', 'USD'),  # ❌
    broker_position_id=str(item.get('PositionId', '')),
    raw_data={...}
)

# Après (CORRECT)
# Déterminer le side (LONG ou SHORT) à partir de la quantité
amount = Decimal(str(position_base.get('Amount', 0)))
side = 'LONG' if amount >= 0 else 'SHORT'

# Extraire les prix et PnL
entry_price = Decimal(str(position_view.get('AverageOpenPrice', 0)))
current_price = Decimal(str(position_view.get('CurrentPrice', 0)))
pnl = Decimal(str(position_view.get('ProfitLossOnTrade', 0)))

# Calculer le PnL en pourcentage
pnl_percent = Decimal('0')
if entry_price and entry_price > 0:
    pnl_percent = ((current_price - entry_price) / entry_price) * Decimal('100')

position = BrokerPosition(
    symbol=position_base.get('Symbol', ''),
    quantity=abs(amount),  # Quantité absolue
    entry_price=entry_price,  # ✅
    current_price=current_price,
    side=side,  # ✅
    pnl=pnl,  # ✅
    pnl_percent=pnl_percent,  # ✅
    broker_position_id=str(item.get('PositionId', '')),
    raw_data={
        'uic': position_base.get('Uic'),
        'currency': position_base.get('Currency', 'USD'),  # Dans raw_data ✅
        ...
    }
)
```

**Lignes modifiées** :
- `get_positions()` : Lignes ~736-755
- `get_position_details()` : Lignes ~809-830

---

## ❌ Problème 2 : Erreur `BrokerTrade.__init__()` - Paramètres incorrects

### Symptômes

Le code utilisait des noms de paramètres incorrects pour `BrokerTrade` :
- ❌ `side` au lieu de `trade_type`
- ❌ `timestamp` au lieu de `executed_at`
- ❌ `commission` au lieu de `fees`

### Solution

**Fichier** : `backend/apps/trading/brokers/saxo.py`

**Correction appliquée** :

```python
# Avant (INCORRECT)
trade = BrokerTrade(
    symbol=item.get('Symbol', ''),
    side='buy' if item.get('BuySell') == 'Buy' else 'sell',  # ❌
    quantity=Decimal(str(item.get('FilledAmount', item.get('Amount', 0)))),
    price=Decimal(str(item.get('Price', 0))),
    timestamp=item.get('FilledTime') or item.get('OrderTime'),  # ❌
    broker_trade_id=str(item.get('OrderId', '')),
    commission=Decimal(str(item.get('Commission', 0))),  # ❌
    raw_data={...}
)

# Après (CORRECT)
trade = BrokerTrade(
    symbol=item.get('Symbol', ''),
    trade_type='BUY' if item.get('BuySell') == 'Buy' else 'SELL',  # ✅
    quantity=Decimal(str(item.get('FilledAmount', item.get('Amount', 0)))),
    price=Decimal(str(item.get('Price', 0))),
    executed_at=item.get('FilledTime') or item.get('OrderTime'),  # ✅
    broker_trade_id=str(item.get('OrderId', '')),
    fees=Decimal(str(item.get('Commission', 0))),  # ✅
    raw_data={...}
)
```

**Lignes modifiées** :
- `get_trades()` : Lignes ~849-865

---

## ❌ Problème 3 : Positions non sauvegardées - Conversion incorrecte du `side`

### Symptômes

- 5 positions récupérées depuis Saxo
- Seulement 1 position sauvegardée dans la base de données
- Le `side` affiché était `BUY` au lieu de `LONG`/`SHORT`

### Cause

Le code de synchronisation convertissait incorrectement le `side` :
- Le modèle `Position` attend `LONG` ou `SHORT` (selon `PositionSide`)
- Le code convertissait `LONG` → `BUY` et `SHORT` → `SELL` (incorrect)

### Solution

**Fichier** : `backend/apps/trading/services/sync/position_sync_service.py`

**Correction appliquée** :

```python
# Avant (INCORRECT)
side = 'BUY' if broker_position.side == 'LONG' else 'SELL'  # ❌

# Après (CORRECT)
# Convert side: BrokerPosition uses 'LONG'/'SHORT', Position model also uses 'LONG'/'SHORT'
side = broker_position.side.upper() if broker_position.side else 'LONG'
if side not in ['LONG', 'SHORT']:
    # Fallback: if side is invalid, determine from quantity
    side = 'LONG' if broker_position.quantity >= 0 else 'SHORT'
```

**Lignes modifiées** :
- `_sync_single_position()` : Lignes ~227-232

---

## ❌ Problème 4 : Logique de sauvegarde des positions inefficace

### Symptômes

- Utilisation de `update_or_create()` avec plusieurs critères pouvant créer des doublons
- Pas de logs détaillés pour identifier les échecs

### Solution

**Fichier** : `backend/apps/trading/services/sync/position_sync_service.py`

**Améliorations appliquées** :

1. **Recherche explicite avant création** :
```python
# Recherche explicite de position existante
existing_position = Position.objects.filter(
    user=self.user,
    broker=broker_account.broker,
    asset=asset,
    side=side,
    is_open=True,
).first()

if existing_position:
    # Mise à jour
    existing_position.quantity = broker_position.quantity
    existing_position.entry_price = entry_price
    existing_position.current_price = broker_position.current_price
    existing_position.side = side  # S'assurer que le side est correct
    existing_position.is_open = True
    existing_position.save()
    created = False
else:
    # Création
    position = Position.objects.create(...)
    created = True
```

2. **Logging amélioré** :
```python
self.logger.info(f"Processing position: {broker_position.symbol}, side={broker_position.side}")
self.logger.info(f"Position {position.id} created/updated successfully")
```

3. **Validation renforcée** :
```python
# Validation du symbol
if not broker_position.symbol or not broker_position.symbol.strip():
    raise ValueError(f"Position has empty or invalid symbol")
```

**Lignes modifiées** :
- `_sync_positions()` : Lignes ~146-166 (logging amélioré)
- `_sync_single_position()` : Lignes ~207-280 (validation et logique améliorée)

---

## ✅ Structure des Modèles

### BrokerPosition (base.py)

```python
@dataclass
class BrokerPosition:
    symbol: str
    quantity: Decimal
    entry_price: Decimal  # ✅ Pas 'average_price'
    current_price: Decimal
    side: str  # 'LONG' or 'SHORT' ✅
    pnl: Decimal = Decimal('0')  # ✅ Pas 'unrealized_pnl'
    pnl_percent: Decimal = Decimal('0')
    broker_position_id: Optional[str] = None
    raw_data: Optional[Dict] = None
```

### BrokerTrade (base.py)

```python
@dataclass
class BrokerTrade:
    symbol: str
    trade_type: str  # 'BUY' or 'SELL' ✅ Pas 'side'
    quantity: Decimal
    price: Decimal
    fees: Decimal = Decimal('0')  # ✅ Pas 'commission'
    executed_at: Optional[str] = None  # ✅ Pas 'timestamp'
    broker_trade_id: Optional[str] = None
    raw_data: Optional[Dict] = None
```

### Position (models/trading.py)

```python
class Position(TimeStampedModel):
    class PositionSide(models.TextChoices):
        LONG = 'LONG', 'Long'  # ✅
        SHORT = 'SHORT', 'Short'  # ✅
    
    side = models.CharField(
        max_length=10, 
        choices=PositionSide.choices, 
        default=PositionSide.LONG
    )
    # ...
```

---

## 🧪 Tests de Vérification

### Test 1 : Vérifier les positions sauvegardées

```python
from apps.trading.models import Position, BrokerAccount
from django.contrib.auth.models import User

user = User.objects.first()
account = BrokerAccount.objects.filter(user=user, broker_type='SAXO', is_active=True).first()
positions = Position.objects.filter(user=user, broker=account.broker, is_open=True)

print(f"Positions Saxo ouvertes: {positions.count()}")
for p in positions:
    print(f"  - {p.asset.symbol} {p.side} qty={p.quantity}")
```

### Test 2 : Vérifier les trades sauvegardés

```python
from apps.trading.models import Trade, BrokerAccount
from django.contrib.auth.models import User

user = User.objects.first()
account = BrokerAccount.objects.filter(user=user, broker_type='SAXO', is_active=True).first()
trades = Trade.objects.filter(user=user, broker=account.broker)

print(f"Trades Saxo: {trades.count()}")
for t in trades[:10]:
    print(f"  - {t.trade_type} {t.quantity} {t.asset.symbol} @ {t.price}")
```

---

## 📊 Résultats Attendus

Après les corrections :

1. ✅ **Positions** : Toutes les positions récupérées depuis Saxo sont sauvegardées
2. ✅ **Trades** : Tous les trades récupérés depuis Saxo sont sauvegardés
3. ✅ **Side** : Les positions utilisent correctement `LONG`/`SHORT`
4. ✅ **Logs** : Les logs indiquent clairement les créations/mises à jour/erreurs

---

## 🔍 Points d'Attention

1. **Quantité négative** : Les positions SHORT ont une quantité négative dans l'API Saxo, le code utilise `abs(amount)` pour la sauvegarde
2. **Side déterminé** : Le side est déterminé à partir du signe de la quantité si non fourni
3. **PnL en pourcentage** : Calculé automatiquement si `entry_price > 0`
4. **Currency** : Stocké dans `raw_data` car `BrokerPosition` n'a pas de champ `currency`

---

## 📚 Fichiers Modifiés

1. `backend/apps/trading/brokers/saxo.py`
   - `get_positions()` : Correction des paramètres `BrokerPosition`
   - `get_position_details()` : Correction des paramètres `BrokerPosition`
   - `get_trades()` : Correction des paramètres `BrokerTrade`

2. `backend/apps/trading/services/sync/position_sync_service.py`
   - `_sync_single_position()` : Correction du `side`, amélioration de la logique
   - `_sync_positions()` : Amélioration du logging

---

## ❌ Problème 5 : Positions avec symboles vides

### Symptômes

- 5 positions récupérées depuis Saxo
- Erreur : `Position has empty or invalid symbol`
- 0 position créée dans la base de données

### Cause

L'API Saxo peut parfois retourner des positions sans champ `Symbol` dans `PositionBase`. Le code rejetait ces positions car la validation exige un symbole non vide.

### Solution

**Fichier** : `backend/apps/trading/brokers/saxo.py`

**Correction appliquée** :

1. **Nouvelle méthode `_get_symbol_from_uic()`** : Tente de récupérer le symbole depuis l'UIC via l'API Saxo

2. **Gestion du symbole vide dans `get_positions()`** :
```python
# Extraire le symbole
symbol = position_base.get('Symbol', '').strip()
uic = position_base.get('Uic')
asset_type = position_base.get('AssetType', 'Stock')

# Si le symbole est vide, essayer de le récupérer depuis l'UIC
if not symbol and uic:
    try:
        symbol_from_uic = self._get_symbol_from_uic(uic, asset_type)
        if symbol_from_uic:
            symbol = symbol_from_uic
            logger.debug(f"Saxo: Recovered symbol {symbol} from UIC {uic}")
    except Exception as e:
        logger.warning(f"Saxo: Error recovering symbol from UIC {uic}: {e}")

# Si toujours pas de symbole, utiliser un identifiant de fallback
if not symbol:
    position_id = str(item.get('PositionId', ''))
    uic_str = str(uic) if uic else 'UNKNOWN'
    symbol = f"UIC_{uic_str}" if uic else f"POS_{position_id[:8]}"
    logger.warning(f"Saxo: Position {position_id} has no symbol, using fallback: {symbol}")
```

3. **Même logique dans `get_position_details()`**

**Résultats** :
- ✅ Toutes les positions sont maintenant synchronisées
- ✅ Les positions sans symbole utilisent un fallback `UIC_{uic}` ou `POS_{position_id}`
- ✅ Logging amélioré pour tracer les symboles manquants

**Lignes modifiées** :
- `get_positions()` : Lignes ~733-771 (gestion du symbole vide)
- `get_position_details()` : Lignes ~806-843 (même logique)
- `_get_symbol_from_uic()` : Lignes ~1340-1395 (nouvelle méthode)

---

## ✅ Statut Final

- ✅ Problème 1 : Résolu
- ✅ Problème 2 : Résolu
- ✅ Problème 3 : Résolu
- ✅ Problème 4 : Résolu
- ✅ Problème 5 : Résolu (Positions avec symboles vides)

**Date de résolution** : 2025-12-29  
**Version** : 4.1

## 📦 Fichiers Ajoutés

1. **`backend/apps/trading/tests/test_saxo_sync.py`** : Tests unitaires complets pour la synchronisation Saxo
2. **`backend/scripts/monitor_saxo_sync.py`** : Script de monitoring de la santé de la synchronisation
3. **`backend/docs/SAXO_BEST_PRACTICES.md`** : Guide de bonnes pratiques pour l'intégration Saxo

