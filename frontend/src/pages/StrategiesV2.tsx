/**
 * StrategiesV2 - Nouvelle interface pour les stratégies
 * Layout: KPIs + Liste cards + Panneau détail
 */
import { useState, useEffect, useMemo, useCallback } from 'react'
import { Button, Loading, Input } from '@components/common'
import { strategyService } from '@services'
import strategyExecutionService, { type StrategyExecution } from '@services/strategyExecutionService'
import type { Strategy } from '@types'
import StrategyKPIs from '@components/strategies/StrategyKPIs'
import StrategyCard from '@components/strategies/StrategyCard'
import StrategyDetailPanel from '@components/strategies/StrategyDetailPanel'
import { Plus, Search, Filter, LayoutGrid, List, RefreshCw, Zap } from 'lucide-react'
import './StrategiesV2.css'

// Options de filtre
const ALGORITHM_OPTIONS = [
  { value: '', label: 'Tous les algorithmes' },
  { value: 'threshold', label: 'Seuils' },
  { value: 'ma_crossover', label: 'MA Crossover' },
  { value: 'rsi', label: 'RSI' },
  { value: 'bollinger', label: 'Bollinger' },
  { value: 'macd', label: 'MACD' },
  { value: 'grid', label: 'Grid' },
]

const STATUS_OPTIONS = [
  { value: '', label: 'Tous les statuts' },
  { value: 'active', label: 'Actives' },
  { value: 'inactive', label: 'Inactives' },
  { value: 'automated', label: 'Automatisées' },
]

export default function StrategiesV2() {
  // Data
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [executions, setExecutions] = useState<StrategyExecution[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Selection
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null)

  // Filters
  const [searchQuery, setSearchQuery] = useState('')
  const [algorithmFilter, setAlgorithmFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [showFilters, setShowFilters] = useState(false)

  // UI state
  const [executing, setExecuting] = useState(false)

  // Load data
  const loadStrategies = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await strategyService.getAll()
      const strategiesList = Array.isArray(response)
        ? response
        : (response.results || response.data || [])
      setStrategies(strategiesList)
      
      // Si une stratégie était sélectionnée, la mettre à jour
      if (selectedStrategy) {
        const updated = strategiesList.find((s: Strategy) => s.id === selectedStrategy.id)
        if (updated) {
          setSelectedStrategy(updated)
        }
      }
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Erreur lors du chargement')
    } finally {
      setLoading(false)
    }
  }, [selectedStrategy])

  const loadExecutions = useCallback(async () => {
    try {
      const data = await strategyExecutionService.getRecent()
      setExecutions(data)
    } catch (err) {
      console.error('Erreur chargement exécutions:', err)
    }
  }, [])

  useEffect(() => {
    loadStrategies()
    loadExecutions()
  }, [])

  // Filtered strategies
  const filteredStrategies = useMemo(() => {
    return strategies.filter(strategy => {
      // Search
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        const nameMatch = strategy.name.toLowerCase().includes(query)
        const symbolMatch = (strategy.all_asset_symbol || '').toLowerCase().includes(query)
        if (!nameMatch && !symbolMatch) return false
      }

      // Algorithm filter
      if (algorithmFilter && strategy.algorithm_type !== algorithmFilter) {
        return false
      }

      // Status filter
      if (statusFilter === 'active' && !strategy.is_active) return false
      if (statusFilter === 'inactive' && strategy.is_active) return false
      if (statusFilter === 'automated' && !strategy.is_automated) return false

      return true
    })
  }, [strategies, searchQuery, algorithmFilter, statusFilter])

  // Get last execution for each strategy
  const getLastExecution = useCallback((strategyId: number) => {
    const exec = executions.find(e => e.strategy_id === strategyId || e.strategy === strategyId)
    if (!exec) return null
    return {
      signal: exec.signal,
      timestamp: exec.started_at,
    }
  }, [executions])

  // Handlers
  const handleCreateNew = async () => {
    try {
      const newStrategy = await strategyService.create({
        name: 'Nouvelle stratégie',
        description: '',
        risk_level: 'MEDIUM',
        is_active: false,
        is_automated: false,
      })
      await loadStrategies()
      setSelectedStrategy(newStrategy)
    } catch (err: any) {
      alert(err.response?.data?.error || 'Erreur lors de la création')
    }
  }

  const handleToggleActive = async (strategy: Strategy) => {
    try {
      await strategyService.toggleActive(strategy.id, !strategy.is_active)
      loadStrategies()
    } catch (err: any) {
      alert(err.response?.data?.error || 'Erreur')
    }
  }

  const handleExecute = async (strategy: Strategy) => {
    if (!window.confirm(`Exécuter la stratégie "${strategy.name}" maintenant ?`)) {
      return
    }
    try {
      await strategyExecutionService.execute(strategy.id)
      loadExecutions()
      alert(`Stratégie "${strategy.name}" exécutée`)
    } catch (err: any) {
      alert(err.response?.data?.error || 'Erreur lors de l\'exécution')
    }
  }

  const handleDelete = async (strategy: Strategy) => {
    if (!window.confirm(`Supprimer la stratégie "${strategy.name}" ?`)) {
      return
    }
    try {
      await strategyService.delete(strategy.id)
      if (selectedStrategy?.id === strategy.id) {
        setSelectedStrategy(null)
      }
      loadStrategies()
    } catch (err: any) {
      alert(err.response?.data?.error || 'Erreur lors de la suppression')
    }
  }

  const handleExecuteAll = async () => {
    if (!window.confirm('Exécuter toutes les stratégies actives ?')) {
      return
    }
    setExecuting(true)
    try {
      const result = await strategyExecutionService.executeAll()
      alert(`${result.total_strategies} stratégies exécutées`)
      loadExecutions()
    } catch (err: any) {
      alert(err.message || 'Erreur')
    } finally {
      setExecuting(false)
    }
  }

  const handleRefresh = () => {
    loadStrategies()
    loadExecutions()
  }

  if (loading && strategies.length === 0) {
    return (
      <div className="strategies-v2-page">
        <Loading text="Chargement des stratégies..." />
      </div>
    )
  }

  return (
    <div className="strategies-v2-page">
      {/* Header */}
      <div className="page-header">
        <div className="header-left">
          <h1>Stratégies</h1>
          <span className="count">{filteredStrategies.length} stratégie{filteredStrategies.length > 1 ? 's' : ''}</span>
        </div>
        <div className="header-actions">
          <Button variant="outline" onClick={handleRefresh} title="Rafraîchir">
            <RefreshCw size={16} />
          </Button>
          <Button variant="outline" onClick={handleExecuteAll} disabled={executing}>
            <Zap size={16} /> {executing ? 'Exécution...' : 'Exécuter tout'}
          </Button>
          <Button variant="primary" onClick={handleCreateNew}>
            <Plus size={16} /> Nouvelle stratégie
          </Button>
        </div>
      </div>

      {/* KPIs */}
      <StrategyKPIs 
        strategies={strategies} 
        executions={executions}
        loading={loading}
      />

      {/* Filters Bar */}
      <div className="filters-bar">
        <div className="search-box">
          <Search size={18} />
          <input
            type="text"
            placeholder="Rechercher par nom ou symbole..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="filter-controls">
          <select 
            value={algorithmFilter}
            onChange={(e) => setAlgorithmFilter(e.target.value)}
            className="filter-select"
          >
            {ALGORITHM_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>

          <select 
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="filter-select"
          >
            {STATUS_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <Button variant="outline" size="sm" onClick={handleRefresh}>Réessayer</Button>
        </div>
      )}

      {/* Main Content - Split Layout */}
      <div className="main-content">
        {/* Strategies List */}
        <div className="strategies-list-panel">
          {filteredStrategies.length === 0 ? (
            <div className="empty-list">
              {searchQuery || algorithmFilter || statusFilter ? (
                <>
                  <p>Aucune stratégie ne correspond aux filtres</p>
                  <Button variant="outline" onClick={() => {
                    setSearchQuery('')
                    setAlgorithmFilter('')
                    setStatusFilter('')
                  }}>
                    Réinitialiser les filtres
                  </Button>
                </>
              ) : (
                <>
                  <p>Aucune stratégie créée</p>
                  <Button variant="primary" onClick={handleCreateNew}>
                    <Plus size={16} /> Créer votre première stratégie
                  </Button>
                </>
              )}
            </div>
          ) : (
            <div className="strategies-grid">
              {filteredStrategies.map(strategy => (
                <StrategyCard
                  key={strategy.id}
                  strategy={strategy}
                  isSelected={selectedStrategy?.id === strategy.id}
                  onSelect={setSelectedStrategy}
                  onToggleActive={handleToggleActive}
                  onExecute={handleExecute}
                  lastExecution={getLastExecution(strategy.id)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Detail Panel */}
        <div className="detail-panel-container">
          <StrategyDetailPanel
            strategy={selectedStrategy}
            executions={executions}
            onUpdate={loadStrategies}
            onDelete={handleDelete}
            onExecute={handleExecute}
          />
        </div>
      </div>
    </div>
  )
}
