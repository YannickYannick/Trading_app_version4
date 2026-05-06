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
  PieChart,
  TrendingDown,
  TrendingUp,
  Wallet,
} from 'lucide-react'
import { Card, Badge, Button, Loading } from '@components/common'
import { positionService, orderService } from '@services'
import strategyExecutionService, { type StrategyExecution } from '@services/strategyExecutionService'
import type { Order, Position } from '@types'
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

export default function StrategiesV4() {
  const [positions, setPositions] = useState<Position[]>([])
  const [activeOrders, setActiveOrders] = useState<Order[]>([])
  const [executions, setExecutions] = useState<StrategyExecution[]>([])

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      const [pos, orders, execs] = await Promise.all([
        positionService.getOpen(),
        orderService.getActivePendingList(),
        strategyExecutionService.getRecent(),
      ])
      setPositions(pos || [])
      setActiveOrders(Array.isArray(orders) ? orders : [])
      setExecutions(Array.isArray(execs) ? execs : [])
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
    return activeOrders.slice(0, 8).map((o) => ({
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

  const totalValue = useMemo(() => portfolioCards.reduce((s, p) => s + p.value, 0), [portfolioCards])

  const runningExecs = useMemo(() => executions.filter((e) => e.status === 'running'), [executions])

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
            <h2 className="sv4-section-title">Positions ouvertes</h2>
            <Layers className="sv4-section-icon" />
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
        </section>
      </main>
    </div>
  )
}

