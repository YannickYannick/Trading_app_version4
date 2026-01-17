/**
 * Page Assets - Liste et recherche des assets avec vue DataTree
 */
import { useState, useMemo, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { Card, Button, Table, Badge, Loading, Input } from '@components/common'
import { useAssets } from '@hooks/useAssets'
import SyncAssetsModal from '@components/assets/SyncAssetsModal'
import DataTreeTable from '@components/assets/DataTreeTable'
import { assetService } from '@services/assets'
import { positionService } from '@services/positions'
import { orderService } from '@services/orders'
import { formatCurrency } from '@utils/format'
import { ChevronDown, ChevronRight, List, GitBranch, RefreshCw, ToggleLeft, ToggleRight } from 'lucide-react'
import type { Asset, AssetWithChildren } from '@types'
import './Assets.css'

type TabType = 'list' | 'overview'

export default function Assets() {
  // État pour les onglets
  const [activeTab, setActiveTab] = useState<TabType>('list')

  // État pour la vue Liste
  const [search, setSearch] = useState('')
  const [platformFilter, setPlatformFilter] = useState<'SAXO' | 'BINANCE' | 'IB' | 'OTHER' | undefined>(undefined)
  const [assetTypeFilter, setAssetTypeFilter] = useState<string>('')
  const [isSyncModalOpen, setIsSyncModalOpen] = useState(false)
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set())
  const [groupByType, setGroupByType] = useState(true) // Toggle pour le regroupement par type
  const [showAllAssets, setShowAllAssets] = useState(false) // Toggle pour afficher tous les assets ou seulement ceux suivis

  // État pour la vue DataTree (Vue d'ensemble)
  const [overviewData, setOverviewData] = useState<AssetWithChildren[]>([])
  const [overviewLoading, setOverviewLoading] = useState(false)
  const [overviewError, setOverviewError] = useState<string | null>(null)
  const [includeEmptyAssets, setIncludeEmptyAssets] = useState(true)

  const { assets, loading, error, total, refetch } = useAssets({
    platform: platformFilter,
    search: search || undefined,
    asset_type: assetTypeFilter || undefined,
    is_tracked: showAllAssets ? undefined : true,
  })

  // Gérer l'ajout/retrait des favoris
  const handleToggleFavorite = async (asset: Asset) => {
    try {
      await assetService.updateAsset(asset.id, {
        is_favorite: !asset.is_favorite
      })
      // Rafraîchir la liste
      refetch()
    } catch (err: any) {
      console.error('Erreur lors de la mise à jour du favori:', err)
      alert("Erreur lors de la mise à jour des favoris")
    }
  }

  const columns = [
    {
      key: 'symbol',
      label: 'Symbole',
      align: 'center' as const,
      render: (_value: any, row: Asset) => (
        <Link to={`/assets/${row?.id || ''}`} className="asset-symbol link-symbol">
          {row?.symbol || 'N/A'}
        </Link>
      ),
    },
    {
      key: 'name',
      label: 'Nom',
      align: 'center' as const,
      render: (_value: any, row: Asset) => (
        <span className="asset-name">{row?.name || 'N/A'}</span>
      ),
    },
    {
      key: 'platform',
      label: 'Plateforme',
      align: 'center' as const,
      render: (_value: any, row: Asset) => (
        <Badge variant="outline">{row?.platform || 'N/A'}</Badge>
      ),
    },
    {
      key: 'asset_type',
      label: 'Type',
      align: 'center' as const,
      render: (_value: any, row: Asset) => (
        <span className="asset-type">{row?.asset_type || 'N/A'}</span>
      ),
    },
    {
      key: 'current_price',
      label: 'Prix',
      align: 'center' as const,
      render: (_value: any, row: Asset) => (
        <span className="asset-price">
          {row?.current_price != null ? formatCurrency(row.current_price) : '-'}
        </span>
      ),
    },
    {
      key: 'currency',
      label: 'Devise',
      align: 'center' as const,
      render: (_value: any, row: Asset) => row?.currency || '-',
    },
    {
      key: 'exchange',
      label: 'Exchange',
      align: 'center' as const,
      render: (_value: any, row: Asset) => row?.exchange || '-',
    },
    {
      key: 'is_tradable',
      label: 'Tradable',
      align: 'center' as const,
      render: (_value: any, row: Asset) => (
        <Badge variant={row?.is_tradable ? 'success' : 'secondary'}>
          {row?.is_tradable ? 'Oui' : 'Non'}
        </Badge>
      ),
    },
    {
      key: 'actions',
      label: 'Actions',
      align: 'center' as const,
      render: (_value: any, row: Asset) => (
        <div className="action-buttons">
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation()
              handleToggleFavorite(row)
            }}
            title={row?.is_favorite ? "Retirer des favoris" : "Ajouter aux favoris"}
          >
            <i className={`fa${row?.is_favorite ? 's' : 'r'} fa-star ${row?.is_favorite ? 'text-warning' : 'text-muted'}`}></i>
          </Button>
        </div>
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

  // Grouper les assets par type
  const groupedAssets = useMemo(() => {
    const groups: Record<string, Asset[]> = {}

    assets.forEach((asset) => {
      const type = asset.asset_type || 'Sans type'
      if (!groups[type]) {
        groups[type] = []
      }
      groups[type].push(asset)
    })

    // Trier les groupes par nom de type
    const sortedGroups: Record<string, Asset[]> = {}
    Object.keys(groups)
      .sort()
      .forEach((type) => {
        sortedGroups[type] = groups[type]
      })

    return sortedGroups
  }, [assets])

  // Initialiser tous les groupes comme ouverts au premier chargement
  useEffect(() => {
    if (expandedGroups.size === 0 && Object.keys(groupedAssets).length > 0) {
      setExpandedGroups(new Set(Object.keys(groupedAssets)))
    }
  }, [groupedAssets])

  // Toggle l'état d'un groupe
  const toggleGroup = (type: string) => {
    setExpandedGroups((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(type)) {
        newSet.delete(type)
      } else {
        newSet.add(type)
      }
      return newSet
    })
  }

  // Toggle tous les groupes
  const toggleAllGroups = () => {
    if (expandedGroups.size === Object.keys(groupedAssets).length) {
      setExpandedGroups(new Set())
    } else {
      setExpandedGroups(new Set(Object.keys(groupedAssets)))
    }
  }

  // ============================================
  // Fonctions pour la vue DataTree (Vue d'ensemble)
  // ============================================

  // Charger les données DataTree
  const loadOverviewData = useCallback(async () => {
    setOverviewLoading(true)
    setOverviewError(null)
    try {
      const data = await assetService.getAssetsOverview(includeEmptyAssets)
      console.log('DataTree chargé:', data.length, 'assets')
      setOverviewData(data)
    } catch (err: any) {
      console.error('Erreur chargement DataTree:', err)
      const errorMessage = err.response?.data?.error || err.message || 'Erreur lors du chargement des données'
      setOverviewError(errorMessage)
      // Si c'est une erreur 401, suggérer de se reconnecter
      if (err.response?.status === 401) {
        setOverviewError('Vous devez être connecté pour voir cette vue. Veuillez vous reconnecter.')
      }
    } finally {
      setOverviewLoading(false)
    }
  }, [includeEmptyAssets])

  // Charger les données quand on passe à l'onglet Vue d'ensemble
  useEffect(() => {
    if (activeTab === 'overview') {
      loadOverviewData()
    }
  }, [activeTab, loadOverviewData])

  // Actions sur les positions
  const handleSellPosition = async (positionId: number) => {
    if (!confirm('Voulez-vous vendre cette position ?')) return
    try {
      await positionService.close(positionId)
      alert('Position vendue avec succès')
      loadOverviewData()
    } catch (err: any) {
      alert(`Erreur: ${err.message}`)
    }
  }

  const handleClosePosition = async (positionId: number) => {
    if (!confirm('Voulez-vous fermer cette position ?')) return
    try {
      await positionService.close(positionId)
      alert('Position fermée avec succès')
      loadOverviewData()
    } catch (err: any) {
      alert(`Erreur: ${err.message}`)
    }
  }

  // Actions sur les orders
  const handleCancelOrder = async (orderId: number) => {
    if (!confirm('Voulez-vous annuler cet ordre ?')) return
    try {
      await orderService.cancel(orderId)
      alert('Ordre annulé avec succès')
      loadOverviewData()
    } catch (err: any) {
      alert(`Erreur: ${err.message}`)
    }
  }

  const handleDeleteOrder = async (orderId: number) => {
    if (!confirm('Voulez-vous supprimer cet ordre ?')) return
    try {
      await orderService.delete(orderId)
      alert('Ordre supprimé avec succès')
      loadOverviewData()
    } catch (err: any) {
      alert(`Erreur: ${err.message}`)
    }
  }

  const handleEditOrder = (orderId: number) => {
    // Naviguer vers la page orders avec l'ordre sélectionné
    window.location.href = `/orders?edit=${orderId}`
  }

  // ============================================
  // Rendu
  // ============================================

  if (loading && activeTab === 'list') {
    return (
      <div className="assets-page">
        <Loading text="Chargement des assets..." />
      </div>
    )
  }

  if (error && activeTab === 'list') {
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
        <div className="header-actions">
          <Button onClick={() => setIsSyncModalOpen(true)} variant="primary">
            <i className="fas fa-sync me-1"></i>
            Synchroniser AllAssets
          </Button>
        </div>
      </div>

      {/* Onglets */}
      <div className="assets-tabs">
        <button
          className={`tab-button ${activeTab === 'list' ? 'active' : ''}`}
          onClick={() => setActiveTab('list')}
        >
          <List size={18} />
          <span>Liste</span>
        </button>
        <button
          className={`tab-button ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          <GitBranch size={18} />
          <span>Vue d'ensemble</span>
        </button>
      </div>

      {/* Contenu de l'onglet Liste */}
      {activeTab === 'list' && (
        <>
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
              <div className="filter-group">
                <label className="filter-label">Affichage</label>
                <div className="filter-buttons">
                  <Button
                    variant={!showAllAssets ? 'primary' : 'secondary'}
                    size="sm"
                    onClick={() => setShowAllAssets(false)}
                    title="Afficher uniquement les assets avec trades, positions ou favoris"
                  >
                    Suivis ({total})
                  </Button>
                  <Button
                    variant={showAllAssets ? 'primary' : 'secondary'}
                    size="sm"
                    onClick={() => setShowAllAssets(true)}
                    title="Afficher tout le catalogue (peut être lent)"
                  >
                    Tous
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

          <Card>
            <div className="assets-table-header">
              <h3 className="assets-table-title">
                {assets.length} asset(s) {groupByType ? 'regroupé(s) par type' : ''}
              </h3>
              <div className="assets-table-actions">
                {/* Toggle regroupement par type */}
                <button
                  className="toggle-group-btn"
                  onClick={() => setGroupByType(!groupByType)}
                  title={groupByType ? 'Désactiver le regroupement' : 'Activer le regroupement par type'}
                >
                  {groupByType ? <ToggleRight size={20} /> : <ToggleLeft size={20} />}
                  <span>{groupByType ? 'Groupé' : 'Liste plate'}</span>
                </button>

                {groupByType && Object.keys(groupedAssets).length > 0 && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={toggleAllGroups}
                  >
                    {expandedGroups.size === Object.keys(groupedAssets).length ? 'Tout replier' : 'Tout déplier'}
                  </Button>
                )}
              </div>
            </div>

            {assets.length > 0 ? (
              groupByType ? (
                // Vue groupée par type
                <div className="assets-grouped-container">
                  {Object.entries(groupedAssets).map(([type, typeAssets]) => {
                    const isExpanded = expandedGroups.has(type)
                    return (
                      <div key={type} className="asset-group">
                        <div
                          className="asset-group-header"
                          onClick={() => toggleGroup(type)}
                        >
                          <div className="asset-group-header-left">
                            {isExpanded ? (
                              <ChevronDown className="group-chevron" />
                            ) : (
                              <ChevronRight className="group-chevron" />
                            )}
                            <h4 className="asset-group-title">
                              {type}
                            </h4>
                            <Badge variant="info" className="asset-group-count">
                              {typeAssets.length}
                            </Badge>
                          </div>
                        </div>

                        {isExpanded && (
                          <div className="asset-group-content">
                            <Table
                              columns={columns}
                              data={typeAssets}
                              keyExtractor={(asset) => asset.id}
                            />
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              ) : (
                // Vue liste plate
                <Table
                  columns={columns}
                  data={assets}
                  keyExtractor={(asset) => asset.id}
                />
              )
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
        </>
      )}

      {/* Contenu de l'onglet Vue d'ensemble (DataTree) */}
      {activeTab === 'overview' && (
        <Card>
          <div className="overview-header">
            <h3 className="overview-title">
              <GitBranch size={20} />
              Vue d'ensemble - Assets avec Positions et Orders
            </h3>
            <div className="overview-actions">
              <button
                className="toggle-empty-btn"
                onClick={() => setIncludeEmptyAssets(!includeEmptyAssets)}
                title={includeEmptyAssets ? 'Masquer les assets vides' : 'Afficher tous les assets'}
              >
                {includeEmptyAssets ? <ToggleRight size={20} /> : <ToggleLeft size={20} />}
                <span>{includeEmptyAssets ? 'Tous les assets' : 'Actifs uniquement'}</span>
              </button>
              <Button
                variant="outline"
                size="small"
                onClick={loadOverviewData}
                disabled={overviewLoading}
              >
                <RefreshCw size={14} className={overviewLoading ? 'spinning' : ''} />
                Actualiser
              </Button>
            </div>
          </div>

          {overviewError && (
            <div className="overview-error">
              <p>Erreur: {overviewError}</p>
              <Button variant="outline" onClick={loadOverviewData}>
                Réessayer
              </Button>
            </div>
          )}

          <DataTreeTable
            data={overviewData}
            loading={overviewLoading}
            onSellPosition={handleSellPosition}
            onClosePosition={handleClosePosition}
            onCancelOrder={handleCancelOrder}
            onDeleteOrder={handleDeleteOrder}
            onEditOrder={handleEditOrder}
          />
        </Card>
      )}

      <SyncAssetsModal
        isOpen={isSyncModalOpen}
        onClose={() => setIsSyncModalOpen(false)}
        onSuccess={() => {
          setIsSyncModalOpen(false)
          // Rafraîchir les données
          if (activeTab === 'list') {
            refetch()
          } else {
            loadOverviewData()
          }
        }}
      />
    </div>
  )
}
