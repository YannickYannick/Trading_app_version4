# 🎣 Phase 4.7 : Hooks Personnalisés Créés

## Vue d'ensemble

Tous les hooks personnalisés ont été créés pour encapsuler la logique réutilisable et séparer la logique métier de la présentation.

## ✅ Checklist Complétée

- [x] `useAssets` créé pour les assets
- [x] `usePositions` créé pour les positions (avec closePosition)
- [x] `useTrades` créé pour les trades
- [x] `useAuth` créé pour l'authentification
- [x] `useDebounce` créé pour le debounce
- [x] `useLocalStorage` créé pour le localStorage
- [x] `useApi` créé comme hook générique
- [x] Tous les hooks ont une gestion d'erreurs
- [x] Tous les hooks ont un état de chargement
- [x] Hooks utilisés dans les composants

---

## 🎣 Hooks Créés

### 1. useAssets

**Fichier** : `hooks/useAssets.ts`

**Fonctionnalités** :
- `useAssets()` - Gère les assets enrichis (Asset)
- `useAllAssets()` - Gère le catalogue universel (AllAssets)
- Auto-fetch configurable
- Gestion d'erreurs
- Total count
- Refetch manuel

**Exemple** :
```typescript
const { assets, loading, error, total, refetch } = useAssets({
  platform: 'SAXO',
  search: 'AAPL',
  autoFetch: true,
})
```

---

### 2. usePositions

**Fichier** : `hooks/usePositions.ts`

**Fonctionnalités** :
- Filtres par statut (OPEN/CLOSED)
- Résumé automatique
- Gestion d'erreurs
- `closePosition()` - Fermer une position et rafraîchir

**Exemple** :
```typescript
const { positions, loading, summary, closePosition } = usePositions({
  status: 'OPEN',
})

// Fermer une position
await closePosition(123, 150.50)
```

---

### 3. useTrades

**Fichier** : `hooks/useTrades.ts`

**Fonctionnalités** :
- Filtres par side (BUY/SELL)
- Filtres par date
- Statistiques automatiques
- Gestion d'erreurs

**Exemple** :
```typescript
const { trades, loading, statistics, refetch } = useTrades({
  side: 'BUY',
  date_from: '2024-01-01',
})
```

---

### 4. useAuth

**Fichier** : `hooks/useAuth.ts`

**Fonctionnalités** :
- Vérification automatique de l'authentification
- Chargement des infos utilisateur
- `login()` - Connexion
- `logout()` - Déconnexion
- `refreshUser()` - Rafraîchir les infos utilisateur
- Gestion d'erreurs

**Exemple** :
```typescript
const { user, isAuthenticated, loading, login, logout } = useAuth()

// Connexion
await login({ username: 'user', password: 'pass' })

// Déconnexion
await logout()
```

---

### 5. useDebounce

**Fichier** : `hooks/useDebounce.ts`

**Fonctionnalités** :
- Retarde la mise à jour d'une valeur
- Utile pour les recherches
- Délai configurable (défaut: 500ms)

**Exemple** :
```typescript
const [search, setSearch] = useState('')
const debouncedSearch = useDebounce(search, 500)

// Utiliser debouncedSearch dans useAssets
const { assets } = useAssets({ search: debouncedSearch })
```

**Cas d'usage** :
- Recherche d'assets
- Filtres de date
- Toute valeur qui doit être retardée

---

### 6. useLocalStorage

**Fichier** : `hooks/useLocalStorage.ts`

**Fonctionnalités** :
- Synchronisation avec localStorage
- API similaire à useState
- Support des fonctions de mise à jour
- Synchronisation entre onglets
- Gestion d'erreurs

**Exemple** :
```typescript
const [theme, setTheme] = useLocalStorage('theme', 'dark')

// Mettre à jour
setTheme('light')

// Avec fonction
setTheme((prev) => prev === 'dark' ? 'light' : 'dark')
```

**Cas d'usage** :
- Thème de l'application
- Préférences utilisateur
- Données de cache

---

### 7. useApi

**Fichier** : `hooks/useApi.ts`

**Fonctionnalités** :
- Hook générique pour les appels API
- Auto-fetch configurable
- Dépendances pour re-fetch
- Callbacks onSuccess/onError
- Gestion d'erreurs

**Exemple** :
```typescript
const { data: asset, loading, error, refetch } = useApi({
  fetchFn: () => assetService.getById(id),
  dependencies: [id],
  onSuccess: (data) => console.log('Asset chargé:', data),
  onError: (error) => console.error('Erreur:', error),
})
```

**Cas d'usage** :
- Chargement d'une ressource unique
- Appels API simples
- Données qui ne nécessitent pas un hook dédié

---

## 📝 Utilisation dans les Composants

### Exemple : Recherche avec debounce

```typescript
import { useState } from 'react'
import { useDebounce } from '@hooks/useDebounce'
import { useAssets } from '@hooks/useAssets'
import { Input } from '@components/common'

export default function AssetSearch() {
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebounce(search, 500)
  const { assets, loading } = useAssets({ search: debouncedSearch })

  return (
    <div>
      <Input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Rechercher un asset..."
      />
      {loading && <p>Chargement...</p>}
      {assets.map((asset) => (
        <div key={asset.id}>{asset.symbol}</div>
      ))}
    </div>
  )
}
```

### Exemple : Authentification

```typescript
import { useAuth } from '@hooks/useAuth'
import { Button } from '@components/common'

export default function UserMenu() {
  const { user, isAuthenticated, logout } = useAuth()

  if (!isAuthenticated) {
    return <div>Non connecté</div>
  }

  return (
    <div>
      <p>Bonjour, {user?.username}</p>
      <Button onClick={logout}>Déconnexion</Button>
    </div>
  )
}
```

### Exemple : LocalStorage pour les préférences

```typescript
import { useLocalStorage } from '@hooks/useLocalStorage'
import { Button } from '@components/common'

export default function ThemeToggle() {
  const [theme, setTheme] = useLocalStorage('theme', 'dark')

  return (
    <Button onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
      Thème: {theme}
    </Button>
  )
}
```

### Exemple : Hook API générique

```typescript
import { useParams } from 'react-router-dom'
import { useApi } from '@hooks/useApi'
import { assetService } from '@services'
import { Loading } from '@components/common'

export default function AssetDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: asset, loading, error } = useApi({
    fetchFn: () => assetService.getAssetById(Number(id!)),
    dependencies: [id],
  })

  if (loading) return <Loading />
  if (error) return <div>Erreur: {error}</div>
  if (!asset) return <div>Asset non trouvé</div>

  return <div>{asset.symbol}</div>
}
```

---

## 🔄 Améliorations des Hooks Existants

### usePositions

**Ajouté** :
- `closePosition()` - Méthode pour fermer une position
- Rafraîchissement automatique après fermeture

**Utilisation** :
```typescript
const { closePosition } = usePositions()

await closePosition(positionId, closePrice)
```

---

## 📦 Structure

```
hooks/
├── useAssets.ts          ✅ Assets et AllAssets
├── usePositions.ts       ✅ Positions avec closePosition
├── useTrades.ts          ✅ Trades avec statistiques
├── useAuth.ts            ✅ Authentification
├── useDebounce.ts        ✅ Debounce
├── useLocalStorage.ts    ✅ LocalStorage
├── useApi.ts             ✅ Hook générique
└── index.ts              ✅ Exports
```

---

## ✅ Prochaines Étapes

1. **Hooks supplémentaires** : useBrokers, useStrategies, useOrders
2. **Optimisations** : Cache, memoization
3. **Tests** : Tests unitaires pour les hooks
4. **Documentation** : JSDoc pour chaque hook

---

## 📚 Ressources

- **Hooks** : `src/hooks/`
- **Services** : `src/services/`
- **Types** : `src/types/index.ts`
- **Documentation React Hooks** : https://react.dev/reference/react

