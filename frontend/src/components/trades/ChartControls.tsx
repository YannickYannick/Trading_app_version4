/**
 * Contrôles pour le graphique des trades
 */
import { useState, useEffect } from 'react'
import { Button } from '@components/common'
import { assetService } from '@services/assets'
import type { AllAsset } from '@types'
import './TradesChart.css'

export interface ChartControlsProps {
  selectedAssets: number[]
  viewMode: 'global' | 'per_asset'
  onSelectedAssetsChange: (assets: number[]) => void
  onViewModeChange: (mode: 'global' | 'per_asset') => void
  allAssetsInTrades: number[] // IDs des AllAssets présents dans les trades
}

const ChartControls: React.FC<ChartControlsProps> = ({
  selectedAssets,
  viewMode,
  onSelectedAssetsChange,
  onViewModeChange,
  allAssetsInTrades,
}) => {
  const [availableAssets, setAvailableAssets] = useState<AllAsset[]>([])
  const [loading, setLoading] = useState(false)

  // Charger les informations des AllAssets disponibles
  useEffect(() => {
    const loadAssets = async () => {
      if (allAssetsInTrades.length === 0) return

      setLoading(true)
      try {
        const assets: AllAsset[] = []
        
        // Charger les assets en parallèle
        const assetPromises = allAssetsInTrades.map(async (assetId) => {
          try {
            const asset = await assetService.getAllAssetById(assetId)
            return asset
          } catch (err) {
            console.error(`Error loading asset ${assetId}:`, err)
            return null
          }
        })

        const loadedAssets = await Promise.all(assetPromises)
        setAvailableAssets(loadedAssets.filter((asset): asset is AllAsset => asset !== null))
      } catch (err) {
        console.error('Error loading assets:', err)
      } finally {
        setLoading(false)
      }
    }

    loadAssets()
  }, [allAssetsInTrades])

  const handleAssetToggle = (assetId: number) => {
    if (selectedAssets.includes(assetId)) {
      onSelectedAssetsChange(selectedAssets.filter((id) => id !== assetId))
    } else {
      onSelectedAssetsChange([...selectedAssets, assetId])
    }
  }

  const handleSelectAll = () => {
    if (selectedAssets.length === allAssetsInTrades.length) {
      onSelectedAssetsChange([])
    } else {
      onSelectedAssetsChange([...allAssetsInTrades])
    }
  }

  return (
    <div className="chart-controls">
      <div className="controls-section">
        <h3>Mode d'affichage</h3>
        <div className="view-mode-buttons">
          <Button
            variant={viewMode === 'global' ? 'primary' : 'outline'}
            onClick={() => onViewModeChange('global')}
            size="sm"
          >
            Vue globale
          </Button>
          <Button
            variant={viewMode === 'per_asset' ? 'primary' : 'outline'}
            onClick={() => onViewModeChange('per_asset')}
            size="sm"
          >
            Par asset
          </Button>
        </div>
      </div>

      <div className="controls-section">
        <div className="assets-header">
          <h3>AllAssets à afficher</h3>
          <Button
            variant="outline"
            onClick={handleSelectAll}
            size="sm"
          >
            {selectedAssets.length === allAssetsInTrades.length ? 'Tout désélectionner' : 'Tout sélectionner'}
          </Button>
        </div>
        {loading ? (
          <p>Chargement...</p>
        ) : availableAssets.length > 0 ? (
          <div className="assets-list">
            {availableAssets.map((asset) => (
              <label key={asset.id} className="asset-checkbox">
                <input
                  type="checkbox"
                  checked={selectedAssets.includes(asset.id)}
                  onChange={() => handleAssetToggle(asset.id)}
                />
                <span className="asset-label">
                  <strong>{asset.symbol}</strong>
                  {asset.name && <span className="asset-name"> - {asset.name}</span>}
                  {asset.symbole_yahoo && (
                    <span className="asset-yahoo"> ({asset.symbole_yahoo})</span>
                  )}
                </span>
              </label>
            ))}
          </div>
        ) : (
          <p className="no-assets">Aucun asset disponible</p>
        )}
      </div>

      {selectedAssets.length > 0 && (
        <div className="controls-info">
          <p>
            {selectedAssets.length} asset(s) sélectionné(s) - {availableAssets.filter((a) => selectedAssets.includes(a.id)).length} avec historique
          </p>
        </div>
      )}
    </div>
  )
}

export default ChartControls

