/**
 * Page Dashboard - Vue d'ensemble du trading
 */
import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Card, Badge, Loading, Table } from '@components/common'
import { usePositions } from '@hooks/usePositions'
import { useTrades } from '@hooks/useTrades'
import { formatCurrency, formatPercent, formatDate } from '@utils/format'
import type { Position } from '@types'
import './Dashboard.css'

export default function Dashboard() {
  const { positions, loading: positionsLoading, summary } = usePositions({ status: 'OPEN' })
  const { trades, loading: tradesLoading, statistics } = useTrades()

  const stats = useMemo(() => {
    const totalPnl = positions.reduce((sum, pos) => sum + (pos.pnl || 0), 0)
    const totalValue = positions.reduce(
      (sum, pos) => sum + (pos.size * (pos.current_price || 0)),
      0
    )
    const winRate = statistics?.win_rate || 0

    return {
      totalPnl,
      totalValue,
      winRate,
      openPositions: positions.length,
      totalTrades: trades.length,
    }
  }, [positions, trades, statistics])

  if (positionsLoading || tradesLoading) {
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
      render: (pos: Position) => (
        <Link to={`/positions/${pos.id}`} className="link-symbol">
          {pos.asset.symbol}
        </Link>
      ),
    },
    {
      key: 'size',
      label: 'Taille',
      align: 'right' as const,
      render: (pos: Position) => pos.size.toFixed(4),
    },
    {
      key: 'entry_price',
      label: 'Prix d\'entrée',
      align: 'right' as const,
      render: (pos: Position) => formatCurrency(pos.entry_price),
    },
    {
      key: 'current_price',
      label: 'Prix actuel',
      align: 'right' as const,
      render: (pos: Position) => formatCurrency(pos.current_price),
    },
    {
      key: 'pnl',
      label: 'P&L',
      align: 'right' as const,
      render: (pos: Position) => (
        <Badge variant={(pos.pnl || 0) >= 0 ? 'success' : 'danger'}>
          {formatCurrency(pos.pnl)}
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

      {/* Statistiques principales */}
      <div className="dashboard-stats-grid">
        <Card className="stat-card stat-card-primary">
          <div className="stat-card-content">
            <h3 className="stat-card-label">P&L Total</h3>
            <p className={`stat-card-value ${stats.totalPnl >= 0 ? 'positive' : 'negative'}`}>
              {formatCurrency(stats.totalPnl)}
            </p>
            <Badge variant={stats.totalPnl >= 0 ? 'success' : 'danger'} className="stat-card-badge">
              {formatPercent((stats.totalPnl / (stats.totalValue || 1)) * 100)}
            </Badge>
          </div>
        </Card>

        <Card className="stat-card">
          <div className="stat-card-content">
            <h3 className="stat-card-label">Valeur Totale</h3>
            <p className="stat-card-value">{formatCurrency(stats.totalValue)}</p>
          </div>
        </Card>

        <Card className="stat-card">
          <div className="stat-card-content">
            <h3 className="stat-card-label">Taux de Réussite</h3>
            <p className="stat-card-value">{formatPercent(stats.winRate)}</p>
          </div>
        </Card>

        <Card className="stat-card">
          <div className="stat-card-content">
            <h3 className="stat-card-label">Positions Ouvertes</h3>
            <p className="stat-card-value">{stats.openPositions}</p>
            <Link to="/positions" className="stat-card-link">
              Voir toutes →
            </Link>
          </div>
        </Card>

        <Card className="stat-card">
          <div className="stat-card-content">
            <h3 className="stat-card-label">Total Trades</h3>
            <p className="stat-card-value">{stats.totalTrades}</p>
            <Link to="/trades" className="stat-card-link">
              Voir tous →
            </Link>
          </div>
        </Card>

        {summary && (
          <Card className="stat-card">
            <div className="stat-card-content">
              <h3 className="stat-card-label">Positions Fermées</h3>
              <p className="stat-card-value">{summary.closed_positions || 0}</p>
            </div>
          </Card>
        )}
      </div>

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
            keyExtractor={(pos) => pos.id}
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
            {trades.slice(0, 5).map((trade) => (
              <div key={trade.id} className="trade-item">
                <div className="trade-item-main">
                  <span className="trade-symbol">{trade.asset.symbol}</span>
                  <Badge variant={trade.side === 'BUY' ? 'success' : 'danger'}>
                    {trade.side}
                  </Badge>
                </div>
                <div className="trade-item-details">
                  <span>{formatCurrency(trade.price)}</span>
                  <span className="trade-size">{trade.size.toFixed(4)}</span>
                  <span className="trade-date">{formatDate(trade.timestamp, 'dd/MM HH:mm')}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}
