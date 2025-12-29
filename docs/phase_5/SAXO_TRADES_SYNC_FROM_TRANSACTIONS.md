# 🔄 Synchronisation des Trades Saxo depuis les Transactions

## 📋 Vue d'ensemble

Ce document décrit la synchronisation des trades Saxo depuis l'endpoint `hist/v1/transactions`, remplaçant l'usage de `/port/v1/orders` pour un historique complet et précis.

**Date** : 2025-12-29  
**Version** : 1.0

---

## 🎯 Objectif

Synchroniser les trades Saxo dans le modèle `Trade` de Django en utilisant les transactions brutes (`hist/v1/transactions`) pour avoir :
- Un historique complet et granulaire
- Les frais (commissions) intégrés
- Les clôtures partielles capturées
- Une source de données fiable

---

## 🔧 Implémentation

### 1. Modification de `get_trades()`

**Fichier** : `backend/apps/trading/brokers/saxo.py`

La méthode `get_trades()` utilise maintenant `get_transactions()` qui récupère les données depuis `hist/v1/transactions`.

**Changements** :
- Utilise `hist/v1/transactions` au lieu de `/port/v1/orders`
- Extrait les données depuis `Instrument.Symbol` et `Instrument.Uic`
- Parcourt le tableau `Trades[]` pour chaque transaction
- Extrait les frais depuis `Bookings[]` avec `AmountType == "Commission"`

### 2. Structure des Données

#### Transaction Saxo (hist/v1/transactions)

```json
{
  "TransactionType": "Trade",
  "TradeId": "6475879404",
  "Date": "2025-11-11",
  "Instrument": {
    "Symbol": "MP:xnys",
    "Uic": 20088572,
    "AssetType": "Stock",
    "Description": "MP Materials Corp."
  },
  "Trades": [
    {
      "TradeId": "6475879404",
      "ToOpenOrClose": "ToOpen",
      "TradedQuantity": 2,
      "Price": 63.21,
      "TradeExecutionTime": "2025-11-11T14:30:01.043000Z",
      "TradeEventType": "Bought",
      "OrderId": "5342707954",
      "PositionId": "7365065010"
    }
  ],
  "Bookings": [
    {
      "AmountType": "Commission",
      "BookedAmount": -0.86
    },
    {
      "AmountType": "Share Amount",
      "BookedAmount": -109.24
    }
  ]
}
```

### 3. Conversion en BrokerTrade

**Logique d'extraction** :

1. **Filtrage** : Seulement `TransactionType == "Trade"` avec `Trades[]` non vide
2. **Symbole** : Extrait de `Instrument.Symbol` et nettoie (ex: "MP:xnys" → "MP")
3. **UIC** : Extrait de `Instrument.Uic`
4. **Parcours** : Boucle sur chaque élément de `Trades[]`
5. **Quantité** : `TradedQuantity` depuis `Trades[].TradedQuantity`
6. **Prix** : `Price` depuis `Trades[].Price`
7. **Date** : `TradeExecutionTime` ou `Date`
8. **Type** : Déterminé depuis `TradeEventType` (Bought/Sold) ou `Event` (Buy/Sell)
9. **Frais** : Somme des `Bookings[]` avec `AmountType == "Commission"`

### 4. ID Unique

Création d'un `broker_trade_id` composite :
- Format : `{TradeId}_{OrderId}` si les deux sont présents
- Sinon : `{TradeId}_{PositionId}`
- Dernière option : `TX_{PositionId}`

---

## 🔄 Workflow de Synchronisation

```
1. Appel API : POST /api/broker-accounts/{id}/sync/
   Body: { "sync_type": "TRADES" }

2. TradeSyncService.sync()
   ├─ SaxoBroker.get_trades()
   │  ├─ get_transactions() [hist/v1/transactions]
   │  └─ Conversion en BrokerTrade[]
   │
   └─ _sync_trades()
      └─ Pour chaque BrokerTrade:
         ├─ Vérifier si existe (broker_trade_id)
         ├─ Créer Asset si nécessaire
         ├─ Créer Trade dans la base
         └─ Lier à Position si possible
```

---

## 📊 Structure BrokerTrade

```python
BrokerTrade(
    symbol="MP",                    # Nettoyé depuis Instrument.Symbol
    trade_type="BUY",               # Bought/Sold depuis TradeEventType
    quantity=Decimal('2'),          # TradedQuantity
    price=Decimal('63.21'),         # Price
    executed_at="2025-11-11T14:30:01Z",  # TradeExecutionTime
    broker_trade_id="6475879404_5342707954",  # TradeId_OrderId
    fees=Decimal('0.86'),           # Somme des commissions
    raw_data={
        'uic': 20088572,
        'asset_type': 'Stock',
        'to_open_or_close': 'ToOpen',
        'trade_id': '6475879404',
        'order_id': '5342707954',
        'position_id': '7365065010',
        ...
    }
)
```

---

## 🚀 Utilisation

### Via l'Interface Web

1. Aller sur `/brokers`
2. Cliquer sur **"Synchroniser"** pour un compte Saxo
3. Sélectionner `sync_type: "TRADES"`
4. Les trades sont synchronisés dans `/admin/trading/trade/`

### Via l'API

```python
from apps.trading.services.sync.trade_sync_service import TradeSyncService

service = TradeSyncService(user)
result = service.sync(
    broker_account=account,
    limit=1000
)
```

### Via l'API REST

```bash
POST /api/broker-accounts/{id}/sync/
Content-Type: application/json

{
  "sync_type": "TRADES",
  "force": false
}
```

---

## ✅ Avantages vs /port/v1/orders

| Aspect | /port/v1/orders | hist/v1/transactions |
|--------|----------------|---------------------|
| **Historique** | Limité | Complet |
| **Frais** | Inclus dans Price | Détail séparé |
| **Clôtures partielles** | Moyennées | Détail complet |
| **Granularité** | Par ordre | Par transaction |
| **Fiabilité** | Dépend de Saxo | Source de vérité |

---

## 📚 Fichiers

- **Broker** : `backend/apps/trading/brokers/saxo.py` (méthode `get_trades()`)
- **Service** : `backend/apps/trading/services/sync/trade_sync_service.py`
- **Tests** : `backend/apps/trading/tests/test_saxo_sync.py`

---

## 🔍 Dépannage

### Problème : Aucun trade synchronisé

**Causes possibles** :
- Pas de transactions de type "Trade" dans la période (90 jours par défaut)
- Erreur d'authentification (token expiré)
- Format de date incorrect

**Solutions** :
- Vérifier l'authentification : `/api/broker-accounts/{id}/test-connection/`
- Augmenter la période de recherche
- Vérifier les logs : `backend/logs/sync.log`

### Problème : Doublons

**Cause** : `broker_trade_id` non unique

**Solution** : Le système utilise maintenant un ID composite `{TradeId}_{OrderId}` pour éviter les doublons.

---

## ✅ Statut

- ✅ `get_trades()` modifié pour utiliser transactions
- ✅ Extraction depuis `Trades[]` et `Instrument`
- ✅ Extraction des frais depuis `Bookings[]`
- ✅ Conversion correcte en `BrokerTrade`
- ✅ Synchronisation vers modèle `Trade`
- ✅ Tests unitaires

**Date de création** : 2025-12-29

