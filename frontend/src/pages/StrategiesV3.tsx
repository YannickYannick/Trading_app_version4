/**
 * StrategiesV3 - Interface style terminal de trading
 * Inspiré de bot-bloom-forge
 */
import { useState, useEffect, useMemo, useCallback } from 'react'
import { strategyService } from '@services'
import strategyExecutionService, { type StrategyExecution } from '@services/strategyExecutionService'
import { useToast } from '@hooks/useToast'
import type { Strategy } from '@types'
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

  useEffect(() => {
    loadData()
  }, [loadData])

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
    try {
      await strategyExecutionService.execute(s.id)
      loadData()
    } catch (err) {
      alert('Erreur lors de l\'exécution')
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
        await strategyService.create({
          name: wizardData.name || `${wizardData.asset} ${ALGORITHM_LABELS[wizardData.algorithm_type]}`,
          description: wizardData.description,
          risk_level: wizardData.risk_level as 'LOW' | 'MEDIUM' | 'HIGH',
          is_active: false,
          is_automated: wizardData.is_automated,
        })
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
                    <span className="v3-asset-symbol">{getAssetSymbol(s)}</span>
                    <span className={`v3-mode-tag ${s.execution_mode}`}>
                      [{MODE_LABELS[s.execution_mode || ''] || s.execution_mode || 'SIM'}]
                    </span>
                  </div>
                  <span className="v3-strategy-meta">{s.name} · ID-{s.id}</span>
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
                    <button className="v3-action-btn" onClick={() => handleExecute(s)}>EXE</button>
                    <button className="v3-action-btn" onClick={() => handleDuplicate(s)}>DUP</button>
                    <button className="v3-action-btn delete" onClick={() => handleDelete(s)}>X</button>
                  </div>
                </div>
              </div>

              {/* Expanded */}
              {expandedId === s.id && (
                <div className="v3-strategy-expanded">
                  <div className="v3-chart-section">
                    <h4>Prix & Signaux — {getAssetSymbol(s)}</h4>
                    <StrategyVisualizationChart
                      strategy={s}
                      parameters={s.parameters || {}}
                    />
                  </div>
                  <div className="v3-config-section">
                    <h4>Configuration</h4>
                    <div className="v3-config-list">
                      <div className="v3-config-row">
                        <span className="config-key">Algorithme</span>
                        <span className="config-value">{ALGORITHM_LABELS[s.algorithm_type || ''] || s.algorithm_type}</span>
                      </div>
                      {s.parameters && Object.entries(s.parameters).map(([key, val]) => (
                        <div key={key} className="v3-config-row">
                          <span className="config-key">{key}</span>
                          <span className="config-value">{val}</span>
                        </div>
                      ))}
                      <div className="v3-config-row" style={{ borderTop: '1px solid hsl(240, 4%, 16%)', paddingTop: '0.5rem', marginTop: '0.5rem' }}>
                        <span className="config-key">Broker</span>
                        <span className="config-value">{s.broker_name || 'N/A'}</span>
                      </div>
                      <div className="v3-config-row">
                        <span className="config-key">Risque</span>
                        <span className={`config-value ${s.risk_level === 'HIGH' ? 'text-signal-red' : s.risk_level === 'MEDIUM' ? 'text-signal-yellow' : 'text-signal-green'}`}>
                          {s.risk_level}
                        </span>
                      </div>
                      <div className="v3-config-row">
                        <span className="config-key">Quantité</span>
                        <span className="config-value">{s.target_min_quantity} – {s.target_max_quantity}</span>
                      </div>
                      <div className="v3-config-row">
                        <span className="config-key">Fréquence</span>
                        <span className="config-value">{s.check_frequency || 45} min</span>
                      </div>
                      <div className="v3-config-row">
                        <span className="config-key">Automatisé</span>
                        <span className={`config-value ${s.is_automated ? 'text-signal-green' : ''}`}>
                          {s.is_automated ? 'OUI' : 'NON'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
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
    </div>
  )
}
