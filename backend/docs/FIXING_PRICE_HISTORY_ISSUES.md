# Fixing Price History Issues - Problèmes et Solutions

Ce document décrit les problèmes rencontrés lors de l'implémentation de l'historique des prix et leurs solutions.

## Table des matières

1. [Problème de Routing DRF avec le paramètre `format`](#1-problème-de-routing-drf-avec-le-paramètre-format)
2. [Erreur 404/401 avec les query parameters](#2-erreur-404401-avec-les-query-parameters)
3. [Migration vers lightweight-charts v5](#3-migration-vers-lightweight-charts-v5)
4. [Boucle infinie de rechargement](#4-boucle-infinie-de-rechargement)

---

## 1. Problème de Routing DRF avec le paramètre `format`

### Symptômes

- L'endpoint `/api/all-assets/{id}/prices/` fonctionnait sans query params
- L'endpoint `/api/all-assets/{id}/prices/?days=365&format=list` retournait une erreur 404
- L'erreur persistait même après authentification

### Cause

Dans Django REST Framework, le paramètre `format` est réservé pour le système de format suffix (`.json`, `.xml`, etc.). DRF intercepte ce paramètre avant qu'il n'atteigne la vue, ce qui cause un problème de routage.

### Solution

**Renommer le paramètre `format` en `output_format`** :

**Backend (`apps/trading/api/views.py`)** :
```python
# Avant (ne fonctionne pas)
format_type = query_params.get('format', 'list')

# Après (fonctionne)
format_type = query_params.get('output_format') or query_params.get('format', 'list')
```

**Frontend (`frontend/src/services/assets.ts`)** :
```typescript
// Avant (ne fonctionne pas)
params: { days, format }

// Après (fonctionne)
params: { days, output_format: format }
```

### Références

- [Documentation DRF - Format Suffixes](https://www.django-rest-framework.org/api-guide/format-suffixes/)

---

## 2. Erreur 404/401 avec les query parameters

### Symptômes

- Erreur 404 lors des appels depuis le frontend React
- Erreur 401 (Unauthorized) lors des tests dans l'interface DRF
- Les tests Python passaient mais le frontend échouait

### Causes

1. **404** : Conflit avec le paramètre `format` (voir section 1)
2. **401** : Authentification requise mais non fournie dans l'interface DRF du navigateur

### Solutions

#### Pour l'erreur 404

Voir la section 1 - renommer `format` en `output_format`.

#### Pour l'erreur 401

L'erreur 401 dans l'interface DRF est normale si vous n'êtes pas connecté. Pour tester :
- Cliquez sur "Log in" dans l'interface DRF
- Ou utilisez le frontend React qui gère automatiquement l'authentification JWT

**Frontend (`frontend/src/services/api/client.ts`)** :
```typescript
// L'intercepteur axios ajoute automatiquement le token JWT
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const accessToken = localStorage.getItem('access_token')
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`
    }
    return config
  }
)
```

---

## 3. Migration vers lightweight-charts v5

### Symptômes

- Erreur : `addLineSeries is not a function`
- Erreur : `Assertion failed` lors de la création de série
- Erreur : `setMarkers is not a function`

### Cause

Lightweight-charts v5.0+ a changé son API :
- Les méthodes spécifiques (`addLineSeries`, `addAreaSeries`, etc.) ont été supprimées
- Une méthode générique `addSeries()` est maintenant utilisée
- Les marqueurs sont maintenant gérés via une primitive séparée `createSeriesMarkers()`

### Solutions

#### 3.1 Création de série

**Avant (v4 - ne fonctionne pas en v5)** :
```typescript
import { createChart } from 'lightweight-charts'
const chart = createChart(container, {})
const lineSeries = chart.addLineSeries({ color: 'red' })
```

**Après (v5 - fonctionne)** :
```typescript
import { createChart, LineSeries } from 'lightweight-charts'
const chart = createChart(container, {})
const lineSeries = chart.addSeries(LineSeries, { color: 'red' })
```

#### 3.2 Gestion des marqueurs

**Avant (v4 - ne fonctionne pas en v5)** :
```typescript
series.setMarkers([
  {
    time: '2019-04-09',
    position: 'aboveBar',
    color: 'black',
    shape: 'arrowDown',
  },
])
```

**Après (v5 - fonctionne)** :
```typescript
import { createSeriesMarkers } from 'lightweight-charts'

const seriesMarkers = createSeriesMarkers(series, [
  {
    time: '2019-04-09',
    position: 'aboveBar',
    color: 'black',
    shape: 'arrowDown',
  },
])

// Pour mettre à jour les marqueurs plus tard
seriesMarkers.setMarkers([/* nouveaux marqueurs */])
```

### Références

- [Documentation officielle - Migration v4 vers v5](https://tradingview.github.io/lightweight-charts/docs/migrations/from-v4-to-v5)

---

## 4. Boucle infinie de rechargement

### Symptômes

- Le graphique se recharge en boucle infinie
- Les logs montrent des appels répétés à `loadPriceHistory`
- Performance dégradée

### Cause

Le `useEffect` qui charge l'historique des prix avait `loadPriceHistory` dans ses dépendances. Comme `loadPriceHistory` est un `useCallback` qui dépend de `allAssetsMap` et `priceColors`, il peut changer à chaque render, déclenchant le `useEffect` en boucle.

### Solution

**Avant (boucle infinie)** :
```typescript
useEffect(() => {
  if (selectedAssets.length > 0) {
    loadPriceHistory(selectedAssets)
  }
}, [selectedAssets, loadPriceHistory]) // ❌ loadPriceHistory change souvent
```

**Après (pas de boucle)** :
```typescript
const prevSelectedAssetsRef = useRef<number[]>([])

useEffect(() => {
  // Comparer les assets pour éviter les rechargements inutiles
  const prevAssets = prevSelectedAssetsRef.current
  const assetsChanged = 
    prevAssets.length !== selectedAssets.length ||
    !prevAssets.every((id, index) => id === selectedAssets[index])

  if (!assetsChanged && selectedAssets.length > 0) {
    return // Pas besoin de recharger
  }

  prevSelectedAssetsRef.current = [...selectedAssets]

  if (selectedAssets.length > 0) {
    loadPriceHistory(selectedAssets)
  }
}, [selectedAssets.join(',')]) // ✅ Dépendance stable
```

### Points clés

1. **Comparaison des assets** : Vérifier si les assets ont réellement changé avant de recharger
2. **Dépendances stables** : Utiliser `selectedAssets.join(',')` au lieu de `loadPriceHistory`
3. **Référence pour comparaison** : Utiliser `useRef` pour stocker les assets précédents

---

## Résumé des fichiers modifiés

### Backend
- `apps/trading/api/views.py` : Renommage du paramètre `format` en `output_format`
- `apps/trading/api/serializers.py` : Aucune modification nécessaire

### Frontend
- `frontend/src/services/assets.ts` : Utilisation de `output_format` au lieu de `format`
- `frontend/src/components/trades/TradesChart.tsx` : 
  - Migration vers l'API v5 de lightweight-charts
  - Correction de la boucle infinie
  - Gestion des marqueurs via `createSeriesMarkers`

---

## Tests effectués

1. ✅ Endpoint `/api/all-assets/{id}/prices/` sans query params
2. ✅ Endpoint `/api/all-assets/{id}/prices/?days=365&output_format=list`
3. ✅ Création de série avec `addSeries(LineSeries, options)`
4. ✅ Gestion des marqueurs avec `createSeriesMarkers`
5. ✅ Pas de boucle infinie lors du chargement du graphique

---

## Notes importantes

- **Toujours vérifier la documentation officielle** lors de la migration de versions majeures
- **Tester les endpoints avec et sans authentification** pour identifier les problèmes
- **Utiliser des dépendances stables** dans les `useEffect` pour éviter les boucles infinies
- **Éviter les noms de paramètres réservés** dans les frameworks (comme `format` dans DRF)



