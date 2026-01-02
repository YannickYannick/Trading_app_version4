/**
 * Composant de graphique interactif pour visualiser les trades et l'historique des prix
 */
import { useEffect, useRef, useState, useCallback } from 'react'
import { createChart, IChartApi, ISeriesApi, Time, LineData, MarkerData } from 'lightweight-charts'
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
      chart.remove()
    }
  }, [])

  // Charger l'historique des prix pour les assets sélectionnés
  const loadPriceHistory = useCallback(async (assetIds: number[]) => {
    if (!chartRef.current || assetIds.length === 0) return

    setLoading(true)
    setError(null)

    try {
      // Charger les historiques en parallèle
      const historyPromises = assetIds.map(async (assetId) => {
        try {
          const history = await assetService.getPriceHistory(assetId, 365, 'list')
          return { assetId, history }
        } catch (err) {
          console.error(`Error loading history for asset ${assetId}:`, err)
          return { assetId, history: null }
        }
      })

      const histories = await Promise.all(historyPromises)

      // Créer ou récupérer les séries pour chaque asset
      histories.forEach(({ assetId, history }, index) => {
        if (!history || history.results.length === 0) {
          console.warn(`No price history for asset ${assetId}`)
          return
        }

        let series = priceSeriesRefs.current.get(assetId)

        // Créer la série si elle n'existe pas
        if (!series && chartRef.current) {
          const color = priceColors[index % priceColors.length]
          const assetSymbol = allAssetsMap?.get(assetId)?.symbol || `Asset ${assetId}`
          
          series = chartRef.current.addLineSeries({
            color,
            lineWidth: 2,
            title: assetSymbol,
            priceLineVisible: false,
            lastValueVisible: true,
          })
          priceSeriesRefs.current.set(assetId, series)
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
            
            // Ajuster l'échelle de temps pour afficher toutes les données
            if (priceData.length > 0) {
              chartRef.current.timeScale().fitContent()
            }
          } else {
            console.warn(`No valid price data for asset ${assetId} after filtering`)
          }
        }
      })

      // Ajuster l'échelle de temps une fois toutes les séries ajoutées
      if (chartRef.current && priceSeriesRefs.current.size > 0) {
        chartRef.current.timeScale().fitContent()
      }
      
      // Si aucune série n'a été créée, afficher un message d'erreur
      if (priceSeriesRefs.current.size === 0) {
        setError('Aucun historique de prix disponible pour les assets sélectionnés')
      }

      // Supprimer les séries pour les assets non sélectionnés
      priceSeriesRefs.current.forEach((series, assetId) => {
        if (!assetIds.includes(assetId)) {
          chartRef.current?.removeSeries(series)
          priceSeriesRefs.current.delete(assetId)
        }
      })
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
    if (!chartRef.current || filteredTrades.length === 0) return

    // Ajouter les marqueurs à toutes les séries concernées
    priceSeriesRefs.current.forEach((series, assetId) => {
      // Filtrer les trades pour cet asset
      const assetTrades = filteredTrades.filter((trade) => {
        const tradeAssetId = trade.all_asset?.id || (typeof trade.all_asset === 'number' ? trade.all_asset : null)
        return tradeAssetId === assetId
      })

      if (assetTrades.length === 0) return

      // Convertir les trades en marqueurs
      const markers: MarkerData[] = assetTrades
        .map((trade) => {
          const tradeDate = trade.executed_at || trade.timestamp
          if (!tradeDate) return null
          
          const isBuy = trade.side === 'BUY'
          const quantity = trade.quantity || trade.size || 0
          const price = trade.price || 0

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

      if (markers.length > 0) {
        console.log(`Adding ${markers.length} markers to series for asset ${assetId}`)
        series.setMarkers(markers)
      }
    })
  }, [filteredTrades, selectedAssets, viewMode])

  // Charger l'historique quand les assets sélectionnés changent
  useEffect(() => {
    if (selectedAssets.length > 0) {
      loadPriceHistory(selectedAssets)
    } else {
      // Supprimer toutes les séries si aucun asset sélectionné
      priceSeriesRefs.current.forEach((series) => {
        chartRef.current?.removeSeries(series)
      })
      priceSeriesRefs.current.clear()
    }
  }, [selectedAssets, loadPriceHistory])

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

