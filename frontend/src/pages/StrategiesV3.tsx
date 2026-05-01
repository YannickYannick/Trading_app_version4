/**
 * StrategiesV3 - Interface style terminal de trading
 * Inspiré de bot-bloom-forge
 */
import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { strategyService, assetService, positionService } from '@services'
import strategyExecutionService, { type StrategyExecution } from '@services/strategyExecutionService'
import { useToast } from '@hooks/useToast'
import type { Strategy, AllAsset, Position } from '@types'
import StrategyVisualizationChart from '@components/strategies/StrategyVisualizationChart'
import './StrategiesV3.css'

const ALGORITHM_LABELS: Record<string, string> = {
  threshold: 'Threshold',
  ma_crossover: 'MA Cross',
  rsi: 'RSI',
  bollinger: 'Bollinger',
  macd: 'MACD',
  grid: 'Grid',
}

const ALGORITHM_PARAMS: Record<string, { key: string; label: string; default: number }[]> = {
  threshold: [
    { key: 'threshold_low', label: 'Seuil bas', default: 60000 },
    { key: 'threshold_high', label: 'Seuil haut', default: 68000 },
  ],
  ma_crossover: [
    { key: 'ma1_period', label: 'MA courte', default: 20 },
    { key: 'ma2_period', label: 'MA longue', default: 50 },
  ],
  rsi: [
    { key: 'rsi_period', label: 'Période', default: 14 },
    { key: 'rsi_low', label: 'Seuil bas', default: 30 },
    { key: 'rsi_high', label: 'Seuil haut', default: 70 },
  ],
  bollinger: [
    { key: 'bb_period', label: 'Période', default: 20 },
    { key: 'bb_std', label: 'Écart-type', default: 2 },
  ],
  macd: [
    { key: 'macd_fast', label: 'Rapide', default: 12 },
    { key: 'macd_slow', label: 'Lent', default: 26 },
    { key: 'macd_signal', label: 'Signal', default: 9 },
  ],
  grid: [
    { key: 'grid_min', label: 'Prix min', default: 2800 },
    { key: 'grid_max', label: 'Prix max', default: 3600 },
    { key: 'grid_levels', label: 'Niveaux', default: 10 },
  ],
}

const MODE_LABELS: Record<string, string> = {
  simulation: 'SIM',
  paper_trading: 'PAPER',
  live_trading: 'LIVE',
}

export default function StrategiesV3() {
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [executions, setExecutions] = useState<StrategyExecution[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  
  // Inline edit state
  const [inlineEdit, setInlineEdit] = useState<Record<number, Record<string, any>>>({})
  const [savingId, setSavingId] = useState<number | null>(null)
  
  // Asset search state (autocomplete like Orders page)
  const [assetSearchQuery, setAssetSearchQuery] = useState('')
  const [autocompleteResults, setAutocompleteResults] = useState<any[]>([])
  const [loadingAutocomplete, setLoadingAutocomplete] = useState(false)
  const [showAssetDropdown, setShowAssetDropdown] = useState<number | null>(null)
  const autocompleteTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const assetDropdownRef = useRef<HTMLDivElement>(null)
  
  // Execution details modal state
  const [executionModalOpen, setExecutionModalOpen] = useState(false)
  const [executionResult, setExecutionResult] = useState<any>(null)
  const [executingId, setExecutingId] = useState<number | null>(null)
  
  // Yahoo data sync state
  const [syncingYahooId, setSyncingYahooId] = useState<number | null>(null)
  const [yahooSyncResult, setYahooSyncResult] = useState<Record<number, { success: boolean; message: string }>>({})
  
  // Chart period state (per strategy)
  const [chartPeriods, setChartPeriods] = useState<Record<number, number>>({})
  
  // Key to force chart remount after sync
  const [chartKey, setChartKey] = useState(0)
  
  // Portfolio positions for "Create from portfolio" feature
  const [positions, setPositions] = useState<Position[]>([])
  const [portfolioModalOpen, setPortfolioModalOpen] = useState(false)
  const [loadingPositions, setLoadingPositions] = useState(false)
  
  // Asset association modal (for strategies without asset)
  const [assetAssociationModal, setAssetAssociationModal] = useState<{ strategyId: number; strategyName: string } | null>(null)
  const [associationSearchQuery, setAssociationSearchQuery] = useState('')
  const [associationResults, setAssociationResults] = useState<any[]>([])
  const [associationLoading, setAssociationLoading] = useState(false)
  const [associating, setAssociating] = useState(false)
  const associationTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  
  // Filters
  const [search, setSearch] = useState('')
  const [filterAlgo, setFilterAlgo] = useState('all')
  const [filterStatus, setFilterStatus] = useState('all')
  
  // Wizard
  const [wizardOpen, setWizardOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<Strategy | null>(null)
  const [wizardStep, setWizardStep] = useState(0)
  const [wizardData, setWizardData] = useState({
    name: '',
    description: '',
    asset: '',
    algorithm_type: 'threshold',
    parameters: {} as Record<string, number>,
    execution_mode: 'simulation',
    risk_level: 'MEDIUM',
    is_automated: false,
    target_min_quantity: 0.001,
    target_max_quantity: 1,
    check_frequency: 5,
  })

  // Time display
  const [currentTime, setCurrentTime] = useState(new Date())
  
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  // Close asset dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (assetDropdownRef.current && !assetDropdownRef.current.contains(e.target as Node)) {
        setShowAssetDropdown(null)
        setAssetSearchQuery('')
        setAutocompleteResults([])
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Search assets with autocomplete (like Orders page)
  const handleAssetSearch = useCallback((query: string) => {
    setAssetSearchQuery(query)
    
    if (autocompleteTimeoutRef.current) {
      clearTimeout(autocompleteTimeoutRef.current)
    }
    
    if (query.length < 2) {
      setAutocompleteResults([])
      return
    }
    
    setLoadingAutocomplete(true)
    autocompleteTimeoutRef.current = setTimeout(async () => {
      try {
        const results = await assetService.autocompleteAllAssets(query)
        setAutocompleteResults(results.slice(0, 15))
      } catch (err) {
        console.error('Erreur recherche assets:', err)
        setAutocompleteResults([])
      } finally {
        setLoadingAutocomplete(false)
      }
    }, 200)
  }, [])

  const handleAssetSelect = (strategyId: number, asset: any) => {
    updateInlineEdit(strategyId, 'all_asset', asset.id)
    updateInlineEdit(strategyId, 'all_asset_name', asset.name || asset.symbol)
    updateInlineEdit(strategyId, 'all_asset_symbol', asset.symbol)
    setAssetSearchQuery(asset.symbol)
    setShowAssetDropdown(null)
    setAutocompleteResults([])
  }

  // Search for asset association
  const handleAssociationSearch = useCallback((query: string) => {
    setAssociationSearchQuery(query)
    
    if (associationTimeoutRef.current) {
      clearTimeout(associationTimeoutRef.current)
    }
    
    if (query.length < 2) {
      setAssociationResults([])
      return
    }
    
    setAssociationLoading(true)
    associationTimeoutRef.current = setTimeout(async () => {
      try {
        const results = await assetService.autocompleteAllAssets(query)
        setAssociationResults(results.slice(0, 15))
      } catch (err) {
        console.error('Erreur recherche assets:', err)
        setAssociationResults([])
      } finally {
        setAssociationLoading(false)
      }
    }, 200)
  }, [])

  // Associate asset to strategy and sync Yahoo
  const handleAssociateAndSync = async (strategyId: number, asset: any) => {
    setAssociating(true)
    try {
      // Update strategy with asset
      await strategyService.update(strategyId, {
        all_asset: asset.id
      })
      
      // Close modal
      setAssetAssociationModal(null)
      setAssociationSearchQuery('')
      setAssociationResults([])
      
      // Reload data to get updated strategy
      await loadData()
      
      // Now sync Yahoo data
      setSyncingYahooId(strategyId)
      setYahooSyncResult(prev => ({ ...prev, [strategyId]: { success: false, message: 'Association OK, synchronisation...' } }))
      
      await assetService.validateYahoo(asset.id)
      const periodDays = chartPeriods[strategyId] || 365
      const result = await assetService.syncPriceHistory(asset.id, periodDays, '1d')
      
      if (result.success) {
        setYahooSyncResult(prev => ({
          ...prev,
          [strategyId]: { success: true, message: `${result.records || 0} points chargés` }
        }))
        setChartKey(prev => prev + 1)
      } else {
        setYahooSyncResult(prev => ({
          ...prev,
          [strategyId]: { success: false, message: result.error || 'Erreur sync' }
        }))
      }
    } catch (err: any) {
      setYahooSyncResult(prev => ({
        ...prev,
        [strategyId]: { success: false, message: err?.message || 'Erreur association' }
      }))
    } finally {
      setAssociating(false)
      setSyncingYahooId(null)
    }
  }

  // Sync Yahoo price data for a strategy's asset
  const handleSyncYahoo = async (s: Strategy) => {
    const assetId = getAssetId(s)
    if (!assetId) {
      // Open asset association modal instead of alert
      setAssetAssociationModal({ strategyId: s.id, strategyName: s.name })
      // Pre-fill search with strategy name (might help find the asset)
      const searchHint = s.name.split(' ')[0] || ''
      if (searchHint.length >= 2) {
        handleAssociationSearch(searchHint)
      }
      return
    }

    setSyncingYahooId(s.id)
    setYahooSyncResult(prev => ({ ...prev, [s.id]: { success: false, message: 'Synchronisation...' } }))

    try {
      // First validate Yahoo symbol if needed
      await assetService.validateYahoo(assetId)
      
      // Then sync price history (use selected period, default 365 days)
      const periodDays = chartPeriods[s.id] || 365
      const result = await assetService.syncPriceHistory(assetId, periodDays, '1d')
      
      if (result.success) {
        setYahooSyncResult(prev => ({
          ...prev,
          [s.id]: { success: true, message: `${result.records || 0} points chargés` }
        }))
        // Force chart remount to reload data
        setChartKey(prev => prev + 1)
      } else {
        setYahooSyncResult(prev => ({
          ...prev,
          [s.id]: { success: false, message: result.error || 'Erreur inconnue' }
        }))
      }
    } catch (err: any) {
      setYahooSyncResult(prev => ({
        ...prev,
        [s.id]: { success: false, message: err?.response?.data?.error || err?.message || 'Erreur de synchronisation' }
      }))
    } finally {
      setSyncingYahooId(null)
    }
  }

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      const [stratResponse, execResponse] = await Promise.all([
        strategyService.getAll(),
        strategyExecutionService.getRecent(),
      ])
      const list = Array.isArray(stratResponse) ? stratResponse : (stratResponse.results || [])
      setStrategies(list)
      setExecutions(execResponse)
    } catch (err) {
      console.error('Erreur chargement:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  const loadPositions = useCallback(async () => {
    setLoadingPositions(true)
    try {
      const openPositions = await positionService.getOpen()
      setPositions(openPositions)
    } catch (err) {
      console.error('Erreur chargement positions:', err)
    } finally {
      setLoadingPositions(false)
    }
  }, [])

  const openPortfolioModal = () => {
    loadPositions()
    setPortfolioModalOpen(true)
  }

  const createFromPosition = (position: Position) => {
    setPortfolioModalOpen(false)
    
    // Pre-fill wizard with position's asset
    // Priority: all_asset_id (flat) > all_asset.id (nested object) > all_asset (if number) > asset.id
    let assetId: number | undefined
    
    if (position.all_asset_id) {
      assetId = position.all_asset_id
    } else if (typeof position.all_asset === 'object' && position.all_asset?.id) {
      assetId = position.all_asset.id
    } else if (typeof position.all_asset === 'number') {
      assetId = position.all_asset
    } else if (typeof position.asset === 'object' && position.asset?.id) {
      assetId = position.asset.id
    }
    
    const assetSymbol = position.all_asset_symbol || position.symbol || ''
    const assetName = position.all_asset_name 
      || (typeof position.all_asset === 'object' ? position.all_asset?.name : null) 
      || assetSymbol
    
    console.log('[createFromPosition] Position:', position)
    console.log('[createFromPosition] Asset ID:', assetId, 'Symbol:', assetSymbol, 'Name:', assetName)
    
    if (!assetId) {
      console.warn('[createFromPosition] No asset ID found in position!')
    }
    
    const defaults: Record<string, number> = {}
    ALGORITHM_PARAMS['threshold'].forEach(p => { defaults[p.key] = p.default })
    
    setEditTarget(null)
    setWizardData({
      name: `Stratégie ${assetName}`,
      description: `Stratégie automatique pour ${assetSymbol}`,
      asset: assetId?.toString() || '',
      algorithm_type: 'threshold',
      parameters: defaults,
      execution_mode: 'simulation',
      risk_level: 'MEDIUM',
      is_automated: false,
      target_min_quantity: Math.min(position.quantity || 1, 1),
      target_max_quantity: position.quantity || 10,
      check_frequency: 60,
      // Store asset info for wizard
      all_asset_id: assetId,
      all_asset_symbol: assetSymbol,
      all_asset_name: assetName,
    } as any)
    setWizardStep(0)
    setWizardOpen(true)
  }

  useEffect(() => {
    loadData()
  }, [loadData])

  // Initialize inline edit state when expanding a strategy
  const initInlineEdit = (s: Strategy) => {
    if (!inlineEdit[s.id]) {
      const params = s.parameters || {}
      setInlineEdit(prev => ({
        ...prev,
        [s.id]: {
          algorithm_type: s.algorithm_type || 'threshold',
          risk_level: s.risk_level || 'MEDIUM',
          target_min_quantity: s.target_min_quantity ?? 1,
          target_max_quantity: s.target_max_quantity ?? 10,
          check_frequency: s.check_frequency ?? 45,
          is_automated: s.is_automated ?? false,
          all_asset: getAssetId(s),
          all_asset_name: getAssetName(s),
          all_asset_symbol: getAssetSymbol(s),
          ...params,
        }
      }))
    }
  }

  const updateInlineEdit = (strategyId: number, key: string, value: any) => {
    setInlineEdit(prev => ({
      ...prev,
      [strategyId]: {
        ...prev[strategyId],
        [key]: value,
      }
    }))
  }

  const saveInlineEdit = async (s: Strategy) => {
    const edits = inlineEdit[s.id]
    if (!edits) return

    setSavingId(s.id)
    try {
      // Separate algo params from strategy fields
      const algoParamKeys = ALGORITHM_PARAMS[edits.algorithm_type || s.algorithm_type || 'threshold']?.map(p => p.key) || []
      const parameters: Record<string, number> = {}
      algoParamKeys.forEach(key => {
        if (edits[key] !== undefined) {
          parameters[key] = parseFloat(edits[key]) || 0
        }
      })

      const updateData: Record<string, any> = {
        algorithm_type: edits.algorithm_type,
        risk_level: edits.risk_level,
        target_min_quantity: parseFloat(edits.target_min_quantity) || 0,
        target_max_quantity: parseFloat(edits.target_max_quantity) || 0,
        check_frequency: parseInt(edits.check_frequency) || 45,
        is_automated: edits.is_automated,
        parameters,
      }

      // Include asset if modified
      if (edits.all_asset && edits.all_asset !== getAssetId(s)) {
        updateData.all_asset = edits.all_asset
      }

      await strategyService.update(s.id, updateData)
      
      loadData()
    } catch (err) {
      console.error('Erreur sauvegarde:', err)
      alert('Erreur lors de la sauvegarde')
    } finally {
      setSavingId(null)
    }
  }

  // Filtered strategies
  const filtered = useMemo(() => {
    return strategies.filter(s => {
      if (filterAlgo !== 'all' && s.algorithm_type !== filterAlgo) return false
      if (filterStatus === 'active' && !s.is_active) return false
      if (filterStatus === 'inactive' && s.is_active) return false
      if (search) {
        const q = search.toLowerCase()
        if (!s.name.toLowerCase().includes(q) && !(s.all_asset_symbol || '').toLowerCase().includes(q)) {
          return false
        }
      }
      return true
    })
  }, [strategies, filterAlgo, filterStatus, search])

  // KPIs
  const activeCount = strategies.filter(s => s.is_active).length
  const totalPnl = strategies.reduce((sum, s) => sum + parseFloat(s.total_pnl?.toString() || '0'), 0)
  const totalTrades = strategies.reduce((sum, s) => sum + (s.total_trades || 0), 0)
  const failedExecs = executions.filter(e => e.status === 'failed').length
  const buySignals = executions.filter(e => e.signal === 'BUY').length
  const sellSignals = executions.filter(e => e.signal === 'SELL').length

  // Handlers
  const handleToggle = async (s: Strategy) => {
    try {
      await strategyService.toggleActive(s.id, !s.is_active)
      loadData()
    } catch (err) {
      alert('Erreur lors de la modification')
    }
  }

  const handleExecute = async (s: Strategy) => {
    setExecutingId(s.id)
    try {
      const result = await strategyExecutionService.execute(s.id)
      setExecutionResult({
        strategy: s,
        ...result
      })
      setExecutionModalOpen(true)
      loadData()
    } catch (err: any) {
      setExecutionResult({
        strategy: s,
        status: 'error',
        error: err?.response?.data?.error || err?.message || 'Erreur lors de l\'exécution'
      })
      setExecutionModalOpen(true)
    } finally {
      setExecutingId(null)
    }
  }

  const handleDuplicate = async (s: Strategy) => {
    try {
      await strategyService.create({
        name: `${s.name} (copie)`,
        description: s.description,
        risk_level: s.risk_level,
        is_active: false,
        is_automated: false,
      })
      loadData()
    } catch (err) {
      alert('Erreur lors de la duplication')
    }
  }

  const handleDelete = async (s: Strategy) => {
    if (!window.confirm(`Supprimer "${s.name}" ?`)) return
    try {
      await strategyService.delete(s.id)
      if (expandedId === s.id) setExpandedId(null)
      loadData()
    } catch (err) {
      alert('Erreur lors de la suppression')
    }
  }

  const openWizard = (strategy?: Strategy) => {
    if (strategy) {
      setEditTarget(strategy)
      setWizardData({
        name: strategy.name,
        description: strategy.description || '',
        asset: strategy.all_asset_symbol || '',
        algorithm_type: strategy.algorithm_type || 'threshold',
        parameters: strategy.parameters || {},
        execution_mode: strategy.execution_mode || 'simulation',
        risk_level: strategy.risk_level || 'MEDIUM',
        is_automated: strategy.is_automated || false,
        target_min_quantity: strategy.target_min_quantity || 0.001,
        target_max_quantity: strategy.target_max_quantity || 1,
        check_frequency: strategy.check_frequency || 5,
      })
    } else {
      setEditTarget(null)
      const defaults: Record<string, number> = {}
      ALGORITHM_PARAMS['threshold'].forEach(p => { defaults[p.key] = p.default })
      setWizardData({
        name: '',
        description: '',
        asset: '',
        algorithm_type: 'threshold',
        parameters: defaults,
        execution_mode: 'simulation',
        risk_level: 'MEDIUM',
        is_automated: false,
        target_min_quantity: 0.001,
        target_max_quantity: 1,
        check_frequency: 5,
      })
    }
    setWizardStep(0)
    setWizardOpen(true)
  }

  const handleWizardAlgoChange = (algo: string) => {
    const defaults: Record<string, number> = {}
    ALGORITHM_PARAMS[algo]?.forEach(p => { defaults[p.key] = p.default })
    setWizardData(prev => ({ ...prev, algorithm_type: algo, parameters: defaults }))
  }

  const handleWizardSave = async () => {
    try {
      if (editTarget) {
        await strategyService.update(editTarget.id, {
          name: wizardData.name,
          description: wizardData.description,
          algorithm_type: wizardData.algorithm_type,
          execution_mode: wizardData.execution_mode,
          risk_level: wizardData.risk_level as 'LOW' | 'MEDIUM' | 'HIGH',
          is_automated: wizardData.is_automated,
          target_min_quantity: wizardData.target_min_quantity,
          target_max_quantity: wizardData.target_max_quantity,
          check_frequency: wizardData.check_frequency,
          parameters: wizardData.parameters,
        })
      } else {
        // Build create data with all fields including asset
        const createData: any = {
          name: wizardData.name || `${(wizardData as any).all_asset_symbol || wizardData.asset} ${ALGORITHM_LABELS[wizardData.algorithm_type]}`,
          description: wizardData.description,
          risk_level: wizardData.risk_level as 'LOW' | 'MEDIUM' | 'HIGH',
          is_active: false,
          is_automated: wizardData.is_automated,
          algorithm_type: wizardData.algorithm_type,
          execution_mode: wizardData.execution_mode,
          target_min_quantity: wizardData.target_min_quantity,
          target_max_quantity: wizardData.target_max_quantity,
          check_frequency: wizardData.check_frequency,
          parameters: wizardData.parameters,
        }
        
        // Include asset if set (from "Create from portfolio" or manual selection)
        const assetId = (wizardData as any).all_asset_id
        if (assetId) {
          createData.all_asset = assetId
        }
        
        await strategyService.create(createData)
      }
      setWizardOpen(false)
      loadData()
    } catch (err) {
      alert('Erreur lors de la sauvegarde')
    }
  }

  const getAssetSymbol = (s: Strategy) => {
    return s.all_asset_symbol || (typeof s.all_asset === 'object' ? s.all_asset?.symbol : null) || 'N/A'
  }

  const getAssetName = (s: Strategy) => {
    return s.all_asset_name || (typeof s.all_asset === 'object' ? s.all_asset?.name : null) || getAssetSymbol(s)
  }

  const getAssetId = (s: Strategy): number | null => {
    if (typeof s.all_asset === 'number') return s.all_asset
    if (typeof s.all_asset === 'object' && s.all_asset?.id) return s.all_asset.id
    return null
  }

  // Helper to detect duplicate strategies by asset
  const usedAssetIds = useMemo(() => {
    return new Set(
      strategies
        .map(s => getAssetId(s))
        .filter((id): id is number => id !== null)
    )
  }, [strategies])

  const hasStrategyForAsset = useCallback((assetId: number | null | undefined, excludeStrategyId?: number): boolean => {
    if (!assetId) return false
    // Check if any strategy (except the one being edited) uses this asset
    return strategies.some(s => {
      if (excludeStrategyId && s.id === excludeStrategyId) return false
      return getAssetId(s) === assetId
    })
  }, [strategies])

  const formatPnl = (val: number) => {
    return (val >= 0 ? '+' : '') + val.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })
  }

  return (
    <div className="strategies-v3">
      {/* Header */}
      <header className="v3-header">
        <div className="v3-header-left">
          <div className="v3-header-title">
            <span className="label">Trading Terminal</span>
            <span className="title">Stratégies</span>
          </div>
          <div className="v3-header-status">
            <span className="label-xs">Status</span>
            <span className="status-label">
              <span className="status-dot" />
              SYSTEM_NOMINAL
            </span>
          </div>
        </div>
        <div className="v3-header-right">
          <span className="v3-time-badge">
            {currentTime.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </span>
          <button className="v3-btn-secondary" onClick={openPortfolioModal}>
            📂 Depuis portefeuille
          </button>
          <button className="v3-btn-primary" onClick={() => openWizard()}>
            + Nouvelle Stratégie
          </button>
        </div>
      </header>

      {/* KPI Cluster */}
      <div className="v3-kpi-grid">
        <div className="v3-kpi-card instrument-panel">
          <span className="kpi-label">Actives</span>
          <span className="kpi-value">
            {activeCount}
            <span className="kpi-secondary">/ {strategies.length}</span>
          </span>
          <div className="kpi-bar">
            <div className="kpi-bar-fill" style={{ width: `${strategies.length > 0 ? (activeCount / strategies.length) * 100 : 0}%` }} />
          </div>
        </div>

        <div className="v3-kpi-card instrument-panel">
          <span className="kpi-label">PnL Total</span>
          <span className={`kpi-value ${totalPnl >= 0 ? 'text-signal-green' : 'text-signal-red'}`}>
            {formatPnl(totalPnl)}
          </span>
        </div>

        <div className="v3-kpi-card instrument-panel">
          <span className="kpi-label">Signaux (24h)</span>
          <span className="kpi-value">{executions.length}</span>
          <div className="kpi-breakdown">
            <span className="text-signal-green">{buySignals} BUY</span>
            <span className="text-signal-red">{sellSignals} SELL</span>
          </div>
        </div>

        <div className="v3-kpi-card instrument-panel">
          <span className="kpi-label">Trades</span>
          <span className="kpi-value">{totalTrades.toLocaleString()}</span>
        </div>

        <div className="v3-kpi-card instrument-panel">
          <span className="kpi-label">Erreurs</span>
          <span className={`kpi-value ${failedExecs > 0 ? 'text-signal-red' : 'text-signal-green'}`}>
            {failedExecs}
          </span>
        </div>
      </div>

      {/* Filters */}
      <div className="v3-filters">
        <input
          type="text"
          className="v3-search-input"
          placeholder="Rechercher..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <select className="v3-filter-select" value={filterAlgo} onChange={e => setFilterAlgo(e.target.value)}>
          <option value="all">Tous les algos</option>
          {Object.entries(ALGORITHM_LABELS).map(([key, label]) => (
            <option key={key} value={key}>{label}</option>
          ))}
        </select>
        <select className="v3-filter-select" value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
          <option value="all">Tous les statuts</option>
          <option value="active">Actives</option>
          <option value="inactive">Inactives</option>
        </select>
        <span className="v3-filter-count">
          {filtered.length} stratégie{filtered.length > 1 ? 's' : ''} affichée{filtered.length > 1 ? 's' : ''}
        </span>
      </div>

      {/* Strategy List */}
      <div className="v3-strategy-list">
        <h2 className="v3-section-title">Stratégies</h2>
        
        {loading ? (
          <div className="v3-empty instrument-panel">Chargement...</div>
        ) : filtered.length === 0 ? (
          <div className="v3-empty instrument-panel">Aucune stratégie trouvée</div>
        ) : (
          filtered.map(s => (
            <div key={s.id} className="v3-strategy-card instrument-panel">
              {/* Main Row */}
              <div className="v3-strategy-main" onClick={() => setExpandedId(expandedId === s.id ? null : s.id)}>
                <div className="v3-strategy-info">
                  <div className="v3-strategy-badges">
                    <span className={`v3-algo-badge ${s.algorithm_type}`}>
                      {ALGORITHM_LABELS[s.algorithm_type || ''] || s.algorithm_type}
                    </span>
                    <span className="v3-asset-name">{getAssetName(s)}</span>
                    <span className={`v3-mode-tag ${s.execution_mode}`}>
                      [{MODE_LABELS[s.execution_mode || ''] || s.execution_mode || 'SIM'}]
                    </span>
                  </div>
                  <span className="v3-strategy-meta">{s.name} · {getAssetSymbol(s)} · ID-{s.id}</span>
                </div>

                <div className="v3-strategy-metrics">
                  <div className="v3-metric">
                    <span className="v3-metric-label">PnL</span>
                    <span className={`v3-metric-value ${parseFloat(s.total_pnl?.toString() || '0') >= 0 ? 'text-signal-green' : 'text-signal-red'}`}>
                      {formatPnl(parseFloat(s.total_pnl?.toString() || '0'))}
                    </span>
                  </div>
                  <div className="v3-metric">
                    <span className="v3-metric-label">Win Rate</span>
                    <span className="v3-metric-value">
                      {s.total_trades && s.successful_trades ? ((s.successful_trades / s.total_trades) * 100).toFixed(0) : 0}%
                    </span>
                  </div>
                  <div className="v3-metric">
                    <span className="v3-metric-label">Risque</span>
                    <span className={`v3-metric-value ${s.risk_level === 'HIGH' ? 'text-signal-red' : s.risk_level === 'MEDIUM' ? 'text-signal-yellow' : 'text-signal-green'}`}>
                      {s.risk_level}
                    </span>
                  </div>
                  <div className="v3-metric">
                    <span className="v3-metric-label">Trades</span>
                    <span className="v3-metric-value">{s.total_trades || 0}</span>
                  </div>
                </div>

                <div className="v3-strategy-right">
                  <div className="v3-status-cell">
                    <span className="label-xs">Status</span>
                    <div className="v3-status-indicator">
                      <span className={`v3-status-dot ${s.is_active ? 'active' : 'inactive'}`} />
                      <span className={`v3-status-label ${s.is_active ? 'active' : 'inactive'}`}>
                        {s.is_active ? 'RUNNING' : 'PAUSED'}
                      </span>
                    </div>
                  </div>
                  <div className="v3-actions" onClick={e => e.stopPropagation()}>
                    <button
                      className={`v3-action-btn ${s.is_active ? '' : 'run'}`}
                      onClick={() => handleToggle(s)}
                    >
                      {s.is_active ? 'PAU' : 'RUN'}
                    </button>
                    <button className="v3-action-btn" onClick={() => openWizard(s)}>CFG</button>
                    <button 
                      className={`v3-action-btn ${executingId === s.id ? 'executing' : ''}`}
                      onClick={() => handleExecute(s)}
                      disabled={executingId === s.id}
                    >
                      {executingId === s.id ? '...' : 'EXE'}
                    </button>
                    <button className="v3-action-btn" onClick={() => handleDuplicate(s)}>DUP</button>
                    <button className="v3-action-btn delete" onClick={() => handleDelete(s)}>X</button>
                  </div>
                </div>
              </div>

              {/* Expanded */}
              {expandedId === s.id && (() => {
                initInlineEdit(s)
                const edits = inlineEdit[s.id] || {}
                const currentAlgo = edits.algorithm_type || s.algorithm_type || 'threshold'
                const algoParams = ALGORITHM_PARAMS[currentAlgo] || []
                
                return (
                  <div className="v3-strategy-expanded">
                    <div className="v3-chart-section">
                      <div className="v3-chart-header">
                        <h4>Prix & Signaux — {edits.all_asset_name || getAssetName(s)}</h4>
                        <button
                          className={`v3-sync-btn ${syncingYahooId === s.id ? 'syncing' : ''} ${yahooSyncResult[s.id]?.success ? 'success' : ''}`}
                          onClick={(e) => { e.stopPropagation(); handleSyncYahoo(s); }}
                          disabled={syncingYahooId === s.id}
                        >
                          {syncingYahooId === s.id ? '⏳ Chargement...' : '📊 Charger données Yahoo'}
                        </button>
                      </div>
                      {yahooSyncResult[s.id] && (
                        <div className={`v3-sync-message ${yahooSyncResult[s.id].success ? 'success' : 'error'}`}>
                          {yahooSyncResult[s.id].success ? '✓' : '✕'} {yahooSyncResult[s.id].message}
                        </div>
                      )}
                      <StrategyVisualizationChart
                        key={`chart-${s.id}-${chartKey}`}
                        strategy={s}
                        parameters={edits}
                        initialPeriod={chartPeriods[s.id] || 365}
                        onPeriodChange={(days) => setChartPeriods(prev => ({ ...prev, [s.id]: days }))}
                      />
                    </div>
                    <div className="v3-config-section">
                      <div className="v3-config-header">
                        <h4>Configuration</h4>
                        <button 
                          className="v3-save-btn"
                          onClick={(e) => { e.stopPropagation(); saveInlineEdit(s); }}
                          disabled={savingId === s.id}
                        >
                          {savingId === s.id ? 'Sauvegarde...' : '✓ Sauvegarder'}
                        </button>
                      </div>
                      <div className="v3-config-list">
                        {/* Algorithme */}
                        <div className="v3-config-row">
                          <span className="config-key">Algorithme</span>
                          <select
                            className="v3-inline-select"
                            value={currentAlgo}
                            onChange={(e) => {
                              updateInlineEdit(s.id, 'algorithm_type', e.target.value)
                              // Reset params to defaults for new algo
                              const newParams = ALGORITHM_PARAMS[e.target.value] || []
                              newParams.forEach(p => {
                                updateInlineEdit(s.id, p.key, p.default)
                              })
                            }}
                            onClick={(e) => e.stopPropagation()}
                          >
                            {Object.entries(ALGORITHM_LABELS).map(([key, label]) => (
                              <option key={key} value={key}>{label}</option>
                            ))}
                          </select>
                        </div>
                        
                        {/* Algo Parameters */}
                        {algoParams.map(param => (
                          <div key={param.key} className="v3-config-row">
                            <span className="config-key">{param.label}</span>
                            <input
                              type="number"
                              className="v3-inline-input"
                              value={edits[param.key] ?? param.default}
                              onChange={(e) => updateInlineEdit(s.id, param.key, e.target.value)}
                              onClick={(e) => e.stopPropagation()}
                              step="any"
                            />
                          </div>
                        ))}
                        
                        <div className="v3-config-separator" />
                        
                        {/* Asset Selection - Autocomplete like Orders page */}
                        <div className="v3-config-row asset-config">
                          <span className="config-key">Asset</span>
                          <div className="v3-asset-selector" ref={showAssetDropdown === s.id ? assetDropdownRef : null} onClick={(e) => e.stopPropagation()}>
                            <input
                              type="text"
                              className="v3-asset-input"
                              placeholder="Rechercher un asset..."
                              value={showAssetDropdown === s.id ? assetSearchQuery : (edits.all_asset_symbol || getAssetSymbol(s))}
                              onChange={(e) => handleAssetSearch(e.target.value)}
                              onFocus={() => {
                                setShowAssetDropdown(s.id)
                                setAssetSearchQuery('')
                              }}
                              onBlur={() => {
                                setTimeout(() => {
                                  setShowAssetDropdown(null)
                                  setAssetSearchQuery('')
                                  setAutocompleteResults([])
                                }, 200)
                              }}
                            />
                            {showAssetDropdown === s.id && (
                              <div className="v3-autocomplete-dropdown">
                                {loadingAutocomplete ? (
                                  <div className="v3-autocomplete-item loading">Recherche...</div>
                                ) : assetSearchQuery.length >= 2 && autocompleteResults.length === 0 ? (
                                  <div className="v3-autocomplete-item empty">Aucun résultat</div>
                                ) : (
                                  autocompleteResults.map(asset => {
                                    const isUsed = hasStrategyForAsset(asset.id, s.id)
                                    return (
                                      <div
                                        key={asset.id}
                                        className={`v3-autocomplete-item ${isUsed ? 'disabled' : ''}`}
                                        onMouseDown={(e) => e.preventDefault()}
                                        onClick={() => !isUsed && handleAssetSelect(s.id, asset)}
                                      >
                                        <span className="autocomplete-symbol">{asset.symbol}</span>
                                        <span className="autocomplete-name">{asset.name}</span>
                                        <span className="autocomplete-platform">{asset.platform}</span>
                                        {isUsed && <span className="autocomplete-used">Utilisé</span>}
                                      </div>
                                    )
                                  })
                                )}
                              </div>
                            )}
                            {edits.all_asset && edits.all_asset !== getAssetId(s) && (
                              <span className="asset-changed-badge">Modifié</span>
                            )}
                          </div>
                        </div>
                        
                        {/* Broker (read-only) */}
                        <div className="v3-config-row">
                          <span className="config-key">Broker</span>
                          <span className="config-value">{s.broker_name || 'N/A'}</span>
                        </div>
                        
                        {/* Risk Level */}
                        <div className="v3-config-row">
                          <span className="config-key">Risque</span>
                          <div className="v3-inline-options" onClick={(e) => e.stopPropagation()}>
                            {['LOW', 'MEDIUM', 'HIGH'].map(level => (
                              <button
                                key={level}
                                className={`v3-inline-option ${edits.risk_level === level ? 'selected' : ''} risk-${level.toLowerCase()}`}
                                onClick={() => updateInlineEdit(s.id, 'risk_level', level)}
                              >
                                {level}
                              </button>
                            ))}
                          </div>
                        </div>
                        
                        {/* Quantity Range */}
                        <div className="v3-config-row">
                          <span className="config-key">Quantité</span>
                          <div className="v3-inline-range" onClick={(e) => e.stopPropagation()}>
                            <input
                              type="number"
                              className="v3-inline-input small"
                              value={edits.target_min_quantity ?? s.target_min_quantity ?? 1}
                              onChange={(e) => updateInlineEdit(s.id, 'target_min_quantity', e.target.value)}
                              step="any"
                            />
                            <span className="range-separator">–</span>
                            <input
                              type="number"
                              className="v3-inline-input small"
                              value={edits.target_max_quantity ?? s.target_max_quantity ?? 10}
                              onChange={(e) => updateInlineEdit(s.id, 'target_max_quantity', e.target.value)}
                              step="any"
                            />
                          </div>
                        </div>
                        
                        {/* Frequency */}
                        <div className="v3-config-row">
                          <span className="config-key">Fréquence</span>
                          <div className="v3-inline-range" onClick={(e) => e.stopPropagation()}>
                            <input
                              type="number"
                              className="v3-inline-input small"
                              value={edits.check_frequency ?? s.check_frequency ?? 45}
                              onChange={(e) => updateInlineEdit(s.id, 'check_frequency', e.target.value)}
                              min={1}
                            />
                            <span className="range-unit">min</span>
                          </div>
                        </div>
                        
                        {/* Automated */}
                        <div className="v3-config-row">
                          <span className="config-key">Automatisé</span>
                          <button
                            className={`v3-inline-toggle ${edits.is_automated ? 'active' : ''}`}
                            onClick={(e) => { e.stopPropagation(); updateInlineEdit(s.id, 'is_automated', !edits.is_automated); }}
                          >
                            {edits.is_automated ? '✓ OUI' : 'NON'}
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })()}
            </div>
          ))
        )}
      </div>

      {/* Execution Log */}
      <div className="v3-execution-log instrument-panel">
        <div className="v3-log-header">
          <span className="label-xs">Exécutions Récentes</span>
          <span className="font-mono" style={{ fontSize: '9px', color: 'hsl(240, 4%, 40%)' }}>
            {executions.length} entrées
          </span>
        </div>
        <div className="v3-log-list">
          {executions.slice(0, 20).map(ex => {
            const strat = strategies.find(s => s.id === ex.strategy_id || s.id === ex.strategy)
            return (
              <div key={ex.id} className="v3-log-item">
                <span className="v3-log-time">
                  {new Date(ex.started_at).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
                <span className={`v3-log-status ${ex.status}`}>{ex.status}</span>
                <span className={`v3-log-signal ${ex.signal}`}>{ex.signal}</span>
                <span className="v3-log-strategy">{strat?.name || `ID-${ex.strategy_id}`}</span>
                {ex.signal_price && ex.signal_price > 0 && (
                  <span className="v3-log-price">@ {Number(ex.signal_price).toLocaleString()} €</span>
                )}
                {ex.error && <span className="v3-log-error">{ex.error}</span>}
              </div>
            )
          })}
          {executions.length === 0 && (
            <div className="v3-log-item">
              <span style={{ color: 'hsl(240, 4%, 40%)' }}>Aucune exécution récente</span>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer className="v3-footer">
        <div className="v3-footer-brokers">
          <div className="v3-broker-status">
            <span className="v3-broker-dot bg-signal-green" />
            Binance: Connected
          </div>
          <div className="v3-broker-status">
            <span className="v3-broker-dot bg-signal-yellow" />
            Saxo Bank: Latency 42ms
          </div>
        </div>
        <span className="v3-footer-version">v1.0.0 · Trading Dashboard</span>
      </footer>

      {/* Wizard Modal */}
      {wizardOpen && (
        <div className="v3-modal-overlay" onClick={() => setWizardOpen(false)}>
          <div className="v3-modal" onClick={e => e.stopPropagation()}>
            <div className="v3-modal-header">
              <span className="v3-modal-title">
                {editTarget ? 'Modifier la stratégie' : 'Nouvelle stratégie'}
              </span>
            </div>

            <div className="v3-modal-body">
              {/* Steps */}
              <div className="v3-steps">
                {['Asset & Algo', 'Paramètres', 'Exécution'].map((label, i) => (
                  <button
                    key={label}
                    className={`v3-step ${i === wizardStep ? 'active' : i < wizardStep ? 'completed' : ''}`}
                    onClick={() => setWizardStep(i)}
                  >
                    {i < wizardStep ? '✓ ' : ''}{label}
                  </button>
                ))}
              </div>

              {/* Step 0: Asset & Algo */}
              {wizardStep === 0 && (
                <>
                  <div className="v3-form-group">
                    <label className="v3-form-label">Nom de la stratégie</label>
                    <input
                      type="text"
                      className="v3-form-input"
                      placeholder="Ex: BTC Threshold Swift"
                      value={wizardData.name}
                      onChange={e => setWizardData(prev => ({ ...prev, name: e.target.value }))}
                    />
                  </div>
                  <div className="v3-form-group">
                    <label className="v3-form-label">Description (optionnel)</label>
                    <input
                      type="text"
                      className="v3-form-input"
                      placeholder="Ex: Achète sous 60k, vend au-dessus de 68k"
                      value={wizardData.description}
                      onChange={e => setWizardData(prev => ({ ...prev, description: e.target.value }))}
                    />
                  </div>
                  <div className="v3-form-group">
                    <label className="v3-form-label">Algorithme</label>
                    <div className="v3-option-grid cols-2">
                      {Object.entries(ALGORITHM_LABELS).map(([key, label]) => (
                        <button
                          key={key}
                          className={`v3-option-btn ${wizardData.algorithm_type === key ? 'selected' : ''}`}
                          onClick={() => handleWizardAlgoChange(key)}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {/* Step 1: Parameters */}
              {wizardStep === 1 && (
                <>
                  <p style={{ fontSize: '10px', fontFamily: 'IBM Plex Mono', color: 'hsl(240, 4%, 40%)', marginBottom: '1rem' }}>
                    Paramètres pour <span style={{ color: 'hsl(0, 0%, 95%)' }}>{ALGORITHM_LABELS[wizardData.algorithm_type]}</span>
                  </p>
                  {ALGORITHM_PARAMS[wizardData.algorithm_type]?.map(param => (
                    <div key={param.key} className="v3-form-group">
                      <label className="v3-form-label">{param.label}</label>
                      <input
                        type="number"
                        className="v3-form-input"
                        value={wizardData.parameters[param.key] ?? param.default}
                        onChange={e => setWizardData(prev => ({
                          ...prev,
                          parameters: { ...prev.parameters, [param.key]: parseFloat(e.target.value) || 0 }
                        }))}
                      />
                    </div>
                  ))}
                </>
              )}

              {/* Step 2: Execution */}
              {wizardStep === 2 && (
                <>
                  <div className="v3-form-group">
                    <label className="v3-form-label">Mode d'exécution</label>
                    <div className="v3-option-grid">
                      {['simulation', 'paper_trading', 'live_trading'].map(mode => (
                        <button
                          key={mode}
                          className={`v3-option-btn ${wizardData.execution_mode === mode ? 'selected' : ''}`}
                          onClick={() => setWizardData(prev => ({ ...prev, execution_mode: mode }))}
                        >
                          {mode === 'simulation' ? 'Simulation' : mode === 'paper_trading' ? 'Paper' : 'Live'}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="v3-form-group">
                    <label className="v3-form-label">Niveau de risque</label>
                    <div className="v3-option-grid">
                      {['LOW', 'MEDIUM', 'HIGH'].map(level => (
                        <button
                          key={level}
                          className={`v3-option-btn ${wizardData.risk_level === level ? 'selected' : ''}`}
                          onClick={() => setWizardData(prev => ({ ...prev, risk_level: level }))}
                        >
                          {level}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                    <div className="v3-form-group">
                      <label className="v3-form-label">Quantité min</label>
                      <input
                        type="number"
                        className="v3-form-input"
                        value={wizardData.target_min_quantity}
                        onChange={e => setWizardData(prev => ({ ...prev, target_min_quantity: parseFloat(e.target.value) || 0 }))}
                        step="any"
                      />
                    </div>
                    <div className="v3-form-group">
                      <label className="v3-form-label">Quantité max</label>
                      <input
                        type="number"
                        className="v3-form-input"
                        value={wizardData.target_max_quantity}
                        onChange={e => setWizardData(prev => ({ ...prev, target_max_quantity: parseFloat(e.target.value) || 0 }))}
                        step="any"
                      />
                    </div>
                  </div>
                  <div className="v3-form-group">
                    <label className="v3-form-label">Fréquence de vérification (min)</label>
                    <input
                      type="number"
                      className="v3-form-input"
                      value={wizardData.check_frequency}
                      onChange={e => setWizardData(prev => ({ ...prev, check_frequency: parseInt(e.target.value) || 1 }))}
                      min={1}
                    />
                  </div>
                  <div className="v3-form-group">
                    <button
                      className={`v3-option-btn ${wizardData.is_automated ? 'selected' : ''}`}
                      style={{ width: 'auto' }}
                      onClick={() => setWizardData(prev => ({ ...prev, is_automated: !prev.is_automated }))}
                    >
                      {wizardData.is_automated ? '✓ AUTO' : 'MANUEL'}
                    </button>
                    <span style={{ marginLeft: '0.75rem', fontSize: '10px', fontFamily: 'IBM Plex Mono', color: 'hsl(240, 4%, 40%)' }}>
                      {wizardData.is_automated ? 'Exécution automatique' : 'Validation manuelle requise'}
                    </span>
                  </div>
                </>
              )}
            </div>

            <div className="v3-modal-footer">
              <button
                className="v3-btn-secondary"
                onClick={() => wizardStep > 0 ? setWizardStep(wizardStep - 1) : setWizardOpen(false)}
              >
                {wizardStep === 0 ? 'Annuler' : '← Retour'}
              </button>
              {wizardStep < 2 ? (
                <button className="v3-btn-primary" onClick={() => setWizardStep(wizardStep + 1)}>
                  Suivant →
                </button>
              ) : (
                <button className="v3-btn-success" onClick={handleWizardSave}>
                  {editTarget ? 'Enregistrer' : 'Créer la stratégie'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Execution Details Modal */}
      {executionModalOpen && executionResult && (
        <div className="v3-modal-overlay" onClick={() => setExecutionModalOpen(false)}>
          <div className="v3-modal execution-modal" onClick={e => e.stopPropagation()}>
            <div className="v3-modal-header">
              <span className="v3-modal-title">
                Résultat de l'exécution
              </span>
              <button 
                className="v3-modal-close"
                onClick={() => setExecutionModalOpen(false)}
              >
                ✕
              </button>
            </div>

            <div className="v3-modal-body">
              {/* Strategy Info */}
              <div className="execution-section">
                <h4 className="execution-section-title">Stratégie</h4>
                <div className="execution-info-grid">
                  <div className="execution-info-item">
                    <span className="info-label">Nom</span>
                    <span className="info-value">{executionResult.strategy?.name}</span>
                  </div>
                  <div className="execution-info-item">
                    <span className="info-label">Asset</span>
                    <span className="info-value">{getAssetName(executionResult.strategy)}</span>
                  </div>
                </div>
              </div>

              {/* Status */}
              <div className="execution-section">
                <h4 className="execution-section-title">Statut</h4>
                <div className={`execution-status-badge ${executionResult.status}`}>
                  {executionResult.status === 'success' ? '✓ Succès' : '✕ Erreur'}
                </div>
                {executionResult.error && (
                  <div className="execution-error">
                    <span className="error-label">Erreur:</span>
                    <span className="error-message">{executionResult.error}</span>
                  </div>
                )}
              </div>

              {/* Signal */}
              {executionResult.signal && (
                <div className="execution-section">
                  <h4 className="execution-section-title">Signal</h4>
                  <div className="execution-info-grid">
                    <div className="execution-info-item">
                      <span className="info-label">Type</span>
                      <span className={`info-value signal-${executionResult.signal.toLowerCase()}`}>
                        {executionResult.signal}
                      </span>
                    </div>
                    {executionResult.signal_price && (
                      <div className="execution-info-item">
                        <span className="info-label">Prix</span>
                        <span className="info-value">
                          {Number(executionResult.signal_price).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €
                        </span>
                      </div>
                    )}
                    {executionResult.signal_quantity && (
                      <div className="execution-info-item">
                        <span className="info-label">Quantité</span>
                        <span className="info-value">{executionResult.signal_quantity}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Output Details */}
              {executionResult.output && (
                <div className="execution-section">
                  <h4 className="execution-section-title">Détails</h4>
                  <div className="execution-info-grid">
                    <div className="execution-info-item">
                      <span className="info-label">Points de données</span>
                      <span className="info-value">{executionResult.output.price_data_count || 'N/A'}</span>
                    </div>
                    <div className="execution-info-item">
                      <span className="info-label">Ordres en attente</span>
                      <span className="info-value">{executionResult.output.pending_orders_count ?? 'N/A'}</span>
                    </div>
                    {executionResult.output.execution_executed && (
                      <div className="execution-info-item full-width">
                        <span className="info-label">Ordre exécuté</span>
                        <span className="info-value text-signal-green">✓ Oui</span>
                      </div>
                    )}
                  </div>

                  {/* Signals Details */}
                  {executionResult.output.signals && (
                    <div className="execution-signals">
                      <h5>Signaux de l'algorithme</h5>
                      <pre className="signals-json">
                        {JSON.stringify(executionResult.output.signals, null, 2)}
                      </pre>
                    </div>
                  )}

                  {/* Broker API Response */}
                  {executionResult.output.broker_api_url && (
                    <div className="execution-broker-api">
                      <h5>Réponse API Broker</h5>
                      <div className="api-url">
                        <span className="api-label">URL:</span>
                        <code>{executionResult.output.broker_api_url}</code>
                      </div>
                      {executionResult.output.broker_api_response && (
                        <div className="api-response">
                          <span className="api-label">Réponse:</span>
                          <pre className="api-json">
                            {JSON.stringify(executionResult.output.broker_api_response, null, 2)}
                          </pre>
                        </div>
                      )}
                      {executionResult.output.broker_api_error && (
                        <div className="api-error">
                          <span className="api-label">Erreur API:</span>
                          <pre className="api-json error">
                            {JSON.stringify(executionResult.output.broker_api_error, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Portfolio */}
                  {executionResult.output.portfolio && (
                    <div className="execution-portfolio">
                      <h5>Portfolio</h5>
                      <pre className="portfolio-json">
                        {JSON.stringify(executionResult.output.portfolio, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="v3-modal-footer">
              <button
                className="v3-btn-secondary"
                onClick={() => setExecutionModalOpen(false)}
              >
                Fermer
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Portfolio Selection Modal */}
      {portfolioModalOpen && (
        <div className="v3-modal-overlay" onClick={() => setPortfolioModalOpen(false)}>
          <div className="v3-modal portfolio-modal" onClick={e => e.stopPropagation()}>
            <div className="v3-modal-header">
              <span className="v3-modal-title">
                Créer depuis le portefeuille
              </span>
              <button 
                className="v3-modal-close"
                onClick={() => setPortfolioModalOpen(false)}
              >
                ✕
              </button>
            </div>

            <div className="v3-modal-body">
              <p className="portfolio-modal-hint">
                Sélectionnez une position pour créer une stratégie avec cet asset :
              </p>
              
              {loadingPositions ? (
                <div className="portfolio-loading">Chargement des positions...</div>
              ) : positions.length === 0 ? (
                <div className="portfolio-empty">
                  Aucune position ouverte dans votre portefeuille.
                </div>
              ) : (
                <div className="portfolio-list">
                  {positions.map(position => {
                    const assetName = position.all_asset_name || position.all_asset?.name || position.symbol
                    const assetSymbol = position.all_asset_symbol || position.symbol
                    const pnlClass = position.pnl >= 0 ? 'positive' : 'negative'
                    
                    // Check if a strategy already exists for this asset
                    const positionAssetId = position.all_asset_id 
                      || (typeof position.all_asset === 'object' ? position.all_asset?.id : null)
                      || (typeof position.all_asset === 'number' ? position.all_asset : null)
                    const alreadyHasStrategy = hasStrategyForAsset(positionAssetId)
                    
                    return (
                      <div 
                        key={position.id} 
                        className={`portfolio-item ${alreadyHasStrategy ? 'disabled' : ''}`}
                        onClick={() => !alreadyHasStrategy && createFromPosition(position)}
                      >
                        <div className="portfolio-item-info">
                          <span className="portfolio-item-name">{assetName}</span>
                          <span className="portfolio-item-symbol">{assetSymbol}</span>
                          {alreadyHasStrategy && (
                            <span className="existing-strategy-badge">Stratégie existante</span>
                          )}
                        </div>
                        <div className="portfolio-item-details">
                          <span className="portfolio-item-qty">{position.quantity} unités</span>
                          <span className={`portfolio-item-pnl ${pnlClass}`}>
                            {position.pnl >= 0 ? '+' : ''}{position.pnl?.toFixed(2)} €
                          </span>
                        </div>
                        <div className="portfolio-item-platform">
                          {position.all_asset_platform || 'N/A'}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            <div className="v3-modal-footer">
              <button
                className="v3-btn-secondary"
                onClick={() => setPortfolioModalOpen(false)}
              >
                Annuler
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Asset Association Modal */}
      {assetAssociationModal && (
        <div className="v3-modal-overlay" onClick={() => !associating && setAssetAssociationModal(null)}>
          <div className="v3-modal association-modal" onClick={e => e.stopPropagation()}>
            <div className="v3-modal-header">
              <span className="v3-modal-title">
                Associer un asset
              </span>
              <button 
                className="v3-modal-close"
                onClick={() => !associating && setAssetAssociationModal(null)}
                disabled={associating}
              >
                ✕
              </button>
            </div>

            <div className="v3-modal-body">
              <p className="association-hint">
                La stratégie <strong>"{assetAssociationModal.strategyName}"</strong> n'a pas d'asset associé.
                <br />Recherchez et sélectionnez un asset pour continuer :
              </p>
              
              <div className="association-search">
                <input
                  type="text"
                  className="v3-form-input"
                  placeholder="Rechercher un asset (ex: AAPL, Bitcoin, Microsoft...)"
                  value={associationSearchQuery}
                  onChange={(e) => handleAssociationSearch(e.target.value)}
                  disabled={associating}
                  autoFocus
                />
              </div>

              {associating ? (
                <div className="association-loading">
                  <span className="loading-spinner">⏳</span>
                  Association et synchronisation en cours...
                </div>
              ) : (
                <div className="association-results">
                  {associationLoading && (
                    <div className="association-item loading">Recherche...</div>
                  )}
                  {!associationLoading && associationSearchQuery.length >= 2 && associationResults.length === 0 && (
                    <div className="association-item empty">Aucun résultat pour "{associationSearchQuery}"</div>
                  )}
                  {!associationLoading && associationResults.map(asset => {
                    const isUsed = hasStrategyForAsset(asset.id, assetAssociationModal.strategyId)
                    return (
                      <div
                        key={asset.id}
                        className={`association-item ${isUsed ? 'disabled' : 'selectable'}`}
                        onClick={() => !isUsed && handleAssociateAndSync(assetAssociationModal.strategyId, asset)}
                      >
                        <div className="association-item-main">
                          <span className="association-symbol">{asset.symbol}</span>
                          <span className="association-name">{asset.name}</span>
                          {isUsed && <span className="association-used-badge">Stratégie existante</span>}
                        </div>
                        <span className="association-platform">{asset.platform}</span>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            <div className="v3-modal-footer">
              <button
                className="v3-btn-secondary"
                onClick={() => setAssetAssociationModal(null)}
                disabled={associating}
              >
                Annuler
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
