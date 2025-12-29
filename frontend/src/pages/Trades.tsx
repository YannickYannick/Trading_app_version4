/**
 * Page Trades - Historique des trades
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Card, Button, Table, Badge, Loading, Input } from '@components/common'
import { useTrades } from '@hooks/useTrades'
import { formatCurrency, formatDate } from '@utils/format'
import type { Trade } from '@types'
import './Trades.css'

export default function Trades() {
  const [sideFilter, setSideFilter] = useState<'BUY' | 'SELL' | undefined>(undefined)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  
  const { trades, loading, error, statistics, total } = useTrades({
    side: sideFilter,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  })

  const columns = [
    {
      key: 'timestamp',
      label: 'Date',
      render: (trade: Trade) => formatDate(trade.timestamp || trade.executed_at || '', 'dd/MM/yyyy HH:mm'),
    },
    {
      key: 'symbol',
      label: 'Symbole',
      render: (trade: Trade) => (
        <Link to={`/trades/${trade.id}`} className="trade-symbol link-symbol">
          {trade.asset?.symbol || 'N/A'}
        </Link>
      ),
    },
    {
      key: 'side',
      label: 'Side',
      render: (trade: Trade) => (
        <Badge variant={trade.side === 'BUY' ? 'success' : 'danger'}>
          {trade.side}
        </Badge>
      ),
    },
    {
      key: 'size',
      label: 'Taille',
      align: 'right' as const,
      render: (trade: Trade) => (trade.size || trade.quantity || 0).toFixed(4),
    },
    {
      key: 'price',
      label: 'Prix',
      align: 'right' as const,
      render: (trade: Trade) => formatCurrency(trade.price || 0),
    },
    {
      key: 'total',
      label: 'Total',
      align: 'right' as const,
      render: (trade: Trade) => formatCurrency((trade.size || trade.quantity || 0) * (trade.price || 0)),
    },
    {
      key: 'fees',
      label: 'Frais',
      align: 'right' as const,
      render: (trade: Trade) => formatCurrency(trade.fees || 0),
    },
  ]

  if (loading) {
    return (
      <div className="trades-page">
        <Loading text="Chargement des trades..." />
      </div>
    )
  }

  if (error) {
    return (
      <div className="trades-page">
        <Card>
          <div className="error-state">
            <p>Erreur: {error}</p>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="trades-page">
      <div className="trades-header">
        <div>
          <h1 className="page-title">Trades</h1>
          <p className="page-subtitle">
            {total} trade(s) au total
            {statistics && (
              <>
                {' • '}
                <span className={statistics.win_rate >= 50 ? 'positive' : 'negative'}>
                  {statistics.win_rate.toFixed(1)}% de réussite
                </span>
              </>
            )}
          </p>
        </div>
        <div className="filter-buttons">
          <Button
            variant={sideFilter === undefined ? 'primary' : 'secondary'}
            onClick={() => setSideFilter(undefined)}
          >
            Tous
          </Button>
          <Button
            variant={sideFilter === 'BUY' ? 'primary' : 'secondary'}
            onClick={() => setSideFilter('BUY')}
          >
            Achat
          </Button>
          <Button
            variant={sideFilter === 'SELL' ? 'primary' : 'secondary'}
            onClick={() => setSideFilter('SELL')}
          >
            Vente
          </Button>
        </div>
      </div>

      {statistics && (
        <div className="trades-statistics">
          <Card className="stat-card">
            <h3>Volume Total</h3>
            <p className="stat-value">{formatCurrency(statistics.total_volume)}</p>
          </Card>
          <Card className="stat-card">
            <h3>Frais Totaux</h3>
            <p className="stat-value">{formatCurrency(statistics.total_fees)}</p>
          </Card>
          <Card className="stat-card">
            <h3>Achats</h3>
            <p className="stat-value">{statistics.buy_trades}</p>
          </Card>
          <Card className="stat-card">
            <h3>Ventes</h3>
            <p className="stat-value">{statistics.sell_trades}</p>
          </Card>
        </div>
      )}

      <Card
        title="Filtres de date"
        className="filters-card"
      >
        <div className="date-filters">
          <Input
            label="Date de début"
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
          />
          <Input
            label="Date de fin"
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
          />
          {(dateFrom || dateTo) && (
            <Button
              variant="outline"
              onClick={() => {
                setDateFrom('')
                setDateTo('')
              }}
            >
              Réinitialiser
            </Button>
          )}
        </div>
      </Card>

      <Card title={`${trades.length} trade(s)`}>
        {trades.length > 0 ? (
          <Table
            columns={columns}
            data={trades}
            keyExtractor={(trade) => trade.id}
          />
        ) : (
          <div className="empty-state">
            <p>Aucun trade {sideFilter ? sideFilter === 'BUY' ? 'd\'achat' : 'de vente' : ''}</p>
          </div>
        )}
      </Card>
    </div>
  )
}
