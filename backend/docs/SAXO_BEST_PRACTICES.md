# 📚 Bonnes Pratiques - Intégration Saxo Bank

## 🎯 Guide de Référence Post-Résolution

Ce document compile les bonnes pratiques à suivre pour l'intégration Saxo Bank, basées sur les problèmes résolus.

---

## 1. ✅ Utilisation des DataClasses

### BrokerPosition - Paramètres Corrects

```python
from apps.trading.brokers.base import BrokerPosition
from decimal import Decimal

# ✅ CORRECT
position = BrokerPosition(
    symbol='AAPL',
    quantity=Decimal('100'),
    entry_price=Decimal('150.50'),      # ✅ entry_price
    current_price=Decimal('155.00'),
    side='LONG',                         # ✅ 'LONG' ou 'SHORT'
    pnl=Decimal('450.00'),              # ✅ pnl
    pnl_percent=Decimal('2.99'),
    broker_position_id='SAX123',
    raw_data={'currency': 'USD'}        # ✅ currency dans raw_data
)

# ❌ INCORRECT - Ne jamais utiliser
position = BrokerPosition(
    average_price=Decimal('150.50'),    # ❌ N'existe pas
    unrealized_pnl=Decimal('450.00'),   # ❌ N'existe pas
    currency='USD'                       # ❌ N'est pas un paramètre direct
)
```

### BrokerTrade - Paramètres Corrects

```python
from apps.trading.brokers.base import BrokerTrade
from decimal import Decimal

# ✅ CORRECT
trade = BrokerTrade(
    symbol='AAPL',
    trade_type='BUY',                    # ✅ 'BUY' ou 'SELL'
    quantity=Decimal('100'),
    price=Decimal('150.50'),
    fees=Decimal('2.50'),               # ✅ fees
    executed_at='2025-12-29T10:30:00Z', # ✅ executed_at
    broker_trade_id='TRD123',
    raw_data={'order_id': 'ORD456'}
)

# ❌ INCORRECT - Ne jamais utiliser
trade = BrokerTrade(
    side='buy',                          # ❌ Utiliser trade_type
    commission=Decimal('2.50'),         # ❌ Utiliser fees
    timestamp='2025-12-29T10:30:00Z'    # ❌ Utiliser executed_at
)
```

---

## 2. 🔄 Mapping des Données Saxo API

### Positions Saxo → BrokerPosition

```python
def map_saxo_position(saxo_data: dict) -> BrokerPosition:
    """
    Convertit une position Saxo en BrokerPosition
    
    Saxo API Response Structure:
    {
        "PositionId": "SAX123",
        "PositionBase": {
            "Symbol": "AAPL",
            "Amount": 100,          # Négatif si SHORT
            "Uic": 211,
            "Currency": "USD"
        },
        "PositionView": {
            "AverageOpenPrice": 150.50,
            "CurrentPrice": 155.00,
            "ProfitLossOnTrade": 450.00
        }
    }
    """
    position_base = saxo_data['PositionBase']
    position_view = saxo_data['PositionView']
    
    # 1. Extraire la quantité et déterminer le side
    amount = Decimal(str(position_base.get('Amount', 0)))
    side = 'LONG' if amount >= 0 else 'SHORT'
    quantity = abs(amount)  # Toujours positif
    
    # 2. Extraire les prix
    entry_price = Decimal(str(position_view.get('AverageOpenPrice', 0)))
    current_price = Decimal(str(position_view.get('CurrentPrice', 0)))
    pnl = Decimal(str(position_view.get('ProfitLossOnTrade', 0)))
    
    # 3. Calculer le PnL en pourcentage
    pnl_percent = Decimal('0')
    if entry_price and entry_price > 0:
        pnl_percent = ((current_price - entry_price) / entry_price) * Decimal('100')
    
    # 4. Créer BrokerPosition
    return BrokerPosition(
        symbol=position_base.get('Symbol', ''),
        quantity=quantity,
        entry_price=entry_price,
        current_price=current_price,
        side=side,
        pnl=pnl,
        pnl_percent=pnl_percent,
        broker_position_id=str(saxo_data.get('PositionId', '')),
        raw_data={
            'uic': position_base.get('Uic'),
            'currency': position_base.get('Currency', 'USD'),
            'position_base': position_base,
            'position_view': position_view
        }
    )
```

### Trades/Orders Saxo → BrokerTrade

```python
def map_saxo_trade(saxo_order: dict) -> BrokerTrade:
    """
    Convertit un ordre Saxo en BrokerTrade
    
    Saxo API Order Structure:
    {
        "OrderId": "ORD123",
        "Symbol": "AAPL",
        "BuySell": "Buy",        # "Buy" ou "Sell"
        "Amount": 100,
        "FilledAmount": 100,
        "Price": 150.50,
        "FilledTime": "2025-12-29T10:30:00Z",
        "OrderTime": "2025-12-29T10:29:00Z",
        "Commission": 2.50
    }
    """
    # 1. Convertir BuySell en trade_type
    trade_type = 'BUY' if saxo_order.get('BuySell') == 'Buy' else 'SELL'
    
    # 2. Utiliser FilledAmount ou Amount
    quantity = Decimal(str(saxo_order.get('FilledAmount', saxo_order.get('Amount', 0))))
    
    # 3. Prix et frais
    price = Decimal(str(saxo_order.get('Price', 0)))
    fees = Decimal(str(saxo_order.get('Commission', 0)))
    
    # 4. Timestamp d'exécution
    executed_at = saxo_order.get('FilledTime') or saxo_order.get('OrderTime')
    
    # 5. Créer BrokerTrade
    return BrokerTrade(
        symbol=saxo_order.get('Symbol', ''),
        trade_type=trade_type,
        quantity=quantity,
        price=price,
        fees=fees,
        executed_at=executed_at,
        broker_trade_id=str(saxo_order.get('OrderId', '')),
        raw_data=saxo_order
    )
```

---

## 3. 🛡️ Validations Essentielles

### Avant la Création d'une Position

```python
def validate_broker_position(broker_position: BrokerPosition) -> None:
    """Valide un BrokerPosition avant sauvegarde"""
    
    # 1. Symbol non vide
    if not broker_position.symbol or not broker_position.symbol.strip():
        raise ValueError(f"Position has empty or invalid symbol")
    
    # 2. Side valide
    if broker_position.side not in ['LONG', 'SHORT']:
        raise ValueError(f"Invalid side: {broker_position.side}. Must be 'LONG' or 'SHORT'")
    
    # 3. Quantité positive
    if broker_position.quantity < 0:
        raise ValueError(f"Quantity must be positive: {broker_position.quantity}")
    
    # 4. Prix positifs
    if broker_position.entry_price < 0 or broker_position.current_price < 0:
        raise ValueError(f"Prices must be positive")
    
    # 5. Broker ID présent
    if not broker_position.broker_position_id:
        raise ValueError(f"Missing broker_position_id")
```

### Avant la Création d'un Trade

```python
def validate_broker_trade(broker_trade: BrokerTrade) -> None:
    """Valide un BrokerTrade avant sauvegarde"""
    
    # 1. Symbol non vide
    if not broker_trade.symbol or not broker_trade.symbol.strip():
        raise ValueError(f"Trade has empty or invalid symbol")
    
    # 2. Trade type valide
    if broker_trade.trade_type not in ['BUY', 'SELL']:
        raise ValueError(f"Invalid trade_type: {broker_trade.trade_type}. Must be 'BUY' or 'SELL'")
    
    # 3. Quantité positive
    if broker_trade.quantity <= 0:
        raise ValueError(f"Quantity must be positive: {broker_trade.quantity}")
    
    # 4. Prix positif
    if broker_trade.price <= 0:
        raise ValueError(f"Price must be positive: {broker_trade.price}")
```

---

## 4. 📝 Logging Recommandé

### Structure de Logs

```python
import logging

logger = logging.getLogger(__name__)

def sync_saxo_positions(user):
    """Synchronise les positions Saxo avec logging approprié"""
    
    # Début de sync
    logger.info(f"Starting Saxo position sync for user {user.username}")
    
    try:
        # Récupération depuis API
        broker_positions = get_saxo_positions(user)
        logger.info(f"Retrieved {len(broker_positions)} positions from Saxo API")
        
        # Traitement position par position
        synced_count = 0
        failed_count = 0
        
        for broker_pos in broker_positions:
            try:
                logger.debug(f"Processing position: {broker_pos.symbol}, side={broker_pos.side}, qty={broker_pos.quantity}")
                
                position, created = sync_single_position(broker_pos)
                
                action = "created" if created else "updated"
                logger.info(f"Position {position.id} {action}: {broker_pos.symbol} {broker_pos.side}")
                synced_count += 1
                
            except Exception as e:
                logger.error(f"Failed to sync position {broker_pos.symbol}: {str(e)}", exc_info=True)
                failed_count += 1
        
        # Résumé
        logger.info(f"Saxo position sync completed: {synced_count} synced, {failed_count} failed")
        
        return {
            'success': True,
            'synced': synced_count,
            'failed': failed_count
        }
        
    except Exception as e:
        logger.error(f"Saxo position sync failed: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }
```

---

## 5. 🧪 Tests Unitaires Obligatoires

### Tests à Inclure Systématiquement

```python
class TestSaxoSync(TestCase):
    
    def test_broker_position_with_correct_params(self):
        """Vérifie que BrokerPosition accepte les bons paramètres"""
        # Test à inclure dans chaque suite de tests
        pass
    
    def test_saxo_position_mapping(self):
        """Vérifie le mapping Saxo API → BrokerPosition"""
        # Test avec données réelles de l'API Saxo
        pass
    
    def test_side_determination_from_quantity(self):
        """Vérifie la détermination du side depuis la quantité"""
        # Important car Saxo utilise des quantités négatives pour SHORT
        pass
    
    def test_position_validation(self):
        """Vérifie que les validations fonctionnent"""
        # Test des cas limites et erreurs
        pass
```

---

## 6. ⚠️ Pièges à Éviter

### ❌ Erreurs Communes

```python
# 1. ❌ Utiliser des noms de paramètres incorrects
position = BrokerPosition(
    average_price=150.50,  # ❌ N'existe pas
)

# 2. ❌ Oublier le side
position = BrokerPosition(
    symbol='AAPL',
    quantity=100,
    entry_price=150,
    current_price=155
    # ❌ side manquant
)

# 3. ❌ Confondre trade_type et side
trade = BrokerTrade(
    side='buy',  # ❌ Utiliser trade_type
)

# 4. ❌ Convertir incorrectement le side pour Position model
side = 'BUY' if broker_position.side == 'LONG' else 'SELL'  # ❌
# Position model attend 'LONG'/'SHORT', pas 'BUY'/'SELL'

# 5. ❌ Oublier abs() pour quantités négatives
quantity = amount  # ❌ Peut être négatif
quantity = abs(amount)  # ✅ Toujours positif
```

### ✅ Solutions

```python
# 1. ✅ Toujours utiliser les noms corrects
position = BrokerPosition(
    entry_price=150.50,  # ✅
)

# 2. ✅ Toujours inclure le side
side = 'LONG' if amount >= 0 else 'SHORT'
position = BrokerPosition(
    symbol='AAPL',
    quantity=abs(amount),
    entry_price=150,
    current_price=155,
    side=side  # ✅
)

# 3. ✅ Utiliser trade_type pour BrokerTrade
trade = BrokerTrade(
    trade_type='BUY',  # ✅
)

# 4. ✅ Pas de conversion nécessaire
side = broker_position.side.upper()  # ✅ Déjà 'LONG'/'SHORT'

# 5. ✅ Toujours prendre la valeur absolue
quantity = abs(amount)  # ✅
```

---

## 7. 🔍 Checklist de Vérification

Avant de considérer une intégration comme terminée :

- [ ] Les paramètres `BrokerPosition` sont corrects (`entry_price`, `pnl`, `side`)

- [ ] Les paramètres `BrokerTrade` sont corrects (`trade_type`, `fees`, `executed_at`)

- [ ] Le mapping Saxo API → BrokerPosition est testé

- [ ] Le mapping Saxo API → BrokerTrade est testé

- [ ] La détermination du `side` depuis la quantité fonctionne

- [ ] Les validations sont en place (symbol, side, quantités)

- [ ] Les logs sont clairs et informatifs

- [ ] Les tests unitaires couvrent les cas limites

- [ ] Le script de monitoring fonctionne

- [ ] La documentation est à jour

---

## 8. 📚 Ressources

### Fichiers de Référence

- `backend/apps/trading/brokers/base.py` - DataClasses BrokerPosition/BrokerTrade

- `backend/apps/trading/brokers/saxo.py` - Implémentation Saxo

- `backend/apps/trading/services/sync/position_sync_service.py` - Service de sync

- `backend/apps/trading/models/trading.py` - Modèles Position/Trade

### Documentation Saxo Bank

- [Saxo OpenAPI Documentation](https://www.developer.saxo/)

- [Portfolio Positions Endpoint](https://www.developer.saxo/openapi/referencedocs/port/v1/positions)

- [Orders Endpoint](https://www.developer.saxo/openapi/referencedocs/trade/v2/orders)

---

## 🎯 Conclusion

En suivant ces bonnes pratiques, vous éviterez les erreurs courantes d'intégration Saxo Bank et assurerez une synchronisation fiable des positions et trades.

**Points Clés** :

1. Respecter strictement les noms de paramètres des DataClasses

2. Valider les données avant sauvegarde

3. Logger les opérations importantes

4. Tester les cas limites

5. Documenter les décisions de design

**Dernière mise à jour** : 2025-12-29


