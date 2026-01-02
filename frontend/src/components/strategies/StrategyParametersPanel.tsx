/**
 * Panneau latéral pour ajuster les paramètres d'une stratégie en temps réel
 */
import { useState, useEffect, useRef } from 'react'
import { Button, Loading } from '@components/common'
import { strategyService } from '@services'
import type { Strategy } from '@types'
import './StrategyParametersPanel.css'

// Définitions des paramètres par algorithme (copié depuis AlgorithmParametersModal)
const ALGORITHM_PARAMETERS_DEFINITIONS: Record<string, Array<{
  key: string
  label: string
  type: 'int' | 'float' | 'str' | 'bool'
  default: any
  min?: number
  max?: number
  description?: string
}>> = {
  threshold: [
    { key: 'threshold_low', label: 'Seuil bas', type: 'float', default: 100.0, description: 'Prix en dessous = signal d\'achat' },
    { key: 'threshold_high', label: 'Seuil haut', type: 'float', default: 200.0, description: 'Prix au-dessus = signal de vente' },
    { key: 'min_quantity', label: 'Quantité minimale', type: 'float', default: 0, min: 0, description: 'Quantité min (1 pour actions, 0.0005 pour crypto)' },
    { key: 'order_size', label: 'Taille d\'ordre max', type: 'float', default: 1.0, min: 0.01 },
    { key: 'stop_loss', label: 'Stop-loss (%)', type: 'float', default: 0.05, min: 0, max: 1 },
  ],
  ma_crossover: [
    { key: 'ma1_period', label: 'Période MA rapide', type: 'int', default: 20, min: 1, max: 200 },
    { key: 'ma2_period', label: 'Période MA lente', type: 'int', default: 50, min: 1, max: 200 },
    { key: 'min_quantity', label: 'Quantité minimale', type: 'float', default: 0, min: 0, description: 'Quantité min (1 pour actions, 0.0005 pour crypto)' },
    { key: 'order_size', label: 'Taille d\'ordre max', type: 'float', default: 1.0, min: 0.01 },
    { key: 'stop_loss', label: 'Stop-loss (%)', type: 'float', default: 0.05, min: 0, max: 1 },
  ],
  rsi: [
    { key: 'rsi_period', label: 'Période RSI', type: 'int', default: 14, min: 2, max: 100 },
    { key: 'rsi_low', label: 'Seuil bas RSI', type: 'int', default: 30, min: 0, max: 100 },
    { key: 'rsi_high', label: 'Seuil haut RSI', type: 'int', default: 70, min: 0, max: 100 },
    { key: 'min_quantity', label: 'Quantité minimale', type: 'float', default: 0, min: 0, description: 'Quantité min (1 pour actions, 0.0005 pour crypto)' },
    { key: 'order_size', label: 'Taille d\'ordre max', type: 'float', default: 1.0, min: 0.01 },
    { key: 'stop_loss', label: 'Stop-loss (%)', type: 'float', default: 0.05, min: 0, max: 1 },
  ],
  bollinger: [
    { key: 'bb_period', label: 'Période Bollinger', type: 'int', default: 20, min: 2, max: 200 },
    { key: 'bb_std', label: 'Écart-type', type: 'float', default: 2.0, min: 0.1, max: 5 },
    { key: 'min_quantity', label: 'Quantité minimale', type: 'float', default: 0, min: 0, description: 'Quantité min (1 pour actions, 0.0005 pour crypto)' },
    { key: 'order_size', label: 'Taille d\'ordre max', type: 'float', default: 1.0, min: 0.01 },
    { key: 'stop_loss', label: 'Stop-loss (%)', type: 'float', default: 0.05, min: 0, max: 1 },
  ],
  macd: [
    { key: 'macd_fast', label: 'Période EMA rapide', type: 'int', default: 12, min: 1, max: 50 },
    { key: 'macd_slow', label: 'Période EMA lente', type: 'int', default: 26, min: 1, max: 100 },
    { key: 'macd_signal', label: 'Période signal', type: 'int', default: 9, min: 1, max: 50 },
    { key: 'min_quantity', label: 'Quantité minimale', type: 'float', default: 0, min: 0, description: 'Quantité min (1 pour actions, 0.0005 pour crypto)' },
    { key: 'order_size', label: 'Taille d\'ordre max', type: 'float', default: 1.0, min: 0.01 },
    { key: 'stop_loss', label: 'Stop-loss (%)', type: 'float', default: 0.05, min: 0, max: 1 },
  ],
  grid: [
    { key: 'grid_min', label: 'Prix minimum', type: 'float', default: 100.0, min: 0 },
    { key: 'grid_max', label: 'Prix maximum', type: 'float', default: 200.0, min: 0 },
    { key: 'grid_levels', label: 'Nombre de niveaux', type: 'int', default: 10, min: 2, max: 100 },
    { key: 'min_quantity', label: 'Quantité minimale', type: 'float', default: 0, min: 0, description: 'Quantité min (1 pour actions, 0.0005 pour crypto)' },
    { key: 'order_size', label: 'Taille d\'ordre max', type: 'float', default: 1.0, min: 0.01 },
    { key: 'stop_loss', label: 'Stop-loss (%)', type: 'float', default: 0.05, min: 0, max: 1 },
  ],
}

interface StrategyParametersPanelProps {
  strategy: Strategy | null
  currentParameters: Record<string, any>
  onParameterChange: (key: string, value: any) => void // Temps réel
  onSave: (parameters: Record<string, any>) => Promise<void>
}

export default function StrategyParametersPanel({
  strategy,
  currentParameters,
  onParameterChange,
  onSave,
}: StrategyParametersPanelProps) {
  const [localParameters, setLocalParameters] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const initializedRef = useRef<string | null>(null) // Pour éviter les réinitialisations multiples

  // Initialiser les paramètres locaux (uniquement quand la stratégie change)
  useEffect(() => {
    if (!strategy || !strategy.algorithm_type) return
    
    // Vérifier si on a déjà initialisé pour cette stratégie
    const strategyKey = `${strategy.id}-${strategy.algorithm_type}`
    if (initializedRef.current === strategyKey) {
      return // Déjà initialisé
    }

    const params: Record<string, any> = {}
    
    // Charger depuis strategy.algorithm_parameters
    if (strategy.algorithm_parameters && strategy.algorithm_parameters.length > 0) {
      strategy.algorithm_parameters.forEach(param => {
        let value: any = param.value
        if (param.param_type === 'int') {
          value = parseInt(value, 10)
        } else if (param.param_type === 'float') {
          value = parseFloat(value)
        } else if (param.param_type === 'bool') {
          value = value.toLowerCase() === 'true' || value === true || value === '1'
        }
        params[param.key] = value
      })
    }

    // Remplir avec les valeurs par défaut si manquantes
    const definitions = ALGORITHM_PARAMETERS_DEFINITIONS[strategy.algorithm_type] || []
    definitions.forEach(def => {
      if (params[def.key] === undefined || params[def.key] === null) {
        params[def.key] = def.default
      }
    })

    setLocalParameters(params)
    initializedRef.current = strategyKey
    
    // Initialiser currentParameters UNIQUEMENT si elles sont vides
    // Utiliser setTimeout pour différer et éviter les boucles
    const hasCurrentParams = currentParameters && Object.keys(currentParameters).length > 0
    if (!hasCurrentParams && Object.keys(params).length > 0) {
      setTimeout(() => {
        Object.keys(params).forEach(key => {
          onParameterChange(key, params[key])
        })
      }, 0)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [strategy?.id, strategy?.algorithm_type]) // Utiliser uniquement strategy.id pour éviter les re-renders

  const handleParameterChange = (key: string, value: any) => {
    setLocalParameters(prev => ({ ...prev, [key]: value }))
    onParameterChange(key, value) // Mise à jour temps réel
  }

  const handleSave = async () => {
    if (!strategy) return

    setLoading(true)
    setError(null)

    try {
      const algorithmType = strategy.algorithm_type
      if (!algorithmType) {
        throw new Error('Aucun algorithme sélectionné')
      }

      const definitions = ALGORITHM_PARAMETERS_DEFINITIONS[algorithmType] || []
      const algorithmParameters = definitions.map(def => {
        const value = localParameters[def.key] ?? def.default
        return {
          key: def.key,
          value: String(value),
          param_type: def.type,
          description: def.description || ''
        }
      })

      await strategyService.update(strategy.id, {
        algorithm_parameters_data: algorithmParameters
      } as any)

      await onSave(localParameters)
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Erreur lors de la sauvegarde')
    } finally {
      setLoading(false)
    }
  }

  if (!strategy || !strategy.algorithm_type) {
    return (
      <div className="strategy-parameters-panel">
        <p className="text-muted">Sélectionnez une stratégie</p>
      </div>
    )
  }

  const algorithmType = strategy.algorithm_type
  const definitions = ALGORITHM_PARAMETERS_DEFINITIONS[algorithmType] || []

  if (definitions.length === 0) {
    return (
      <div className="strategy-parameters-panel">
        <p className="text-muted">Aucun paramètre défini pour cet algorithme</p>
      </div>
    )
  }

  return (
    <div className="strategy-parameters-panel">
      <div className="panel-header">
        <h3>Paramètres</h3>
        {strategy.name && <p className="text-muted small">{strategy.name}</p>}
      </div>

      {error && (
        <div className="panel-error">
          {error}
        </div>
      )}

      <div className="panel-body">
        {definitions.map(def => {
          const value = localParameters[def.key] ?? def.default
          
          return (
            <div key={def.key} className="parameter-field">
              <label htmlFor={def.key}>
                {def.label}
                {def.description && (
                  <span className="text-muted small" style={{ display: 'block', fontSize: '0.75rem', fontWeight: 'normal' }}>
                    {def.description}
                  </span>
                )}
              </label>
              
              {def.type === 'bool' ? (
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    id={def.key}
                    checked={Boolean(value)}
                    onChange={(e) => handleParameterChange(def.key, e.target.checked)}
                  />
                  <span>{value ? 'Oui' : 'Non'}</span>
                </label>
              ) : def.type === 'int' ? (
                <div className="input-with-slider">
                  <input
                    type="range"
                    id={`${def.key}_slider`}
                    min={def.min ?? 0}
                    max={def.max ?? 100}
                    value={value}
                    onChange={(e) => handleParameterChange(def.key, parseInt(e.target.value, 10))}
                    className="parameter-slider"
                  />
                  <input
                    type="number"
                    id={def.key}
                    value={value}
                    onChange={(e) => handleParameterChange(def.key, parseInt(e.target.value, 10) || 0)}
                    min={def.min}
                    max={def.max}
                    className="parameter-input"
                  />
                </div>
              ) : def.type === 'float' ? (
                <div className="input-with-slider">
                  <input
                    type="range"
                    id={`${def.key}_slider`}
                    min={def.min ?? 0}
                    max={def.max ?? (def.max !== undefined ? def.max : 100)}
                    step={def.key.includes('stop_loss') ? 0.01 : 0.1}
                    value={value}
                    onChange={(e) => handleParameterChange(def.key, parseFloat(e.target.value))}
                    className="parameter-slider"
                  />
                  <input
                    type="number"
                    id={def.key}
                    step={def.key.includes('stop_loss') ? 0.01 : 0.1}
                    value={value}
                    onChange={(e) => handleParameterChange(def.key, parseFloat(e.target.value) || 0)}
                    min={def.min}
                    max={def.max}
                    className="parameter-input"
                  />
                </div>
              ) : (
                <input
                  type="text"
                  id={def.key}
                  value={value}
                  onChange={(e) => handleParameterChange(def.key, e.target.value)}
                  className="parameter-input"
                />
              )}
            </div>
          )
        })}
      </div>

      <div className="panel-footer">
        <Button
          variant="primary"
          onClick={handleSave}
          disabled={loading}
          fullWidth
        >
          {loading ? <Loading size="small" /> : 'Sauvegarder'}
        </Button>
      </div>
    </div>
  )
}

