/**
 * StrategyCard - Carte compacte pour afficher une stratégie dans la liste
 */
import { Badge } from '@components/common'
import type { Strategy } from '@types'
import { Play, Pause, Zap, TrendingUp, TrendingDown, Clock, Target } from 'lucide-react'
import './StrategyCard.css'

// Mapping des algorithmes
const ALGORITHM_LABELS: Record<string, string> = {
  threshold: 'Seuils',
  ma_crossover: 'MA Cross',
  rsi: 'RSI',
  bollinger: 'Bollinger',
  macd: 'MACD',
  grid: 'Grid',
}

interface StrategyCardProps {
  strategy: Strategy
  isSelected: boolean
  onSelect: (strategy: Strategy) => void
  onToggleActive: (strategy: Strategy) => void
  onExecute: (strategy: Strategy) => void
  lastExecution?: {
    signal: string
    timestamp: string
  } | null
}

export default function StrategyCard({
  strategy,
  isSelected,
  onSelect,
  onToggleActive,
  onExecute,
  lastExecution,
}: StrategyCardProps) {
  const pnl = parseFloat(strategy.total_pnl?.toString() || '0')
  const pnlPositive = pnl >= 0
  const algoLabel = ALGORITHM_LABELS[strategy.algorithm_type || ''] || strategy.algorithm_type || 'N/A'

  const assetSymbol = strategy.all_asset_symbol || 
    (typeof strategy.all_asset === 'object' ? strategy.all_asset?.symbol : null) || 
    'N/A'

  const handleCardClick = (e: React.MouseEvent) => {
    onSelect(strategy)
  }

  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation()
    onToggleActive(strategy)
  }

  const handleExecute = (e: React.MouseEvent) => {
    e.stopPropagation()
    onExecute(strategy)
  }

  return (
    <div 
      className={`strategy-card ${isSelected ? 'selected' : ''} ${strategy.is_active ? 'active' : 'inactive'}`}
      onClick={handleCardClick}
    >
      <div className="strategy-card-header">
        <div className="strategy-card-title">
          <span className={`status-dot ${strategy.is_active ? 'active' : 'inactive'}`} />
          <h4>{strategy.name}</h4>
        </div>
        <div className="strategy-card-badges">
          <Badge variant={strategy.is_active ? 'success' : 'secondary'} size="small">
            {strategy.is_active ? 'Actif' : 'Inactif'}
          </Badge>
          {strategy.is_automated && (
            <Badge variant="info" size="small">Auto</Badge>
          )}
        </div>
      </div>

      <div className="strategy-card-body">
        <div className="strategy-card-info">
          <div className="info-row">
            <Target size={14} />
            <span className="asset-symbol">{assetSymbol}</span>
            <span className="separator">•</span>
            <span className="algo-type">{algoLabel}</span>
          </div>
          
          <div className="info-row">
            <span className={`pnl ${pnlPositive ? 'positive' : 'negative'}`}>
              {pnlPositive ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
              {pnlPositive ? '+' : ''}{pnl.toFixed(2)} €
            </span>
            {strategy.total_trades !== undefined && (
              <>
                <span className="separator">•</span>
                <span className="trades-count">{strategy.total_trades} trades</span>
              </>
            )}
          </div>

          {lastExecution && (
            <div className="info-row last-signal">
              <Clock size={12} />
              <span className={`signal signal-${lastExecution.signal.toLowerCase()}`}>
                {lastExecution.signal}
              </span>
              <span className="timestamp">
                {new Date(lastExecution.timestamp).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="strategy-card-actions">
        <button 
          className={`action-btn toggle ${strategy.is_active ? 'pause' : 'play'}`}
          onClick={handleToggle}
          title={strategy.is_active ? 'Mettre en pause' : 'Activer'}
        >
          {strategy.is_active ? <Pause size={16} /> : <Play size={16} />}
        </button>
        <button 
          className="action-btn execute"
          onClick={handleExecute}
          title="Exécuter maintenant"
          disabled={!strategy.is_active}
        >
          <Zap size={16} />
        </button>
      </div>
    </div>
  )
}
