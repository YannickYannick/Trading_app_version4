/**
 * StrategiesV4 - Dashboard moderne multi-broker (inspiré du mock fourni).
 * Pour l'instant : récap positions du portefeuille + ordres/stratégies en cours d'exécution.
 */
import { useEffect, useMemo, useState } from 'react'
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  BrainCircuit,
  CheckCircle2,
  Clock,
  Layers,
  Maximize2,
  PieChart,
  TrendingDown,
  TrendingUp,
  Wallet,
} from 'lucide-react'
import { Card, Badge, Button, Loading } from '@components/common'
import { positionService, orderService, strategyService } from '@services'
import strategyExecutionService, { type StrategyExecution } from '@services/strategyExecutionService'
import type { Order, Position, Strategy } from '@types'
import { formatCurrency } from '@utils/format'
import './StrategiesV4.css'

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

function posMarketValueEUR(p: Position): number {
  const qty = posQuantity(p)
  const px = safeNumber((p as any).yahoo_current_price ?? (p as any).current_price ?? (p as any).entry_price)
  return Math.max(0, qty * px)
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

export default function StrategiesV4() {
  const [positions, setPositions] = useState<Position[]>([])
  const [activeOrders, setActiveOrders] = useState<Order[]>([])
  const [executions, setExecutions] = useState<StrategyExecution[]>([])
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [centerMode, setCenterMode] = useState<'heatmap' | 'cards'>('heatmap')

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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

  useEffect(() => {
    void loadData()
  }, [])

  // Rafraîchissement léger pour donner une sensation “live”
  useEffect(() => {
    const t = setInterval(() => {
      void loadData()
    }, 12000)
    return () => clearInterval(t)
  }, [])

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
        const pnlPct = safeNumber((p as any).pnl_percent)
        const value = posMarketValueEUR(p)
        return {
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
          symbol: posSymbol(p),
          name: posName(p),
          sector: posSector(p),
          broker: posBroker(p),
          size,
          pnl: safeNumber((p as any).pnl_percent),
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
  const automatedStrategies = useMemo(
    () => strategies.filter((s) => Boolean(s.is_automated)).slice(0, 12),
    [strategies]
  )

  return (
    <div className="strategies-v4">
      <header className="sv4-header">
        <div>
          <h1 className="sv4-title">
            <Activity className="sv4-title-icon" />
            Stratégies V4
          </h1>
          <p className="sv4-subtitle">
            Récap portefeuille + activités en cours (ordres & exécutions).
          </p>
        </div>

        <div className="sv4-header-cards">
          <Card className="sv4-stat-card">
            <div className="sv4-stat-icon blue">
              <Wallet className="sv4-stat-icon-svg" />
            </div>
            <div>
              <p className="sv4-stat-k">Valeur totale (estim.)</p>
              <p className="sv4-stat-v">{formatCurrency(totalValue)}</p>
            </div>
          </Card>
          <Card className="sv4-stat-card">
            <div className="sv4-stat-icon green">
              <TrendingUp className="sv4-stat-icon-svg" />
            </div>
            <div>
              <p className="sv4-stat-k">Ordres actifs</p>
              <p className="sv4-stat-v">{activeOrders.length}</p>
            </div>
          </Card>
        </div>
      </header>

      <main className="sv4-grid">
        {/* Gauche : ordres + exécutions */}
        <section className="sv4-col sv4-col-left">
          <div className="sv4-section-head">
            <h2 className="sv4-section-title">
              Ordres actifs <span className="sv4-section-muted">({uiOrders.length})</span>
            </h2>
            <Clock className="sv4-section-icon" />
          </div>

          {loading && uiOrders.length === 0 ? (
            <Card className="sv4-pad">
              <Loading text="Chargement…" />
            </Card>
          ) : (
            <div className="sv4-stack">
              {uiOrders.map((o) => (
                <Card key={String(o.id)} className="sv4-order-card">
                  <div className="sv4-order-top">
                    <div>
                      <span className={`sv4-chip ${o.type === 'BUY' ? 'buy' : 'sell'}`}>{o.type}</span>
                      <div className="sv4-order-symbol">{o.symbol}</div>
                    </div>
                    <Badge variant={statusVariant(o.status)}>{o.progress === 100 ? 'Terminé' : o.status}</Badge>
                  </div>

                  <div className="sv4-order-meta">
                    <span>
                      {o.qty || 0} unités{typeof o.price === 'number' ? ` @ ${o.price} €` : ''}
                    </span>
                    <span className="sv4-order-broker">{o.broker}</span>
                  </div>

                  <div className="sv4-progress">
                    <div className="sv4-progress-rail" />
                    <div
                      className={`sv4-progress-bar ${o.type === 'BUY' ? 'buy' : 'sell'}`}
                      style={{ width: `${o.progress}%` }}
                    />
                  </div>
                </Card>
              ))}

              {uiOrders.length === 0 && (
                <Card className="sv4-empty">
                  <p>Aucun ordre actif.</p>
                </Card>
              )}
            </div>
          )}

          <div className="sv4-section-head sv4-mt">
            <h2 className="sv4-section-title purple">
              <BrainCircuit className="sv4-section-icon purple" />
              Exécutions en cours <span className="sv4-section-muted">({runningExecs.length})</span>
            </h2>
            <div />
          </div>

          <div className="sv4-stack">
            {runningExecs.slice(0, 8).map((e) => (
              <Card key={e.id} className="sv4-exec-card">
                <div className="sv4-exec-top">
                  <div className="sv4-exec-title">
                    <span className="sv4-exec-name">{e.strategy_name}</span>
                    <span className="sv4-exec-time">
                      {new Date(e.started_at).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                  </div>
                  <Badge variant="info">running</Badge>
                </div>
                <div className="sv4-exec-bottom">
                  <span className={`sv4-exec-signal ${e.signal}`}>
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
                  {e.signal_price ? <span className="sv4-exec-price">@ {Number(e.signal_price).toLocaleString()} €</span> : <span />}
                </div>
              </Card>
            ))}

            {runningExecs.length === 0 && (
              <Card className="sv4-empty">
                <p>Aucune exécution en cours.</p>
              </Card>
            )}
          </div>
        </section>

        {/* Centre : positions */}
        <section className="sv4-col sv4-col-center">
          <div className="sv4-section-head">
            <h2 className="sv4-section-title">
              Analyse thermique du portefeuille
            </h2>
            <div className="sv4-center-tools">
              <div className="sv4-legend">
                <span className="sv4-legend-item"><i className="sv4-legend-dot neg" /> &lt; -3%</span>
                <span className="sv4-legend-item"><i className="sv4-legend-dot zero" /> 0%</span>
                <span className="sv4-legend-item"><i className="sv4-legend-dot pos" /> &gt; +3%</span>
              </div>
              <div className="sv4-mode-toggle">
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
            </div>
          </div>

          {error && (
            <Card className="sv4-error">
              <div className="sv4-error-row">
                <Badge variant="danger">Erreur</Badge>
                <span>{error}</span>
                <Button size="sm" variant="outline" onClick={() => void loadData()}>
                  Réessayer
                </Button>
              </div>
            </Card>
          )}

          {centerMode === 'cards' ? (
            <div className="sv4-positions-grid">
              {portfolioCards.map((p) => (
                <Card key={`${p.symbol}-${p.broker}`} className="sv4-pos-card">
                  <div className="sv4-pos-top">
                    <div className="sv4-pos-left">
                      <div className="sv4-avatar">{(p.symbol || '?').slice(0, 1).toUpperCase()}</div>
                      <div>
                        <div className="sv4-pos-symbol">{p.symbol}</div>
                        <div className="sv4-pos-name">{p.name}</div>
                      </div>
                    </div>
                    <div className="sv4-pos-right">
                      <div className="sv4-pos-broker">{p.broker}</div>
                      <div className={`sv4-pos-pnl ${p.pnl >= 0 ? 'pos' : 'neg'}`}>
                        {p.pnl >= 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                        {Math.abs(p.pnl).toFixed(2)}%
                      </div>
                    </div>
                  </div>

                  <div className="sv4-pos-bottom">
                    <div>
                      <div className="sv4-pos-value">{formatCurrency(p.value)}</div>
                      <div className="sv4-pos-qty">{p.qty.toLocaleString()} part{p.qty > 1 ? 's' : ''}</div>
                    </div>
                  </div>
                </Card>
              ))}

              {!loading && portfolioCards.length === 0 && (
                <Card className="sv4-empty">
                  <p>Aucune position ouverte.</p>
                </Card>
              )}
            </div>
          ) : (
            <Card className="sv4-heatmap-card">
              <div className="sv4-heatmap">
                {sectorTreemap.map((sec) => (
                  <div
                    key={sec.name}
                    className="sv4-sector"
                    style={{ flex: `${clamp(sec.weight, 8, 100)} 1 0%` }}
                  >
                    <div className="sv4-sector-head">
                      <span className="sv4-sector-name">
                        {sec.name} <Maximize2 size={11} />
                      </span>
                      <span className="sv4-sector-alloc">{Math.round(sec.weight)}%</span>
                    </div>

                    <div className="sv4-sector-assets">
                      {sec.assets.map((a) => {
                        const w = (a.size / sec.total) * 100
                        return (
                          <div
                            key={`${sec.name}-${a.symbol}-${a.broker}`}
                            className="sv4-heat-asset"
                            style={{
                              flex: `${Math.max(3, w)} 1 0%`,
                              backgroundColor: pnlBg(a.pnl),
                            }}
                            title={`${a.symbol} (${a.broker}) • ${a.pnl > 0 ? '+' : ''}${a.pnl.toFixed(2)}% • ${formatCurrency(a.size)}`}
                          >
                            <div className="sv4-heat-overlay" />
                            <div className="sv4-heat-center">
                              <div className="sv4-heat-symbol">{a.symbol}</div>
                              <div className={`sv4-heat-pnl ${a.pnl >= 0 ? 'pos' : 'neg'}`}>
                                {a.pnl > 0 ? '+' : ''}{a.pnl.toFixed(2)}%
                              </div>
                            </div>
                            <div className="sv4-heat-value">{formatCurrency(a.size)}</div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                ))}

                {!loading && sectorTreemap.length === 0 && (
                  <div className="sv4-heat-empty">Aucune position ouverte.</div>
                )}
              </div>
            </Card>
          )}
        </section>

        {/* Droite : statuts rapides */}
        <section className="sv4-col sv4-col-right">
          <div className="sv4-section-head">
            <h2 className="sv4-section-title">Statuts</h2>
            <PieChart className="sv4-section-icon" />
          </div>

          <Card className="sv4-status-card blue">
            <h3 className="sv4-status-title">
              <CheckCircle2 size={16} /> Robot status
            </h3>
            <p className="sv4-status-text">
              Rafraîchissement auto toutes les 12s. Dernier load :{' '}
              {new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}.
            </p>
          </Card>

          <Card className="sv4-status-card amber">
            <h3 className="sv4-status-title">
              <TrendingDown size={16} /> À surveiller
            </h3>
            <p className="sv4-status-text">
              Cette V4 est un squelette : on branchera ensuite la liquidité par broker, les signaux IA et les analytics.
            </p>
          </Card>

          <div className="sv4-section-head sv4-mt">
            <h2 className="sv4-section-title">Actions automatisées</h2>
            <Layers className="sv4-section-icon" />
          </div>

          <div className="sv4-stack">
            {automatedStrategies.map((s) => (
              <Card key={s.id} className="sv4-auto-card">
                <div className="sv4-auto-top">
                  <span className="sv4-auto-name">{s.name}</span>
                  <Badge variant={s.is_active ? 'success' : 'warning'}>{s.is_active ? 'Actif' : 'Inactif'}</Badge>
                </div>
                <div className="sv4-auto-meta">
                  <span className="sv4-auto-algo">{(s.algorithm_type as string) || '—'}</span>
                  <span className="sv4-auto-asset">{(s.all_asset_symbol as string) || '—'}</span>
                </div>
              </Card>
            ))}
            {!loading && automatedStrategies.length === 0 && (
              <Card className="sv4-empty">
                <p>Aucune stratégie automatisée.</p>
              </Card>
            )}
          </div>
        </section>
      </main>
    </div>
  )
}

