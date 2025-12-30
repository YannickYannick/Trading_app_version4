/**
 * Page Strategies - Liste et gestion des stratégies de trading
 */
import { useState, useEffect } from 'react'
import { Card, Button, Table, Badge, Loading } from '@components/common'
import { strategyService, brokerService, assetService } from '@services'
import { formatDate, formatCurrency } from '@utils/format'
import type { Strategy, BrokerAccount, AllAsset } from '@types'
import './Strategies.css'

// Algorithmes disponibles
const ALGORITHM_OPTIONS = [
  { value: 'threshold', label: 'Seuils (Threshold)' },
  { value: 'ma_crossover', label: 'Moving Average Crossover' },
  { value: 'rsi', label: 'RSI (Relative Strength Index)' },
  { value: 'bollinger', label: 'Bollinger Bands' },
  { value: 'macd', label: 'MACD' },
  { value: 'grid', label: 'Grid Trading' },
]

const EXECUTION_MODE_OPTIONS = [
  { value: 'simulation', label: 'Simulation' },
  { value: 'paper_trading', label: 'Paper Trading' },
  { value: 'live_trading', label: 'Trading Réel' },
]

export default function Strategies() {
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Options pour les selects
  const [assets, setAssets] = useState<AllAsset[]>([])
  const [brokerAccounts, setBrokerAccounts] = useState<BrokerAccount[]>([])
  const [loadingOptions, setLoadingOptions] = useState(true)

  const loadStrategies = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await strategyService.getAll()
      const strategiesList = Array.isArray(response) 
        ? response 
        : (response.results || response.data || [])
      setStrategies(strategiesList)
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || err.message || err.error || 'Erreur lors du chargement des stratégies'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const loadOptions = async () => {
    try {
      setLoadingOptions(true)
      const assetsResponse = await assetService.getAllAssets({ page_size: 1000 })
      setAssets(assetsResponse.results || [])
      const brokersResponse = await brokerService.getAccounts()
      setBrokerAccounts(brokersResponse.results || [])
    } catch (err) {
      console.error('Erreur lors du chargement des options:', err)
    } finally {
      setLoadingOptions(false)
    }
  }

  useEffect(() => {
    loadStrategies()
    loadOptions()
  }, [])

  const handleCellEdit = async (newValue: any, row: Strategy, key: string) => {
    try {
      const updateData: any = {}
      
      if (key === 'asset_id') {
        updateData['asset'] = newValue || null
      } else if (key === 'broker_account_id') {
        updateData['broker_account'] = newValue || null
      } else if (key === 'price_min' || key === 'price_max') {
        const params = { ...(row.parameters || {}) }
        params[key] = newValue ? parseFloat(newValue) : null
        updateData['parameters'] = params
      } else if (key === 'max_position_size' || key === 'max_daily_loss' || 
                 key === 'target_min_quantity' || key === 'target_max_quantity' ||
                 key === 'check_frequency') {
        updateData[key] = newValue ? parseFloat(newValue) : null
      } else if (key === 'is_active' || key === 'is_automated') {
        updateData[key] = Boolean(newValue)
      } else {
        updateData[key] = newValue
      }
      
      await strategyService.update(row.id, updateData)
      loadStrategies()
    } catch (err: any) {
      console.error('Erreur lors de la mise à jour:', err)
      alert(err.response?.data?.error || 'Erreur lors de la modification')
      throw err
    }
  }

  const handleToggleActive = async (strategy: Strategy) => {
    try {
      await strategyService.toggleActive(strategy.id, !strategy.is_active)
      loadStrategies()
    } catch (err) {
      alert('Erreur lors de la modification')
    }
  }

  const handleExecute = async (strategy: Strategy) => {
    if (!window.confirm(`Exécuter la stratégie "${strategy.name}" maintenant ?`)) {
      return
    }
    try {
      alert(`Exécution de la stratégie ${strategy.id} - À implémenter`)
    } catch (err) {
      alert('Erreur lors de l\'exécution')
    }
  }

  const handleCreateNew = async () => {
    try {
      const newStrategy = await strategyService.create({
        name: 'Nouvelle stratégie',
        description: '',
        risk_level: 'MEDIUM',
        is_active: false,
        is_automated: false,
      })
      loadStrategies()
      // Focus sur la ligne créée après un court délai
      setTimeout(() => {
        const element = document.querySelector(`[data-strategy-id="${newStrategy.id}"]`)
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'center' })
        }
      }, 100)
    } catch (err: any) {
      alert(err.response?.data?.error || 'Erreur lors de la création')
    }
  }

  const columns = [
    {
      key: 'name',
      label: 'Nom',
      editable: true,
      onCellEdit: handleCellEdit,
      render: (value: string, row: Strategy) => (
        <strong style={{ cursor: 'pointer' }} title="Double-cliquer pour éditer">
          {value || '-'}
        </strong>
      ),
    },
    {
      key: 'description',
      label: 'Description',
      editable: true,
      onCellEdit: handleCellEdit,
      render: (value: string) => <span className="text-muted small">{value || '-'}</span>,
    },
    {
      key: 'asset_id',
      label: 'Asset',
      editable: true,
      cellType: 'select' as const,
      selectOptions: [
        { value: '', label: '- Sélectionner -' },
        ...assets.map(asset => ({ value: String(asset.id), label: `${asset.symbol} - ${asset.name}` }))
      ],
      onCellEdit: handleCellEdit,
      render: (_: any, row: Strategy) => {
        const value = String(row.asset?.id || row.asset_id || '')
        return <span className="text-muted">{row.asset?.symbol || '-'}</span>
      },
    },
    {
      key: 'algorithm_type',
      label: 'Algorithme',
      editable: true,
      cellType: 'select' as const,
      selectOptions: ALGORITHM_OPTIONS,
      onCellEdit: handleCellEdit,
      render: (value: string) => {
        const algo = ALGORITHM_OPTIONS.find(a => a.value === value)
        return <span>{algo?.label || value || '-'}</span>
      },
    },
    {
      key: 'broker_account_id',
      label: 'Broker',
      editable: true,
      cellType: 'select' as const,
      selectOptions: [
        { value: '', label: '- Sélectionner -' },
        ...brokerAccounts.map(account => ({ 
          value: account.id, 
          label: account.broker?.name || account.account_name || `Compte ${account.id}` 
        }))
      ],
      onCellEdit: handleCellEdit,
      render: (_: any, row: Strategy) => (
        <span className="text-muted">{row.broker_name || '-'}</span>
      ),
    },
    {
      key: 'execution_mode',
      label: 'Mode',
      editable: true,
      cellType: 'select' as const,
      selectOptions: EXECUTION_MODE_OPTIONS,
      onCellEdit: handleCellEdit,
      render: (value: string) => {
        const mode = EXECUTION_MODE_OPTIONS.find(m => m.value === value)
        return <span>{mode?.label || value || '-'}</span>
      },
    },
    {
      key: 'target_min_quantity',
      label: 'Qty Min',
      editable: true,
      cellType: 'number' as const,
      onCellEdit: handleCellEdit,
      align: 'right' as const,
      render: (_: any, row: Strategy) => {
        const minQty = parseFloat(row.target_min_quantity?.toString() || '0')
        return minQty > 0 ? <span className="text-info">{minQty.toFixed(2)}</span> : '-'
      },
    },
    {
      key: 'target_max_quantity',
      label: 'Qty Max',
      editable: true,
      cellType: 'number' as const,
      onCellEdit: handleCellEdit,
      align: 'right' as const,
      render: (_: any, row: Strategy) => {
        const maxQty = parseFloat(row.target_max_quantity?.toString() || '0')
        return maxQty > 0 ? <span className="text-warning">{maxQty.toFixed(2)}</span> : '-'
      },
    },
    {
      key: 'price_min',
      label: 'Prix Min',
      editable: true,
      cellType: 'number' as const,
      onCellEdit: handleCellEdit,
      align: 'right' as const,
      render: (_: any, row: Strategy) => {
        const priceMin = row.parameters?.price_min
        return priceMin ? formatCurrency(priceMin) : '-'
      },
    },
    {
      key: 'price_max',
      label: 'Prix Max',
      editable: true,
      cellType: 'number' as const,
      onCellEdit: handleCellEdit,
      align: 'right' as const,
      render: (_: any, row: Strategy) => {
        const priceMax = row.parameters?.price_max
        return priceMax ? formatCurrency(priceMax) : '-'
      },
    },
    {
      key: 'portfolio_quantity',
      label: 'Portefeuille',
      align: 'right' as const,
      render: (_: any, row: Strategy) => {
        const quantity = parseFloat(row.portfolio_quantity?.toString() || '0')
        if (quantity === 0) return <span className="text-muted">0</span>
        const colorClass = quantity > 0 ? 'text-success' : 'text-danger'
        return <span className={`${colorClass} fw-bold`}>{quantity.toFixed(2)}</span>
      },
    },
    {
      key: 'check_frequency',
      label: 'Fréquence (min)',
      editable: true,
      cellType: 'number' as const,
      onCellEdit: handleCellEdit,
      align: 'right' as const,
      render: (value: number) => value || 45,
    },
    {
      key: 'max_position_size',
      label: 'Taille Max (%)',
      editable: true,
      cellType: 'number' as const,
      onCellEdit: handleCellEdit,
      align: 'right' as const,
      render: (_: any, row: Strategy) => {
        const size = parseFloat(row.max_position_size?.toString() || '0')
        return size > 0 ? `${size.toFixed(2)}%` : '-'
      },
    },
    {
      key: 'max_daily_loss',
      label: 'Perte Max (%)',
      editable: true,
      cellType: 'number' as const,
      onCellEdit: handleCellEdit,
      align: 'right' as const,
      render: (_: any, row: Strategy) => {
        const loss = parseFloat(row.max_daily_loss?.toString() || '0')
        return loss > 0 ? `${loss.toFixed(2)}%` : '-'
      },
    },
    {
      key: 'risk_level',
      label: 'Risque',
      editable: true,
      cellType: 'select' as const,
      selectOptions: [
        { value: 'LOW', label: 'Faible' },
        { value: 'MEDIUM', label: 'Moyen' },
        { value: 'HIGH', label: 'Élevé' },
      ],
      onCellEdit: handleCellEdit,
      render: (value: string) => (
        <Badge variant={value === 'LOW' ? 'success' : value === 'HIGH' ? 'danger' : 'warning'}>
          {value === 'LOW' ? 'Faible' : value === 'HIGH' ? 'Élevé' : 'Moyen'}
        </Badge>
      ),
    },
    {
      key: 'is_active',
      label: 'Statut',
      editable: true,
      cellType: 'checkbox' as const,
      onCellEdit: handleCellEdit,
      render: (value: boolean) => (
        <Badge variant={value ? 'success' : 'secondary'}>
          {value ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
    {
      key: 'is_automated',
      label: 'Auto',
      editable: true,
      cellType: 'checkbox' as const,
      onCellEdit: handleCellEdit,
      render: (value: boolean) => (value ? '✅' : '❌'),
    },
    {
      key: 'total_trades',
      label: 'Performance',
      render: (_: any, row: Strategy) => {
        const total = row.total_trades || 0
        const successful = row.successful_trades || 0
        const pnl = parseFloat(row.total_pnl?.toString() || '0')
        const pnlColor = pnl >= 0 ? 'text-success' : 'text-danger'
        return (
          <div>
            <small>{total} ({successful} réussis)</small>
            <br />
            <span className={`${pnlColor} fw-bold`}>{pnl.toFixed(2)} €</span>
          </div>
        )
      },
    },
    {
      key: 'actions',
      label: 'Actions',
      align: 'center' as const,
      render: (_: any, row: Strategy) => (
        <div className="strategy-actions-inline">
          <Button
            variant="outline"
            size="small"
            onClick={(e) => {
              e.stopPropagation()
              alert(`Voir stratégie ${row.id}`)
            }}
            title="Voir"
          >
            👁️
          </Button>
          <Button
            variant="outline"
            size="small"
            onClick={(e) => {
              e.stopPropagation()
              handleToggleActive(row)
            }}
            title={row.is_active ? 'Mettre en pause' : 'Activer'}
          >
            {row.is_active ? '⏸️' : '▶️'}
          </Button>
          <Button
            variant="outline"
            size="small"
            onClick={(e) => {
              e.stopPropagation()
              handleExecute(row)
            }}
            title="Exécuter"
          >
            🚀
          </Button>
          <Button
            variant="outline"
            size="small"
            onClick={(e) => {
              e.stopPropagation()
              alert(`Historique stratégie ${row.id}`)
            }}
            title="Historique"
          >
            📜
          </Button>
          <Button
            variant="danger"
            size="small"
            onClick={async (e) => {
              e.stopPropagation()
              if (window.confirm(`Supprimer la stratégie "${row.name}" ?`)) {
                try {
                  await strategyService.delete(row.id)
                  loadStrategies()
                } catch (err) {
                  alert('Erreur lors de la suppression')
                }
              }
            }}
            title="Supprimer"
          >
            🗑️
          </Button>
        </div>
      ),
    },
  ]

  return (
    <div className="strategies-page">
      <div className="strategies-header">
        <h1>Stratégies de Trading</h1>
        <Button
          variant="primary"
          onClick={handleCreateNew}
        >
          Créer une stratégie
        </Button>
      </div>

      {loading || loadingOptions ? (
        <Loading text="Chargement des stratégies..." />
      ) : error ? (
        <Card>
          <div className="error-message">
            <Badge variant="danger">Erreur</Badge>
            <p>{error}</p>
            <Button onClick={loadStrategies}>Réessayer</Button>
          </div>
        </Card>
      ) : (
        <Card>
          <div className="strategies-hint">
            <strong>💡 Astuce :</strong> Double-cliquez sur n'importe quelle cellule pour la modifier directement dans le tableau.
          </div>
          {strategies.length > 0 && (
            <div style={{ marginBottom: '1rem', color: 'var(--text-secondary, #6b7280)' }}>
              {strategies.length} stratégie{strategies.length > 1 ? 's' : ''} trouvée{strategies.length > 1 ? 's' : ''}
            </div>
          )}
          <Table data={strategies} columns={columns} />
          {strategies.length === 0 && (
            <div className="empty-state" style={{ padding: '2rem', textAlign: 'center' }}>
              <p>Aucune stratégie trouvée.</p>
              <p className="text-muted small">
                Créez votre première stratégie pour commencer.
              </p>
              <Button
                variant="primary"
                onClick={handleCreateNew}
                style={{ marginTop: '1rem' }}
              >
                Créer votre première stratégie
              </Button>
            </div>
          )}
        </Card>
      )}
    </div>
  )
}
