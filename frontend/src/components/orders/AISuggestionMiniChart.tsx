/**
 * Petit graphique prix (Yahoo) pour les suggestions IA — périodes + marqueurs trades (achats/ventes).
 */
import { useEffect, useRef, useState, useCallback } from 'react'
import {
  createChart,
  LineSeries,
  createSeriesMarkers,
  IChartApi,
  ISeriesApi,
  Time,
  LineData,
  MarkerData,
} from 'lightweight-charts'
import { assetService } from '@services/assets'
import type { Trade } from '@types'
import './AISuggestionMiniChart.css'

const PERIOD_OPTIONS = [
  { label: '1M', value: 30 },
  { label: '3M', value: 90 },
  { label: '6M', value: 180 },
  { label: '1A', value: 365 },
  { label: '2A', value: 730 },
]

interface Point {
  time: string
  value: number
}

interface AISuggestionMiniChartProps {
  allAssetId: number
  trades?: Trade[]
  showTradeMarkers?: boolean
  entryPrice?: number | null
}

export default function AISuggestionMiniChart({
  allAssetId,
  trades = [],
  showTradeMarkers = false,
  entryPrice = null,
}: AISuggestionMiniChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const priceSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const entrySeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const markersRef = useRef<ReturnType<typeof createSeriesMarkers> | null>(null)

  const [periodDays, setPeriodDays] = useState(180)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [ohlcv, setOhlcv] = useState<Point[]>([])

  const shouldRefreshYahoo = useCallback((assetId: number): boolean => {
    const key = `yahoo_sync_${assetId}`
    const last = localStorage.getItem(key)
    if (!last) return true
    const h = (Date.now() - new Date(last).getTime()) / (1000 * 60 * 60)
    return h > 4
  }, [])

  const markSynced = useCallback((assetId: number) => {
    localStorage.setItem(`yahoo_sync_${assetId}`, new Date().toISOString())
  }, [])

  useEffect(() => {
    if (!containerRef.current) return
    const el = containerRef.current
    const w = el.clientWidth || 400

    const chart = createChart(el, {
      width: w,
      height: 220,
      layout: {
        background: { color: 'transparent' },
        textColor: 'var(--text-secondary, #a1a1aa)',
      },
      grid: {
        vertLines: { color: 'rgba(128,128,128,0.15)' },
        horzLines: { color: 'rgba(128,128,128,0.15)' },
      },
      timeScale: { borderColor: 'rgba(128,128,128,0.2)', timeVisible: true, secondsVisible: false },
      rightPriceScale: { borderColor: 'rgba(128,128,128,0.2)' },
    })
    chartRef.current = chart

    const series = chart.addSeries(LineSeries, {
      color: 'var(--accent-primary, #3b82f6)',
      lineWidth: 2,
      priceLineVisible: true,
      lastValueVisible: true,
    })
    priceSeriesRef.current = series

    const ro = new ResizeObserver(() => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: containerRef.current.clientWidth })
      }
    })
    ro.observe(el)

    return () => {
      ro.disconnect()
      markersRef.current = null
      entrySeriesRef.current = null
      priceSeriesRef.current = null
      chart.remove()
      chartRef.current = null
    }
  }, [])

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        if (shouldRefreshYahoo(allAssetId)) {
          assetService.syncPriceHistory(allAssetId, periodDays).then(() => markSynced(allAssetId)).catch(() => {})
        }
        const res = await assetService.getPriceHistory(allAssetId, periodDays, 'list')
        if (cancelled) return

        const points = (res.results || [])
          .map((p: { date: string; close: number }) => ({
            time: (p.date?.split('T')[0] || p.date) as string,
            value: p.close || 0,
          }))
          .filter((p) => p.value > 0 && p.time)
          .sort((a, b) => a.time.localeCompare(b.time))

        if (points.length === 0) {
          setOhlcv([])
          setError('Pas de données historiques pour cette période.')
        } else {
          setOhlcv(points)
          setError(null)
        }
      } catch (e: unknown) {
        if (!cancelled) {
          setOhlcv([])
          setError((e as Error)?.message || 'Historique indisponible')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void load()

    return () => {
      cancelled = true
    }
  }, [allAssetId, periodDays, shouldRefreshYahoo, markSynced])

  useEffect(() => {
    if (!chartRef.current || !priceSeriesRef.current) return

    if (ohlcv.length === 0) {
      priceSeriesRef.current.setData([])
      if (markersRef.current) markersRef.current.setMarkers([])
      return
    }

    const priceData: LineData[] = ohlcv.map((p) => ({
      time: p.time as Time,
      value: p.value,
    }))
    priceSeriesRef.current.setData(priceData)

    const times = ohlcv.map((p) => p.time as Time)

    if (entryPrice != null && entryPrice > 0) {
      if (!entrySeriesRef.current && chartRef.current) {
        entrySeriesRef.current = chartRef.current.addSeries(LineSeries, {
          color: '#f59e0b',
          lineWidth: 1,
          lineStyle: 2,
          title: 'Entrée',
          priceLineVisible: false,
          lastValueVisible: false,
        })
      }
      entrySeriesRef.current?.setData(times.map((t) => ({ time: t, value: entryPrice })))
    } else if (entrySeriesRef.current && chartRef.current) {
      try {
        chartRef.current.removeSeries(entrySeriesRef.current)
      } catch {
        /* ignore */
      }
      entrySeriesRef.current = null
    }

    let tradeMarkers: MarkerData[] = []
    if (showTradeMarkers && trades.length > 0) {
      tradeMarkers = trades
        .map((trade) => {
          const tradeDate = trade.executed_at || trade.timestamp
          if (!tradeDate) return null
          const dateStr =
            typeof tradeDate === 'string'
              ? tradeDate.split('T')[0]
              : tradeDate instanceof Date
                ? tradeDate.toISOString().split('T')[0]
                : null
          if (!dateStr) return null
          const side = trade.side || 'BUY'
          const isBuy = side === 'BUY'
          const qty = Number(trade.quantity ?? trade.size ?? 0)
          const px = Number(trade.price ?? 0)
          if (Number.isNaN(qty) || Number.isNaN(px)) return null
          return {
            time: dateStr as Time,
            position: isBuy ? ('belowBar' as const) : ('aboveBar' as const),
            color: isBuy ? '#22c55e' : '#ef4444',
            shape: isBuy ? ('arrowUp' as const) : ('arrowDown' as const),
            text: `${side} ${qty.toFixed(2)} @ ${px.toFixed(2)}`,
          }
        })
        .filter((m): m is MarkerData => m !== null)
        .sort((a, b) => (a.time as string).localeCompare(b.time as string))
    }

    if (priceSeriesRef.current) {
      if (!markersRef.current) {
        markersRef.current = createSeriesMarkers(priceSeriesRef.current, tradeMarkers)
      } else {
        markersRef.current.setMarkers(tradeMarkers)
      }
    }

    requestAnimationFrame(() => {
      chartRef.current?.timeScale().fitContent()
    })
  }, [ohlcv, trades, showTradeMarkers, entryPrice])

  const onPeriodClick = async (days: number) => {
    try {
      await assetService.syncPriceHistory(allAssetId, days)
      markSynced(allAssetId)
    } catch {
      /* ignore */
    }
    setPeriodDays(days)
  }

  return (
    <div className="ai-mini-chart">
      <div className="ai-mini-chart-period">
        <span className="ai-mini-chart-period-label">Période</span>
        <div className="ai-mini-chart-period-btns">
          {PERIOD_OPTIONS.map((o) => (
            <button
              key={o.value}
              type="button"
              className={`ai-mini-period-btn ${periodDays === o.value ? 'active' : ''}`}
              disabled={loading}
              onClick={() => void onPeriodClick(o.value)}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>
      {error && <p className="ai-mini-chart-error">{error}</p>}
      <div ref={containerRef} className="ai-mini-chart-canvas" />
      {loading && <div className="ai-mini-chart-loading">Chargement…</div>}
      {showTradeMarkers && trades.length === 0 && !loading && !error && ohlcv.length > 0 && (
        <p className="ai-mini-chart-hint">Aucun trade enregistré pour ce titre — marqueurs d’achat masqués.</p>
      )}
    </div>
  )
}
