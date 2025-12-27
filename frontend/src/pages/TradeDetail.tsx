/**
 * Page Détail Trade - Affichage détaillé d'un trade
 */
import { useParams, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Card, Button, Loading, Badge } from '@components/common'
import { tradeService } from '@services/trades'
import { formatCurrency, formatDate } from '@utils/format'
import type { Trade } from '@types'
import './TradeDetail.css'

export default function TradeDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [trade, setTrade] = useState<Trade | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchTrade() {
      if (!id) return

      try {
        setLoading(true)
        const data = await tradeService.getById(Number(id))
        setTrade(data)
        setError(null)
      } catch (err: any) {
        setError(err.response?.data?.error || err.message || 'Erreur lors du chargement')
      } finally {
        setLoading(false)
      }
    }

    fetchTrade()
  }, [id])

  if (loading) return <Loading text="Chargement du trade..." />
  if (error) return <div className="error-message">Erreur: {error}</div>
  if (!trade) return <div className="error-message">Trade non trouvé</div>

  return (
    <div className="trade-detail">
      <div className="trade-detail-header">
        <div>
          <h1>Trade {trade.asset.symbol}</h1>
          <p className="trade-detail-subtitle">{trade.asset.name}</p>
        </div>
        <Button variant="outline" onClick={() => navigate('/trades')}>
          ← Retour
        </Button>
      </div>

      <div className="trade-detail-grid">
        <Card title="Informations Générales" className="trade-detail-card">
          <div className="trade-detail-info">
            <div className="info-row">
              <span className="info-label">Symbole:</span>
              <span className="info-value">{trade.asset.symbol}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Nom:</span>
              <span className="info-value">{trade.asset.name}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Side:</span>
              <Badge variant={trade.side === 'BUY' ? 'success' : 'danger'}>
                {trade.side}
              </Badge>
            </div>
            <div className="info-row">
              <span className="info-label">Date:</span>
              <span className="info-value">{formatDate(trade.timestamp, 'dd/MM/yyyy HH:mm:ss')}</span>
            </div>
            {trade.broker && (
              <div className="info-row">
                <span className="info-label">Broker:</span>
                <span className="info-value">{trade.broker.name}</span>
              </div>
            )}
          </div>
        </Card>

        <Card title="Détails du Trade" className="trade-detail-card">
          <div className="trade-detail-info">
            <div className="info-row">
              <span className="info-label">Taille:</span>
              <span className="info-value">{trade.size.toFixed(4)}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Prix:</span>
              <span className="info-value">{formatCurrency(trade.price, trade.asset.currency)}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Valeur:</span>
              <span className="info-value">
                {formatCurrency(trade.size * trade.price, trade.asset.currency)}
              </span>
            </div>
            {trade.fees && (
              <div className="info-row">
                <span className="info-label">Frais:</span>
                <span className="info-value">{formatCurrency(trade.fees, trade.asset.currency)}</span>
              </div>
            )}
            {trade.pnl !== null && trade.pnl !== undefined && (
              <div className="info-row">
                <span className="info-label">P&L:</span>
                <Badge variant={trade.pnl >= 0 ? 'success' : 'danger'}>
                  {formatCurrency(trade.pnl, trade.asset.currency)}
                </Badge>
              </div>
            )}
          </div>
        </Card>

        {trade.position && (
          <Card title="Position Associée" className="trade-detail-card">
            <div className="trade-detail-info">
              <div className="info-row">
                <span className="info-label">Position ID:</span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => navigate(`/positions/${trade.position?.id}`)}
                >
                  Voir Position #{trade.position.id}
                </Button>
              </div>
              <div className="info-row">
                <span className="info-label">Statut:</span>
                <Badge variant={trade.position.status === 'OPEN' ? 'success' : 'secondary'}>
                  {trade.position.status}
                </Badge>
              </div>
            </div>
          </Card>
        )}
      </div>
    </div>
  )
}

