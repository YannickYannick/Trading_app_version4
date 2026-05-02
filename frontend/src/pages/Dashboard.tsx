/**
 * Page Dashboard - Vue d'ensemble du trading
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Card, Badge, Loading, Table } from '@components/common'
import { usePositions } from '@hooks/usePositions'
import { useTrades } from '@hooks/useTrades'
import { formatCurrency, formatPercent, formatDate } from '@utils/format'
import type { Position } from '@types'
import AIInsightWidget from '@components/AIInsightWidget'
import { AnalyticsCharts } from '@components/dashboard/AnalyticsCharts'
import { PortfolioCategoryChart } from '@components/dashboard/PortfolioCategoryChart'
import api from '@services/api'
import './Dashboard.css'

interface DashboardKpi {
  total_value: number;
  total_invested: number;
  total_cash: number;
  win_rate: number;
  total_closed_positions: number;
  active_positions: number;
}

export default function Dashboard() {
  const { positions, loading: positionsLoading } = usePositions({ status: 'OPEN' })
  const { trades, loading: tradesLoading } = useTrades()

  const [kpi, setKpi] = useState<DashboardKpi | null>(null)
  const [history, setHistory] = useState<any[]>([])
  const [breakdown, setBreakdown] = useState<any[]>([])
  const [loadingAnalytics, setLoadingAnalytics] = useState(true)
  const [showBreakdown, setShowBreakdown] = useState(false)

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const data = await api.getAnalyticsSummary()
        setKpi(data.kpi)
        setHistory(data.history)
        setBreakdown(data.breakdown)
      } catch (error) {
        console.error("Failed to fetch analytics", error)
      } finally {
        setLoadingAnalytics(false)
      }
    }
    fetchAnalytics()
  }, [])

  if (positionsLoading || tradesLoading || loadingAnalytics) {
    return (
      <div className="dashboard-page">
        <Loading text="Chargement du dashboard..." />
      </div>
    )
  }

  const recentPositions = positions.slice(0, 5)

  const positionColumns = [
    {
      key: 'symbol',
      label: 'Symbole',
      render: (_value: any, row: Position) => (
        <Link to={`/positions/${row?.id || ''}`} className="link-symbol">
          <div>{row?.symbol || row?.all_asset_symbol || 'N/A'}</div>
          {row?.all_asset_yahoo_symbol && (
            <div style={{ fontSize: '0.75rem', color: '#666' }}>{row.all_asset_yahoo_symbol}</div>
          )}
        </Link>
      ),
    },
    {
      key: 'size',
      label: 'Taille',
      align: 'right' as const,
      render: (_value: any, row: Position) => {
        const size = Number(row?.quantity || 0)
        return isNaN(size) ? '0.0000' : size.toFixed(4)
      },
    },
    {
      key: 'entry_price',
      label: 'Prix d\'entrée',
      align: 'right' as const,
      render: (_value: any, row: Position) => formatCurrency(row?.entry_price || 0),
    },
    {
      key: 'current_price',
      label: 'Prix actuel',
      align: 'right' as const,
      render: (_value: any, row: Position) => formatCurrency(row?.yahoo_current_price || row?.current_price || 0),
    },
    {
      key: 'pnl',
      label: 'P&L',
      align: 'right' as const,
      render: (_value: any, row: Position) => (
        <Badge variant={(row?.pnl || 0) >= 0 ? 'success' : 'danger'}>
          {formatCurrency(row?.pnl || 0)}
        </Badge>
      ),
    },
  ]

  return (
    <div className="dashboard-page">
      <div className="dashboard-header">
        <h1 className="dashboard-title">Dashboard</h1>
        <p className="dashboard-subtitle">Vue d'ensemble de votre portefeuille</p>
      </div>

      {/* AI Widget */}
      <div style={{ marginBottom: '24px' }}>
        <AIInsightWidget scope="PORTFOLIO" />
      </div>

      {/* Statistiques principales - Source API Analytics */}
      <div className="dashboard-stats-grid">
        <Card className="stat-card stat-card-primary stat-card-expandable">
          <div className="stat-card-content">
            <h3 className="stat-card-label">Valeur Totale</h3>
            <p className="stat-card-value">{formatCurrency(kpi?.total_value || 0)}</p>
            <div style={{ display: 'flex', gap: '10px', fontSize: '0.8rem', opacity: 0.8, marginTop: '5px' }}>
              <span>Cash: {formatCurrency(kpi?.total_cash || 0)}</span>
              <span>|</span>
              <span>Investi: {formatCurrency(kpi?.total_invested || 0)}</span>
            </div>
            
            {/* Bouton pour voir le détail */}
            <button 
              className="breakdown-toggle"
              onClick={() => setShowBreakdown(!showBreakdown)}
            >
              {showBreakdown ? '▲ Masquer détails' : '▼ Voir détails par compte'}
            </button>
            
            {/* Panneau déroulant avec détails par broker */}
            {showBreakdown && breakdown.length > 0 && (
              <div className="breakdown-panel">
                {breakdown.map((broker, idx) => (
                  <div key={idx} className="breakdown-item">
                    <div className="breakdown-broker-name">{broker.broker_name || 'Inconnu'}</div>
                    <div className="breakdown-details">
                      <div className="breakdown-row">
                        <span className="breakdown-label">Cash:</span>
                        <span className="breakdown-value">{formatCurrency(broker.cash || 0)}</span>
                      </div>
                      <div className="breakdown-row">
                        <span className="breakdown-label">Investi:</span>
                        <span className="breakdown-value">{formatCurrency(broker.invested || 0)}</span>
                      </div>
                      <div className="breakdown-row breakdown-total">
                        <span className="breakdown-label">Total:</span>
                        <span className="breakdown-value">{formatCurrency((broker.cash || 0) + (broker.invested || 0))}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>

        <Card className="stat-card">
          <div className="stat-card-content">
            <h3 className="stat-card-label">Taux de Réussite</h3>
            <p className={`stat-card-value ${(kpi?.win_rate || 0) >= 50 ? 'positive' : 'negative'}`}>
              {formatPercent(kpi?.win_rate || 0)}
            </p>
            <span style={{ fontSize: '0.75rem', color: '#888' }}>Sur trades fermés</span>
          </div>
        </Card>

        <Card className="stat-card">
          <div className="stat-card-content">
            <h3 className="stat-card-label">Positions Ouvertes</h3>
            <p className="stat-card-value">{kpi?.active_positions || 0}</p>
            <Link to="/positions" className="stat-card-link">
              Voir toutes →
            </Link>
          </div>
        </Card>

        <Card className="stat-card">
          <div className="stat-card-content">
            <h3 className="stat-card-label">Positions Fermées</h3>
            <p className="stat-card-value">{kpi?.total_closed_positions || 0}</p>
            <Link to="/trades" className="stat-card-link">
              Voir trades →
            </Link>
          </div>
        </Card>
      </div>

      {/* Nouveaux Graphiques d'Analytique */}
      <AnalyticsCharts history={history} breakdown={breakdown} />

      {/* Allocation portefeuille (catégories) */}
      <div style={{ marginBottom: '24px' }}>
        <PortfolioCategoryChart positions={positions} totalCash={kpi?.total_cash || 0} />
      </div>

      <div className="dashboard-sections-grid">
        {/* Positions récentes */}
        <Card
          title="Positions Ouvertes"
          subtitle={`${positions.length} position(s) ouverte(s)`}
          actions={
            <Link to="/positions">
              <button className="btn btn-outline btn-sm">Voir toutes</button>
            </Link>
          }
          className="dashboard-positions-card"
        >
          {recentPositions.length > 0 ? (
            <Table
              columns={positionColumns}
              data={recentPositions}
              keyExtractor={(pos) => pos?.id || ''}
              compact
            />
          ) : (
            <div className="empty-state">
              <p>Aucune position ouverte</p>
              <Link to="/positions">
                <button className="btn btn-primary">Créer une position</button>
              </Link>
            </div>
          )}
        </Card>

        {/* Trades récents */}
        {trades.length > 0 && (
          <Card
            title="Trades Récents"
            subtitle={`${trades.length} trade(s) au total`}
            actions={
              <Link to="/trades">
                <button className="btn btn-outline btn-sm">Voir tous</button>
              </Link>
            }
            className="dashboard-trades-card"
          >
            <div className="trades-list">
              {trades.slice(0, 5).map((trade) => {
                const size = Number(trade?.size || trade?.quantity || 0)
                return (
                  <div key={trade?.id || Math.random()} className="trade-item">
                    <div className="trade-item-main">
                      <div className="trade-symbol-container">
                        <span className="trade-symbol">{trade?.symbol || trade?.all_asset_symbol || 'N/A'}</span>
                        {trade?.all_asset_yahoo_symbol && (
                          <span style={{ fontSize: '0.75rem', color: '#666', marginLeft: '6px' }}>
                            {trade.all_asset_yahoo_symbol}
                          </span>
                        )}
                      </div>
                      <Badge variant={trade?.side === 'BUY' ? 'success' : 'danger'}>
                        {trade?.side || 'N/A'}
                      </Badge>
                    </div>
                    <div className="trade-item-details">
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
                        <span style={{ fontSize: '0.9rem' }}>Exec: {formatCurrency(trade?.price || 0)}</span>
                        {trade?.yahoo_current_price && (
                          <span style={{ fontSize: '0.8rem', color: '#aaa' }}>
                            Actuel: {formatCurrency(trade.yahoo_current_price)}
                          </span>
                        )}
                      </div>
                      <span className="trade-size">
                        {isNaN(size) ? '0.0000' : size.toFixed(4)}
                      </span>
                      <span className="trade-date">
                        {formatDate(trade?.timestamp || trade?.executed_at || '', 'dd/MM HH:mm')}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          </Card>
        )}
      </div>
    </div>
  )
}
