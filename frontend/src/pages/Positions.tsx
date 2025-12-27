/**
 * Page Positions - Liste et gestion des positions
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Card, Button, Table, Badge, Loading, Modal, Input } from '@components/common'
import { usePositions } from '@hooks/usePositions'
import { positionService } from '@services'
import { formatCurrency, formatPercent, formatDate } from '@utils/format'
import type { Position } from '@types'
import './Positions.css'

export default function Positions() {
  const [statusFilter, setStatusFilter] = useState<'OPEN' | 'CLOSED' | undefined>(undefined)
  const [selectedPosition, setSelectedPosition] = useState<Position | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [closePrice, setClosePrice] = useState('')
  const [isClosing, setIsClosing] = useState(false)

  const { positions, loading, error, summary, refetch } = usePositions({
    status: statusFilter,
  })

  const handleClosePosition = async (id: number) => {
    try {
      setIsClosing(true)
      const price = closePrice ? parseFloat(closePrice) : undefined
      await positionService.close(id, price)
      setIsModalOpen(false)
      setClosePrice('')
      refetch()
    } catch (err: any) {
      console.error('Erreur lors de la fermeture:', err)
      alert(err.error || 'Erreur lors de la fermeture de la position')
    } finally {
      setIsClosing(false)
    }
  }

  const columns = [
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
      key: 'side',
      label: 'Side',
      render: (pos: Position) => (
        <Badge variant={pos.side === 'BUY' ? 'success' : 'danger'}>
          {pos.side}
        </Badge>
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
    {
      key: 'pnl_percent',
      label: 'P&L %',
      align: 'right' as const,
      render: (pos: Position) => (
        <span className={pos.pnl_percent >= 0 ? 'positive' : 'negative'}>
          {formatPercent(pos.pnl_percent)}
        </span>
      ),
    },
    {
      key: 'status',
      label: 'Statut',
      render: (pos: Position) => (
        <Badge variant={pos.status === 'OPEN' ? 'success' : 'secondary'}>
          {pos.status === 'OPEN' ? 'Ouverte' : 'Fermée'}
        </Badge>
      ),
    },
    {
      key: 'opened_at',
      label: 'Ouverte le',
      render: (pos: Position) => formatDate(pos.opened_at, 'dd/MM/yyyy'),
    },
    {
      key: 'actions',
      label: 'Actions',
      render: (pos: Position) => (
        <div className="position-actions">
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              setSelectedPosition(pos)
              setIsModalOpen(true)
            }}
          >
            Détails
          </Button>
          {pos.status === 'OPEN' && (
            <Button
              size="sm"
              variant="danger"
              onClick={() => {
                setSelectedPosition(pos)
                setIsModalOpen(true)
              }}
            >
              Fermer
            </Button>
          )}
        </div>
      ),
    },
  ]

  if (loading) {
    return (
      <div className="positions-page">
        <Loading text="Chargement des positions..." />
      </div>
    )
  }

  if (error) {
    return (
      <div className="positions-page">
        <Card>
          <div className="error-state">
            <p>Erreur: {error}</p>
            <Button onClick={() => refetch()}>Réessayer</Button>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="positions-page">
      <div className="positions-header">
        <div>
          <h1 className="page-title">Positions</h1>
          {summary && (
            <p className="page-subtitle">
              {summary.open_positions} ouverte(s) • {summary.closed_positions} fermée(s)
            </p>
          )}
        </div>
        <div className="filter-buttons">
          <Button
            variant={statusFilter === undefined ? 'primary' : 'secondary'}
            onClick={() => setStatusFilter(undefined)}
          >
            Toutes
          </Button>
          <Button
            variant={statusFilter === 'OPEN' ? 'primary' : 'secondary'}
            onClick={() => setStatusFilter('OPEN')}
          >
            Ouvertes
          </Button>
          <Button
            variant={statusFilter === 'CLOSED' ? 'primary' : 'secondary'}
            onClick={() => setStatusFilter('CLOSED')}
          >
            Fermées
          </Button>
        </div>
      </div>

      {summary && (
        <div className="positions-summary">
          <Card className="summary-card">
            <h3>P&L Total</h3>
            <p className={`summary-value ${summary.total_pnl >= 0 ? 'positive' : 'negative'}`}>
              {formatCurrency(summary.total_pnl)}
            </p>
          </Card>
          <Card className="summary-card">
            <h3>Valeur Totale</h3>
            <p className="summary-value">{formatCurrency(summary.total_value)}</p>
          </Card>
        </div>
      )}

      <Card title={`${positions.length} position(s)`}>
        {positions.length > 0 ? (
          <Table
            columns={columns}
            data={positions}
            keyExtractor={(pos) => pos.id}
          />
        ) : (
          <div className="empty-state">
            <p>Aucune position {statusFilter ? statusFilter === 'OPEN' ? 'ouverte' : 'fermée' : ''}</p>
          </div>
        )}
      </Card>

      <Modal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          setSelectedPosition(null)
          setClosePrice('')
        }}
        title={selectedPosition ? `Position ${selectedPosition.asset.symbol}` : 'Détails'}
        size="md"
      >
        {selectedPosition && (
          <div className="position-details">
            <div className="detail-section">
              <h4>Informations Générales</h4>
              <div className="detail-grid">
                <div>
                  <span className="detail-label">Symbole</span>
                  <span className="detail-value">{selectedPosition.asset.symbol}</span>
                </div>
                <div>
                  <span className="detail-label">Nom</span>
                  <span className="detail-value">{selectedPosition.asset.name}</span>
                </div>
                <div>
                  <span className="detail-label">Statut</span>
                  <Badge variant={selectedPosition.status === 'OPEN' ? 'success' : 'secondary'}>
                    {selectedPosition.status === 'OPEN' ? 'Ouverte' : 'Fermée'}
                  </Badge>
                </div>
                <div>
                  <span className="detail-label">Side</span>
                  <Badge variant={selectedPosition.side === 'BUY' ? 'success' : 'danger'}>
                    {selectedPosition.side}
                  </Badge>
                </div>
              </div>
            </div>

            <div className="detail-section">
              <h4>Prix</h4>
              <div className="detail-grid">
                <div>
                  <span className="detail-label">Prix d'entrée</span>
                  <span className="detail-value">{formatCurrency(selectedPosition.entry_price)}</span>
                </div>
                <div>
                  <span className="detail-label">Prix actuel</span>
                  <span className="detail-value">{formatCurrency(selectedPosition.current_price)}</span>
                </div>
                {selectedPosition.status === 'CLOSED' && selectedPosition.closed_at && (
                  <div>
                    <span className="detail-label">Fermée le</span>
                    <span className="detail-value">{formatDate(selectedPosition.closed_at)}</span>
                  </div>
                )}
              </div>
            </div>

            <div className="detail-section">
              <h4>P&L</h4>
              <div className="detail-grid">
                <div>
                  <span className="detail-label">P&L</span>
                  <span className={`detail-value ${selectedPosition.pnl >= 0 ? 'positive' : 'negative'}`}>
                    {formatCurrency(selectedPosition.pnl)}
                  </span>
                </div>
                <div>
                  <span className="detail-label">P&L %</span>
                  <span className={`detail-value ${selectedPosition.pnl_percent >= 0 ? 'positive' : 'negative'}`}>
                    {formatPercent(selectedPosition.pnl_percent)}
                  </span>
                </div>
              </div>
            </div>

            {selectedPosition.status === 'OPEN' && (
              <div className="detail-section">
                <h4>Fermer la position</h4>
                <div className="close-position-form">
                  <Input
                    label="Prix de fermeture (optionnel)"
                    type="number"
                    value={closePrice}
                    onChange={(e) => setClosePrice(e.target.value)}
                    placeholder="Laissez vide pour prix actuel"
                  />
                  <Button
                    variant="danger"
                    onClick={() => handleClosePosition(selectedPosition.id)}
                    isLoading={isClosing}
                    fullWidth
                  >
                    Fermer la position
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
