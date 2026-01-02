/**
 * Graphique de visualisation d'une stratégie avec indicateurs techniques et signaux
 */
import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import { createChart, LineSeries, createSeriesMarkers, IChartApi, ISeriesApi, Time, LineData, MarkerData } from 'lightweight-charts'
import { assetService } from '@services/assets'
import { tradeService } from '@services'
import { calculateRSI, calculateMA, calculateBollingerBands, calculateMACD, calculateEMA } from '@utils/technicalIndicators'
import { calculateStrategySignals, type StrategyParameters, type Signal } from '@utils/strategySignals'
import { simulateTradesFromSignals, calculatePerformanceMetrics, type TradeSimulation } from '@utils/strategyPerformance'
import type { Strategy, Trade } from '@types'
import './StrategyVisualizationChart.css'

interface StrategyVisualizationChartProps {
  strategy: Strategy | null
  parameters: Record<string, any> // Paramètres actuels (peuvent changer en temps réel)
  onParametersChange?: (params: Record<string, any>) => void
}

interface PriceHistoryPoint {
  time: string // Format YYYY-MM-DD
  value: number // close price
  open?: number
  high?: number
  low?: number
}

const StrategyVisualizationChart: React.FC<StrategyVisualizationChartProps> = ({
  strategy,
  parameters,
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  
  // Références aux séries
  const priceSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const indicatorSeriesRefs = useRef<Map<string, ISeriesApi<'Line'>>>(new Map())
  const markersRef = useRef<ReturnType<typeof createSeriesMarkers> | null>(null)
  
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [priceHistory, setPriceHistory] = useState<PriceHistoryPoint[]>([])
  const [trades, setTrades] = useState<Trade[]>([])
  const [simulatedTrades, setSimulatedTrades] = useState<TradeSimulation[]>([])
  const [performanceMetrics, setPerformanceMetrics] = useState<any>(null)

  // Initialiser le graphique
  useEffect(() => {
    if (!chartContainerRef.current) return

    const containerWidth = chartContainerRef.current.clientWidth
    if (containerWidth === 0) {
      console.warn('[StrategyVisualizationChart] Container has no width')
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
      height: 600,
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
      },
      crosshair: {
        mode: 1,
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
      priceSeriesRef.current = null
      indicatorSeriesRefs.current.clear()
      markersRef.current = null
    }
  }, [])

  // Charger les données de la stratégie
  useEffect(() => {
    const loadData = async () => {
      if (!strategy || !strategy.all_asset) return

      setLoading(true)
      setError(null)

      try {
        const assetId = typeof strategy.all_asset === 'number' 
          ? strategy.all_asset 
          : strategy.all_asset.id

        // Charger l'historique des prix
        const historyResponse = await assetService.getPriceHistory(assetId, 365, 'list')
        
        const priceData: PriceHistoryPoint[] = (historyResponse.results || [])
          .map((point: any) => ({
            time: point.date?.split('T')[0] || point.date,
            value: point.close || 0,
            open: point.open,
            high: point.high,
            low: point.low,
          }))
          .filter((p: PriceHistoryPoint) => p.value > 0 && p.time)
          .sort((a: PriceHistoryPoint, b: PriceHistoryPoint) => 
            (a.time as string).localeCompare(b.time as string)
          )

        setPriceHistory(priceData)

        // Charger les trades de cette stratégie (si le service le supporte)
        try {
          // Note: Le filtre 'strategy' peut ne pas être supporté, on essaie quand même
          const tradesResponse = await tradeService.getAll({} as any) // Filtrer côté frontend si nécessaire
          const allTrades = tradesResponse.results || []
          // Filtrer par stratégie si possible (dépend de la structure des trades)
          setTrades(allTrades)
        } catch (err) {
          console.warn('[StrategyVisualizationChart] Could not load trades:', err)
          setTrades([])
        }
      } catch (err: any) {
        setError(err.response?.data?.error || err.message || 'Erreur lors du chargement des données')
        console.error('[StrategyVisualizationChart] Error loading data:', err)
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [strategy])

  // Calculer et afficher les indicateurs et signaux
  useEffect(() => {
    if (!chartRef.current || !priceSeriesRef.current || priceHistory.length === 0 || !strategy) return

    const algorithmType = strategy.algorithm_type
    if (!algorithmType) return

    // Convertir les paramètres au format StrategyParameters
    const strategyParams: StrategyParameters = {
      rsi_period: parameters.rsi_period,
      rsi_low: parameters.rsi_low,
      rsi_high: parameters.rsi_high,
      ma1_period: parameters.ma1_period,
      ma2_period: parameters.ma2_period,
      bb_period: parameters.bb_period,
      bb_std: parameters.bb_std,
      macd_fast: parameters.macd_fast,
      macd_slow: parameters.macd_slow,
      macd_signal: parameters.macd_signal,
      threshold_low: parameters.threshold_low,
      threshold_high: parameters.threshold_high,
      grid_min: parameters.grid_min,
      grid_max: parameters.grid_max,
      grid_levels: parameters.grid_levels,
    }

    const prices = priceHistory.map(p => p.value)
    const dates = priceHistory.map(p => p.time)

    // Supprimer les anciennes séries d'indicateurs
    indicatorSeriesRefs.current.forEach((series) => {
      try {
        chartRef.current?.removeSeries(series)
      } catch (err) {
        console.warn('[StrategyVisualizationChart] Error removing indicator series:', err)
      }
    })
    indicatorSeriesRefs.current.clear()

    // Calculer et afficher les indicateurs selon l'algorithme
    switch (algorithmType) {
      case 'rsi': {
        const rsiPeriod = strategyParams.rsi_period || 14
        const rsiValues = calculateRSI(prices, rsiPeriod)
        const rsiData: LineData[] = dates.map((date, i) => ({
          time: date as Time,
          value: isNaN(rsiValues[i]) ? 50 : rsiValues[i],
        })).filter(p => !isNaN(p.value))

        // Créer une série RSI sur un graphique séparé (ou utiliser un axe secondaire)
        // Pour simplifier, on l'affiche en overlay avec un prix normalisé
        // Dans une vraie implémentation, on utiliserait un graphique séparé
        break
      }

      case 'ma_crossover': {
        const ma1Period = strategyParams.ma1_period || 20
        const ma2Period = strategyParams.ma2_period || 50
        const ma1 = calculateMA(prices, ma1Period)
        const ma2 = calculateMA(prices, ma2Period)

        // Ligne MA rapide
        const ma1Series = chartRef.current.addSeries(LineSeries, {
          color: '#3b82f6',
          lineWidth: 2,
          title: `MA ${ma1Period}`,
          priceLineVisible: false,
        })
        const ma1Data: LineData[] = dates
          .map((date, i) => ({ time: date as Time, value: ma1[i] }))
          .filter(p => !isNaN(p.value))
        ma1Series.setData(ma1Data)
        indicatorSeriesRefs.current.set('ma1', ma1Series)

        // Ligne MA lente
        const ma2Series = chartRef.current.addSeries(LineSeries, {
          color: '#ef4444',
          lineWidth: 2,
          title: `MA ${ma2Period}`,
          priceLineVisible: false,
        })
        const ma2Data: LineData[] = dates
          .map((date, i) => ({ time: date as Time, value: ma2[i] }))
          .filter(p => !isNaN(p.value))
        ma2Series.setData(ma2Data)
        indicatorSeriesRefs.current.set('ma2', ma2Series)
        break
      }

      case 'bollinger': {
        const bbPeriod = strategyParams.bb_period || 20
        const bbStd = strategyParams.bb_std || 2
        const bands = calculateBollingerBands(prices, bbPeriod, bbStd)

        // Bande supérieure
        const upperSeries = chartRef.current.addSeries(LineSeries, {
          color: '#10b981',
          lineWidth: 1,
          title: 'BB Upper',
          lineStyle: 2, // Dashed
          priceLineVisible: false,
        })
        const upperData: LineData[] = dates
          .map((date, i) => ({ time: date as Time, value: bands.upper[i] }))
          .filter(p => !isNaN(p.value))
        upperSeries.setData(upperData)
        indicatorSeriesRefs.current.set('bb_upper', upperSeries)

        // Bande moyenne
        const middleSeries = chartRef.current.addSeries(LineSeries, {
          color: '#6b7280',
          lineWidth: 1,
          title: 'BB Middle',
          priceLineVisible: false,
        })
        const middleData: LineData[] = dates
          .map((date, i) => ({ time: date as Time, value: bands.middle[i] }))
          .filter(p => !isNaN(p.value))
        middleSeries.setData(middleData)
        indicatorSeriesRefs.current.set('bb_middle', middleSeries)

        // Bande inférieure
        const lowerSeries = chartRef.current.addSeries(LineSeries, {
          color: '#ef4444',
          lineWidth: 1,
          title: 'BB Lower',
          lineStyle: 2, // Dashed
          priceLineVisible: false,
        })
        const lowerData: LineData[] = dates
          .map((date, i) => ({ time: date as Time, value: bands.lower[i] }))
          .filter(p => !isNaN(p.value))
        lowerSeries.setData(lowerData)
        indicatorSeriesRefs.current.set('bb_lower', lowerSeries)
        break
      }

      case 'threshold': {
        const thresholdLow = strategyParams.threshold_low
        const thresholdHigh = strategyParams.threshold_high

        if (thresholdLow !== undefined) {
          const lowSeries = chartRef.current.addSeries(LineSeries, {
            color: '#10b981',
            lineWidth: 1,
            title: 'Seuil bas',
            lineStyle: 2,
            priceLineVisible: false,
          })
          const lowData: LineData[] = dates.map(date => ({
            time: date as Time,
            value: thresholdLow,
          }))
          lowSeries.setData(lowData)
          indicatorSeriesRefs.current.set('threshold_low', lowSeries)
        }

        if (thresholdHigh !== undefined) {
          const highSeries = chartRef.current.addSeries(LineSeries, {
            color: '#ef4444',
            lineWidth: 1,
            title: 'Seuil haut',
            lineStyle: 2,
            priceLineVisible: false,
          })
          const highData: LineData[] = dates.map(date => ({
            time: date as Time,
            value: thresholdHigh,
          }))
          highSeries.setData(highData)
          indicatorSeriesRefs.current.set('threshold_high', highSeries)
        }
        break
      }
    }

    // Calculer les signaux
    const signals = calculateStrategySignals(algorithmType, prices, dates, strategyParams)
    
    // Simuler les trades basés sur les signaux
    const orderSize = strategyParams.order_size || 1.0
    const stopLoss = strategyParams.stop_loss
    const simulated = simulateTradesFromSignals(signals, prices, dates, orderSize, stopLoss)
    setSimulatedTrades(simulated)
    
    // Calculer les métriques de performance
    const metrics = calculatePerformanceMetrics(simulated)
    setPerformanceMetrics(metrics)
    
    // Ne montrer que les signaux qui ont déclenché un trade (entry points)
    // Cela évite d'afficher trop de marqueurs
    const signalMarkers: MarkerData[] = simulated
      .filter(trade => trade.status === 'CLOSED' || trade.status === 'OPEN')
      .map(trade => {
        let text = `${trade.side} @ ${trade.entryPrice.toFixed(2)}`
        if (trade.status === 'CLOSED' && trade.pnl !== null) {
          const pnlSign = trade.pnl >= 0 ? '+' : ''
          text = `${trade.side} @ ${trade.entryPrice.toFixed(2)} (${pnlSign}${trade.pnl.toFixed(2)})`
        }
        
        return {
          time: trade.entryTime as Time,
          position: trade.side === 'BUY' ? ('belowBar' as const) : ('aboveBar' as const),
          color: trade.side === 'BUY' ? '#10b981' : '#ef4444',
          shape: trade.side === 'BUY' ? ('arrowUp' as const) : ('arrowDown' as const),
          text,
        }
      })

    // Ajouter les marqueurs des trades réels
    const tradeMarkers: MarkerData[] = trades
      .map((trade) => {
        const tradeDate = trade.executed_at || trade.timestamp
        if (!tradeDate) return null

        const dateStr = typeof tradeDate === 'string' 
          ? tradeDate.split('T')[0] 
          : tradeDate instanceof Date 
            ? tradeDate.toISOString().split('T')[0]
            : null

        if (!dateStr) return null

        const tradeSide = trade.side || (trade as any).trade_type || 'UNKNOWN'
        const isBuy = tradeSide === 'BUY'
        const quantity = Number(trade.quantity || trade.size || 0)
        const price = Number(trade.price || 0)

        if (isNaN(quantity) || isNaN(price)) return null

        return {
          time: dateStr as Time,
          position: isBuy ? ('belowBar' as const) : ('aboveBar' as const),
          color: isBuy ? '#3b82f6' : '#ef4444',
          shape: isBuy ? ('arrowUp' as const) : ('arrowDown' as const),
          text: `TRADE ${tradeSide} ${quantity.toFixed(2)} @ ${price.toFixed(2)}`,
        }
      })
      .filter((m): m is MarkerData => m !== null)

    // Combiner les marqueurs de signaux et de trades
    const allMarkers = [...signalMarkers, ...tradeMarkers]

    // Mettre à jour les marqueurs (uniquement si la série de prix existe)
    if (allMarkers.length > 0 && priceSeriesRef.current) {
      if (!markersRef.current) {
        markersRef.current = createSeriesMarkers(priceSeriesRef.current, allMarkers)
      } else {
        markersRef.current.setMarkers(allMarkers)
      }
    } else if (markersRef.current) {
      // Supprimer les marqueurs si pas de données
      markersRef.current.setMarkers([])
    }

    // Ajuster l'échelle après toutes les données
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (chartRef.current && chartContainerRef.current) {
          const containerWidth = chartContainerRef.current.clientWidth
          if (containerWidth > 0) {
            chartRef.current.applyOptions({ width: containerWidth })
          }
          chartRef.current.timeScale().fitContent()
        }
      })
    })
  }, [priceHistory, strategy, parameters, trades])

  // Créer la série de prix et réajouter les marqueurs après
  useEffect(() => {
    if (!chartRef.current || priceHistory.length === 0) return

    // Supprimer l'ancienne série si elle existe
    if (priceSeriesRef.current) {
      try {
        chartRef.current.removeSeries(priceSeriesRef.current)
      } catch (err) {
        console.warn('[StrategyVisualizationChart] Error removing price series:', err)
      }
    }

    // Créer la série de prix
    const priceSeries = chartRef.current.addSeries(LineSeries, {
      color: '#1f2937',
      lineWidth: 2,
      title: strategy?.all_asset_name || 'Prix',
      priceLineVisible: false,
      lastValueVisible: true,
    })

    const priceData: LineData[] = priceHistory
      .map((point) => ({
        time: point.time as Time,
        value: point.value,
      }))
      .filter((p) => p.value > 0)

    priceSeries.setData(priceData)
    priceSeriesRef.current = priceSeries

    // Réajouter les marqueurs après création de la série
    // Cela sera géré par l'useEffect des indicateurs qui se déclenchera après
  }, [priceHistory, strategy])

  if (!strategy) {
    return (
      <div className="strategy-chart-empty">
        <p className="text-muted">Sélectionnez une stratégie pour visualiser son graphique</p>
      </div>
    )
  }

  return (
    <div className="strategy-visualization-chart">
      {error && (
        <div className="chart-error">
          <p>{error}</p>
        </div>
      )}

      {/* Panneau d'informations sur les performances */}
      {performanceMetrics && (
        <div className="performance-panel">
          <div className="performance-metric">
            <span className="metric-label">Trades simulés:</span>
            <span className="metric-value">{performanceMetrics.totalTrades}</span>
          </div>
          <div className="performance-metric">
            <span className="metric-label">Taux de réussite:</span>
            <span className={`metric-value ${performanceMetrics.winRate >= 50 ? 'positive' : 'negative'}`}>
              {performanceMetrics.winRate.toFixed(1)}%
            </span>
          </div>
          <div className="performance-metric">
            <span className="metric-label">PnL total:</span>
            <span className={`metric-value ${performanceMetrics.totalPnL >= 0 ? 'positive' : 'negative'}`}>
              {performanceMetrics.totalPnL >= 0 ? '+' : ''}{performanceMetrics.totalPnL.toFixed(2)}
            </span>
          </div>
          <div className="performance-metric">
            <span className="metric-label">PnL moyen:</span>
            <span className={`metric-value ${performanceMetrics.totalPnLPercent >= 0 ? 'positive' : 'negative'}`}>
              {performanceMetrics.totalPnLPercent >= 0 ? '+' : ''}{performanceMetrics.totalPnLPercent.toFixed(2)}%
            </span>
          </div>
          {performanceMetrics.currentPosition && (
            <div className="performance-metric">
              <span className="metric-label">Position ouverte:</span>
              <span className="metric-value">
                {performanceMetrics.currentPosition.side} @ {performanceMetrics.currentPosition.entryPrice.toFixed(2)}
              </span>
            </div>
          )}
        </div>
      )}

      <div
        ref={chartContainerRef}
        style={{
          visibility: loading ? 'hidden' : 'visible',
          height: '600px',
          width: '100%',
        }}
      />
      {loading && (
        <div className="chart-loading">
          <p>Chargement des données...</p>
        </div>
      )}
    </div>
  )
}

export default StrategyVisualizationChart

