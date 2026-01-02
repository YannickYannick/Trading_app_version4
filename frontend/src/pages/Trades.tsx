/**
 * Page Trades - Historique des trades
 */
import { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Card, Button, Table, Badge, Loading, Input, YahooActions } from '@components/common'
import { useTrades } from '@hooks/useTrades'
import { assetService } from '@services/assets'
import { formatCurrency, formatDate } from '@utils/format'
import type { Trade, AllAsset } from '@types'
import TradesChart from '@components/trades/TradesChart'
import ChartControls from '@components/trades/ChartControls'
import PriceHistoryTable from '@components/trades/PriceHistoryTable'
import './Trades.css'

export default function Trades() {
  const [sideFilter, setSideFilter] = useState<'BUY' | 'SELL' | undefined>(undefined)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [yahooPrices, setYahooPrices] = useState<Record<number, number | null>>({})
  const [selectedAssets, setSelectedAssets] = useState<number[]>([])
  const [chartViewMode, setChartViewMode] = useState<'global' | 'per_asset'>('global')
  const [showChart, setShowChart] = useState(true)
  
  const { trades, loading, error, statistics, total, refetch } = useTrades({
    side: sideFilter,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  })

  // Extraire les IDs uniques des AllAssets présents dans les trades
  const allAssetsInTrades = useMemo(() => {
    const assetIds = new Set<number>()
    trades.forEach((trade) => {
      const assetId = trade.all_asset?.id || (typeof trade.all_asset === 'number' ? trade.all_asset : null)
      if (assetId) {
        assetIds.add(assetId)
      }
    })
    return Array.from(assetIds)
  }, [trades])

  // Créer une Map pour accéder rapidement aux AllAssets
  const allAssetsMap = useMemo(() => {
    const map = new Map<number, AllAsset>()
    trades.forEach((trade) => {
      if (trade.all_asset && typeof trade.all_asset === 'object') {
        map.set(trade.all_asset.id, trade.all_asset)
      }
    })
    return map
  }, [trades])

  // Sélectionner automatiquement le premier asset si aucun n'est sélectionné et qu'on est en mode per_asset
  useEffect(() => {
    if (chartViewMode === 'per_asset' && selectedAssets.length === 0 && allAssetsInTrades.length > 0) {
      setSelectedAssets([allAssetsInTrades[0]])
    }
  }, [chartViewMode, allAssetsInTrades])

  // Charger les prix Yahoo actuels pour tous les AllAssets
  useEffect(() => {
    if (trades.length > 0) {
      const loadYahooPrices = async () => {
        const priceMap: Record<number, number | null> = {}
        const allAssetIds = trades
          .map(t => t.all_asset?.id || (typeof t.all_asset === 'number' ? t.all_asset : null))
          .filter((id): id is number => id !== null && id !== undefined)
        
        // Charger les prix en parallèle (limité à 10 à la fois)
        const batches = []
        for (let i = 0; i < allAssetIds.length; i += 10) {
          batches.push(allAssetIds.slice(i, i + 10))
        }
        
        for (const batch of batches) {
          const results = await Promise.allSettled(
            batch.map(async (id) => {
              const price = await assetService.getYahooCurrentPrice(id)
              return { id, price }
            })
          )
          
          results.forEach((result) => {
            if (result.status === 'fulfilled') {
              priceMap[result.value.id] = result.value.price
            }
          })
        }
        
        setYahooPrices(priceMap)
      }
      
      loadYahooPrices()
    }
  }, [trades])

  const columns = [
    {
      key: 'timestamp',
      label: 'Date',
      align: 'center' as const,
      render: (_value: any, row: Trade) => formatDate(row?.timestamp || row?.executed_at || '', 'dd/MM/yyyy HH:mm'),
    },
    {
      key: 'all_asset_symbol',
      label: 'Symbole AllAsset',
      align: 'center' as const,
      render: (_value: any, row: Trade) => (
        <span className="all-asset-symbol">
          {row?.all_asset_symbol || row?.all_asset?.symbol || 'N/A'}
        </span>
      ),
    },
    {
      key: 'yahoo_symbol',
      label: 'Symbole Yahoo',
      align: 'center' as const,
      render: (_value: any, row: Trade) => (
        <span className="yahoo-symbol">
          {row?.all_asset_yahoo_symbol || row?.all_asset?.symbole_yahoo || 'N/A'}
        </span>
      ),
    },
    {
      key: 'yahoo_price',
      label: 'Prix Yahoo',
      align: 'center' as const,
      render: (_value: any, row: Trade) => {
        const allAssetId = row?.all_asset?.id || (typeof row?.all_asset === 'number' ? row.all_asset : null)
        const price = allAssetId ? yahooPrices[allAssetId] : null
        return price !== null && price !== undefined ? formatCurrency(price) : 'N/A'
      },
    },
    {
      key: 'symbol',
      label: 'Symbole',
      align: 'center' as const,
      render: (_value: any, row: Trade) => (
        <Link to={`/trades/${row?.id || ''}`} className="trade-symbol link-symbol">
          {row?.asset?.symbol || 'N/A'}
        </Link>
      ),
    },
    {
      key: 'side',
      label: 'Side',
      align: 'center' as const,
      render: (_value: any, row: Trade) => (
        <Badge variant={row?.side === 'BUY' ? 'success' : 'danger'}>
          {row?.side || 'N/A'}
        </Badge>
      ),
    },
    {
      key: 'size',
      label: 'Taille',
      align: 'center' as const,
      render: (_value: any, row: Trade) => {
        const size = Number(row?.size || row?.quantity || 0)
        return isNaN(size) ? '0.0000' : size.toFixed(4)
      },
    },
    {
      key: 'price',
      label: 'Prix',
      align: 'center' as const,
      render: (_value: any, row: Trade) => formatCurrency(row?.price || 0),
    },
    {
      key: 'total',
      label: 'Total',
      align: 'center' as const,
      render: (_value: any, row: Trade) => formatCurrency((row?.size || row?.quantity || 0) * (row?.price || 0)),
    },
    {
      key: 'fees',
      label: 'Frais',
      align: 'center' as const,
      render: (_value: any, row: Trade) => formatCurrency(row?.fees || 0),
    },
    {
      key: 'yahoo_actions',
      label: 'Actions Yahoo',
      align: 'center' as const,
      render: (_value: any, row: Trade) => {
        const allAssetId = row?.all_asset?.id || (typeof row?.all_asset === 'number' ? row.all_asset : null)
        return (
          <YahooActions
            allAssetId={allAssetId}
            allAssetSymbol={row?.all_asset_symbol || row?.all_asset?.symbol}
            onSuccess={() => {
              refetch()
              // Recharger le prix Yahoo après succès
              if (allAssetId) {
                assetService.getYahooCurrentPrice(allAssetId).then(price => {
                  setYahooPrices(prev => ({ ...prev, [allAssetId]: price }))
                })
              }
            }}
            compact
          />
        )
      },
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
                <span className={(statistics.win_rate || 0) >= 50 ? 'positive' : 'negative'}>
                  {(statistics.win_rate || 0).toFixed(1)}% de réussite
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
            <p className="stat-value">{formatCurrency(statistics.total_volume || 0)}</p>
          </Card>
          <Card className="stat-card">
            <h3>Frais Totaux</h3>
            <p className="stat-value">{formatCurrency(statistics.total_fees || 0)}</p>
          </Card>
          <Card className="stat-card">
            <h3>Achats</h3>
            <p className="stat-value">{statistics.buy_trades || 0}</p>
          </Card>
          <Card className="stat-card">
            <h3>Ventes</h3>
            <p className="stat-value">{statistics.sell_trades || 0}</p>
          </Card>
        </div>
      )}

      {/* Graphique des trades */}
      {trades.length > 0 && (
        <Card
          title="Graphique des Trades"
          className="trades-chart-card"
          actions={
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowChart(!showChart)}
            >
              {showChart ? 'Masquer' : 'Afficher'} le graphique
            </Button>
          }
        >
          {showChart && (
            <>
                  <ChartControls
                    selectedAssets={selectedAssets}
                    viewMode={chartViewMode}
                    onSelectedAssetsChange={setSelectedAssets}
                    onViewModeChange={setChartViewMode}
                    allAssetsInTrades={allAssetsInTrades}
                    allAssetsMap={allAssetsMap}
                  />
              <TradesChart
                trades={trades}
                selectedAssets={selectedAssets}
                viewMode={chartViewMode}
                allAssetsMap={allAssetsMap}
              />
            </>
          )}
        </Card>
      )}

      {/* Tableau d'historique des prix */}
      {trades.length > 0 && selectedAssets.length > 0 && (
        <Card
          title="Historique des Prix"
          className="price-history-card"
        >
          {selectedAssets.map((assetId) => {
            const asset = allAssetsMap.get(assetId)
            return (
              <PriceHistoryTable
                key={assetId}
                allAssetId={assetId}
                allAssetSymbol={asset?.symbol || `Asset #${assetId}`}
                days={365}
              />
            )
          })}
        </Card>
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
            keyExtractor={(trade) => trade?.id || ''}
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
