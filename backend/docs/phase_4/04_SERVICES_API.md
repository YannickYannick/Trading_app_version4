# 🌐 Phase 4.4 : Services API Créés

## Vue d'ensemble

Tous les services API ont été créés pour communiquer avec le backend Django. La structure est modulaire, typée et gère automatiquement l'authentification et les erreurs.

## ✅ Checklist Complétée

- [x] Client HTTP de base créé (`api/client.ts`)
- [x] Intercepteurs configurés (requêtes et réponses)
- [x] Service d'authentification créé (`api/auth.ts`)
- [x] Service pour les assets créé (`assets.ts`)
- [x] Service pour les positions créé (`positions.ts`)
- [x] Service pour les trades créé (`trades.ts`)
- [x] Service pour les orders créé (`orders.ts`)
- [x] Service pour les brokers créé (`brokers.ts`)
- [x] Service pour les strategies créé (`strategies.ts`)
- [x] Gestion d'erreurs centralisée
- [x] Types TypeScript pour toutes les réponses
- [x] Refresh token automatique

---

## 📦 Structure des Services

```
src/services/
├── api/
│   ├── client.ts          # Client HTTP avec intercepteurs
│   └── auth.ts            # Service d'authentification
├── assets.ts              # Service pour les assets
├── positions.ts           # Service pour les positions
├── trades.ts              # Service pour les trades
├── orders.ts              # Service pour les ordres
├── brokers.ts             # Service pour les brokers
├── strategies.ts          # Service pour les stratégies
├── api.ts                 # Legacy (compatibilité)
└── index.ts               # Exports centralisés
```

---

## 🔧 Client HTTP de Base

### `api/client.ts`

**Fonctionnalités** :
- Instance axios configurée avec baseURL
- Timeout de 30 secondes
- Support des cookies (withCredentials)
- Intercepteur de requêtes :
  - Ajout automatique du token JWT
  - Ajout du CSRF token
- Intercepteur de réponses :
  - Gestion des erreurs 401 (refresh token automatique)
  - Gestion des erreurs réseau
  - Formatage des erreurs API

**Exemple** :
```typescript
import apiClient from '@services/api/client'

// Utilisation directe
const response = await apiClient.get('/assets/')
```

---

## 🔐 Service d'Authentification

### `api/auth.ts`

**Fonctionnalités** :
- Connexion Session (`loginSession`)
- Connexion JWT (`loginJWT`)
- Déconnexion (`logout`)
- Inscription (`register`)
- Refresh token (`refreshToken`)
- Vérification token (`verifyToken`)
- Utilisateur actuel (`getCurrentUser`)

**Exemple** :
```typescript
import { authService } from '@services'

// Connexion JWT
const response = await authService.loginJWT({
  username: 'user',
  password: 'pass',
})
// Les tokens sont automatiquement stockés dans localStorage

// Vérifier si authentifié
if (authService.isAuthenticated()) {
  // ...
}

// Déconnexion
await authService.logout()
```

---

## 💰 Service Assets

### `assets.ts`

**Fonctionnalités** :
- `getAllAssets()` - Récupérer tous les AllAssets
- `getAllAssetById()` - Récupérer un AllAsset par ID
- `searchAllAssets()` - Rechercher des AllAssets
- `getAssets()` - Récupérer les assets enrichis
- `getAssetById()` - Récupérer un asset par ID
- `getAssetBySymbol()` - Récupérer par symbole
- `searchAssets()` - Rechercher des assets
- `createAsset()` - Créer un asset
- `updateAsset()` - Mettre à jour un asset
- `updatePrice()` - Mettre à jour le prix
- `deleteAsset()` - Supprimer un asset
- `getPricesBatch()` - Récupérer les prix en batch

**Exemple** :
```typescript
import { assetService } from '@services'

// Récupérer tous les assets avec filtres
const response = await assetService.getAssets({
  platform: 'SAXO',
  asset_type: 'Stock',
  search: 'AAPL',
  page: 1,
  page_size: 20,
})

// Rechercher
const assets = await assetService.searchAssets('Apple')

// Mettre à jour le prix
await assetService.updatePrice(123, 150.50)
```

---

## 📊 Service Positions

### `positions.ts`

**Fonctionnalités** :
- `getAll()` - Récupérer toutes les positions
- `getById()` - Récupérer une position par ID
- `getOpen()` - Récupérer les positions ouvertes
- `getClosed()` - Récupérer les positions fermées
- `getSummary()` - Récupérer le résumé
- `create()` - Créer une position
- `update()` - Mettre à jour une position
- `close()` - Fermer une position
- `delete()` - Supprimer une position
- `updateStopLoss()` - Mettre à jour le stop loss
- `updateTakeProfit()` - Mettre à jour le take profit

**Exemple** :
```typescript
import { positionService } from '@services'

// Récupérer les positions ouvertes
const openPositions = await positionService.getOpen()

// Créer une position
const position = await positionService.create({
  asset: 123,
  size: 10,
  entry_price: 150.50,
  side: 'BUY',
  stop_loss: 145,
  take_profit: 160,
})

// Fermer une position
await positionService.close(456, 155.00)
```

---

## 📈 Service Trades

### `trades.ts`

**Fonctionnalités** :
- `getAll()` - Récupérer tous les trades
- `getById()` - Récupérer un trade par ID
- `getRecent()` - Récupérer les trades récents
- `getByAsset()` - Récupérer par asset
- `getByDateRange()` - Récupérer par période
- `create()` - Créer un trade
- `update()` - Mettre à jour un trade
- `delete()` - Supprimer un trade
- `getStatistics()` - Obtenir les statistiques

**Exemple** :
```typescript
import { tradeService } from '@services'

// Récupérer les trades récents
const recentTrades = await tradeService.getRecent(20)

// Récupérer par période
const trades = await tradeService.getByDateRange(
  '2024-01-01',
  '2024-01-31'
)

// Obtenir les statistiques
const stats = await tradeService.getStatistics()
```

---

## 🛒 Service Orders

### `orders.ts`

**Fonctionnalités** :
- `getAll()` - Récupérer tous les ordres
- `getById()` - Récupérer un ordre par ID
- `getPending()` - Récupérer les ordres en attente
- `create()` - Créer un ordre
- `update()` - Mettre à jour un ordre
- `cancel()` - Annuler un ordre
- `delete()` - Supprimer un ordre

**Exemple** :
```typescript
import { orderService } from '@services'

// Créer un ordre limit
const order = await orderService.create({
  asset: 123,
  order_type: 'LIMIT',
  side: 'BUY',
  quantity: 10,
  price: 150.00,
})

// Annuler un ordre
await orderService.cancel(456)
```

---

## 🏦 Service Brokers

### `brokers.ts`

**Fonctionnalités** :
- `getAll()` - Récupérer tous les brokers
- `getById()` - Récupérer un broker par ID
- `getAccounts()` - Récupérer tous les comptes
- `getAccountById()` - Récupérer un compte par ID
- `createAccount()` - Créer un compte broker
- `updateAccount()` - Mettre à jour un compte
- `deleteAccount()` - Supprimer un compte
- `testConnection()` - Tester la connexion
- `sync()` - Synchroniser les données
- `getSyncLogs()` - Récupérer les logs de sync
- `getLastSyncLog()` - Récupérer le dernier log

**Exemple** :
```typescript
import { brokerService } from '@services'

// Tester la connexion
const test = await brokerService.testConnection(accountId)
if (test.success) {
  console.log('Connexion OK')
}

// Synchroniser les assets
await brokerService.sync(accountId, {
  sync_type: 'ASSETS',
  force: true,
})

// Récupérer les logs
const logs = await brokerService.getSyncLogs(accountId)
```

---

## 🎯 Service Strategies

### `strategies.ts`

**Fonctionnalités** :
- `getAll()` - Récupérer toutes les stratégies
- `getById()` - Récupérer une stratégie par ID
- `getActive()` - Récupérer les stratégies actives
- `create()` - Créer une stratégie
- `update()` - Mettre à jour une stratégie
- `toggleActive()` - Activer/Désactiver
- `delete()` - Supprimer une stratégie
- `getPerformance()` - Récupérer les performances
- `getAllPerformance()` - Récupérer toutes les performances

**Exemple** :
```typescript
import { strategyService } from '@services'

// Créer une stratégie
const strategy = await strategyService.create({
  name: 'Momentum',
  description: 'Stratégie de momentum',
  strategy_type: 'MOMENTUM',
  is_active: true,
})

// Récupérer les performances
const performance = await strategyService.getPerformance(strategyId)
```

---

## 🔄 Gestion Automatique

### Refresh Token

Le client HTTP gère automatiquement le refresh du token JWT :
- Détection des erreurs 401
- Tentative de refresh automatique
- Réessai de la requête originale
- Déconnexion si le refresh échoue

### Gestion d'Erreurs

Toutes les erreurs sont formatées de manière cohérente :
```typescript
interface ApiError {
  error: string
  code?: string
  details?: Record<string, any>
  message?: string
}
```

---

## 📝 Utilisation dans les Composants

### Exemple avec Hook

```typescript
// hooks/useAssets.ts
import { useState, useEffect } from 'react'
import { assetService } from '@services'
import type { Asset } from '@types'

export function useAssets(filters?: { platform?: 'SAXO' | 'BINANCE' }) {
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchAssets() {
      try {
        setLoading(true)
        const response = await assetService.getAssets(filters)
        setAssets(response.results)
        setError(null)
      } catch (err: any) {
        setError(err.error || 'Erreur lors du chargement')
      } finally {
        setLoading(false)
      }
    }

    fetchAssets()
  }, [filters?.platform])

  return { assets, loading, error }
}
```

### Exemple dans un Composant

```typescript
// pages/AssetsPage.tsx
import { useAssets } from '@hooks/useAssets'
import { Loading, Table } from '@components/common'

export default function AssetsPage() {
  const { assets, loading, error } = useAssets({ platform: 'SAXO' })

  if (loading) return <Loading />
  if (error) return <div>Erreur: {error}</div>

  return (
    <Table
      columns={[
        { key: 'symbol', label: 'Symbole' },
        { key: 'name', label: 'Nom' },
        { key: 'current_price', label: 'Prix' },
      ]}
      data={assets}
      keyExtractor={(asset) => asset.id}
    />
  )
}
```

---

## 🔗 Imports

Tous les services sont exportés depuis `@services` :

```typescript
import {
  apiClient,
  authService,
  assetService,
  positionService,
  tradeService,
  orderService,
  brokerService,
  strategyService,
} from '@services'
```

---

## ✅ Prochaines Étapes

1. **Hooks personnalisés** : Créer des hooks pour chaque service
2. **Pages principales** : Implémenter avec les services
3. **Gestion d'état** : Intégrer avec Zustand/Redux si nécessaire
4. **Tests** : Créer des tests pour les services

---

## 📚 Ressources

- **Services** : `src/services/`
- **Types** : `src/types/index.ts`
- **Config** : `src/utils/config.ts`
- **Backend API** : `backend/apps/trading/api/urls.py`

