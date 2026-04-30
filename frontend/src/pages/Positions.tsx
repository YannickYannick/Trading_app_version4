/**
 * Page Positions - Liste et gestion des positions
 */
import { useState, useEffect, useCallback, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Card, Button, Table, Badge, Loading, Modal, Input, YahooActions } from '@components/common'
import { PortfolioCategoryChart } from '@components/dashboard/PortfolioCategoryChart'
import { usePositions } from '@hooks/usePositions'
import { positionService } from '@services'
import { assetService } from '@services/assets'
import api from '@services/api'
import { formatCurrency, formatPercent, formatDate } from '@utils/format'
import type { Position } from '@types'
import './Positions.css'

export default function Positions() {
  const [statusFilter, setStatusFilter] = useState<'OPEN' | 'CLOSED' | undefined>(undefined)
  const [selectedPosition, setSelectedPosition] = useState<Position | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [closePrice, setClosePrice] = useState('')
  const [isClosing, setIsClosing] = useState(false)
  const [yahooPrices, setYahooPrices] = useState<Record<number, number | null>>({})
  /** Si false : max 20 actifs uniques ; si true : tous les actifs uniques de la page courante */
  const [loadAllPrices, setLoadAllPrices] = useState(false)
  const [yahooPricesLoading, setYahooPricesLoading] = useState(false)
  const [yahooProgress, setYahooProgress] = useState<{ done: number; total: number }>({ done: 0, total: 0 })
  const [yahooError, setYahooError] = useState<string | null>(null)
  const [totalCash, setTotalCash] = useState<number>(0)

  const { positions, loading, error, summary, refetch } = usePositions({
    status: statusFilter,
  })

  // Cash (pour inclure dans le diagramme catégories)
  useEffect(() => {
    const loadCash = async () => {
      try {
        const data = await api.getAnalyticsSummary()
        const cash = Number(data?.kpi?.total_cash || 0) || 0
        setTotalCash(cash)
      } catch {
        setTotalCash(0)
      }
    }
    loadCash()
  }, [])

  const allAssetsInPositions = useMemo(() => {
    const ids = new Set<number>()
    positions.forEach((p) => {
      const id =
        (p as any)?.all_asset_id ||
        p.all_asset?.id ||
        (typeof p.all_asset === 'number' ? p.all_asset : null)
      if (id) ids.add(id)
    })
    return Array.from(ids)
  }, [positions])

  // Réinitialiser les prix affichés quand le filtre change (données potentiellement différentes)
  useEffect(() => {
    setYahooPrices({})
    setYahooProgress({ done: 0, total: 0 })
    setYahooError(null)
  }, [statusFilter])

  const loadYahooPricesManual = useCallback(async () => {
    if (allAssetsInPositions.length === 0) return
    setYahooPricesLoading(true)
    setYahooError(null)
    try {
      const targetIds = loadAllPrices ? allAssetsInPositions : allAssetsInPositions.slice(0, 20)
      // 1) Enrichir name/sector/industry via Yahoo pour ces AllAssets (workflow prévu)
      // (ne bloque pas si ça échoue, mais permet de rafraîchir les colonnes Secteur/Industrie)
      try {
        await assetService.enrichYahooMeta(targetIds)
      } catch {
        // ignore (on affiche quand même les prix)
      }
      const priceMap: Record<number, number | null> = {}
      setYahooProgress({ done: 0, total: targetIds.length })

      const batches: number[][] = []
      for (let i = 0; i < targetIds.length; i += 10) {
        batches.push(targetIds.slice(i, i + 10))
      }

      let rejectedCount = 0
      for (const batch of batches) {
        const results = await Promise.allSettled(
          batch.map(async (id) => {
            try {
              const price = await assetService.getYahooCurrentPrice(id)
              return { id, price }
            } finally {
              // Progression "asset par asset" (au fur et à mesure des réponses réseau)
              setYahooProgress((prev) => ({
                done: Math.min(prev.total, prev.done + 1),
                total: prev.total,
              }))
            }
          })
        )
        results.forEach((result) => {
          if (result.status === 'fulfilled') {
            priceMap[result.value.id] = result.value.price
          } else {
            rejectedCount += 1
          }
        })
      }

      setYahooPrices(priceMap)
      // 2) Rafraîchir les positions pour récupérer secteur/industrie mis à jour
      refetch()

      // 3) Feedback utilisateur si rien n'a pu être chargé
      const nonNullCount = Object.values(priceMap).filter((v) => v !== null && v !== undefined).length
      if (nonNullCount === 0) {
        setYahooError(
          rejectedCount > 0
            ? 'Impossible de charger les prix Yahoo (erreurs API). Vérifie la session et/ou les symboles Yahoo.'
            : 'Aucun prix Yahoo disponible pour les actifs sélectionnés (symbole Yahoo non validé ou non trouvé).'
        )
      }
    } finally {
      setYahooPricesLoading(false)
    }
  }, [allAssetsInPositions, loadAllPrices, refetch])

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

  const columns = useMemo(
    () => [
    {
      key: 'all_asset_symbol',
      label: 'Symbole AllAsset',
      align: 'center' as const,
      render: (_value: any, row: Position) => (
        <span className="all-asset-symbol">
          {row?.all_asset_symbol || row?.all_asset?.symbol || 'N/A'}
        </span>
      ),
    },
    {
      key: 'all_asset_name',
      label: 'Nom',
      align: 'left' as const,
      render: (_value: any, row: Position) => {
        const raw =
          row?.all_asset_name ||
          (row as any)?.all_asset?.name ||
          row?.asset?.name ||
          ''
        const name = String(raw).trim()
        const fallback = row?.all_asset_symbol || row?.all_asset?.symbol || row?.asset?.symbol || '—'
        return <span className="all-asset-name">{name ? name : fallback}</span>
      },
    },
    {
      key: 'all_asset_sector',
      label: 'Secteur',
      align: 'left' as const,
      render: (_value: any, row: Position) => {
        const raw = (row as any)?.all_asset_sector || row?.all_asset?.sector || ''
        const val = String(raw).trim()
        return <span>{val || '—'}</span>
      },
    },
    {
      key: 'all_asset_industry',
      label: 'Industrie',
      align: 'left' as const,
      render: (_value: any, row: Position) => {
        const raw = (row as any)?.all_asset_industry || row?.all_asset?.industry || ''
        const val = String(raw).trim()
        return <span>{val || '—'}</span>
      },
    },
    {
      key: 'yahoo_symbol',
      label: 'Symbole Yahoo',
      align: 'center' as const,
      render: (_value: any, row: Position) => (
        <span className="yahoo-symbol">
          {row?.all_asset_yahoo_symbol || row?.all_asset?.symbole_yahoo || 'N/A'}
        </span>
      ),
    },
    {
      key: 'side',
      label: 'Side',
      align: 'center' as const,
      render: (_value: any, row: Position) => (
        <Badge variant={row?.side === 'BUY' ? 'success' : 'danger'}>
          {row?.side || 'N/A'}
        </Badge>
      ),
    },
    {
      key: 'quantity',
      label: 'Taille',
      align: 'center' as const,
      render: (_value: any, row: Position) => {
        const val = row?.quantity || row?.size || 0
        return Number(val).toFixed(4)
      },
    },
    {
      key: 'entry_price',
      label: 'Prix d\'entrée',
      align: 'center' as const,
      render: (_value: any, row: Position) => formatCurrency(row?.entry_price || 0),
    },
    {
      key: 'current_price',
      label: 'Prix actuel',
      align: 'center' as const,
      render: (_value: any, row: Position) => {
        // En priorité : prix Yahoo chargé en live (yahooPrices), sinon prix de l'objet row
        const allAssetId =
          (row as any)?.all_asset_id ||
          row?.all_asset?.id ||
          (typeof row?.all_asset === 'number' ? row.all_asset : null)
        const livePrice = allAssetId ? yahooPrices[allAssetId] : null

        const price = livePrice ?? (row as any)?.yahoo_current_price ?? row?.current_price
        return formatCurrency(price || 0)
      },
    },
    {
      key: 'pnl',
      label: 'P&L',
      align: 'center' as const,
      render: (_value: any, row: Position) => (
        <Badge variant={(row?.pnl || 0) >= 0 ? 'success' : 'danger'}>
          {formatCurrency(row?.pnl || 0)}
        </Badge>
      ),
    },
    {
      key: 'pnl_percent',
      label: 'P&L %',
      align: 'center' as const,
      render: (_value: any, row: Position) => (
        <span className={(row?.pnl_percent || 0) >= 0 ? 'positive' : 'negative'}>
          {formatPercent(row?.pnl_percent || 0)}
        </span>
      ),
    },
    {
      key: 'status',
      label: 'Statut',
      align: 'center' as const,
      render: (_value: any, row: Position) => (
        <Badge variant={row?.status === 'OPEN' ? 'success' : 'secondary'}>
          {row?.status === 'OPEN' ? 'Ouverte' : 'Fermée'}
        </Badge>
      ),
    },
    {
      key: 'opened_at',
      label: 'Ouverte le',
      align: 'center' as const,
      render: (_value: any, row: Position) => formatDate(row?.opened_at || '', 'dd/MM/yyyy'),
    },
    {
      key: 'actions',
      label: 'Actions',
      align: 'center' as const,
      render: (_value: any, row: Position) => (
        <div className="position-actions">
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              setSelectedPosition(row)
              setIsModalOpen(true)
            }}
          >
            Détails
          </Button>
          {row?.status === 'OPEN' && (
            <Button
              size="sm"
              variant="danger"
              onClick={() => {
                setSelectedPosition(row)
                setIsModalOpen(true)
              }}
            >
              Fermer
            </Button>
          )}
        </div>
      ),
    },
    {
      key: 'yahoo_actions',
      label: 'Actions Yahoo',
      align: 'center' as const,
      render: (_value: any, row: Position) => {
        const allAssetId =
          (row as any)?.all_asset_id ||
          row?.all_asset?.id ||
          (typeof row?.all_asset === 'number' ? row.all_asset : null)
        return (
          <YahooActions
            allAssetId={allAssetId}
            allAssetSymbol={row?.all_asset_symbol || row?.all_asset?.symbol}
            onSuccess={async () => {
              // Mise à jour asynchrone sans recharger la page
              if (allAssetId) {
                try {
                  const price = await assetService.getYahooCurrentPrice(allAssetId)
                  setYahooPrices(prev => ({ ...prev, [allAssetId]: price }))
                } catch (error) {
                  console.error('Erreur lors de la mise à jour:', error)
                }
              }
            }}
            compact
          />
        )
      },
    },
    ],
    [yahooPrices]
  )

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
          <Button
            variant={loadAllPrices ? 'success' : 'outline'}
            onClick={() => setLoadAllPrices(!loadAllPrices)}
            disabled={yahooPricesLoading}
            title={
              loadAllPrices
                ? 'Prochain chargement : tous les actifs uniques de la page (plus lent)'
                : 'Prochain chargement : max 20 actifs uniques (plus rapide)'
            }
          >
            {loadAllPrices ? '📊 Tous les actifs' : '⚡ Max 20 actifs'}
          </Button>
          <Button
            variant="primary"
            onClick={() => void loadYahooPricesManual()}
            disabled={yahooPricesLoading || allAssetsInPositions.length === 0}
            title="Interroge Yahoo via l’API pour remplir la colonne « Prix actuel »"
          >
            {yahooPricesLoading ? 'Chargement…' : 'Charger les prix Yahoo'}
          </Button>
        </div>
      </div>

      {yahooPricesLoading && yahooProgress.total > 0 && (
        <div className="yahoo-progress">
          <div className="yahoo-progress-top">
            <span>Chargement des prix Yahoo</span>
            <span>
              {yahooProgress.done}/{yahooProgress.total}
            </span>
          </div>
          <div className="yahoo-progress-bar">
            <div
              className="yahoo-progress-bar-fill"
              style={{
                width: `${Math.round((yahooProgress.done / yahooProgress.total) * 100)}%`,
              }}
            />
          </div>
        </div>
      )}

      {yahooError && (
        <div className="error-banner">
          <Badge variant="danger">Yahoo</Badge>
          <span>{yahooError}</span>
        </div>
      )}

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

      {/* Diagramme catégories (positions filtrées + cash global) */}
      <div style={{ marginBottom: '24px' }}>
        <PortfolioCategoryChart
          positions={positions}
          totalCash={statusFilter === 'OPEN' ? totalCash : 0}
          title="Allocation par catégories (positions)"
        />
      </div>

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
        title={
          selectedPosition
            ? `Position ${selectedPosition.all_asset_symbol || selectedPosition.asset?.symbol || 'N/A'}`
            : 'Détails'
        }
        size="md"
      >
        {selectedPosition && (
          <div className="position-details">
            <div className="detail-section">
              <h4>Informations Générales</h4>
              <div className="detail-grid">
                <div>
                  <span className="detail-label">Symbole</span>
                  <span className="detail-value">
                    {selectedPosition.all_asset_symbol || selectedPosition.asset?.symbol || 'N/A'}
                  </span>
                </div>
                <div>
                  <span className="detail-label">Nom</span>
                  <span className="detail-value">
                    {selectedPosition.all_asset_name ||
                      selectedPosition.all_asset?.name ||
                      selectedPosition.asset?.name ||
                      'N/A'}
                  </span>
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
                  <span className={`detail-value ${(selectedPosition.pnl_percent || 0) >= 0 ? 'positive' : 'negative'}`}>
                    {formatPercent(selectedPosition.pnl_percent || 0)}
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
