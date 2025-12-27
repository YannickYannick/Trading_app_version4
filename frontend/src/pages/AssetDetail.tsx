/**
 * Page Détail Asset - Affichage détaillé d'un asset
 */
import { useParams, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Card, Button, Loading, Badge } from '@components/common'
import { assetService } from '@services/assets'
import { formatCurrency, formatDate, formatPercent } from '@utils/format'
import type { Asset } from '@types'
import './AssetDetail.css'

export default function AssetDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [asset, setAsset] = useState<Asset | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchAsset() {
      if (!id) return

      try {
        setLoading(true)
        const data = await assetService.getAssetById(Number(id))
        setAsset(data)
        setError(null)
      } catch (err: any) {
        setError(err.response?.data?.error || err.message || 'Erreur lors du chargement')
      } finally {
        setLoading(false)
      }
    }

    fetchAsset()
  }, [id])

  if (loading) return <Loading text="Chargement de l'asset..." />
  if (error) return <div className="error-message">Erreur: {error}</div>
  if (!asset) return <div className="error-message">Asset non trouvé</div>

  return (
    <div className="asset-detail">
      <div className="asset-detail-header">
        <div>
          <h1>{asset.symbol}</h1>
          <p className="asset-detail-subtitle">{asset.name}</p>
        </div>
        <Button variant="outline" onClick={() => navigate('/assets')}>
          ← Retour
        </Button>
      </div>

      <div className="asset-detail-grid">
        <Card title="Informations Générales" className="asset-detail-card">
          <div className="asset-detail-info">
            <div className="info-row">
              <span className="info-label">Symbole:</span>
              <span className="info-value">{asset.symbol}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Nom:</span>
              <span className="info-value">{asset.name}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Plateforme:</span>
              <Badge variant="outline">{asset.platform}</Badge>
            </div>
            <div className="info-row">
              <span className="info-label">Type:</span>
              <span className="info-value">{asset.asset_type}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Tradable:</span>
              <Badge variant={asset.is_tradable ? 'success' : 'secondary'}>
                {asset.is_tradable ? 'Oui' : 'Non'}
              </Badge>
            </div>
          </div>
        </Card>

        <Card title="Prix" className="asset-detail-card">
          <div className="asset-detail-info">
            {asset.current_price && (
              <div className="info-row">
                <span className="info-label">Prix actuel:</span>
                <span className="info-value">{formatCurrency(asset.current_price, asset.currency)}</span>
              </div>
            )}
            <div className="info-row">
              <span className="info-label">Devise:</span>
              <span className="info-value">{asset.currency}</span>
            </div>
            {asset.price_updated_at && (
              <div className="info-row">
                <span className="info-label">Dernière mise à jour:</span>
                <span className="info-value">{formatDate(asset.price_updated_at)}</span>
              </div>
            )}
          </div>
        </Card>

        <Card title="Informations Supplémentaires" className="asset-detail-card">
          <div className="asset-detail-info">
            <div className="info-row">
              <span className="info-label">Marché:</span>
              <span className="info-value">{asset.market}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Exchange:</span>
              <span className="info-value">{asset.exchange}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Créé le:</span>
              <span className="info-value">{formatDate(asset.created_at)}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Dernière mise à jour:</span>
              <span className="info-value">{formatDate(asset.last_updated)}</span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}

