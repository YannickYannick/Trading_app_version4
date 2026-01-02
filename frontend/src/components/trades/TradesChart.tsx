/**
 * Composant de graphique interactif pour visualiser les trades et l'historique des prix
 */
import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import { createChart, LineSeries, createSeriesMarkers, IChartApi, ISeriesApi, Time, LineData, MarkerData } from 'lightweight-charts'
import { assetService } from '@services/assets'
import type { Trade, AllAsset } from '@types'
import './TradesChart.css'

export interface TradesChartProps {
  trades: Trade[]
  selectedAssets: number[]
  viewMode: 'global' | 'per_asset'
  allAssetsMap?: Map<number, AllAsset> // Map pour accéder rapidement aux AllAssets
}

interface PriceHistoryPoint {
  time: string // Format YYYY-MM-DD
  value: number // close price
  open?: number
  high?: number
  low?: number
}

const TradesChart: React.FC<TradesChartProps> = ({
  trades,
  selectedAssets,
  viewMode,
  allAssetsMap,
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const priceSeriesRefs = useRef<Map<number, ISeriesApi<'Line'>>>(new Map())
  const markersRefs = useRef<Map<number, ReturnType<typeof createSeriesMarkers>>>(new Map())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Couleurs pour différentes séries de prix
  const priceColors = [
    '#3b82f6', // bleu
    '#10b981', // vert
    '#f59e0b', // orange
    '#ef4444', // rouge
    '#8b5cf6', // violet
    '#ec4899', // rose
  ]

  // Initialiser le graphique
  useEffect(() => {
    if (!chartContainerRef.current) return

    // Nettoyer le graphique existant s'il y en a un
    if (chartRef.current) {
      chartRef.current.remove()
      chartRef.current = null
      priceSeriesRefs.current.clear()
    }

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 500,
      layout: {
        background: { color: 'transparent' },
        textColor: '#333',
      },
      grid: {
        vertLines: { color: '#f0f0f0' },
        horzLines: { color: '#f0f0f0' },
      },
      rightPriceScale: {
        borderColor: '#e0e0e0',
      },
      timeScale: {
        borderColor: '#e0e0e0',
        timeVisible: true,
        secondsVisible: false,
        fitContent: true, // Activer le fit automatique
      },
      crosshair: {
        mode: 1, // Normal mode
      },
    })

    chartRef.current = chart
    console.log('[TradesChart] Chart initialized:', chartRef.current)

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
      priceSeriesRefs.current.clear()
      markersRefs.current.clear()
    }
  }, [])

  // Charger l'historique des prix pour les assets sélectionnés
  const loadPriceHistory = useCallback(async (assetIds: number[]) => {
    if (!chartRef.current) {
      console.warn('[TradesChart] Chart not initialized yet, skipping loadPriceHistory')
      return
    }

    if (assetIds.length === 0) {
      // Supprimer toutes les séries si aucun asset sélectionné
      priceSeriesRefs.current.forEach((series) => {
        chartRef.current?.removeSeries(series)
      })
      priceSeriesRefs.current.clear()
      return
    }

    setLoading(true)
    setError(null)

    try {
      // Vérifier à nouveau que le graphique est toujours initialisé
      if (!chartRef.current) {
        console.error('[TradesChart] Chart was destroyed during loadPriceHistory')
        setError('Graphique non disponible')
        return
      }

      // ✅ D'abord, supprimer les séries qui ne sont plus sélectionnées
      const assetsToKeepSet = new Set(assetIds)
      const seriesToRemove: Array<{ assetId: number; series: ISeriesApi<'Line'> }> = []
      
      priceSeriesRefs.current.forEach((series, assetId) => {
        if (!assetsToKeepSet.has(assetId)) {
          seriesToRemove.push({ assetId, series })
        }
      })
      
      // Supprimer les séries marquées
      const hasRemovedSeries = seriesToRemove.length > 0
      seriesToRemove.forEach(({ assetId, series }) => {
        console.log(`[TradesChart] Removing series for asset ${assetId} (no longer selected)`)
        if (chartRef.current) {
          chartRef.current.removeSeries(series)
        }
        priceSeriesRefs.current.delete(assetId)
        // Supprimer aussi les marqueurs associés
        const markersPrimitive = markersRefs.current.get(assetId)
        if (markersPrimitive) {
          markersPrimitive.setMarkers([])
          markersRefs.current.delete(assetId)
        }
      })

      // ✅ Ensuite, charger uniquement les NOUVEAUX assets (pas déjà dans priceSeriesRefs)
      const newAssetIds = assetIds.filter(id => !priceSeriesRefs.current.has(id))
      
      if (newAssetIds.length === 0) {
        console.log('[TradesChart] All assets already loaded, skipping fetch')
        setLoading(false)
        // Ajuster l'échelle même si pas de nouveaux assets (notamment après suppression de séries)
        if (hasRemovedSeries || priceSeriesRefs.current.size > 0) {
          requestAnimationFrame(() => {
            setTimeout(() => {
              if (chartRef.current) {
                try {
                  const timeScale = chartRef.current.timeScale()
                  timeScale.fitContent()
                  console.log('[TradesChart] Time scale adjusted after series removal')
                } catch (err) {
                  console.error('[TradesChart] Error fitting content after removal:', err)
                }
              }
            }, 50)
          })
        }
        return
      }

      console.log(`[TradesChart] Loading price history for ${newAssetIds.length} new asset(s):`, newAssetIds)

      // Charger les historiques en parallèle pour les NOUVEAUX assets uniquement
      const historyPromises = newAssetIds.map(async (assetId) => {
        try {
          console.log(`[TradesChart] Loading price history for asset ${assetId}...`)
          const history = await assetService.getPriceHistory(assetId, 365, 'list')
          console.log(`[TradesChart] Loaded price history for asset ${assetId}: ${history.count} records`, history)
          return { assetId, history }
        } catch (err) {
          console.error(`[TradesChart] Error loading history for asset ${assetId}:`, err)
          return { assetId, history: null }
        }
      })

      const histories = await Promise.all(historyPromises)
      console.log(`[TradesChart] All histories loaded:`, histories)

      // Vérifier à nouveau que le graphique est toujours disponible avant d'ajouter des séries
      if (!chartRef.current) {
        console.error('[TradesChart] Chart was destroyed after loading histories')
        setError('Graphique non disponible')
        return
      }

      // Créer ou récupérer les séries pour chaque asset
      histories.forEach(({ assetId, history }, index) => {
        if (!history) {
          console.warn(`[TradesChart] No history object for asset ${assetId}`)
          return
        }
        
        if (!history.results || history.results.length === 0) {
          console.warn(`[TradesChart] No price history results for asset ${assetId} (count: ${history.count}, results: ${history.results?.length || 0})`)
          return
        }
        
        console.log(`[TradesChart] Processing ${history.results.length} price records for asset ${assetId}`)

        // Vérifier que la série n'existe pas déjà (ne devrait pas arriver car on filtre newAssetIds)
        let series = priceSeriesRefs.current.get(assetId)
        if (series) {
          console.warn(`[TradesChart] Series already exists for asset ${assetId}, skipping creation`)
          return
        }

        // Créer la série (elle n'existe pas car c'est un nouvel asset)
        if (chartRef.current) {
          // Dans lightweight-charts v5+, utiliser addSeries(LineSeries, options) selon la doc officielle
          // https://tradingview.github.io/lightweight-charts/docs/migrations/from-v4-to-v5
          // Vérifier que addSeries existe
          if (typeof chartRef.current.addSeries !== 'function') {
            console.error('[TradesChart] addSeries is not a function on chart object', chartRef.current)
            setError('Erreur lors de l\'initialisation du graphique')
            return
          }

          // Utiliser la taille actuelle de priceSeriesRefs pour l'index de couleur (pas l'index de la boucle)
          const colorIndex = priceSeriesRefs.current.size
          const color = priceColors[colorIndex % priceColors.length]
          const assetSymbol = allAssetsMap?.get(assetId)?.symbol || `Asset ${assetId}`
          
          try {
            // Utiliser addSeries(LineSeries, options) pour lightweight-charts v5+
            // LineSeries doit être importé séparément depuis 'lightweight-charts'
            series = chartRef.current.addSeries(LineSeries, {
              color,
              lineWidth: 2,
              title: assetSymbol,
              priceLineVisible: false,
              lastValueVisible: true,
            }) as ISeriesApi<'Line'>
            priceSeriesRefs.current.set(assetId, series)
            console.log(`[TradesChart] Created line series for asset ${assetId}`)
          } catch (err) {
            console.error(`[TradesChart] Error creating line series for asset ${assetId}:`, err)
            setError(`Erreur lors de la création de la série pour ${assetSymbol}`)
            return
          }
        }

        if (series && chartRef.current) {
          // Convertir les données au format lightweight-charts
          const priceData: LineData[] = history.results
            .map((point) => {
              // Convertir la date au format YYYY-MM-DD si nécessaire
              let dateStr = point.date
              if (dateStr.includes('T')) {
                dateStr = dateStr.split('T')[0]
              }
              
              return {
                time: dateStr as Time,
                value: point.close || point.close_price || point.close || 0,
              }
            })
            .filter((point) => point.value > 0 && point.time) // Filtrer les valeurs invalides
            .sort((a, b) => {
              // Trier chronologiquement
              const timeA = a.time as string
              const timeB = b.time as string
              return timeA.localeCompare(timeB)
            })

          if (priceData.length > 0) {
            console.log(`Setting ${priceData.length} price points for asset ${assetId}`)
            series.setData(priceData)
            // Ne pas appeler fitContent ici, on le fait après toutes les séries
          } else {
            console.warn(`No valid price data for asset ${assetId} after filtering`)
          }
        }
      })

      // Ajuster l'échelle de temps une fois toutes les séries ajoutées
      // Utiliser requestAnimationFrame + setTimeout pour s'assurer que toutes les données sont rendues
      // Toujours ajuster l'échelle, même s'il n'y a pas de nouvelles séries (au cas où des séries ont été supprimées)
      requestAnimationFrame(() => {
        setTimeout(() => {
          if (chartRef.current) {
            try {
              const timeScale = chartRef.current.timeScale()
              timeScale.fitContent()
              console.log('[TradesChart] Time scale adjusted to fit content')
            } catch (err) {
              console.error('[TradesChart] Error fitting content:', err)
            }
          }
        }, 50)
      })
      
      // Si aucune série n'a été créée, afficher un message d'erreur avec détails
      if (priceSeriesRefs.current.size === 0) {
        const assetsWithoutHistory = histories
          .filter(({ history }) => !history || !history.results || history.results.length === 0)
          .map(({ assetId }) => assetId)
        
        console.warn(`[TradesChart] No series created. Assets without history:`, assetsWithoutHistory)
        console.warn(`[TradesChart] Full histories data:`, histories)
        
        if (assetsWithoutHistory.length === assetIds.length) {
          setError('Aucun historique de prix disponible pour les assets sélectionnés. Utilisez le bouton "Charger l\'historique" pour synchroniser.')
        } else {
          setError(`Aucun historique pour ${assetsWithoutHistory.length} asset(s) sur ${assetIds.length}`)
        }
      } else {
        console.log(`[TradesChart] Created ${priceSeriesRefs.current.size} series successfully`)
      }

      // Les séries non sélectionnées ont déjà été supprimées au début de la fonction
    } catch (err: any) {
      setError(err.message || 'Erreur lors du chargement de l\'historique')
      console.error('Error loading price history:', err)
    } finally {
      setLoading(false)
    }
  }, [allAssetsMap, priceColors])

  // Filtrer les trades selon le mode d'affichage
  const filteredTrades = viewMode === 'per_asset' && selectedAssets.length === 1
    ? trades.filter((trade) => {
        const tradeAssetId = trade.all_asset?.id || (typeof trade.all_asset === 'number' ? trade.all_asset : null)
        return tradeAssetId === selectedAssets[0]
      })
    : trades

  // Ajouter les marqueurs de trades au graphique
  useEffect(() => {
    if (!chartRef.current || filteredTrades.length === 0) {
      // Supprimer tous les marqueurs si pas de trades
      markersRefs.current.forEach((markersPrimitive) => {
        markersPrimitive.setMarkers([])
      })
      return
    }

    // Ajouter les marqueurs à toutes les séries concernées
    priceSeriesRefs.current.forEach((series, assetId) => {
      // Filtrer les trades pour cet asset
      const assetTrades = filteredTrades.filter((trade) => {
        const tradeAssetId = trade.all_asset?.id || (typeof trade.all_asset === 'number' ? trade.all_asset : null)
        return tradeAssetId === assetId
      })

      // Convertir les trades en marqueurs
      const markers: MarkerData[] = assetTrades
        .map((trade) => {
          const tradeDate = trade.executed_at || trade.timestamp
          if (!tradeDate) return null
          
          const isBuy = trade.side === 'BUY'
          // Convertir explicitement en nombres pour éviter l'erreur toFixed
          const quantity = Number(trade.quantity || trade.size || 0)
          const price = Number(trade.price || 0)

          // Vérifier que les valeurs sont valides
          if (isNaN(quantity) || isNaN(price)) {
            console.warn(`[TradesChart] Invalid quantity or price for trade:`, trade)
            return null
          }

          // Convertir la date au format YYYY-MM-DD
          let dateStr = tradeDate
          if (dateStr.includes('T')) {
            dateStr = dateStr.split('T')[0]
          }

          return {
            time: dateStr as Time,
            position: isBuy ? ('belowBar' as const) : ('aboveBar' as const),
            color: isBuy ? '#10b981' : '#ef4444',
            shape: isBuy ? ('arrowUp' as const) : ('arrowDown' as const),
            text: `${trade.side} ${quantity.toFixed(2)} @ ${price.toFixed(2)}`,
          }
        })
        .filter((marker): marker is MarkerData => marker !== null) // Filtrer les marqueurs null

      // Dans lightweight-charts v5+, utiliser createSeriesMarkers pour gérer les marqueurs
      let markersPrimitive = markersRefs.current.get(assetId)
      
      if (markers.length > 0) {
        // Créer ou mettre à jour les marqueurs
        if (!markersPrimitive) {
          console.log(`Creating markers primitive for asset ${assetId} with ${markers.length} markers`)
          markersPrimitive = createSeriesMarkers(series, markers)
          markersRefs.current.set(assetId, markersPrimitive)
        } else {
          console.log(`Updating ${markers.length} markers for asset ${assetId}`)
          markersPrimitive.setMarkers(markers)
        }
      } else {
        // Supprimer les marqueurs si aucun trade
        if (markersPrimitive) {
          markersPrimitive.setMarkers([])
        }
      }
    })

    // Supprimer les marqueurs pour les assets non sélectionnés
    markersRefs.current.forEach((markersPrimitive, assetId) => {
      if (!priceSeriesRefs.current.has(assetId)) {
        markersPrimitive.setMarkers([])
        markersRefs.current.delete(assetId)
      }
    })

    // Réajuster l'échelle après avoir ajouté/mis à jour les marqueurs
    if (chartRef.current && priceSeriesRefs.current.size > 0) {
      requestAnimationFrame(() => {
        setTimeout(() => {
          if (chartRef.current) {
            try {
              const timeScale = chartRef.current.timeScale()
              timeScale.fitContent()
              console.log('[TradesChart] Time scale adjusted after markers update')
            } catch (err) {
              console.error('[TradesChart] Error fitting content after markers:', err)
            }
          }
        }, 50)
      })
    }
  }, [filteredTrades, selectedAssets, viewMode])

  // Créer une clé stable pour la comparaison (trier les IDs pour être indépendant de l'ordre)
  // Utiliser useMemo pour éviter de recalculer à chaque render
  const assetsKey = useMemo(() => {
    const sortedAssets = [...selectedAssets].sort((a, b) => a - b)
    return sortedAssets.join(',')
  }, [selectedAssets])

  // Charger l'historique quand les assets sélectionnés changent
  const prevSelectedAssetsRef = useRef<string>('')
  
  useEffect(() => {
    // Attendre que le graphique soit initialisé avant de charger les données
    if (!chartRef.current) {
      console.log('[TradesChart] Waiting for chart to be initialized...')
      return
    }

    // Comparer avec la valeur précédente pour éviter les rechargements inutiles
    if (prevSelectedAssetsRef.current === assetsKey) {
      console.log('[TradesChart] Selected assets unchanged, skipping reload. Current key:', assetsKey)
      return
    }

    console.log('[TradesChart] Selected assets changed from', prevSelectedAssetsRef.current, 'to', assetsKey)
    
    // ✅ METTRE À JOUR LA RÉFÉRENCE IMMÉDIATEMENT pour éviter les doubles appels
    const previousKey = prevSelectedAssetsRef.current
    prevSelectedAssetsRef.current = assetsKey

    if (selectedAssets.length > 0) {
      // Charger l'historique pour les nouveaux assets sélectionnés
      loadPriceHistory([...selectedAssets])
        .catch((err) => {
          console.error('[TradesChart] Error in loadPriceHistory:', err)
          // En cas d'erreur, restaurer la valeur précédente pour permettre une nouvelle tentative
          prevSelectedAssetsRef.current = previousKey
        })
    } else {
      // Supprimer toutes les séries si aucun asset sélectionné
      if (chartRef.current) {
        priceSeriesRefs.current.forEach((series) => {
          chartRef.current?.removeSeries(series)
        })
      }
      priceSeriesRefs.current.clear()
      markersRefs.current.forEach((markersPrimitive) => {
        markersPrimitive.setMarkers([])
      })
      markersRefs.current.clear()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assetsKey]) // Dépendance basée sur la clé triée

  if (!trades || trades.length === 0) {
    return (
      <div className="trades-chart-container">
        <div className="trades-chart-empty">
          <p>Aucun trade à afficher</p>
        </div>
      </div>
    )
  }

  return (
    <div className="trades-chart-container">
      {loading && (
        <div className="trades-chart-loading">
          <p>Chargement de l'historique des prix...</p>
        </div>
      )}
      {error && !loading && (
        <div className="trades-chart-error">
          <p>Erreur: {error}</p>
        </div>
      )}
      {!loading && !error && selectedAssets.length === 0 && (
        <div className="trades-chart-empty">
          <p>Sélectionnez au moins un asset pour afficher le graphique</p>
        </div>
      )}
      <div 
        ref={chartContainerRef} 
        className="trades-chart"
        style={{ display: (loading || error || selectedAssets.length === 0) ? 'none' : 'block' }}
      />
      <div className="trades-chart-legend">
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: '#10b981' }}></span>
          <span>Achat (BUY)</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: '#ef4444' }}></span>
          <span>Vente (SELL)</span>
        </div>
      </div>
    </div>
  )
}

export default TradesChart

