/**
 * Contrôles pour le graphique des trades
 */
import { useMemo } from 'react'
import { Button } from '@components/common'
import type { AllAsset } from '@types'
import './TradesChart.css'

export interface ChartControlsProps {
  selectedAssets: number[]
  viewMode: 'global' | 'per_asset'
  onSelectedAssetsChange: (assets: number[]) => void
  onViewModeChange: (mode: 'global' | 'per_asset') => void
  allAssetsInTrades: number[] // IDs des AllAssets présents dans les trades
  allAssetsMap: Map<number, AllAsset> // Map des AllAssets déjà chargés depuis les trades
}

const ChartControls: React.FC<ChartControlsProps> = ({
  selectedAssets,
  viewMode,
  onSelectedAssetsChange,
  onViewModeChange,
  allAssetsInTrades,
  allAssetsMap,
}) => {
  // Utiliser directement la Map depuis le parent au lieu de recharger via API
  // Cela évite les rechargements inutiles et les disparitions de la liste
  const availableAssets = useMemo(() => {
    return allAssetsInTrades
      .map((assetId) => allAssetsMap.get(assetId))
      .filter((asset): asset is AllAsset => asset !== undefined)
      .sort((a, b) => {
        // Trier par symbole pour une meilleure UX
        return (a.symbol || '').localeCompare(b.symbol || '')
      })
  }, [allAssetsInTrades, allAssetsMap])

  const handleAssetToggle = (assetId: number) => {
    // Prévenir tout comportement par défaut (comme le submit de formulaire)
    // ... (pas besoin de event ici, mais on peut ajouter preventDefault si nécessaire)
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
        {availableAssets.length > 0 ? (
          <div className="assets-list">
            {availableAssets.map((asset) => {
              const isSelected = selectedAssets.includes(asset.id)
              const hasHistory = asset.price_history_days && asset.price_history_days > 0
              
              return (
                <label key={asset.id} className="asset-checkbox">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      handleAssetToggle(asset.id)
                    }}
                  />
                  <span className="asset-label">
                    <strong className={isSelected ? 'selected' : ''}>{asset.symbol}</strong>
                    {asset.name && <span className="asset-name"> - {asset.name}</span>}
                    {asset.symbole_yahoo && (
                      <span className="asset-yahoo"> ({asset.symbole_yahoo})</span>
                    )}
                    {hasHistory && (
                      <span className="asset-history-badge" title={`${asset.price_history_days} jours d'historique`}>
                        📊
                      </span>
                    )}
                  </span>
                </label>
              )
            })}
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

