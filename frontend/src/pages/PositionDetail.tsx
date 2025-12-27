/**
 * Page Détail Position - Affichage détaillé d'une position
 */
import { useParams, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Card, Button, Loading, Badge } from '@components/common'
import { positionService } from '@services/positions'
import { formatCurrency, formatDate, formatPercent } from '@utils/format'
import type { Position } from '@types'
import './PositionDetail.css'

export default function PositionDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [position, setPosition] = useState<Position | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchPosition() {
      if (!id) return

      try {
        setLoading(true)
        const data = await positionService.getById(Number(id))
        setPosition(data)
        setError(null)
      } catch (err: any) {
        setError(err.response?.data?.error || err.message || 'Erreur lors du chargement')
      } finally {
        setLoading(false)
      }
    }

    fetchPosition()
  }, [id])

  const handleClose = async () => {
    if (!position || position.status !== 'OPEN') return

    if (!window.confirm('Êtes-vous sûr de vouloir fermer cette position ?')) {
      return
    }

    try {
      await positionService.close(position.id)
      navigate('/positions')
    } catch (err: any) {
      alert(err.response?.data?.error || err.message || 'Erreur lors de la fermeture')
    }
  }

  if (loading) return <Loading text="Chargement de la position..." />
  if (error) return <div className="error-message">Erreur: {error}</div>
  if (!position) return <div className="error-message">Position non trouvée</div>

  const pnlPercent = position.entry_price > 0 && position.size > 0
    ? ((position.pnl / (position.size * position.entry_price)) * 100)
    : position.pnl_percent || 0

  return (
    <div className="position-detail">
      <div className="position-detail-header">
        <div>
          <h1>Position {position.asset.symbol}</h1>
          <p className="position-detail-subtitle">{position.asset.name}</p>
        </div>
        <div className="position-detail-actions">
          <Button variant="outline" onClick={() => navigate('/positions')}>
            ← Retour
          </Button>
          {position.status === 'OPEN' && (
            <Button variant="danger" onClick={handleClose}>
              Fermer la position
            </Button>
          )}
        </div>
      </div>

      <div className="position-detail-grid">
        <Card title="Informations Générales" className="position-detail-card">
          <div className="position-detail-info">
            <div className="info-row">
              <span className="info-label">Symbole:</span>
              <span className="info-value">{position.asset.symbol}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Nom:</span>
              <span className="info-value">{position.asset.name}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Statut:</span>
              <Badge variant={position.status === 'OPEN' ? 'success' : 'secondary'}>
                {position.status}
              </Badge>
            </div>
            <div className="info-row">
              <span className="info-label">Side:</span>
              <Badge variant={position.side === 'BUY' ? 'success' : 'danger'}>
                {position.side}
              </Badge>
            </div>
            <div className="info-row">
              <span className="info-label">Ouvert le:</span>
              <span className="info-value">{formatDate(position.opened_at)}</span>
            </div>
            {position.closed_at && (
              <div className="info-row">
                <span className="info-label">Fermé le:</span>
                <span className="info-value">{formatDate(position.closed_at)}</span>
              </div>
            )}
          </div>
        </Card>

        <Card title="Prix" className="position-detail-card">
          <div className="position-detail-info">
            <div className="info-row">
              <span className="info-label">Prix d'entrée:</span>
              <span className="info-value">{formatCurrency(position.entry_price, position.asset.currency)}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Prix actuel:</span>
              <span className="info-value">{formatCurrency(position.current_price, position.asset.currency)}</span>
            </div>
            {position.exit_price && (
              <div className="info-row">
                <span className="info-label">Prix de sortie:</span>
                <span className="info-value">{formatCurrency(position.exit_price, position.asset.currency)}</span>
              </div>
            )}
            {position.stop_loss && (
              <div className="info-row">
                <span className="info-label">Stop Loss:</span>
                <span className="info-value">{formatCurrency(position.stop_loss, position.asset.currency)}</span>
              </div>
            )}
            {position.take_profit && (
              <div className="info-row">
                <span className="info-label">Take Profit:</span>
                <span className="info-value">{formatCurrency(position.take_profit, position.asset.currency)}</span>
              </div>
            )}
          </div>
        </Card>

        <Card title="Taille" className="position-detail-card">
          <div className="position-detail-info">
            <div className="info-row">
              <span className="info-label">Taille:</span>
              <span className="info-value">{position.size.toFixed(4)}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Valeur:</span>
              <span className="info-value">
                {formatCurrency(position.size * position.current_price, position.asset.currency)}
              </span>
            </div>
            <div className="info-row">
              <span className="info-label">Valeur initiale:</span>
              <span className="info-value">
                {formatCurrency(position.size * position.entry_price, position.asset.currency)}
              </span>
            </div>
          </div>
        </Card>

        <Card title="P&L" className="position-detail-card">
          <div className="position-detail-info">
            <div className="info-row">
              <span className="info-label">P&L:</span>
              <Badge variant={position.pnl >= 0 ? 'success' : 'danger'} className="pnl-badge">
                {formatCurrency(position.pnl, position.asset.currency)}
              </Badge>
            </div>
            <div className="info-row">
              <span className="info-label">P&L %:</span>
              <Badge variant={pnlPercent >= 0 ? 'success' : 'danger'} className="pnl-badge">
                {formatPercent(pnlPercent)}
              </Badge>
            </div>
            {position.fees && (
              <div className="info-row">
                <span className="info-label">Frais:</span>
                <span className="info-value">{formatCurrency(position.fees, position.asset.currency)}</span>
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}

