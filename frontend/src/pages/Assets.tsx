/**
 * Page Assets - Liste et recherche des assets
 */
import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Card, Button, Table, Badge, Loading, Input } from '@components/common'
import { useAssets } from '@hooks/useAssets'
import { formatCurrency } from '@utils/format'
import type { Asset } from '@types'
import './Assets.css'

export default function Assets() {
  const [search, setSearch] = useState('')
  const [platformFilter, setPlatformFilter] = useState<'SAXO' | 'BINANCE' | 'IB' | 'OTHER' | undefined>(undefined)
  const [assetTypeFilter, setAssetTypeFilter] = useState<string>('')

  const { assets, loading, error, total } = useAssets({
    platform: platformFilter,
    search: search || undefined,
    asset_type: assetTypeFilter || undefined,
  })

  const columns = [
    {
      key: 'symbol',
      label: 'Symbole',
      render: (asset: Asset) => (
        <Link to={`/assets/${asset.id}`} className="asset-symbol link-symbol">
          {asset.symbol}
        </Link>
      ),
    },
    {
      key: 'name',
      label: 'Nom',
      render: (asset: Asset) => (
        <span className="asset-name">{asset.name}</span>
      ),
    },
    {
      key: 'platform',
      label: 'Plateforme',
      render: (asset: Asset) => (
        <Badge variant="outline">{asset.platform}</Badge>
      ),
    },
    {
      key: 'asset_type',
      label: 'Type',
      render: (asset: Asset) => (
        <span className="asset-type">{asset.asset_type}</span>
      ),
    },
    {
      key: 'current_price',
      label: 'Prix',
      align: 'right' as const,
      render: (asset: Asset) => (
        <span className="asset-price">
          {asset.current_price ? formatCurrency(asset.current_price) : '-'}
        </span>
      ),
    },
    {
      key: 'currency',
      label: 'Devise',
      render: (asset: Asset) => asset.currency,
    },
    {
      key: 'exchange',
      label: 'Exchange',
      render: (asset: Asset) => asset.exchange || '-',
    },
    {
      key: 'is_tradable',
      label: 'Tradable',
      render: (asset: Asset) => (
        <Badge variant={asset.is_tradable ? 'success' : 'secondary'}>
          {asset.is_tradable ? 'Oui' : 'Non'}
        </Badge>
      ),
    },
  ]

  // Types d'assets uniques pour le filtre
  const assetTypes = useMemo(() => {
    const types = new Set<string>()
    assets.forEach((asset) => {
      if (asset.asset_type) {
        types.add(asset.asset_type)
      }
    })
    return Array.from(types).sort()
  }, [assets])

  if (loading) {
    return (
      <div className="assets-page">
        <Loading text="Chargement des assets..." />
      </div>
    )
  }

  if (error) {
    return (
      <div className="assets-page">
        <Card>
          <div className="error-state">
            <p>Erreur: {error}</p>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="assets-page">
      <div className="assets-header">
        <div>
          <h1 className="page-title">Assets</h1>
          <p className="page-subtitle">{total} asset(s) disponible(s)</p>
        </div>
      </div>

      <Card title="Filtres" className="filters-card">
        <div className="filters-grid">
          <Input
            label="Rechercher"
            placeholder="Symbole, nom..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            fullWidth
          />
          <div className="filter-group">
            <label className="filter-label">Plateforme</label>
            <div className="filter-buttons">
              <Button
                variant={platformFilter === undefined ? 'primary' : 'secondary'}
                size="sm"
                onClick={() => setPlatformFilter(undefined)}
              >
                Toutes
              </Button>
              <Button
                variant={platformFilter === 'SAXO' ? 'primary' : 'secondary'}
                size="sm"
                onClick={() => setPlatformFilter('SAXO')}
              >
                Saxo
              </Button>
              <Button
                variant={platformFilter === 'BINANCE' ? 'primary' : 'secondary'}
                size="sm"
                onClick={() => setPlatformFilter('BINANCE')}
              >
                Binance
              </Button>
              <Button
                variant={platformFilter === 'IB' ? 'primary' : 'secondary'}
                size="sm"
                onClick={() => setPlatformFilter('IB')}
              >
                IB
              </Button>
            </div>
          </div>
          {assetTypes.length > 0 && (
            <div className="filter-group">
              <label className="filter-label">Type d'asset</label>
              <select
                className="filter-select"
                value={assetTypeFilter}
                onChange={(e) => setAssetTypeFilter(e.target.value)}
              >
                <option value="">Tous</option>
                {assetTypes.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </Card>

      <Card title={`${assets.length} asset(s)`}>
        {assets.length > 0 ? (
          <Table
            columns={columns}
            data={assets}
            keyExtractor={(asset) => asset.id}
          />
        ) : (
          <div className="empty-state">
            <p>Aucun asset trouvé</p>
            {(search || platformFilter || assetTypeFilter) && (
              <Button
                variant="outline"
                onClick={() => {
                  setSearch('')
                  setPlatformFilter(undefined)
                  setAssetTypeFilter('')
                }}
              >
                Réinitialiser les filtres
              </Button>
            )}
          </div>
        )}
      </Card>
    </div>
  )
}
