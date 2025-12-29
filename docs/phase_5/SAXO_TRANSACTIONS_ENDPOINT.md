# 📊 Endpoint Transactions Saxo

## 📋 Vue d'ensemble

Cet endpoint permet de récupérer et visualiser les transactions brutes Saxo depuis `hist/v1/transactions` directement dans l'interface web.

**Date** : 2025-12-29  
**Version** : 1.0

---

## 🎯 Objectif

Permettre la visualisation des transactions Saxo brutes sans synchronisation, pour :
- Debugger les problèmes de synchronisation
- Analyser l'historique des transactions
- Vérifier les données avant synchronisation
- Comprendre la structure des transactions

---

## 🔧 Implémentation

### Backend

**Fichier** : `backend/apps/trading/api/views.py`

**Endpoint** :
```
GET /api/broker-accounts/{id}/saxo-transactions/
```

**Paramètres de requête** :
- `from_date` (optionnel) : Date de début (format `YYYY-MM-DD`)
- `to_date` (optionnel) : Date de fin (format `YYYY-MM-DD`)
- `limit` (optionnel) : Nombre maximum de transactions (défaut: 1000)

**Réponse** :
```json
{
  "success": true,
  "count": 10,
  "transactions": [
    {
      "TransactionType": "Trade",
      "TradeId": "6475879404",
      "Date": "2025-11-11",
      "Instrument": {
        "Symbol": "MP:xnys",
        "Uic": 20088572,
        ...
      },
      "Trades": [...],
      "Bookings": [...]
    }
  ]
}
```

### Frontend

**Fichier** : `frontend/src/components/brokers/SaxoTransactionsModal.tsx`

**Composant** : Modal affichant les transactions dans un tableau avec :
- Filtres par date (from_date, to_date)
- Limite ajustable
- Tableau avec colonnes : Date, Type, TradeId, UIC, Symbole, Quantité, Prix, Valeur
- Détails JSON expandables par transaction

**Bouton** : "📊 Transactions" visible uniquement pour les comptes Saxo

---

## 🚀 Utilisation

### Via l'Interface Web

1. Aller sur `/brokers`
2. Sur un compte Saxo, cliquer sur **"📊 Transactions"**
3. Le modal s'ouvre avec les transactions des 30 derniers jours
4. Ajuster les filtres (dates, limite) si nécessaire
5. Cliquer sur "Actualiser" pour charger

### Via l'API

```bash
GET /api/broker-accounts/4/saxo-transactions/?from_date=2025-11-01&to_date=2025-11-30&limit=500
```

### Via le Service Frontend

```typescript
import { brokerService } from '@services'

const result = await brokerService.getSaxoTransactions(accountId, {
  from_date: '2025-11-01',
  to_date: '2025-11-30',
  limit: 500
})
```

---

## 📊 Structure des Transactions

Les transactions contiennent différents types :

### Transaction Trade

```json
{
  "TransactionType": "Trade",
  "TradeId": "6475879404",
  "Instrument": {
    "Symbol": "MP:xnys",
    "Uic": 20088572
  },
  "Trades": [
    {
      "ToOpenOrClose": "ToOpen",
      "TradedQuantity": 2,
      "Price": 63.21,
      "TradeExecutionTime": "2025-11-11T14:30:01Z"
    }
  ],
  "Bookings": [
    {
      "AmountType": "Commission",
      "BookedAmount": -0.86
    }
  ]
}
```

### Transaction Deposit

```json
{
  "TransactionType": "CashTransfer",
  "FundingSubType": "DepositFromExternal",
  "BookedAmount": 910,
  "Date": "2025-10-15"
}
```

---

## 🔍 Cas d'Usage

### 1. Vérifier les Trades avant Synchronisation

1. Ouvrir le modal Transactions
2. Filtrer par type "Trade"
3. Vérifier que les données sont correctes
4. Lancer la synchronisation

### 2. Analyser les Frais

1. Ouvrir le modal Transactions
2. Regarder les `Bookings[]` avec `AmountType == "Commission"`
3. Vérifier les montants des commissions

### 3. Debugger les Problèmes

1. Si un trade n'apparaît pas après synchronisation
2. Vérifier dans le modal s'il existe dans les transactions
3. Analyser la structure JSON pour comprendre le problème

---

## 📚 Fichiers

- **Backend** : `backend/apps/trading/api/views.py` (méthode `saxo_transactions()`)
- **Service Backend** : `backend/apps/trading/brokers/saxo.py` (méthode `get_transactions()`)
- **Service Frontend** : `frontend/src/services/brokers.ts` (méthode `getSaxoTransactions()`)
- **Composant** : `frontend/src/components/brokers/SaxoTransactionsModal.tsx`
- **Styles** : `frontend/src/components/brokers/SaxoTransactionsModal.css`

---

## ✅ Statut

- ✅ Endpoint backend créé
- ✅ Service frontend créé
- ✅ Modal de visualisation
- ✅ Filtres par date
- ✅ Tableau avec détails
- ✅ Intégration dans page Brokers

**Date de création** : 2025-12-29


