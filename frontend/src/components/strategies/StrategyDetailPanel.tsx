/**
 * StrategyDetailPanel - Panneau de détail pour une stratégie sélectionnée
 */
import { useState, useEffect, useMemo } from 'react'
import { Badge, Button, Loading } from '@components/common'
import { strategyService } from '@services'
import { assetService } from '@services/assets'
import type { Strategy, AllAsset } from '@types'
import type { StrategyExecution } from '@services/strategyExecutionService'
import StrategyVisualizationChart from './StrategyVisualizationChart'
import AlgorithmParametersModal from './AlgorithmParametersModal'
import { 
  Play, Pause, Settings, Trash2, Copy, History, 
  TrendingUp, TrendingDown, Target, Clock, Zap,
  ChevronDown, ChevronUp, Edit3, Save, X
} from 'lucide-react'
import './StrategyDetailPanel.css'

const ALGORITHM_LABELS: Record<string, string> = {
  threshold: 'Seuils (Threshold)',
  ma_crossover: 'Moving Average Crossover',
  rsi: 'RSI (Relative Strength Index)',
  bollinger: 'Bollinger Bands',
  macd: 'MACD',
  grid: 'Grid Trading',
}

const RISK_LEVELS: Record<string, { label: string; variant: 'success' | 'warning' | 'danger' }> = {
  LOW: { label: 'Faible', variant: 'success' },
  MEDIUM: { label: 'Moyen', variant: 'warning' },
  HIGH: { label: 'Élevé', variant: 'danger' },
}

interface StrategyDetailPanelProps {
  strategy: Strategy | null
  executions: StrategyExecution[]
  onUpdate: () => void
  onDelete: (strategy: Strategy) => void
  onExecute: (strategy: Strategy) => void
}

export default function StrategyDetailPanel({
  strategy,
  executions,
  onUpdate,
  onDelete,
  onExecute,
}: StrategyDetailPanelProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [editedName, setEditedName] = useState('')
  const [editedDescription, setEditedDescription] = useState('')
  const [showChart, setShowChart] = useState(true)
  const [showExecutions, setShowExecutions] = useState(true)
  const [paramsModalOpen, setParamsModalOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [chartParameters, setChartParameters] = useState<Record<string, any>>({})

  // Filtrer les exécutions de cette stratégie
  const strategyExecutions = useMemo(() => {
    if (!strategy) return []
    return executions
      .filter(e => e.strategy_id === strategy.id || e.strategy === strategy.id)
      .slice(0, 10)
  }, [executions, strategy])

  // Initialiser les valeurs éditées
  useEffect(() => {
    if (strategy) {
      setEditedName(strategy.name)
      setEditedDescription(strategy.description || '')
      setIsEditing(false)
      
      // Charger les paramètres pour le graphique
      const params: Record<string, any> = {}
      if (strategy.algorithm_parameters && strategy.algorithm_parameters.length > 0) {
        strategy.algorithm_parameters.forEach(param => {
          let value: any = param.value
          if (param.param_type === 'int') value = parseInt(value, 10)
          else if (param.param_type === 'float') value = parseFloat(value)
          else if (param.param_type === 'bool') value = value.toLowerCase() === 'true'
          params[param.key] = value
        })
      }
      setChartParameters(params)
    }
  }, [strategy])

  if (!strategy) {
    return (
      <div className="strategy-detail-panel empty">
        <div className="empty-state">
          <Target size={48} />
          <h3>Sélectionnez une stratégie</h3>
          <p>Cliquez sur une stratégie dans la liste pour voir ses détails</p>
        </div>
      </div>
    )
  }

  const pnl = parseFloat(strategy.total_pnl?.toString() || '0')
  const pnlPositive = pnl >= 0
  const assetSymbol = strategy.all_asset_symbol || 
    (typeof strategy.all_asset === 'object' ? strategy.all_asset?.symbol : null) || 
    'N/A'
  const algoLabel = ALGORITHM_LABELS[strategy.algorithm_type || ''] || strategy.algorithm_type || 'N/A'
  const riskInfo = RISK_LEVELS[strategy.risk_level || 'MEDIUM']

  const handleSave = async () => {
    setSaving(true)
    try {
      await strategyService.update(strategy.id, {
        name: editedName,
        description: editedDescription,
      })
      setIsEditing(false)
      onUpdate()
    } catch (err) {
      console.error('Erreur lors de la sauvegarde:', err)
      alert('Erreur lors de la sauvegarde')
    } finally {
      setSaving(false)
    }
  }

  const handleToggleActive = async () => {
    try {
      await strategyService.toggleActive(strategy.id, !strategy.is_active)
      onUpdate()
    } catch (err) {
      console.error('Erreur:', err)
      alert('Erreur lors de la modification')
    }
  }

  const handleDuplicate = async () => {
    try {
      await strategyService.create({
        name: `${strategy.name} (copie)`,
        description: strategy.description,
        risk_level: strategy.risk_level,
        is_active: false,
        is_automated: false,
      })
      onUpdate()
    } catch (err) {
      console.error('Erreur:', err)
      alert('Erreur lors de la duplication')
    }
  }

  const getSignalBadge = (signal: string) => {
    const variants: Record<string, 'success' | 'danger' | 'warning' | 'secondary'> = {
      BUY: 'success',
      SELL: 'danger',
      HOLD: 'warning',
      NONE: 'secondary',
    }
    return <Badge variant={variants[signal] || 'secondary'}>{signal}</Badge>
  }

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'success' | 'danger' | 'warning' | 'secondary'> = {
      completed: 'success',
      failed: 'danger',
      running: 'warning',
    }
    return <Badge variant={variants[status] || 'secondary'}>{status}</Badge>
  }

  return (
    <div className="strategy-detail-panel">
      {/* Header */}
      <div className="detail-header">
        <div className="detail-title-section">
          {isEditing ? (
            <div className="edit-form">
              <input
                type="text"
                value={editedName}
                onChange={(e) => setEditedName(e.target.value)}
                className="edit-name-input"
                placeholder="Nom de la stratégie"
              />
              <textarea
                value={editedDescription}
                onChange={(e) => setEditedDescription(e.target.value)}
                className="edit-description-input"
                placeholder="Description"
                rows={2}
              />
              <div className="edit-actions">
                <Button variant="primary" size="sm" onClick={handleSave} disabled={saving}>
                  <Save size={14} /> {saving ? 'Sauvegarde...' : 'Sauvegarder'}
                </Button>
                <Button variant="outline" size="sm" onClick={() => setIsEditing(false)}>
                  <X size={14} /> Annuler
                </Button>
              </div>
            </div>
          ) : (
            <>
              <div className="title-row">
                <h2>{strategy.name}</h2>
                <button className="edit-btn" onClick={() => setIsEditing(true)} title="Modifier">
                  <Edit3 size={16} />
                </button>
              </div>
              {strategy.description && (
                <p className="description">{strategy.description}</p>
              )}
            </>
          )}
        </div>

        <div className="detail-badges">
          <Badge variant={strategy.is_active ? 'success' : 'secondary'}>
            {strategy.is_active ? 'Actif' : 'Inactif'}
          </Badge>
          {strategy.is_automated && <Badge variant="info">Automatisé</Badge>}
          <Badge variant={riskInfo.variant}>{riskInfo.label}</Badge>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="detail-stats">
        <div className="stat-item">
          <Target size={16} />
          <span className="stat-label">Asset</span>
          <span className="stat-value">{assetSymbol}</span>
        </div>
        <div className="stat-item">
          <Settings size={16} />
          <span className="stat-label">Algorithme</span>
          <span className="stat-value">{algoLabel}</span>
        </div>
        <div className="stat-item">
          {pnlPositive ? <TrendingUp size={16} className="positive" /> : <TrendingDown size={16} className="negative" />}
          <span className="stat-label">PnL</span>
          <span className={`stat-value ${pnlPositive ? 'positive' : 'negative'}`}>
            {pnlPositive ? '+' : ''}{pnl.toFixed(2)} €
          </span>
        </div>
        <div className="stat-item">
          <History size={16} />
          <span className="stat-label">Trades</span>
          <span className="stat-value">{strategy.total_trades || 0}</span>
        </div>
      </div>

      {/* Actions */}
      <div className="detail-actions">
        <Button 
          variant={strategy.is_active ? 'warning' : 'success'} 
          onClick={handleToggleActive}
        >
          {strategy.is_active ? <Pause size={16} /> : <Play size={16} />}
          {strategy.is_active ? 'Pause' : 'Activer'}
        </Button>
        <Button variant="primary" onClick={() => onExecute(strategy)} disabled={!strategy.is_active}>
          <Zap size={16} /> Exécuter
        </Button>
        <Button variant="outline" onClick={() => setParamsModalOpen(true)}>
          <Settings size={16} /> Paramètres
        </Button>
        <Button variant="outline" onClick={handleDuplicate}>
          <Copy size={16} /> Dupliquer
        </Button>
        <Button variant="danger" onClick={() => onDelete(strategy)}>
          <Trash2 size={16} /> Supprimer
        </Button>
      </div>

      {/* Chart Section */}
      <div className="detail-section">
        <button 
          className="section-header collapsible"
          onClick={() => setShowChart(!showChart)}
        >
          <h3>Backtest & Visualisation</h3>
          {showChart ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
        </button>
        {showChart && (
          <div className="section-content">
            <StrategyVisualizationChart
              strategy={strategy}
              parameters={chartParameters}
              onParametersChange={setChartParameters}
            />
          </div>
        )}
      </div>

      {/* Executions Section */}
      <div className="detail-section">
        <button 
          className="section-header collapsible"
          onClick={() => setShowExecutions(!showExecutions)}
        >
          <h3>Exécutions récentes ({strategyExecutions.length})</h3>
          {showExecutions ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
        </button>
        {showExecutions && (
          <div className="section-content">
            {strategyExecutions.length === 0 ? (
              <p className="no-data">Aucune exécution récente</p>
            ) : (
              <div className="executions-list">
                {strategyExecutions.map((exec) => (
                  <div key={exec.id} className="execution-item">
                    <div className="execution-info">
                      <Clock size={14} />
                      <span className="execution-time">
                        {new Date(exec.started_at).toLocaleString('fr-FR', {
                          day: '2-digit',
                          month: '2-digit',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                      {getStatusBadge(exec.status)}
                      {getSignalBadge(exec.signal)}
                    </div>
                    <div className="execution-details">
                      {exec.signal_price && (
                        <span>Prix: {Number(exec.signal_price).toFixed(2)} €</span>
                      )}
                      {exec.signal_quantity && exec.signal_quantity > 0 && (
                        <span>Qté: {exec.signal_quantity}</span>
                      )}
                      {exec.duration && (
                        <span className="duration">{exec.duration}s</span>
                      )}
                    </div>
                    {exec.error && (
                      <div className="execution-error">{exec.error}</div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Modal pour paramètres */}
      <AlgorithmParametersModal
        isOpen={paramsModalOpen}
        onClose={() => setParamsModalOpen(false)}
        strategy={strategy}
        onSuccess={() => {
          onUpdate()
          setParamsModalOpen(false)
        }}
      />
    </div>
  )
}
