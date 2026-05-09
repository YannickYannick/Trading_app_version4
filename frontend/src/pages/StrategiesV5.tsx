/**
 * StrategiesV5 - Dashboard moderne multi-broker (inspiré du mock fourni).
 * Pour l'instant : récap positions du portefeuille + ordres/stratégies en cours d'exécution.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  BrainCircuit,
  CheckCircle2,
  ChevronDown,
  Clock,
  Layers,
  Maximize2,
  PieChart,
  PlusCircle,
  RefreshCw,
  Settings,
  TrendingDown,
  TrendingUp,
  Wallet,
  X,
} from 'lucide-react'
import { Line, LineChart, ResponsiveContainer, Tooltip as RechartsTooltip, XAxis, YAxis } from 'recharts'
import { Card, Badge, Button, Loading } from '@components/common'
import StrategyVisualizationChart from '@components/strategies/StrategyVisualizationChart'
import { positionService, orderService, strategyService } from '@services'
import strategyExecutionService, { type StrategyExecution } from '@services/strategyExecutionService'
import { assetService } from '@services/assets'
import type { Order, Position, Strategy } from '@types'
import { formatCurrency } from '@utils/format'
import './StrategiesV5.css'

const ALGORITHM_LABELS: Record<string, string> = {
  threshold: 'Threshold',
  ma_crossover: 'MA Cross',
  rsi: 'RSI',
  bollinger: 'Bollinger',
  macd: 'MACD',
  grid: 'Grid',
}

const ALGORITHM_PARAMS: Record<string, { key: string; label: string; default: number }[]> = {
  threshold: [
    { key: 'threshold_low', label: 'Seuil bas', default: 60000 },
    { key: 'threshold_high', label: 'Seuil haut', default: 68000 },
  ],
  ma_crossover: [
    { key: 'ma1_period', label: 'MA courte', default: 20 },
    { key: 'ma2_period', label: 'MA longue', default: 50 },
  ],
  rsi: [
    { key: 'rsi_period', label: 'Période', default: 14 },
    { key: 'rsi_low', label: 'Seuil bas', default: 30 },
    { key: 'rsi_high', label: 'Seuil haut', default: 70 },
  ],
  bollinger: [
    { key: 'bb_period', label: 'Période', default: 20 },
    { key: 'bb_std', label: 'Écart-type', default: 2 },
  ],
  macd: [
    { key: 'macd_fast', label: 'Rapide', default: 12 },
    { key: 'macd_slow', label: 'Lent', default: 26 },
    { key: 'macd_signal', label: 'Signal', default: 9 },
  ],
  grid: [
    { key: 'grid_min', label: 'Prix min', default: 2800 },
    { key: 'grid_max', label: 'Prix max', default: 3600 },
    { key: 'grid_levels', label: 'Niveaux', default: 10 },
  ],
}

type UiOrder = {
  id: number | string
  type: 'BUY' | 'SELL'
  symbol: string
  qty: number
  price: number | null
  status: string
  progress: number
  broker: string
}

type ChartTooltipPayload = {
  all_asset_id: number
  all_asset_symbol: string
  prices: Array<{ date: string; close: number }>
  trades: Array<{ id: number; side: 'BUY' | 'SELL'; quantity: number; price: number; date: string; timestamp: string }>
}

type HoverState = {
  visible: boolean
  x: number
  y: number
  allAssetId: number | null
  symbol: string
  broker: string
}

function formatDateLabel(isoDate: string): string {
  const [y, m, d] = String(isoDate || '').split('-')
  if (!y || !m || !d) return String(isoDate || '')
  return `${d}/${m}`
}

function toUnixMsFromIsoDate(isoDate: string): number | null {
  // Accepte: "YYYY-MM-DD", "YYYY-MM-DDTHH:MM:SS...", "YYYY-MM-DD HH:MM:SS"
  // (forcer UTC pour éviter les décalages)
  const raw = String(isoDate || '').trim()
  const m = raw.match(/\d{4}-\d{2}-\d{2}/)
  const d = m ? m[0] : raw
  const ms = Date.parse(`${d}T00:00:00Z`)
  return Number.isFinite(ms) ? ms : null
}

function todayIsoDate(): string {
  const d = new Date()
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

function formatUnixMsLabel(ms: number): string {
  const dt = new Date(ms)
  if (!Number.isFinite(dt.getTime())) return String(ms)
  const dd = String(dt.getDate()).padStart(2, '0')
  const mm = String(dt.getMonth() + 1).padStart(2, '0')
  return `${dd}/${mm}`
}

/** Extrait YYYY-MM-DD ; snap trades sur dernier jour d'historique <= date. */
function normalizeChartDate(raw: unknown): string | null {
  const s = String(raw ?? '').trim()
  const m = s.match(/\d{4}-\d{2}-\d{2}/)
  return m ? m[0] : null
}

function snapTradeDateToHistory(tradeDate: string, historyDatesAsc: string[]): string | null {
  if (!tradeDate || historyDatesAsc.length === 0) return null
  if (historyDatesAsc.includes(tradeDate)) return tradeDate
  let best: string | null = null
  for (const d of historyDatesAsc) {
    if (d <= tradeDate) best = d
    else break
  }
  return best ?? historyDatesAsc[0]
}

/** Logs console — filtre: `[StrategiesV5][chart]`. Désactiver: localStorage `sv5ChartDebug=0` */
function logHoverChartDebug(opts: {
  symbol: string
  broker: string
  allAssetId: number
  source: 'fetch' | 'cache-hit' | 'cache-refresh'
  prices: Array<{ date: string; close: number }>
}) {
  try {
    if (typeof window !== 'undefined' && window.localStorage?.getItem('sv5ChartDebug') === '0') return
  } catch {
    /* ignore */
  }
  const raw = opts.prices || []
  const firstRaw = raw[0]
  const lastRaw = raw[raw.length - 1]
  const plotted = raw
    .map((p) => {
      const date = String((p as any).date ?? '')
      const close = Number((p as any).close)
      const t = toUnixMsFromIsoDate(date)
      return { date, close, t }
    })
    .filter((p) => Number.isFinite(p.close) && typeof p.t === 'number')
    .sort((a, b) => (a.t as number) - (b.t as number))
  const firstChrono = plotted[0]
  const lastChrono = plotted[plotted.length - 1]
  console.log(
    `[StrategiesV5][chart] ${opts.symbol} (${opts.broker}) · id=${opts.allAssetId} · ${opts.source}`,
    {
      pointsBruts: raw.length,
      pointsTrace: plotted.length,
      premiereValeur_tableauBrut: firstRaw
        ? { date: String((firstRaw as any).date), close: Number((firstRaw as any).close) }
        : null,
      derniereValeur_tableauBrut: lastRaw
        ? { date: String((lastRaw as any).date), close: Number((lastRaw as any).close) }
        : null,
      premiereValeur_chronologique: firstChrono
        ? { date: firstChrono.date, close: firstChrono.close, label: formatUnixMsLabel(firstChrono.t as number) }
        : null,
      derniereValeur_chronologique: lastChrono
        ? { date: lastChrono.date, close: lastChrono.close, label: formatUnixMsLabel(lastChrono.t as number) }
        : null,
    }
  )
}

function safeNumber(v: unknown): number {
  const n = typeof v === 'string' ? Number(v) : (v as number)
  return Number.isFinite(n) ? n : 0
}

function orderSymbol(o: Order): string {
  return (
    (o.all_asset_symbol as string | undefined) ||
    (o.asset?.symbol as string | undefined) ||
    (o.symbol as string | undefined) ||
    '—'
  )
}

function hasAllAssetLink(o: Order): boolean {
  if (o.all_asset_symbol && String(o.all_asset_symbol).trim()) return true
  if (typeof (o as any).all_asset_id === 'number') return true
  if (typeof (o as any).catalog_all_asset_id === 'number') return true
  if (typeof (o as any).all_asset === 'number') return true
  if (typeof (o as any).all_asset === 'object' && (o as any).all_asset?.id) return true
  return false
}

function orderBroker(o: Order): string {
  return (o.broker_name as string | undefined) || (o.broker?.name as string | undefined) || '—'
}

function orderStatusLabel(o: Order): string {
  const s = (o.status as string | undefined) || ''
  if (s === 'PENDING') return 'En attente'
  if (s === 'OPEN') return 'Exécution'
  if (s === 'PARTIALLY_FILLED') return 'Exécution'
  if (s === 'FILLED') return 'Terminé'
  if (s === 'CANCELLED') return 'Annulé'
  if (s === 'REJECTED') return 'Rejeté'
  return s || '—'
}

function statusVariant(label: string): 'success' | 'danger' | 'warning' | 'info' | 'default' {
  if (label === 'Terminé') return 'success'
  if (label === 'Annulé' || label === 'Rejeté') return 'danger'
  if (label === 'Exécution') return 'info'
  if (label === 'En attente') return 'warning'
  return 'default'
}

function estimateProgressFromOrder(o: Order): number {
  const status = (o.status as string | undefined) || ''
  if (status === 'FILLED') return 100
  if (status === 'PENDING') return 0
  if (status === 'PARTIALLY_FILLED') {
    const filled = safeNumber((o as any).filled_quantity)
    const qty = safeNumber(o.quantity)
    if (qty > 0) return Math.max(0, Math.min(100, (filled / qty) * 100))
    return 35
  }
  if (status === 'OPEN') return 65
  return 0
}

function posSymbol(p: Position): string {
  return (
    (p.symbol as string | undefined) ||
    (p.all_asset_symbol as string | undefined) ||
    (p.asset?.symbol as string | undefined) ||
    '—'
  )
}

function posName(p: Position): string {
  return (
    (p.all_asset_name as string | undefined) ||
    (p.asset?.name as string | undefined) ||
    '—'
  )
}

function posBroker(p: Position): string {
  return (p.broker_name as string | undefined) || (p.broker?.name as string | undefined) || '—'
}

function posQuantity(p: Position): number {
  return safeNumber((p as any).quantity ?? (p as any).size)
}

/** Prix unitaire “marché” : Yahoo puis courtier ; pas d’entrée PRU ici (évite un mélange €/USD ou PRU/live). */
function posLiveUnitPrice(p: Position): number | null {
  for (const key of ['yahoo_current_price', 'current_price'] as const) {
    const raw = (p as any)[key]
    if (raw == null || raw === '') continue
    const n = typeof raw === 'string' ? Number(raw) : Number(raw)
    if (Number.isFinite(n) && n > 0) return n
  }
  return null
}

function posMarketValueEUR(p: Position): number {
  const qty = posQuantity(p)
  const live = posLiveUnitPrice(p)
  if (live != null) return Math.max(0, qty * live)
  const entryRaw = (p as any).entry_price
  if (entryRaw != null && entryRaw !== '') {
    const e = typeof entryRaw === 'string' ? Number(entryRaw) : Number(entryRaw)
    if (Number.isFinite(e) && e > 0) return Math.max(0, qty * e)
  }
  return 0
}

/**
 * % de perf : d’abord `pnl_percent` de l’API (calculé avec Yahoo si include_yahoo_price=1),
 * sinon recalcul local avec cours live + entrée ou PRU reconstitué.
 */
function posPnlPercent(p: Position): number {
  const rawApi = (p as any).pnl_percent
  if (rawApi != null && rawApi !== '') {
    const n = typeof rawApi === 'string' ? Number(rawApi) : Number(rawApi)
    if (Number.isFinite(n)) return n
  }

  const entryRaw = safeNumber((p as any).entry_price)
  const entryReconstructed = safeNumber((p as any).reconstructed_entry_price)
  const entry = entryRaw > 0 ? entryRaw : (entryReconstructed > 0 ? entryReconstructed : 0)
  const live = posLiveUnitPrice(p)
  const side = String((p as any).side || '').toUpperCase()
  const isShort = side === 'SHORT' || side === 'SELL'

  if (entry > 0 && live != null) {
    if (isShort) return ((entry - live) / entry) * 100
    return ((live - entry) / entry) * 100
  }

  return 0
}

function posSector(p: Position): string {
  const assetType = String((p as any).all_asset_asset_type || '').toUpperCase()
  const platform = String((p as any).all_asset_platform || '').toUpperCase()
  if (assetType.includes('CRYPTO') || platform === 'BINANCE') return 'Crypto'
  const s = String((p as any).all_asset_sector || '').trim()
  return s || 'Sans secteur'
}

function clamp(n: number, a: number, b: number) {
  return Math.max(a, Math.min(b, n))
}

function pnlBg(pnlPercent: number): string {
  // Palette inspirée du mock : rouge vif <-3%, gris proche de 0, vert vif > +3%
  const p = pnlPercent
  if (p >= 3) return 'hsl(152 70% 38%)'
  if (p >= 1) return `hsl(152 70% ${Math.round(26 + (p - 1) * 6)}%)`
  if (p > 0) return `hsl(152 55% ${Math.round(18 + p * 8)}%)`
  if (p === 0) return 'hsl(215 26% 16%)'
  if (p > -1) return `hsl(350 55% ${Math.round(18 + Math.abs(p) * 8)}%)`
  if (p > -3) return `hsl(350 70% ${Math.round(26 + (Math.abs(p) - 1) * 6)}%)`
  return 'hsl(350 80% 40%)'
}

export default function StrategiesV5() {
  const [positions, setPositions] = useState<Position[]>([])
  const [activeOrders, setActiveOrders] = useState<Order[]>([])
  const [executions, setExecutions] = useState<StrategyExecution[]>([])
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [centerMode, setCenterMode] = useState<'heatmap' | 'cards'>('heatmap')

  const [loading, setLoading] = useState(true)
  const [syncingPortfolioHistory, setSyncingPortfolioHistory] = useState(false)
  const [creatingStrategiesFromPortfolio, setCreatingStrategiesFromPortfolio] = useState(false)
  const [portfolioStrategiesFeedback, setPortfolioStrategiesFeedback] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  // --- Widget stratégie (inline expand) ---
  const [expandedStrategyId, setExpandedStrategyId] = useState<number | null>(null)
  const [inlineEdit, setInlineEdit] = useState<Record<number, Record<string, any>>>({})
  const [savingId, setSavingId] = useState<number | null>(null)
  const [chartPeriods, setChartPeriods] = useState<Record<number, number>>({})
  const [chartKey, setChartKey] = useState(0)
  const [syncingYahooId, setSyncingYahooId] = useState<number | null>(null)
  const [yahooSyncResult, setYahooSyncResult] = useState<Record<number, { success: boolean; message: string }>>({})

  const chartCacheRef = useRef<Map<number, ChartTooltipPayload>>(new Map())
  const chartCacheTimeRef = useRef<Map<number, number>>(new Map())
  const hoverReqIdRef = useRef(0)
  const [hover, setHover] = useState<HoverState>({
    visible: false,
    x: 0,
    y: 0,
    allAssetId: null,
    symbol: '',
    broker: '',
  })
  const [hoverPayload, setHoverPayload] = useState<ChartTooltipPayload | null>(null)

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      const [pos, orders, execs, strategiesRes] = await Promise.all([
        positionService.getOpen(),
        orderService.getActivePendingList(),
        strategyExecutionService.getRecent(),
        strategyService.getAll({ page_size: 500 }),
      ])
      setPositions(pos || [])
      setActiveOrders(Array.isArray(orders) ? orders : [])
      setExecutions(Array.isArray(execs) ? execs : [])
      setStrategies((strategiesRes?.results || []) as Strategy[])
    } catch (e: any) {
      setError(e?.response?.data?.error || e?.message || 'Erreur de chargement')
    } finally {
      setLoading(false)
    }
  }

  const createStrategiesFromPortfolio = async () => {
    setPortfolioStrategiesFeedback(null)
    setError(null)
    setCreatingStrategiesFromPortfolio(true)
    try {
      const res = await strategyService.createFromPortfolio()
      const parts = [
        `${res.created_count} stratégie(s) créée(s)`,
        `${res.skipped_existing.length} déjà couverte(s)`,
        `${res.skipped_no_broker_account.length} sans compte courtier actif`,
      ]
      if (res.errors.length) {
        parts.push(`${res.errors.length} erreur(s)`)
      }
      setPortfolioStrategiesFeedback(parts.join(' · '))
      await loadData()
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.response?.data?.error || e?.message || 'Échec de la création'
      setError(msg)
    } finally {
      setCreatingStrategiesFromPortfolio(false)
    }
  }

  const syncPortfolioPriceHistory = async () => {
    const ids = [
      ...new Set(
        positions
          .map((p) => (p as any).all_asset_id as unknown)
          .filter((id): id is number => typeof id === 'number' && id > 0)
      ),
    ]
    if (!ids.length) return
    setSyncingPortfolioHistory(true)
    chartCacheRef.current.clear()
    chartCacheTimeRef.current.clear()
    try {
      for (const id of ids) {
        try {
          await assetService.syncPriceHistory(id, 365, '1d')
        } catch {
          /* continuer les autres actifs */
        }
      }
      await loadData()
    } finally {
      setSyncingPortfolioHistory(false)
    }
  }

  useEffect(() => {
    void loadData()
  }, [])

  // Refresh silencieux — démarre 30s après le montage, toutes les 60s, sans toucher loading/error
  useEffect(() => {
    const silentRefresh = async () => {
      try {
        const [pos, orders, execs, strategiesRes] = await Promise.all([
          positionService.getOpen(),
          orderService.getActivePendingList(),
          strategyExecutionService.getRecent(),
          strategyService.getAll({ page_size: 500 }),
        ])
        setPositions(pos || [])
        setActiveOrders(Array.isArray(orders) ? orders : [])
        setExecutions(Array.isArray(execs) ? execs : [])
        setStrategies((strategiesRes?.results || []) as Strategy[])
      } catch {
        /* erreurs réseau ignorées silencieusement */
      }
    }
    const delay = setTimeout(() => {
      const t = setInterval(() => void silentRefresh(), 60_000)
      return () => clearInterval(t)
    }, 30_000)
    return () => clearTimeout(delay)
  }, [])

  // --- Helpers widget stratégie ---
  const getAssetId = useCallback((s: Strategy): number | null => {
    if (typeof s.all_asset === 'number') return s.all_asset
    if (typeof s.all_asset === 'object' && (s.all_asset as any)?.id) return (s.all_asset as any).id
    return null
  }, [])

  const getAssetSymbol = useCallback((s: Strategy): string => {
    return (s.all_asset_symbol as string | undefined) ||
      (typeof s.all_asset === 'object' ? (s.all_asset as any)?.symbol : null) ||
      'N/A'
  }, [])

  const getAssetName = useCallback((s: Strategy): string => {
    return (s.all_asset_name as string | undefined) ||
      (typeof s.all_asset === 'object' ? (s.all_asset as any)?.name : null) ||
      getAssetSymbol(s)
  }, [getAssetSymbol])

  const initInlineEdit = useCallback((s: Strategy) => {
    setInlineEdit(prev => {
      if (prev[s.id as number]) return prev
      const params = (s.parameters as Record<string, any>) || {}
      return {
        ...prev,
        [s.id as number]: {
          algorithm_type: s.algorithm_type || 'threshold',
          risk_level: s.risk_level || 'MEDIUM',
          target_min_quantity: s.target_min_quantity ?? 1,
          target_max_quantity: s.target_max_quantity ?? 10,
          portfolio_min_quantity: s.portfolio_min_quantity ?? 0,
          portfolio_max_quantity:
            s.portfolio_max_quantity != null && s.portfolio_max_quantity !== ''
              ? s.portfolio_max_quantity
              : '',
          check_frequency: s.check_frequency ?? 45,
          is_automated: s.is_automated ?? false,
          all_asset: getAssetId(s),
          all_asset_name: getAssetName(s),
          all_asset_symbol: getAssetSymbol(s),
          ...params,
        },
      }
    })
  }, [getAssetId, getAssetName, getAssetSymbol])

  const updateInlineEdit = useCallback((strategyId: number, key: string, value: any) => {
    setInlineEdit(prev => ({
      ...prev,
      [strategyId]: { ...prev[strategyId], [key]: value },
    }))
  }, [])

  const saveInlineEdit = useCallback(async (s: Strategy) => {
    const edits = inlineEdit[s.id as number]
    if (!edits) return
    setSavingId(s.id as number)
    try {
      const algoParamKeys = ALGORITHM_PARAMS[edits.algorithm_type || s.algorithm_type || 'threshold']?.map(p => p.key) || []
      const parameters: Record<string, number> = {}
      algoParamKeys.forEach(key => {
        if (edits[key] !== undefined) parameters[key] = parseFloat(edits[key]) || 0
      })
      const updateData: Record<string, any> = {
        algorithm_type: edits.algorithm_type,
        risk_level: edits.risk_level,
        target_min_quantity: parseFloat(edits.target_min_quantity) || 0,
        target_max_quantity: parseFloat(edits.target_max_quantity) || 0,
        portfolio_min_quantity: parseFloat(String(edits.portfolio_min_quantity ?? 0)) || 0,
        portfolio_max_quantity: (() => {
          if (edits.portfolio_max_quantity === '' || edits.portfolio_max_quantity == null) return null
          const v = parseFloat(String(edits.portfolio_max_quantity))
          return Number.isFinite(v) ? v : null
        })(),
        check_frequency: parseInt(edits.check_frequency) || 45,
        is_automated: edits.is_automated,
        parameters,
      }
      if (edits.all_asset && edits.all_asset !== getAssetId(s)) {
        updateData.all_asset = edits.all_asset
      }
      await strategyService.update(s.id as number, updateData)
      void loadData()
    } catch {
      alert('Erreur lors de la sauvegarde')
    } finally {
      setSavingId(null)
    }
  }, [inlineEdit, getAssetId])

  const handleSyncYahoo = useCallback(async (s: Strategy) => {
    const assetId = getAssetId(s)
    if (!assetId) return
    setSyncingYahooId(s.id as number)
    setYahooSyncResult(prev => ({ ...prev, [s.id as number]: { success: false, message: 'Synchronisation...' } }))
    try {
      await assetService.validateYahoo(assetId)
      const periodDays = chartPeriods[s.id as number] || 365
      const result = await assetService.syncPriceHistory(assetId, periodDays, '1d')
      if (result.success) {
        setYahooSyncResult(prev => ({ ...prev, [s.id as number]: { success: true, message: `${result.records || 0} points chargés` } }))
        setChartKey(k => k + 1)
      } else {
        setYahooSyncResult(prev => ({ ...prev, [s.id as number]: { success: false, message: result.error || 'Erreur inconnue' } }))
      }
    } catch {
      setYahooSyncResult(prev => ({ ...prev, [s.id as number]: { success: false, message: 'Erreur de synchronisation' } }))
    } finally {
      setSyncingYahooId(null)
    }
  }, [getAssetId, chartPeriods])

  const openStrategyWidget = useCallback((s: Strategy) => {
    initInlineEdit(s)
    setExpandedStrategyId(s.id as number)
  }, [initInlineEdit])

  const uiOrders: UiOrder[] = useMemo(() => {
    return activeOrders
      .filter(hasAllAssetLink)
      .slice(0, 8)
      .map((o) => ({
        id: o.id,
        type: (o.side as 'BUY' | 'SELL') || 'BUY',
        symbol: orderSymbol(o),
        qty: safeNumber(o.quantity),
        price: o.price != null ? safeNumber(o.price) : null,
        status: orderStatusLabel(o),
        progress: estimateProgressFromOrder(o),
        broker: orderBroker(o),
      }))
  }, [activeOrders])

  const portfolioCards = useMemo(() => {
    return positions
      .slice()
      .sort((a, b) => posMarketValueEUR(b) - posMarketValueEUR(a))
      .slice(0, 12)
      .map((p) => {
        const pnlPct = posPnlPercent(p)
        const value = posMarketValueEUR(p)
        return {
          positionId: p.id,
          allAssetId: (p as any).all_asset_id ?? (p as any).all_asset?.id ?? null,
          symbol: posSymbol(p),
          name: posName(p),
          qty: posQuantity(p),
          value,
          pnl: pnlPct,
          broker: posBroker(p),
        }
      })
  }, [positions])

  const sectorTreemap = useMemo(() => {
    const items = positions
      .slice()
      .map((p) => {
        const size = posMarketValueEUR(p)
        return {
          positionId: p.id,
          allAssetId: (p as any).all_asset_id ?? (p as any).all_asset?.id ?? null,
          symbol: posSymbol(p),
          name: posName(p),
          sector: posSector(p),
          broker: posBroker(p),
          size,
          pnl: posPnlPercent(p),
        }
      })
      .filter((x) => x.size > 0)

    const bySector = new Map<string, typeof items>()
    for (const it of items) {
      const list = bySector.get(it.sector) || []
      list.push(it)
      bySector.set(it.sector, list)
    }

    const sectors = [...bySector.entries()]
      .map(([name, assets]) => {
        assets.sort((a, b) => b.size - a.size)
        const total = assets.reduce((s, a) => s + a.size, 0)
        return { name, total, assets }
      })
      .sort((a, b) => b.total - a.total)

    const grandTotal = sectors.reduce((s, sec) => s + sec.total, 0) || 1
    return sectors.map((sec) => ({
      ...sec,
      weight: (sec.total / grandTotal) * 100,
    }))
  }, [positions])

  const totalValue = useMemo(() => portfolioCards.reduce((s, p) => s + p.value, 0), [portfolioCards])

  const runningExecs = useMemo(() => executions.filter((e) => e.status === 'running'), [executions])
  const portfolioSymbols = useMemo(
    () => new Set(positions.map((p) => posSymbol(p)).filter(Boolean)),
    [positions]
  )

  const allAutomated = useMemo(
    () => strategies.filter((s) => Boolean(s.is_automated)).slice(0, 20),
    [strategies]
  )

  const strategiesOnPortfolio = useMemo(
    () => allAutomated.filter((s) => portfolioSymbols.has(String(s.all_asset_symbol || ''))),
    [allAutomated, portfolioSymbols]
  )

  const strategiesOffPortfolio = useMemo(
    () => allAutomated.filter((s) => !portfolioSymbols.has(String(s.all_asset_symbol || ''))),
    [allAutomated, portfolioSymbols]
  )

  const strategyBySymbol = useMemo(() => {
    const m = new Map<string, Strategy>()
    for (const s of strategiesOnPortfolio) {
      const sym = String(s.all_asset_symbol || '')
      if (sym) m.set(sym, s)
    }
    return m
  }, [strategiesOnPortfolio])

  const [stratActiveOverride, setStratActiveOverride] = useState<Map<number, boolean>>(new Map())

  const handleToggleStrategy = async (s: Strategy) => {
    const current = stratActiveOverride.has(s.id as number)
      ? (stratActiveOverride.get(s.id as number) as boolean)
      : Boolean(s.is_active)
    const next = !current
    setStratActiveOverride((prev) => new Map(prev).set(s.id as number, next))
    try {
      await strategyService.toggleActive(s.id as number, next)
      void loadData()
    } catch {
      setStratActiveOverride((prev) => new Map(prev).set(s.id as number, current))
    }
  }

  const isStratActive = (s: Strategy) =>
    stratActiveOverride.has(s.id as number)
      ? (stratActiveOverride.get(s.id as number) as boolean)
      : Boolean(s.is_active)

  const ensureHoverPayload = async (
    allAssetId: number,
    label: { symbol: string; broker: string }
  ) => {
    const cached = chartCacheRef.current.get(allAssetId)
    const cachedAt = chartCacheTimeRef.current.get(allAssetId) || 0
    const isFresh = Date.now() - cachedAt < 30_000 // 30s TTL pour avoir un "now" crédible
    if (cached && isFresh) {
      // Même si c’est en cache, on rafraîchit le prix actuel (point "aujourd’hui")
      try {
        const cur = await assetService.getYahooCurrentPrice(allAssetId)
        if (cur != null && Number.isFinite(cur) && cur > 0) {
          const d = todayIsoDate()
          const next = {
            ...cached,
            prices: (() => {
              const prices = [...(cached.prices || [])]
              const idx = prices.findIndex((p) => String((p as any).date) === d)
              if (idx >= 0) prices[idx] = { ...prices[idx], close: cur }
              else prices.push({ date: d, close: cur })
              return prices
            })(),
          }
          chartCacheRef.current.set(allAssetId, next)
          chartCacheTimeRef.current.set(allAssetId, Date.now())
          logHoverChartDebug({
            ...label,
            allAssetId,
            source: 'cache-refresh',
            prices: next.prices || [],
          })
          setHoverPayload(next)
          return
        }
      } catch {
        // ignore
      }
      logHoverChartDebug({
        ...label,
        allAssetId,
        source: 'cache-hit',
        prices: cached.prices || [],
      })
      setHoverPayload(cached)
      return
    }

    const reqId = ++hoverReqIdRef.current
    try {
      const data = await assetService.getChartTooltip(allAssetId, 180, 365, 400)

      // Étendre la courbe jusqu'au prix actuel (Yahoo current price, cache côté client).
      try {
        const cur = await assetService.getYahooCurrentPrice(allAssetId)
        if (cur != null && Number.isFinite(cur) && cur > 0) {
          const d = todayIsoDate()
          const hasToday = (data.prices || []).some((p) => String((p as any).date) === d)
          const lastDate = data.prices?.[data.prices.length - 1]?.date
          const shouldAppend = !hasToday && d !== String(lastDate || '')
          if (shouldAppend) {
            data.prices = [...(data.prices || []), { date: d, close: cur }]
          } else if (hasToday) {
            data.prices = (data.prices || []).map((p) => (String((p as any).date) === d ? { ...p, close: cur } : p))
          }
        }
      } catch {
        // ignore (tooltip reste sur historique stocké)
      }

      chartCacheRef.current.set(allAssetId, data)
      chartCacheTimeRef.current.set(allAssetId, Date.now())
      if (reqId === hoverReqIdRef.current) {
        logHoverChartDebug({
          ...label,
          allAssetId,
          source: 'fetch',
          prices: data.prices || [],
        })
        setHoverPayload(data)
      }
    } catch {
      if (reqId === hoverReqIdRef.current) {
        setHoverPayload(null)
      }
    }
  }

  const handleAssetEnter = (e: React.MouseEvent, allAssetId: number | null, symbol: string, broker: string) => {
    if (!allAssetId) return
    setHover({ visible: true, x: e.clientX, y: e.clientY, allAssetId, symbol, broker })
    setHoverPayload(null)
    void ensureHoverPayload(allAssetId, { symbol, broker })
  }

  const handleAssetMove = (e: React.MouseEvent) => {
    setHover((h) => (h.visible ? { ...h, x: e.clientX, y: e.clientY } : h))
  }

  const handleAssetLeave = () => {
    hoverReqIdRef.current++
    setHover((h) => ({ ...h, visible: false, allAssetId: null }))
    setHoverPayload(null)
  }

  return (
    <div className="strategies-v5">
      <header className="sv5-header">
        <div>
          <h1 className="sv5-title">
            <Activity className="sv5-title-icon" />
            Stratégies V5
          </h1>
          <p className="sv5-subtitle">
            Récap portefeuille + activités en cours (ordres & exécutions).
          </p>
        </div>

        <div className="sv5-header-cards">
          <Card className="sv5-stat-card">
            <div className="sv5-stat-icon blue">
              <Wallet className="sv5-stat-icon-svg" />
            </div>
            <div>
              <p className="sv5-stat-k">Valeur totale (estim.)</p>
              <p className="sv5-stat-v">{formatCurrency(totalValue)}</p>
            </div>
          </Card>
          <Card className="sv5-stat-card">
            <div className="sv5-stat-icon green">
              <TrendingUp className="sv5-stat-icon-svg" />
            </div>
            <div>
              <p className="sv5-stat-k">Ordres actifs</p>
              <p className="sv5-stat-v">{activeOrders.length}</p>
            </div>
          </Card>
        </div>
      </header>

      <main className="sv5-grid">
        {/* Gauche : ordres + exécutions */}
        <section className="sv5-col sv5-col-left">
          <div className="sv5-section-head">
            <h2 className="sv5-section-title">
              Ordres actifs <span className="sv5-section-muted">({uiOrders.length})</span>
            </h2>
            <Clock className="sv5-section-icon" />
          </div>

          {loading && uiOrders.length === 0 ? (
            <Card className="sv5-pad">
              <Loading text="Chargement…" />
            </Card>
          ) : (
            <div className="sv5-stack">
              {uiOrders.map((o) => (
                <Card key={String(o.id)} className="sv5-order-card">
                  <div className="sv5-order-top">
                    <div>
                      <span className={`sv5-chip ${o.type === 'BUY' ? 'buy' : 'sell'}`}>{o.type}</span>
                      <div className="sv5-order-symbol">{o.symbol}</div>
                    </div>
                    <Badge variant={statusVariant(o.status)}>{o.progress === 100 ? 'Terminé' : o.status}</Badge>
                  </div>

                  <div className="sv5-order-meta">
                    <span>
                      {o.qty || 0} unités{typeof o.price === 'number' ? ` @ ${o.price} €` : ''}
                    </span>
                    <span className="sv5-order-broker">{o.broker}</span>
                  </div>

                  <div className="sv5-progress">
                    <div className="sv5-progress-rail" />
                    <div
                      className={`sv5-progress-bar ${o.type === 'BUY' ? 'buy' : 'sell'}`}
                      style={{ width: `${o.progress}%` }}
                    />
                  </div>
                </Card>
              ))}

              {uiOrders.length === 0 && (
                <Card className="sv5-empty">
                  <p>Aucun ordre actif.</p>
                </Card>
              )}
            </div>
          )}

          <div className="sv5-section-head sv5-mt">
            <h2 className="sv5-section-title purple">
              <BrainCircuit className="sv5-section-icon purple" />
              Exécutions en cours <span className="sv5-section-muted">({runningExecs.length})</span>
            </h2>
            <div />
          </div>

          <div className="sv5-stack">
            {runningExecs.slice(0, 8).map((e) => (
              <Card key={e.id} className="sv5-exec-card">
                <div className="sv5-exec-top">
                  <div className="sv5-exec-title">
                    <span className="sv5-exec-name">{e.strategy_name}</span>
                    <span className="sv5-exec-time">
                      {new Date(e.started_at).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                  </div>
                  <Badge variant="info">running</Badge>
                </div>
                <div className="sv5-exec-bottom">
                  <span className={`sv5-exec-signal ${e.signal}`}>
                    {e.signal === 'BUY' ? (
                      <>
                        <ArrowUpRight size={14} /> BUY
                      </>
                    ) : e.signal === 'SELL' ? (
                      <>
                        <ArrowDownRight size={14} /> SELL
                      </>
                    ) : (
                      <>
                        <Activity size={14} /> {e.signal}
                      </>
                    )}
                  </span>
                  {e.signal_price ? <span className="sv5-exec-price">@ {Number(e.signal_price).toLocaleString()} €</span> : <span />}
                </div>
              </Card>
            ))}

            {runningExecs.length === 0 && (
              <Card className="sv5-empty">
                <p>Aucune exécution en cours.</p>
              </Card>
            )}
          </div>
        </section>

        {/* Centre : positions */}
        <section className="sv5-col sv5-col-center">
          <div className="sv5-section-head">
            <h2 className="sv5-section-title">
              Analyse thermique du portefeuille
            </h2>
            <div className="sv5-center-tools">
              <div className="sv5-legend">
                <span className="sv5-legend-item"><i className="sv5-legend-dot neg" /> &lt; -3%</span>
                <span className="sv5-legend-item"><i className="sv5-legend-dot zero" /> 0%</span>
                <span className="sv5-legend-item"><i className="sv5-legend-dot pos" /> &gt; +3%</span>
              </div>
              <div className="sv5-mode-toggle">
                <button
                  type="button"
                  className={centerMode === 'heatmap' ? 'active' : ''}
                  onClick={() => setCenterMode('heatmap')}
                  title="Vue heatmap par secteur"
                >
                  Heatmap
                </button>
                <button
                  type="button"
                  className={centerMode === 'cards' ? 'active' : ''}
                  onClick={() => setCenterMode('cards')}
                  title="Vue cartes (compact)"
                >
                  Cartes
                </button>
              </div>
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="sv5-sync-history-btn"
                disabled={loading || syncingPortfolioHistory || positions.length === 0}
                title="Resynchroniser l’historique Yahoo (365 j) pour chaque actif en position, puis recharger les cours"
                onClick={() => void syncPortfolioPriceHistory()}
              >
                <RefreshCw size={14} className={syncingPortfolioHistory ? 'sv5-spin' : ''} aria-hidden />
                <span>{syncingPortfolioHistory ? 'Sync…' : 'Sync historiques'}</span>
              </Button>
              <Button
                type="button"
                size="sm"
                variant="secondary"
                disabled={loading || creatingStrategiesFromPortfolio}
                title="Crée une stratégie par actif (positions ouvertes + ordres d’achat actifs), sauf si une stratégie existe déjà pour cet actif"
                onClick={() => void createStrategiesFromPortfolio()}
              >
                <PlusCircle size={14} className={creatingStrategiesFromPortfolio ? 'sv5-spin' : ''} aria-hidden />
                <span>
                  {creatingStrategiesFromPortfolio ? 'Création…' : 'Créer stratégies pour le portefeuille'}
                </span>
              </Button>
            </div>
          </div>

          {portfolioStrategiesFeedback && (
            <Card className="sv5-info-banner">
              <div className="sv5-error-row">
                <Badge variant="success">Portefeuille</Badge>
                <span>{portfolioStrategiesFeedback}</span>
                <Button size="sm" variant="outline" onClick={() => setPortfolioStrategiesFeedback(null)}>
                  Fermer
                </Button>
              </div>
            </Card>
          )}

          {error && (
            <Card className="sv5-error">
              <div className="sv5-error-row">
                <Badge variant="danger">Erreur</Badge>
                <span>{error}</span>
                <Button size="sm" variant="outline" onClick={() => void loadData()}>
                  Réessayer
                </Button>
              </div>
            </Card>
          )}

          {centerMode === 'cards' ? (
            <div className="sv5-positions-grid">
              {portfolioCards.map((p) => (
                <Card
                  key={`pos-${p.positionId}`}
                  className="sv5-pos-card"
                  onMouseEnter={(e) => handleAssetEnter(e, p.allAssetId, p.symbol, p.broker)}
                  onMouseMove={handleAssetMove}
                  onMouseLeave={handleAssetLeave}
                >
                  <div className="sv5-pos-top">
                    <div className="sv5-pos-left">
                      <div className="sv5-avatar">{(p.symbol || '?').slice(0, 1).toUpperCase()}</div>
                      <div>
                        <div className="sv5-pos-symbol">{p.symbol}</div>
                        <div className="sv5-pos-name">{p.name}</div>
                      </div>
                    </div>
                    <div className="sv5-pos-right">
                      <div className="sv5-pos-broker">{p.broker}</div>
                      <div className={`sv5-pos-pnl ${p.pnl >= 0 ? 'pos' : 'neg'}`}>
                        {p.pnl >= 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                        {Math.abs(p.pnl).toFixed(2)}%
                      </div>
                    </div>
                  </div>

                  <div className="sv5-pos-bottom">
                    <div>
                      <div className="sv5-pos-value">{formatCurrency(p.value)}</div>
                      <div className="sv5-pos-qty">{p.qty.toLocaleString()} part{p.qty > 1 ? 's' : ''}</div>
                    </div>
                  </div>
                </Card>
              ))}

              {!loading && portfolioCards.length === 0 && (
                <Card className="sv5-empty">
                  <p>Aucune position ouverte.</p>
                </Card>
              )}
            </div>
          ) : (
            <Card className="sv5-heatmap-card">
              <div className="sv5-heatmap">
                {sectorTreemap.map((sec) => (
                  <div
                    key={sec.name}
                    className="sv5-sector"
                    style={{ flex: `${clamp(sec.weight, 8, 100)} 1 0%` }}
                  >
                    <div className="sv5-sector-head">
                      <span className="sv5-sector-name">
                        {sec.name} <Maximize2 size={11} />
                      </span>
                      <span className="sv5-sector-alloc">{Math.round(sec.weight)}%</span>
                    </div>

                    <div className="sv5-sector-assets">
                      {sec.assets.map((a) => {
                        const w = (a.size / sec.total) * 100
                        return (
                          <div
                            key={`${sec.name}-pos-${a.positionId}`}
                            className="sv5-heat-asset"
                            style={{
                              flex: `${Math.max(3, w)} 1 0%`,
                              backgroundColor: pnlBg(a.pnl),
                            }}
                            title={`${a.symbol} (${a.broker}) · position #${a.positionId} · ${a.pnl > 0 ? '+' : ''}${a.pnl.toFixed(2)}% · ${formatCurrency(a.size)}`}
                            onMouseEnter={(e) => handleAssetEnter(e, a.allAssetId, a.symbol, a.broker)}
                            onMouseMove={handleAssetMove}
                            onMouseLeave={handleAssetLeave}
                          >
                            <div className="sv5-heat-overlay" />
                            <div className="sv5-heat-center">
                              <div className="sv5-heat-symbol">{a.symbol}</div>
                              <div className={`sv5-heat-pnl ${a.pnl >= 0 ? 'pos' : 'neg'}`}>
                                {a.pnl > 0 ? '+' : ''}{a.pnl.toFixed(2)}%
                              </div>
                            </div>
                            <div className="sv5-heat-value">{formatCurrency(a.size)}</div>
                            {strategyBySymbol.has(a.symbol) && (() => {
                              const strat = strategyBySymbol.get(a.symbol)!
                              const active = isStratActive(strat)
                              return (
                                <>
                                  <button
                                    type="button"
                                    className={`sv5-heat-strat-toggle ${active ? 'on' : 'off'}`}
                                    title={`${strat.name} — ${active ? 'Actif · cliquer pour désactiver' : 'Inactif · cliquer pour activer'}`}
                                    onClick={(e) => { e.stopPropagation(); void handleToggleStrategy(strat) }}
                                    onMouseEnter={(e) => e.stopPropagation()}
                                    onMouseLeave={(e) => e.stopPropagation()}
                                  >
                                    <BrainCircuit size={9} />
                                    <span>{active ? 'ON' : 'OFF'}</span>
                                  </button>
                                  <button
                                    type="button"
                                    className="sv5-heat-strat-edit"
                                    title="Configurer la stratégie"
                                    onClick={(e) => { e.stopPropagation(); openStrategyWidget(strat) }}
                                    onMouseEnter={(e) => e.stopPropagation()}
                                    onMouseLeave={(e) => e.stopPropagation()}
                                  >
                                    <Settings size={9} />
                                  </button>
                                </>
                              )
                            })()}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                ))}

                {!loading && sectorTreemap.length === 0 && (
                  <div className="sv5-heat-empty">Aucune position ouverte.</div>
                )}
              </div>
            </Card>
          )}

          {hover.visible && hover.allAssetId && (
            <div
              className="sv5-hover-tooltip"
              style={{
                left: clamp(hover.x + 14, 12, window.innerWidth - 520),
                top: clamp(hover.y + 14, 12, window.innerHeight - 360),
              }}
            >
              <div className="sv5-hover-head">
                <div className="sv5-hover-title">{hover.symbol}</div>
                <div className="sv5-hover-sub">{hover.broker}</div>
              </div>

              {!hoverPayload ? (
                <div className="sv5-hover-loading">Chargement du graphe…</div>
              ) : (
                <div className="sv5-hover-chart">
                  {(() => {
                    const byDay = new Map<string, number>()
                    for (const p of hoverPayload.prices || []) {
                      const d = normalizeChartDate((p as any).date)
                      const close = Number((p as any).close)
                      if (!d || !Number.isFinite(close)) continue
                      byDay.set(d, close)
                    }

                    const historyDates = [...byDay.keys()].sort((a, b) => a.localeCompare(b))

                    const tradeRows = (hoverPayload.trades || [])
                      .map((t) => {
                        const d = normalizeChartDate(t.date)
                        return {
                          ...t,
                          date: d ?? String(t.date ?? '').slice(0, 10),
                          dateLabel: formatDateLabel(t.date),
                        }
                      })
                      .filter((t) => t.date && Number.isFinite(t.price))

                    const tradeBySnappedDay = new Map<string, { price: number; side: string }>()
                    for (const t of tradeRows) {
                      const snap = snapTradeDateToHistory(t.date, historyDates)
                      if (!snap) continue
                      tradeBySnappedDay.set(snap, {
                        price: t.price,
                        side: String(t.side || 'BUY').toUpperCase(),
                      })
                    }

                    const chartPrices = historyDates.map((date) => {
                      const tr = tradeBySnappedDay.get(date)
                      return {
                        date,
                        close: byDay.get(date) as number,
                        tradePrice: tr?.price,
                        tradeSide: tr?.side,
                      }
                    })

                    const first = chartPrices[0]
                    const last = chartPrices[chartPrices.length - 1]

                    const numericCloses = chartPrices.map((r) => r.close).filter((c) => Number.isFinite(c))
                    const tradePx = [...tradeBySnappedDay.values()].map((x) => x.price).filter((p) => Number.isFinite(p))
                    const allY = [...numericCloses, ...tradePx]
                    let yLo = allY.length ? Math.min(...allY) : 0
                    let yHi = allY.length ? Math.max(...allY) : 1
                    if (!Number.isFinite(yLo) || !Number.isFinite(yHi)) {
                      yLo = 0
                      yHi = 1
                    }
                    if (yHi - yLo < 1e-9) {
                      const m = yLo || 1
                      yLo = m * 0.9995
                      yHi = m * 1.0005
                    }
                    const yPad = (yHi - yLo) * 0.06
                    const yDomain: [number, number] = [yLo - yPad, yHi + yPad]
                    const ySpan = yHi - yLo
                    const yTickFormat = (v: number) => {
                      if (!Number.isFinite(v)) return ''
                      if (ySpan < 0.02) return v.toFixed(5)
                      if (ySpan < 0.5) return v.toFixed(4)
                      if (ySpan < 5) return v.toFixed(3)
                      if (ySpan < 80) return v.toFixed(2)
                      if (ySpan < 5000) return v.toFixed(1)
                      return v.toFixed(0)
                    }

                    return (
                      <>
                        <div className="sv5-hover-meta">
                          <div className="sv5-hover-meta-row">
                            <span className="sv5-hover-meta-k">Début</span>
                            <span className="sv5-hover-meta-v">
                              {first
                                ? `${formatDateLabel(first.date)} • ${Number(first.close).toFixed(2)}`
                                : '—'}
                            </span>
                          </div>
                          <div className="sv5-hover-meta-row">
                            <span className="sv5-hover-meta-k">Fin</span>
                            <span className="sv5-hover-meta-v">
                              {last
                                ? `${formatDateLabel(last.date)} • ${Number(last.close).toFixed(2)}`
                                : '—'}
                            </span>
                          </div>
                        </div>

                        <ResponsiveContainer width="100%" height={220}>
                          {/*
                            Recharts 3 : ne pas mettre <Scatter> dans <LineChart> (band-scale catégorielle → NaN).
                            Trades : 2e Line stroke transparent + dots. Jours trades hors historique → snap au dernier jour ≤ date.
                          */}
                          <LineChart data={chartPrices} margin={{ top: 10, right: 10, bottom: 8, left: 0 }}>
                            <XAxis
                              dataKey="date"
                              type="category"
                              allowDuplicatedCategory={false}
                              tickFormatter={(d) => formatDateLabel(String(d))}
                              tick={{ fill: 'rgba(255,255,255,0.65)', fontSize: 11 }}
                              tickLine={false}
                              axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
                              interval="preserveStartEnd"
                              minTickGap={20}
                            />
                            <YAxis
                              tick={{ fill: 'rgba(255,255,255,0.65)', fontSize: 11 }}
                              tickLine={false}
                              axisLine={false}
                              width={56}
                              domain={yDomain}
                              allowDataOverflow
                              tickFormatter={(v: any) => yTickFormat(Number(v))}
                            />
                            <RechartsTooltip
                              contentStyle={{ backgroundColor: '#0b1220', border: '1px solid rgba(255,255,255,0.10)' }}
                              labelStyle={{ color: 'rgba(255,255,255,0.85)' }}
                              itemStyle={{ color: '#e5e7eb' }}
                              labelFormatter={(l: any) => `Date: ${formatDateLabel(String(l))}`}
                              formatter={(v: any, name: any) => {
                                if (name === 'close') return [Number(v).toFixed(2), 'Close']
                                if (name === 'tradePrice') return [Number(v).toFixed(2), 'Exécution']
                                return [String(v), String(name)]
                              }}
                            />

                            <Line
                              type="linear"
                              dataKey="close"
                              stroke="#7dd3fc"
                              strokeWidth={2}
                              dot={false}
                              isAnimationActive={false}
                              connectNulls={false}
                            />

                            <Line
                              type="linear"
                              dataKey="tradePrice"
                              stroke="transparent"
                              strokeWidth={0}
                              dot={(dotProps: any) => {
                                const { cx, cy, payload } = dotProps
                                if (
                                  payload?.tradePrice == null ||
                                  !Number.isFinite(Number(payload.tradePrice)) ||
                                  !Number.isFinite(cx) ||
                                  !Number.isFinite(cy)
                                ) {
                                  return null
                                }
                                const isSell = String(payload?.tradeSide).toUpperCase() === 'SELL'
                                const fill = isSell ? '#fb7185' : '#22c55e'
                                const halo = isSell ? 'rgba(251, 113, 133, 0.35)' : 'rgba(34, 197, 94, 0.4)'
                                const r = 6
                                return (
                                  <g aria-hidden>
                                    <circle cx={cx} cy={cy} r={r + 5} fill={halo} />
                                    <circle
                                      cx={cx}
                                      cy={cy}
                                      r={r + 2.5}
                                      fill="none"
                                      stroke="#ffffff"
                                      strokeWidth={2.5}
                                      opacity={0.95}
                                    />
                                    <circle cx={cx} cy={cy} r={r} fill={fill} stroke="#0f172a" strokeWidth={1.5} />
                                  </g>
                                )
                              }}
                              activeDot={false}
                              isAnimationActive={false}
                              legendType="none"
                            />
                          </LineChart>
                        </ResponsiveContainer>

                        <div className="sv5-hover-trades">
                          {(hoverPayload.trades || []).slice(-3).map((t) => (
                            <div
                              key={t.id}
                              className={`sv5-hover-trade ${t.side === 'BUY' ? 'sv5-hover-trade--buy' : 'sv5-hover-trade--sell'}`}
                            >
                              <span className={`sv5-hover-trade-side ${t.side === 'BUY' ? 'buy' : 'sell'}`}>{t.side}</span>
                              <span className="sv5-hover-trade-mid">
                                {t.quantity.toFixed(4)} @ {t.price.toFixed(2)}
                              </span>
                              <span className="sv5-hover-trade-date">{formatDateLabel(t.date)}</span>
                            </div>
                          ))}
                          {(hoverPayload.trades || []).length === 0 && (
                            <div className="sv5-hover-trade-empty">Aucun trade BUY/SELL trouvé pour cet actif.</div>
                          )}
                        </div>

                        <div className="sv5-hover-foot">
                          <span>{chartPrices.length} pts</span>
                          <span>{hoverPayload.trades.length} trades</span>
                        </div>
                      </>
                    )
                  })()}
                </div>
              )}
            </div>
          )}
        </section>

        {/* Droite : statuts rapides */}
        <section className="sv5-col sv5-col-right">
          <div className="sv5-section-head">
            <h2 className="sv5-section-title">Statuts</h2>
            <PieChart className="sv5-section-icon" />
          </div>

          <Card className="sv5-status-card blue">
            <h3 className="sv5-status-title">
              <CheckCircle2 size={16} /> Robot status
            </h3>
            <p className="sv5-status-text">
              Rafraîchissement auto toutes les 12s. Dernier load :{' '}
              {new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}.
            </p>
          </Card>

          <Card className="sv5-status-card amber">
            <h3 className="sv5-status-title">
              <TrendingDown size={16} /> À surveiller
            </h3>
            <p className="sv5-status-text">
              Cette V5 est un squelette : on branchera ensuite la liquidité par broker, les signaux IA et les analytics.
            </p>
          </Card>

          <div className="sv5-section-head sv5-mt">
            <h2 className="sv5-section-title">Actions automatisées</h2>
            <Layers className="sv5-section-icon" />
          </div>

          <div className="sv5-stack">
            {strategiesOffPortfolio.map((s) => {
              const active = isStratActive(s)
              return (
                <Card
                  key={s.id}
                  className="sv5-auto-card sv5-auto-card-clickable"
                  onClick={() => openStrategyWidget(s)}
                >
                  <div className="sv5-auto-top">
                    <span className="sv5-auto-name">{s.name}</span>
                    <div className="sv5-auto-actions">
                      <button
                        type="button"
                        className={`sv5-strat-toggle ${active ? 'on' : 'off'}`}
                        title={active ? 'Actif · cliquer pour désactiver' : 'Inactif · cliquer pour activer'}
                        onClick={(e) => { e.stopPropagation(); void handleToggleStrategy(s) }}
                      >
                        {active ? 'Actif' : 'Inactif'}
                      </button>
                      <ChevronDown size={14} className="sv5-auto-chevron" />
                    </div>
                  </div>
                  <div className="sv5-auto-meta">
                    <span className="sv5-auto-algo">{(s.algorithm_type as string) || '—'}</span>
                    <span className="sv5-auto-asset">{(s.all_asset_symbol as string) || '—'}</span>
                  </div>
                </Card>
              )
            })}
            {!loading && strategiesOffPortfolio.length === 0 && (
              <Card className="sv5-empty">
                <p>Toutes les stratégies actives sont liées à des actifs en portefeuille.</p>
              </Card>
            )}
          </div>
        </section>
      </main>

      {/* Modal widget stratégie */}
      {expandedStrategyId !== null && (() => {
        const s = strategies.find(st => st.id === expandedStrategyId)
        if (!s) return null
        const edits = inlineEdit[expandedStrategyId] || {}
        const currentAlgo = edits.algorithm_type || s.algorithm_type || 'threshold'
        const algoParams = ALGORITHM_PARAMS[currentAlgo] || []
        return (
          <div className="sv5-modal-overlay" onClick={() => setExpandedStrategyId(null)}>
            <div className="sv5-modal" onClick={(e) => e.stopPropagation()}>
              <div className="sv5-modal-header">
                <div className="sv5-modal-title">
                  <BrainCircuit size={16} />
                  <span>{s.name}</span>
                  <span className="sv5-modal-subtitle">{getAssetSymbol(s)} · ID-{s.id}</span>
                </div>
                <button className="sv5-modal-close" onClick={() => setExpandedStrategyId(null)}>
                  <X size={18} />
                </button>
              </div>

              {/* Chart */}
              <div className="sv5-modal-chart-section">
                <div className="sv5-modal-chart-header">
                  <h4>Prix &amp; Signaux — {edits.all_asset_name || getAssetName(s)}</h4>
                  <button
                    className={`sv5-sync-btn ${syncingYahooId === s.id ? 'syncing' : ''} ${yahooSyncResult[s.id as number]?.success ? 'success' : ''}`}
                    onClick={() => void handleSyncYahoo(s)}
                    disabled={syncingYahooId === s.id}
                  >
                    {syncingYahooId === s.id ? '⏳ Chargement...' : '📊 Charger données Yahoo'}
                  </button>
                </div>
                {yahooSyncResult[s.id as number] && (
                  <div className={`sv5-sync-message ${yahooSyncResult[s.id as number].success ? 'success' : 'error'}`}>
                    {yahooSyncResult[s.id as number].success ? '✓' : '✕'} {yahooSyncResult[s.id as number].message}
                  </div>
                )}
                <StrategyVisualizationChart
                  key={`sv5-chart-${s.id}-${chartKey}`}
                  strategy={s}
                  parameters={edits}
                  initialPeriod={chartPeriods[s.id as number] || 365}
                  onPeriodChange={(days) => {
                    setChartPeriods(prev => ({ ...prev, [s.id as number]: days }))
                    const assetId = getAssetId(s)
                    if (assetId && !syncingYahooId) {
                      setSyncingYahooId(s.id as number)
                      assetService.syncPriceHistory(assetId, days, '1d')
                        .then(result => {
                          if (result.success) {
                            setYahooSyncResult(prev => ({ ...prev, [s.id as number]: { success: true, message: `${result.records || 0} points chargés` } }))
                          }
                        })
                        .catch(() => {})
                        .finally(() => setSyncingYahooId(null))
                    }
                  }}
                />
              </div>

              {/* Config */}
              <div className="sv5-modal-config">
                <div className="sv5-modal-config-header">
                  <h4>Configuration</h4>
                  <button
                    className="sv5-modal-save-btn"
                    onClick={() => void saveInlineEdit(s)}
                    disabled={savingId === s.id}
                  >
                    {savingId === s.id ? 'Sauvegarde...' : '✓ Sauvegarder'}
                  </button>
                </div>
                <div className="sv5-modal-config-list">
                  {/* Algorithme */}
                  <div className="sv5-cfg-row">
                    <span className="sv5-cfg-key">Algorithme</span>
                    <select
                      className="sv5-cfg-select"
                      value={currentAlgo}
                      onChange={(e) => {
                        updateInlineEdit(expandedStrategyId, 'algorithm_type', e.target.value)
                        const newParams = ALGORITHM_PARAMS[e.target.value] || []
                        newParams.forEach(p => updateInlineEdit(expandedStrategyId, p.key, p.default))
                      }}
                    >
                      {Object.entries(ALGORITHM_LABELS).map(([key, label]) => (
                        <option key={key} value={key}>{label}</option>
                      ))}
                    </select>
                  </div>
                  {/* Params algo */}
                  {algoParams.map(param => (
                    <div key={param.key} className="sv5-cfg-row">
                      <span className="sv5-cfg-key">{param.label}</span>
                      <input
                        type="number"
                        className="sv5-cfg-input"
                        value={edits[param.key] ?? param.default}
                        onChange={(e) => updateInlineEdit(expandedStrategyId, param.key, e.target.value)}
                        step="any"
                      />
                    </div>
                  ))}
                  <div className="sv5-cfg-separator" />
                  {/* Qté par trade */}
                  <div className="sv5-cfg-row">
                    <span className="sv5-cfg-key">Qté par trade</span>
                    <div className="sv5-cfg-range">
                      <input
                        type="number"
                        className="sv5-cfg-input small"
                        value={edits.target_min_quantity ?? s.target_min_quantity ?? 1}
                        onChange={(e) => updateInlineEdit(expandedStrategyId, 'target_min_quantity', e.target.value)}
                        step="any"
                      />
                      <span className="sv5-range-sep">–</span>
                      <input
                        type="number"
                        className="sv5-cfg-input small"
                        value={edits.target_max_quantity ?? s.target_max_quantity ?? 10}
                        onChange={(e) => updateInlineEdit(expandedStrategyId, 'target_max_quantity', e.target.value)}
                        step="any"
                      />
                    </div>
                  </div>
                  {/* Portefeuille */}
                  <div className="sv5-cfg-row">
                    <span className="sv5-cfg-key">Portefeuille (actions)</span>
                    <div className="sv5-cfg-range">
                      <input
                        type="number"
                        className="sv5-cfg-input small"
                        value={edits.portfolio_min_quantity !== undefined ? edits.portfolio_min_quantity : (s.portfolio_min_quantity ?? 0)}
                        onChange={(e) => updateInlineEdit(expandedStrategyId, 'portfolio_min_quantity', e.target.value)}
                        step="any" min={0}
                      />
                      <span className="sv5-range-sep">–</span>
                      <input
                        type="number"
                        className="sv5-cfg-input small"
                        placeholder="∞"
                        value={edits.portfolio_max_quantity !== undefined ? edits.portfolio_max_quantity : (s.portfolio_max_quantity ?? '')}
                        onChange={(e) => updateInlineEdit(expandedStrategyId, 'portfolio_max_quantity', e.target.value)}
                        step="any" min={0}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )
      })()}
    </div>
  )
}

