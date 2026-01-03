# Guide : Configuration d'un graphique TradingView (lightweight-charts)

Ce guide explique comment configurer correctement un graphique TradingView avec la bibliothèque `lightweight-charts` dans React, en évitant les pièges courants.

## 📚 Table des matières

1. [Problèmes courants](#problèmes-courants)
2. [Solution : Configuration correcte](#solution--configuration-correcte)
3. [Initialisation du graphique](#initialisation-du-graphique)
4. [Ajout de données](#ajout-de-données)
5. [Ajustement de l'échelle](#ajustement-de-léchelle)
6. [Ajout de marqueurs](#ajout-de-marqueurs)
7. [Gestion du resize](#gestion-du-resize)
8. [Checklist de débogage](#checklist-de-débogage)

---

## 🐛 Problèmes courants

### ❌ Problème 1 : Les courbes n'apparaissent pas sans zoomer

**Symptôme** : Le graphique se charge mais les courbes sont invisibles. Il faut zoomer/dézoomer pour les voir apparaître.

**Cause principale** : Le conteneur a `display: none` au moment de l'initialisation.

**Pourquoi** :
- Quand un élément a `display: none`, sa largeur est `0px`
- `lightweight-charts` calcule la largeur du graphique au moment de la création
- Si la largeur est `0`, le graphique ne peut pas afficher les données correctement
- Un "Forced reflow" (recalcul du layout) force le navigateur à recalculer la taille → les courbes apparaissent

### ❌ Problème 2 : Les marqueurs apparaissent avec un retard

**Symptôme** : Les marqueurs BUY/SELL n'apparaissent qu'après avoir sélectionné un autre asset.

**Cause** : Les marqueurs sont ajoutés dans un `useEffect` séparé qui se déclenche avant que les séries de prix ne soient complètement rendues.

### ❌ Problème 3 : L'échelle ne s'ajuste pas automatiquement

**Symptôme** : Il faut zoomer manuellement pour voir les données.

**Cause** : `fitContent()` est appelé trop tôt, avant que les données ne soient rendues.

---

## ✅ Solution : Configuration correcte

### 🔒 Règle d'or #1 : Ne JAMAIS utiliser `display: none`

**❌ MAUVAIS** :
```tsx
<div 
  ref={chartContainerRef}
  style={{ display: loading ? 'none' : 'block' }}
/>
```

**✅ BON** :
```tsx
<div 
  ref={chartContainerRef}
  style={{ 
    visibility: loading ? 'hidden' : 'visible',
    height: '500px', // Hauteur fixe pour garder la taille
    width: '100%'
  }}
/>
```

**Pourquoi** :
- `visibility: hidden` garde la taille du conteneur (largeur/hauteur)
- Le graphique peut calculer sa largeur correctement dès le début
- `display: none` fait perdre la taille → largeur = 0px

---

### 🔒 Règle d'or #2 : Vérifier la largeur avant création

```tsx
useEffect(() => {
  if (!chartContainerRef.current) return

  const containerWidth = chartContainerRef.current.clientWidth
  if (containerWidth === 0) {
    console.warn('Container has no width, chart may not render correctly')
    return // Ne pas créer le graphique si pas de largeur
  }

  const chart = createChart(chartContainerRef.current, {
    width: containerWidth, // Utiliser la largeur réelle
    height: 500,
    // ... autres options
  })
}, [])
```

---

### 🔒 Règle d'or #3 : Forcer le recalcul de taille avec `applyOptions()`

Après avoir ajouté les données, **forcer TradingView à recalculer sa taille** :

```tsx
// Après avoir ajouté toutes les séries et leurs données
requestAnimationFrame(() => {
  requestAnimationFrame(() => {
    if (chartRef.current && chartContainerRef.current) {
      const containerWidth = chartContainerRef.current.clientWidth
      
      // 🔒 Forcer le recalcul de taille (officiel)
      chartRef.current.applyOptions({
        width: containerWidth,
      })
      
      // Puis ajuster l'échelle
      chartRef.current.timeScale().fitContent()
    }
  })
})
```

**Pourquoi** :
- Le conteneur peut avoir changé de taille après le rendu
- `applyOptions({ width })` force TradingView à recalculer sa taille interne
- `fitContent()` fonctionne correctement après le recalcul

---

## 📝 Initialisation du graphique

### Structure de base

```tsx
import { useEffect, useRef } from 'react'
import { createChart, IChartApi, LineSeries, ISeriesApi } from 'lightweight-charts'

const TradesChart = () => {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const priceSeriesRefs = useRef<Map<number, ISeriesApi<'Line'>>>(new Map())

  // Initialiser le graphique
  useEffect(() => {
    if (!chartContainerRef.current) return

    // Vérifier la largeur
    const containerWidth = chartContainerRef.current.clientWidth
    if (containerWidth === 0) {
      console.warn('Container has no width')
      return
    }

    // Nettoyer l'ancien graphique
    if (chartRef.current) {
      chartRef.current.remove()
      chartRef.current = null
    }

    // Créer le graphique
    const chart = createChart(chartContainerRef.current, {
      width: containerWidth,
      height: 500,
      layout: {
        background: { color: 'transparent' },
        textColor: '#333',
      },
      grid: {
        vertLines: { color: '#f0f0f0' },
        horzLines: { color: '#f0f0f0' },
      },
      timeScale: {
        borderColor: '#e0e0e0',
        timeVisible: true,
        secondsVisible: false,
        // ⚠️ Ne PAS utiliser fitContent: true ici
        // On le gère manuellement après le chargement des données
      },
      crosshair: {
        mode: 1, // Normal mode
      },
    })

    chartRef.current = chart

    // Gestion du resize
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        })
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      if (chartRef.current) {
        chartRef.current.remove()
        chartRef.current = null
      }
    }
  }, [])

  return (
    <div 
      ref={chartContainerRef}
      style={{ 
        visibility: loading ? 'hidden' : 'visible', // ✅ Pas display: none
        height: '500px',
        width: '100%'
      }}
    />
  )
}
```

---

## 📊 Ajout de données

### Format des données

Les données doivent être au format :

```typescript
interface LineData {
  time: string // Format 'YYYY-MM-DD' pour daily
  value: number // Prix de clôture
}
```

### Ajout d'une série

```tsx
// Créer une série
const series = chartRef.current.addSeries(LineSeries, {
  color: '#3b82f6',
  lineWidth: 2,
  title: 'AAPL',
  priceLineVisible: false,
  lastValueVisible: true,
})

// Ajouter les données
const priceData: LineData[] = history.results
  .map((point) => ({
    time: point.date.split('T')[0], // Format YYYY-MM-DD
    value: point.close || 0,
  }))
  .filter((point) => point.value > 0 && point.time)
  .sort((a, b) => (a.time as string).localeCompare(b.time as string))

series.setData(priceData)
```

**⚠️ Important** :
- Trier les données chronologiquement
- Filtrer les valeurs invalides (null, 0, NaN)
- Convertir les dates au format `YYYY-MM-DD`

---

## 🎯 Ajustement de l'échelle

### ✅ Méthode correcte (après toutes les données)

```tsx
// Après avoir ajouté TOUTES les séries et leurs données
requestAnimationFrame(() => {
  requestAnimationFrame(() => {
    if (chartRef.current && chartContainerRef.current) {
      const containerWidth = chartContainerRef.current.clientWidth
      
      // 1. Forcer le recalcul de taille
      if (containerWidth > 0) {
        chartRef.current.applyOptions({
          width: containerWidth,
        })
      }
      
      // 2. Reset de l'échelle (si disponible)
      const timeScale = chartRef.current.timeScale()
      if (typeof timeScale.resetTimeScale === 'function') {
        timeScale.resetTimeScale()
      }
      
      // 3. Ajuster l'échelle UNE SEULE FOIS
      timeScale.fitContent()
    }
  })
})
```

**⚠️ Ne PAS** :
- Appeler `fitContent()` plusieurs fois avec des délais croissants
- Appeler `fitContent()` avant que toutes les données soient ajoutées
- Utiliser `fitContent: true` dans les options initiales (non supporté)

---

## 📍 Ajout de marqueurs

### Format des marqueurs

```typescript
interface MarkerData {
  time: string // Format 'YYYY-MM-DD'
  position: 'belowBar' | 'aboveBar'
  color: string
  shape: 'arrowUp' | 'arrowDown'
  text: string
}
```

### Ajout de marqueurs

```tsx
import { createSeriesMarkers } from 'lightweight-charts'

// Convertir les trades en marqueurs
const markers: MarkerData[] = trades.map((trade) => {
  const isBuy = trade.side === 'BUY'
  return {
    time: trade.executed_at.split('T')[0], // Format YYYY-MM-DD
    position: isBuy ? 'belowBar' : 'aboveBar',
    color: isBuy ? '#3b82f6' : '#ef4444', // Bleu pour BUY, rouge pour SELL
    shape: isBuy ? 'arrowUp' : 'arrowDown',
    text: `${trade.side} ${trade.quantity} @ ${trade.price}`,
  }
})

// Créer les marqueurs pour une série
const markersPrimitive = createSeriesMarkers(series, markers)

// Mettre à jour les marqueurs
markersPrimitive.setMarkers(markers)
```

**⚠️ Important** :
- Ajouter les marqueurs **APRÈS** l'ajustement de l'échelle (`fitContent()`)
- Les marqueurs peuvent interférer avec l'ajustement initial si ajoutés trop tôt

---

## 🔄 Gestion du resize

### Resize automatique

```tsx
useEffect(() => {
  const handleResize = () => {
    if (chartContainerRef.current && chartRef.current) {
      const newWidth = chartContainerRef.current.clientWidth
      chartRef.current.applyOptions({
        width: newWidth,
      })
    }
  }

  window.addEventListener('resize', handleResize)
  
  return () => {
    window.removeEventListener('resize', handleResize)
  }
}, [])
```

---

## ✅ Checklist de débogage

Si les courbes n'apparaissent pas :

1. ✅ **Vérifier que le conteneur n'utilise PAS `display: none`**
   ```tsx
   // ❌ MAUVAIS
   style={{ display: loading ? 'none' : 'block' }}
   
   // ✅ BON
   style={{ visibility: loading ? 'hidden' : 'visible', height: '500px' }}
   ```

2. ✅ **Vérifier la largeur du conteneur**
   ```tsx
   console.log('Container width:', chartContainerRef.current?.clientWidth)
   // Doit être > 0
   ```

3. ✅ **Vérifier que `applyOptions({ width })` est appelé**
   ```tsx
   chartRef.current.applyOptions({ width: containerWidth })
   ```

4. ✅ **Vérifier que `fitContent()` est appelé APRÈS toutes les données**
   ```tsx
   // Après series.setData() pour toutes les séries
   chartRef.current.timeScale().fitContent()
   ```

5. ✅ **Vérifier le format des dates**
   ```tsx
   // Doit être 'YYYY-MM-DD'
   console.log('First data point:', priceData[0]?.time)
   ```

6. ✅ **Vérifier que les données sont triées**
   ```tsx
   priceData.sort((a, b) => a.time.localeCompare(b.time))
   ```

---

## 🎨 Exemple complet

```tsx
import { useEffect, useRef, useCallback } from 'react'
import { createChart, LineSeries, createSeriesMarkers, IChartApi, ISeriesApi, Time, LineData } from 'lightweight-charts'

const TradesChart = ({ trades, selectedAssets }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const priceSeriesRefs = useRef<Map<number, ISeriesApi<'Line'>>>(new Map())

  // 1. Initialiser le graphique
  useEffect(() => {
    if (!chartContainerRef.current) return

    const containerWidth = chartContainerRef.current.clientWidth
    if (containerWidth === 0) {
      console.warn('Container has no width')
      return
    }

    if (chartRef.current) {
      chartRef.current.remove()
    }

    const chart = createChart(chartContainerRef.current, {
      width: containerWidth,
      height: 500,
      layout: { background: { color: 'transparent' }, textColor: '#333' },
      grid: { vertLines: { color: '#f0f0f0' }, horzLines: { color: '#f0f0f0' } },
      timeScale: { borderColor: '#e0e0e0', timeVisible: true, secondsVisible: false },
    })

    chartRef.current = chart

    return () => {
      if (chartRef.current) {
        chartRef.current.remove()
        chartRef.current = null
      }
    }
  }, [])

  // 2. Charger les données et créer les séries
  const loadPriceHistory = useCallback(async (assetIds: number[]) => {
    if (!chartRef.current) return

    // Charger les données...
    const histories = await Promise.all(assetIds.map(id => fetchHistory(id)))

    // Créer les séries
    histories.forEach(({ assetId, history }) => {
      const series = chartRef.current.addSeries(LineSeries, {
        color: '#3b82f6',
        lineWidth: 2,
        title: `Asset ${assetId}`,
      })

      const priceData: LineData[] = history.results
        .map((point) => ({
          time: point.date.split('T')[0] as Time,
          value: point.close || 0,
        }))
        .filter((p) => p.value > 0)
        .sort((a, b) => (a.time as string).localeCompare(b.time as string))

      series.setData(priceData)
      priceSeriesRefs.current.set(assetId, series)
    })

    // 3. Ajuster l'échelle APRÈS toutes les données
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (chartRef.current && chartContainerRef.current) {
          const containerWidth = chartContainerRef.current.clientWidth
          
          // Forcer le recalcul de taille
          chartRef.current.applyOptions({ width: containerWidth })
          
          // Ajuster l'échelle
          chartRef.current.timeScale().fitContent()
        }
      })
    })
  }, [])

  return (
    <div 
      ref={chartContainerRef}
      style={{ 
        visibility: loading ? 'hidden' : 'visible', // ✅ Pas display: none
        height: '500px',
        width: '100%'
      }}
    />
  )
}
```

---

## 📚 Ressources

- [Documentation officielle lightweight-charts](https://tradingview.github.io/lightweight-charts/)
- [Migration v4 → v5](https://tradingview.github.io/lightweight-charts/docs/migrations/from-v4-to-v5)
- [API Reference](https://tradingview.github.io/lightweight-charts/docs/api)

---

## 🎯 Résumé des règles d'or

1. ✅ **Ne JAMAIS utiliser `display: none`** → Utiliser `visibility: hidden`
2. ✅ **Vérifier la largeur du conteneur** avant de créer le graphique
3. ✅ **Utiliser `applyOptions({ width })`** pour forcer le recalcul de taille
4. ✅ **Appeler `fitContent()` UNE SEULE FOIS** après toutes les données
5. ✅ **Ajouter les marqueurs APRÈS** l'ajustement de l'échelle
6. ✅ **Trier et filtrer les données** avant de les ajouter
7. ✅ **Utiliser `requestAnimationFrame`** pour attendre le rendu complet

---

**Dernière mise à jour** : Basé sur l'expérience du projet Trading App v4



