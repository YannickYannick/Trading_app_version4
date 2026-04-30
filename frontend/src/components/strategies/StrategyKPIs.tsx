/**
 * StrategyKPIs - Barre de KPIs pour les stratégies
 */
import { Activity, TrendingUp, Zap, AlertTriangle, DollarSign, BarChart3 } from 'lucide-react'
import type { Strategy } from '@types'
import type { StrategyExecution } from '@services/strategyExecutionService'
import './StrategyKPIs.css'

interface StrategyKPIsProps {
  strategies: Strategy[]
  executions: StrategyExecution[]
  loading?: boolean
}

export default function StrategyKPIs({ strategies, executions, loading }: StrategyKPIsProps) {
  // Calcul des KPIs
  const activeCount = strategies.filter(s => s.is_active).length
  const totalCount = strategies.length
  
  const totalPnL = strategies.reduce((sum, s) => {
    return sum + parseFloat(s.total_pnl?.toString() || '0')
  }, 0)
  
  const totalTrades = strategies.reduce((sum, s) => {
    return sum + (s.total_trades || 0)
  }, 0)
  
  // Signaux des dernières 24h
  const last24h = new Date(Date.now() - 24 * 60 * 60 * 1000)
  const recentExecutions = executions.filter(e => new Date(e.started_at) > last24h)
  const signalCount = recentExecutions.length
  
  const buySignals = recentExecutions.filter(e => e.signal === 'BUY').length
  const sellSignals = recentExecutions.filter(e => e.signal === 'SELL').length
  
  // Erreurs récentes
  const errorCount = recentExecutions.filter(e => e.status === 'failed').length

  if (loading) {
    return (
      <div className="strategy-kpis loading">
        <div className="kpi-skeleton" />
        <div className="kpi-skeleton" />
        <div className="kpi-skeleton" />
        <div className="kpi-skeleton" />
      </div>
    )
  }

  return (
    <div className="strategy-kpis">
      <div className="kpi-card">
        <div className="kpi-icon active">
          <Activity size={20} />
        </div>
        <div className="kpi-content">
          <span className="kpi-value">
            {activeCount}<span className="kpi-total">/{totalCount}</span>
          </span>
          <span className="kpi-label">Stratégies actives</span>
        </div>
      </div>

      <div className="kpi-card">
        <div className={`kpi-icon ${totalPnL >= 0 ? 'positive' : 'negative'}`}>
          <TrendingUp size={20} />
        </div>
        <div className="kpi-content">
          <span className={`kpi-value ${totalPnL >= 0 ? 'positive' : 'negative'}`}>
            {totalPnL >= 0 ? '+' : ''}{totalPnL.toFixed(2)} €
          </span>
          <span className="kpi-label">PnL total</span>
        </div>
      </div>

      <div className="kpi-card">
        <div className="kpi-icon signals">
          <Zap size={20} />
        </div>
        <div className="kpi-content">
          <span className="kpi-value">
            {signalCount}
            {signalCount > 0 && (
              <span className="kpi-breakdown">
                <span className="buy">{buySignals} ↑</span>
                <span className="sell">{sellSignals} ↓</span>
              </span>
            )}
          </span>
          <span className="kpi-label">Signaux (24h)</span>
        </div>
      </div>

      <div className="kpi-card">
        <div className="kpi-icon trades">
          <BarChart3 size={20} />
        </div>
        <div className="kpi-content">
          <span className="kpi-value">{totalTrades}</span>
          <span className="kpi-label">Trades exécutés</span>
        </div>
      </div>

      {errorCount > 0 && (
        <div className="kpi-card error">
          <div className="kpi-icon warning">
            <AlertTriangle size={20} />
          </div>
          <div className="kpi-content">
            <span className="kpi-value">{errorCount}</span>
            <span className="kpi-label">Erreurs (24h)</span>
          </div>
        </div>
      )}
    </div>
  )
}
