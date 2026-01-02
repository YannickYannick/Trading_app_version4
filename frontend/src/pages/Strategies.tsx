/**
 * Page Strategies - Liste et gestion des stratégies de trading
 */
import { useState, useEffect } from 'react'
import { Card, Button, Table, Badge, Loading, ColumnSelector, type ColumnOption, YahooActions } from '@components/common'
import { strategyService, brokerService } from '@services'
import { assetService as assetServiceUtil } from '@services/assets'
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
  
  // Colonnes visibles
  const [visibleColumns, setVisibleColumns] = useState<string[]>([])
  const [yahooPrices, setYahooPrices] = useState<Record<number, number | null>>({})

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
      const assetsResponse = await assetServiceUtil.getAllAssets({ page_size: 1000 })
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

  // Charger les prix Yahoo actuels pour tous les AllAssets
  useEffect(() => {
    if (strategies.length > 0) {
      const loadYahooPrices = async () => {
        const priceMap: Record<number, number | null> = {}
        const allAssetIds = strategies
          .map(s => {
            const allAsset = s.all_asset
            if (typeof allAsset === 'object' && allAsset?.id) {
              return allAsset.id
            } else if (typeof allAsset === 'number') {
              return allAsset
            }
            return null
          })
          .filter((id): id is number => id !== null && id !== undefined)
        
        // Charger les prix en parallèle (limité à 10 à la fois)
        const batches = []
        for (let i = 0; i < allAssetIds.length; i += 10) {
          batches.push(allAssetIds.slice(i, i + 10))
        }
        
        for (const batch of batches) {
          const results = await Promise.allSettled(
            batch.map(async (id) => {
              const price = await assetServiceUtil.getYahooCurrentPrice(id)
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
  }, [strategies])

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
      
      // Mise à jour optimiste de l'état local avant la sauvegarde
      setStrategies(prevStrategies => 
        prevStrategies.map(strategy => {
          if (strategy.id === row.id) {
            const updated: Strategy = { ...strategy }
            
            // Mettre à jour les champs directs
            if (key === 'asset_id' || key === 'name' || key === 'description' || 
                key === 'algorithm_type' || key === 'execution_mode' || 
                key === 'check_frequency' || key === 'max_position_size' || 
                key === 'max_daily_loss' || key === 'target_min_quantity' || 
                key === 'target_max_quantity' || key === 'risk_level' ||
                key === 'is_active' || key === 'is_automated') {
              if (key === 'target_min_quantity' || key === 'target_max_quantity' ||
                  key === 'max_position_size' || key === 'max_daily_loss' || 
                  key === 'check_frequency') {
                updated[key as keyof Strategy] = newValue ? parseFloat(newValue) : null
              } else if (key === 'is_active' || key === 'is_automated') {
                updated[key as keyof Strategy] = Boolean(newValue) as any
              } else {
                updated[key as keyof Strategy] = newValue
              }
            }
            
            // Mettre à jour les champs imbriqués
            if (key === 'price_min' || key === 'price_max') {
              updated.parameters = { ...(updated.parameters || {}), [key]: newValue ? parseFloat(newValue) : null }
            }
            
            if (key === 'asset_id' && newValue) {
              const asset = assets.find(a => a.id === parseInt(newValue))
              if (asset) {
                updated.asset = { id: asset.id, symbol: asset.symbol, name: asset.name }
              }
            }
            
            if (key === 'broker_account_id' && newValue) {
              const broker = brokerAccounts.find(b => b.id === parseInt(newValue))
              if (broker) {
                updated.broker_name = broker.broker?.name || broker.account_name
              }
            }
            
            // Pour les ranges (quantity_range, price_range)
            if (key === 'quantity_range' && typeof newValue === 'object') {
              updated.target_min_quantity = newValue.min ? parseFloat(newValue.min) : null
              updated.target_max_quantity = newValue.max ? parseFloat(newValue.max) : null
            }
            
            if (key === 'price_range' && typeof newValue === 'object') {
              updated.parameters = { ...(updated.parameters || {}) }
              updated.parameters.price_min = newValue.min ? parseFloat(newValue.min) : null
              updated.parameters.price_max = newValue.max ? parseFloat(newValue.max) : null
            }
            
            return updated
          }
          return strategy
        })
      )
      
      // Sauvegarde asynchrone en arrière-plan (sans bloquer l'UI)
      strategyService.update(row.id, updateData).catch((err: any) => {
        console.error('Erreur lors de la sauvegarde:', err)
        // En cas d'erreur, recharger pour restaurer l'état correct
        loadStrategies()
        alert(err.response?.data?.error || 'Erreur lors de la sauvegarde. Les données ont été restaurées.')
      })
    } catch (err: any) {
      console.error('Erreur lors de la mise à jour:', err)
      // En cas d'erreur immédiate, recharger
      loadStrategies()
      alert(err.response?.data?.error || 'Erreur lors de la modification')
      throw err
    }
  }

  const handleToggleActive = async (strategy: Strategy) => {
    try {
      const newActiveState = !strategy.is_active
      
      // Mise à jour optimiste de l'état local
      setStrategies(prevStrategies => 
        prevStrategies.map(s => 
          s.id === strategy.id ? { ...s, is_active: newActiveState } : s
        )
      )
      
      // Sauvegarde asynchrone en arrière-plan
      strategyService.toggleActive(strategy.id, newActiveState).catch((err: any) => {
        console.error('Erreur lors du toggle:', err)
        // En cas d'erreur, restaurer l'état
        setStrategies(prevStrategies => 
          prevStrategies.map(s => 
            s.id === strategy.id ? { ...s, is_active: !newActiveState } : s
          )
        )
        alert(err.response?.data?.error || 'Erreur lors de la modification')
      })
    } catch (err: any) {
      alert(err.response?.data?.error || 'Erreur lors de la modification')
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
      
      // Ajouter la nouvelle stratégie à l'état local sans recharger
      setStrategies(prevStrategies => [newStrategy, ...prevStrategies])
      
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

  // Toutes les colonnes disponibles pour le sélecteur
  const allColumnsData: ColumnOption[] = [
    { key: 'name', label: 'Nom', defaultVisible: true },
    { key: 'description', label: 'Description', defaultVisible: true },
    { key: 'all_asset_symbol', label: 'Symbole AllAsset', defaultVisible: true },
    { key: 'yahoo_symbol', label: 'Symbole Yahoo', defaultVisible: true },
    { key: 'yahoo_price', label: 'Prix Yahoo', defaultVisible: true },
    { key: 'asset_id', label: 'Asset', defaultVisible: true },
    { key: 'algorithm_type', label: 'Algorithme', defaultVisible: true },
    { key: 'broker_account_id', label: 'Broker', defaultVisible: true },
    { key: 'execution_mode', label: 'Mode', defaultVisible: true },
    { key: 'quantity_range', label: 'Quantité (Min/Max)', defaultVisible: true },
    { key: 'price_range', label: 'Prix (Min/Max)', defaultVisible: true },
    { key: 'portfolio_quantity', label: 'Portefeuille', defaultVisible: true },
    { key: 'check_frequency', label: 'Fréquence (min)', defaultVisible: true },
    { key: 'max_position_size', label: 'Taille Max (%)', defaultVisible: true },
    { key: 'max_daily_loss', label: 'Perte Max (%)', defaultVisible: true },
    { key: 'risk_level', label: 'Risque', defaultVisible: true },
    { key: 'is_active', label: 'Statut', defaultVisible: true },
    { key: 'is_automated', label: 'Auto', defaultVisible: true },
    { key: 'total_trades', label: 'Performance', defaultVisible: true },
    { key: 'yahoo_actions', label: 'Actions Yahoo', defaultVisible: true },
    { key: 'actions', label: 'Actions', defaultVisible: true },
  ]

  // Initialiser les colonnes visibles depuis localStorage
  useEffect(() => {
    if (visibleColumns.length === 0) {
      try {
        const saved = localStorage.getItem('strategies_visible_columns')
        if (saved) {
          const parsed = JSON.parse(saved)
          if (Array.isArray(parsed) && parsed.length > 0) {
            setVisibleColumns(parsed)
          } else {
            setVisibleColumns(allColumnsData.filter(c => c.defaultVisible !== false).map(c => c.key))
          }
        } else {
          setVisibleColumns(allColumnsData.filter(c => c.defaultVisible !== false).map(c => c.key))
        }
      } catch (e) {
        setVisibleColumns(allColumnsData.filter(c => c.defaultVisible !== false).map(c => c.key))
      }
    }
  }, [])

  const columns = [
    {
      key: 'name',
      label: 'Nom',
      editable: true,
      align: 'center' as const,
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
      align: 'center' as const,
      onCellEdit: handleCellEdit,
      render: (value: string) => <span className="text-muted small">{value || '-'}</span>,
    },
    {
      key: 'all_asset_symbol',
      label: 'Symbole AllAsset',
      align: 'center' as const,
      render: (_value: any, row: Strategy) => (
        <span className="all-asset-symbol">
          {row?.all_asset_symbol || (typeof row.all_asset === 'object' && row.all_asset?.symbol) || 'N/A'}
        </span>
      ),
    },
    {
      key: 'yahoo_symbol',
      label: 'Symbole Yahoo',
      align: 'center' as const,
      render: (_value: any, row: Strategy) => {
        const allAsset = typeof row.all_asset === 'object' ? row.all_asset : null
        const yahooSymbol = row.all_asset_yahoo_symbol || allAsset?.symbole_yahoo
        return <span className="yahoo-symbol">{yahooSymbol || 'N/A'}</span>
      },
    },
    {
      key: 'yahoo_price',
      label: 'Prix Yahoo',
      align: 'center' as const,
      render: (_value: any, row: Strategy) => {
        const allAssetId = typeof row.all_asset === 'object' && row.all_asset?.id 
          ? row.all_asset.id 
          : (typeof row.all_asset === 'number' ? row.all_asset : null)
        const price = allAssetId ? yahooPrices[allAssetId] : null
        return price !== null && price !== undefined ? formatCurrency(price) : 'N/A'
      },
    },
    {
      key: 'asset_id',
      label: 'Asset',
      editable: true,
      cellType: 'select' as const,
      align: 'center' as const,
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
      align: 'center' as const,
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
      align: 'center' as const,
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
      align: 'center' as const,
      selectOptions: EXECUTION_MODE_OPTIONS,
      onCellEdit: handleCellEdit,
      render: (value: string) => {
        const mode = EXECUTION_MODE_OPTIONS.find(m => m.value === value)
        return <span>{mode?.label || value || '-'}</span>
      },
    },
    {
      key: 'quantity_range',
      label: 'Quantité (Min/Max)',
      editable: true, // Maintenant éditable avec deux inputs
      cellType: 'range' as const,
      rangeFields: { min: 'target_min_quantity', max: 'target_max_quantity' },
      align: 'center' as const,
      width: '140px',
      minWidth: '120px',
      onCellEdit: async (value: any, row: Strategy) => {
        // value est un objet { min, max }
        if (typeof value === 'object' && value !== null) {
          await handleCellEdit(value.min, row, 'target_min_quantity')
          await handleCellEdit(value.max, row, 'target_max_quantity')
        }
      },
      render: (_: any, row: Strategy) => {
        const minQty = parseFloat(row.target_min_quantity?.toString() || '0')
        const maxQty = parseFloat(row.target_max_quantity?.toString() || '0')
        return (
          <div style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            gap: '2px', 
            fontSize: '0.875rem', 
            lineHeight: '1.3',
            width: '100%',
            height: '100%',
            justifyContent: 'center',
            alignItems: 'center',
            textAlign: 'center'
          }}>
            <div style={{ textAlign: 'center' }}>
              <span style={{ color: '#6b7280', fontSize: '0.75rem' }}>Min: </span>
              <span style={{ color: '#3b82f6', fontWeight: '500' }}>{minQty > 0 ? minQty.toFixed(2) : '-'}</span>
            </div>
            <div style={{ textAlign: 'center' }}>
              <span style={{ color: '#6b7280', fontSize: '0.75rem' }}>Max: </span>
              <span style={{ color: '#f59e0b', fontWeight: '500' }}>{maxQty > 0 ? maxQty.toFixed(2) : '-'}</span>
            </div>
          </div>
        )
      },
    },
    {
      key: 'price_range',
      label: 'Prix (Min/Max)',
      editable: true, // Maintenant éditable avec deux inputs
      cellType: 'range' as const,
      rangeFields: { min: 'parameters.price_min', max: 'parameters.price_max' },
      align: 'center' as const,
      width: '140px',
      minWidth: '120px',
      onCellEdit: async (value: any, row: Strategy) => {
        // value est un objet { min, max }
        if (typeof value === 'object' && value !== null) {
          await handleCellEdit(value.min, row, 'price_min')
          await handleCellEdit(value.max, row, 'price_max')
        }
      },
      render: (_: any, row: Strategy) => {
        const priceMin = row.parameters?.price_min
        const priceMax = row.parameters?.price_max
        return (
          <div style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            gap: '2px', 
            fontSize: '0.875rem', 
            lineHeight: '1.3',
            width: '100%',
            height: '100%',
            justifyContent: 'center',
            alignItems: 'center',
            textAlign: 'center'
          }}>
            <div style={{ textAlign: 'center' }}>
              <span style={{ color: '#6b7280', fontSize: '0.75rem' }}>Min: </span>
              <span style={{ color: '#3b82f6', fontWeight: '500' }}>{priceMin ? formatCurrency(priceMin) : '-'}</span>
            </div>
            <div style={{ textAlign: 'center' }}>
              <span style={{ color: '#6b7280', fontSize: '0.75rem' }}>Max: </span>
              <span style={{ color: '#f59e0b', fontWeight: '500' }}>{priceMax ? formatCurrency(priceMax) : '-'}</span>
            </div>
          </div>
        )
      },
    },
    {
      key: 'portfolio_quantity',
      label: 'Portefeuille',
      align: 'center' as const,
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
      align: 'center' as const,
      render: (value: number) => value || 45,
    },
    {
      key: 'max_position_size',
      label: 'Taille Max (%)',
      editable: true,
      cellType: 'number' as const,
      onCellEdit: handleCellEdit,
      align: 'center' as const,
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
      align: 'center' as const,
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
      align: 'center' as const,
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
      align: 'center' as const,
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
      align: 'center' as const,
      onCellEdit: handleCellEdit,
      render: (value: boolean) => (value ? '✅' : '❌'),
    },
    {
      key: 'total_trades',
      label: 'Performance',
      align: 'center' as const,
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
      key: 'yahoo_actions',
      label: 'Actions Yahoo',
      align: 'center' as const,
      render: (_value: any, row: Strategy) => {
        const allAssetId = typeof row.all_asset === 'object' && row.all_asset?.id
          ? row.all_asset.id
          : (typeof row.all_asset === 'number' ? row.all_asset : null)
        return (
          <YahooActions
            allAssetId={allAssetId}
            allAssetSymbol={row?.all_asset_symbol || (typeof row.all_asset === 'object' && row.all_asset?.symbol)}
            onSuccess={() => {
              loadStrategies()
              // Recharger le prix Yahoo après succès
              if (allAssetId) {
                assetServiceUtil.getYahooCurrentPrice(allAssetId).then(price => {
                  setYahooPrices(prev => ({ ...prev, [allAssetId]: price }))
                })
              }
            }}
            compact
          />
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
                          // Suppression optimiste : retirer de l'affichage immédiatement
                          setStrategies(prevStrategies => 
                            prevStrategies.filter(s => s.id !== row.id)
                          )
                          
                          // Suppression asynchrone en arrière-plan
                          strategyService.delete(row.id).catch((err: any) => {
                            console.error('Erreur lors de la suppression:', err)
                            // En cas d'erreur, restaurer l'élément
                            loadStrategies()
                            alert(err.response?.data?.error || 'Erreur lors de la suppression')
                          })
                        } catch (err) {
                          // En cas d'erreur immédiate, recharger
                          loadStrategies()
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
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <ColumnSelector
            columns={allColumnsData}
            visibleColumns={visibleColumns}
            onColumnsChange={setVisibleColumns}
            storageKey="strategies_visible_columns"
          />
          <Button
            variant="primary"
            onClick={handleCreateNew}
          >
            Créer une stratégie
          </Button>
        </div>
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
          <Table 
            data={strategies} 
            columns={columns} 
            visibleColumns={visibleColumns.length > 0 ? visibleColumns : undefined} 
          />
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
