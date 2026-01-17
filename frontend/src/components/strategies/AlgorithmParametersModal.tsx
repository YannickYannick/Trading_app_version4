/**
 * Modal pour éditer les paramètres d'algorithme d'une stratégie
 */
import { useState, useEffect } from 'react'
import { Modal, Button, Input, Loading } from '@components/common'
import { strategyService } from '@services'
import type { Strategy } from '@types'
import './AlgorithmParametersModal.css'

// Définitions des paramètres par algorithme
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
    { key: 'order_size', label: 'Taille d\'ordre max', type: 'float', default: 1.0, min: 0.01 },
    { key: 'stop_loss', label: 'Stop-loss (%)', type: 'float', default: 0.05, min: 0, max: 1 },
  ],
  ma_crossover: [
    { key: 'ma1_period', label: 'Période MA rapide', type: 'int', default: 20, min: 1, max: 200 },
    { key: 'ma2_period', label: 'Période MA lente', type: 'int', default: 50, min: 1, max: 200 },
    { key: 'order_size', label: 'Taille d\'ordre max', type: 'float', default: 1.0, min: 0.01 },
    { key: 'stop_loss', label: 'Stop-loss (%)', type: 'float', default: 0.05, min: 0, max: 1 },
  ],
  rsi: [
    { key: 'rsi_period', label: 'Période RSI', type: 'int', default: 14, min: 2, max: 100 },
    { key: 'rsi_low', label: 'Seuil bas RSI', type: 'int', default: 30, min: 0, max: 100 },
    { key: 'rsi_high', label: 'Seuil haut RSI', type: 'int', default: 70, min: 0, max: 100 },
    { key: 'order_size', label: 'Taille d\'ordre max', type: 'float', default: 1.0, min: 0.01 },
    { key: 'stop_loss', label: 'Stop-loss (%)', type: 'float', default: 0.05, min: 0, max: 1 },
  ],
  bollinger: [
    { key: 'bb_period', label: 'Période Bollinger', type: 'int', default: 20, min: 2, max: 200 },
    { key: 'bb_std', label: 'Écart-type', type: 'float', default: 2.0, min: 0.1, max: 5 },
    { key: 'order_size', label: 'Taille d\'ordre max', type: 'float', default: 1.0, min: 0.01 },
    { key: 'stop_loss', label: 'Stop-loss (%)', type: 'float', default: 0.05, min: 0, max: 1 },
  ],
  macd: [
    { key: 'macd_fast', label: 'Période EMA rapide', type: 'int', default: 12, min: 1, max: 50 },
    { key: 'macd_slow', label: 'Période EMA lente', type: 'int', default: 26, min: 1, max: 100 },
    { key: 'macd_signal', label: 'Période signal', type: 'int', default: 9, min: 1, max: 50 },
    { key: 'order_size', label: 'Taille d\'ordre max', type: 'float', default: 1.0, min: 0.01 },
    { key: 'stop_loss', label: 'Stop-loss (%)', type: 'float', default: 0.05, min: 0, max: 1 },
  ],
  grid: [
    { key: 'grid_min', label: 'Prix minimum', type: 'float', default: 100.0, min: 0 },
    { key: 'grid_max', label: 'Prix maximum', type: 'float', default: 200.0, min: 0 },
    { key: 'grid_levels', label: 'Nombre de niveaux', type: 'int', default: 10, min: 2, max: 100 },
    { key: 'order_size', label: 'Taille d\'ordre max', type: 'float', default: 1.0, min: 0.01 },
    { key: 'stop_loss', label: 'Stop-loss (%)', type: 'float', default: 0.05, min: 0, max: 1 },
  ],
}

interface AlgorithmParametersModalProps {
  isOpen: boolean
  onClose: () => void
  strategy: Strategy | null
  onSuccess: () => void
}

export default function AlgorithmParametersModal({
  isOpen,
  onClose,
  strategy,
  onSuccess
}: AlgorithmParametersModalProps) {
  const [parameters, setParameters] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Charger les paramètres depuis la stratégie
  useEffect(() => {
    if (strategy && isOpen) {
      const params: Record<string, any> = {}

      // Utiliser algorithm_parameters si disponible (nouveau système)
      if (strategy.algorithm_parameters && strategy.algorithm_parameters.length > 0) {
        strategy.algorithm_parameters.forEach(param => {
          let value: any = param.value

          // Convertir selon le type
          if (param.param_type === 'int') {
            value = parseInt(value, 10)
          } else if (param.param_type === 'float') {
            value = parseFloat(value)
          } else if (param.param_type === 'bool') {
            value = value.toLowerCase() === 'true' || value === true || value === '1'
          }

          params[param.key] = value
        })
      } else if (strategy.parameters) {
        // Fallback vers parameters (ancien système)
        Object.assign(params, strategy.parameters)
      }

      // Initialiser avec les valeurs par défaut si manquantes
      const algorithmType = strategy.algorithm_type
      if (algorithmType && ALGORITHM_PARAMETERS_DEFINITIONS[algorithmType]) {
        ALGORITHM_PARAMETERS_DEFINITIONS[algorithmType].forEach(def => {
          // Cas spéciaux pour les champs du modèle (order_size et stop_loss)
          if (def.key === 'order_size' && strategy.max_quantity) {
            params[def.key] = Number(strategy.max_quantity)
            return
          }
          if (def.key === 'stop_loss' && strategy.stop_loss_percentage) {
            params[def.key] = Number(strategy.stop_loss_percentage)
            return
          }

          if (params[def.key] === undefined || params[def.key] === null) {
            params[def.key] = def.default
          }
        })
      }

      setParameters(params)
      setError(null)
    }
  }, [strategy, isOpen])

  const handleChange = (key: string, value: any) => {
    setParameters(prev => ({
      ...prev,
      [key]: value
    }))
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

      // Préparer les données globales de la stratégie
      const strategyUpdateData: any = {}

      // Construire la liste des algorithm_parameters à envoyer
      const algorithmParameters = []

      for (const def of definitions) {
        const value = parameters[def.key] ?? def.default

        // Intercepter les champs globaux
        if (def.key === 'order_size') {
          strategyUpdateData.max_quantity = value
          continue
        }
        if (def.key === 'stop_loss') {
          strategyUpdateData.stop_loss_percentage = value
          continue
        }

        algorithmParameters.push({
          key: def.key,
          value: String(value),
          param_type: def.type,
          description: def.description || ''
        })
      }

      // Envoyer les paramètres via l'API
      // Utiliser algorithm_parameters_data pour l'écriture (le serializer gère la conversion)
      await strategyService.update(strategy.id, {
        ...strategyUpdateData,
        algorithm_parameters_data: algorithmParameters
      } as any)

      onSuccess()
      onClose()
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Erreur lors de la sauvegarde')
    } finally {
      setLoading(false)
    }
  }

  if (!strategy || !strategy.algorithm_type) {
    return null
  }

  const algorithmType = strategy.algorithm_type
  const definitions = ALGORITHM_PARAMETERS_DEFINITIONS[algorithmType] || []

  if (definitions.length === 0) {
    return (
      <Modal isOpen={isOpen} onClose={onClose} title="Paramètres d'algorithme">
        <div style={{ padding: '1rem' }}>
          <p className="text-muted">Aucun paramètre défini pour cet algorithme.</p>
          <Button onClick={onClose}>Fermer</Button>
        </div>
      </Modal>
    )
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Paramètres d'algorithme - ${strategy.name}`}>
      <div className="algorithm-parameters-modal">
        {error && (
          <div className="alert alert-danger" style={{ marginBottom: '1rem' }}>
            {error}
          </div>
        )}

        <div className="parameters-form">
          {definitions.map(def => {
            const value = parameters[def.key] ?? def.default

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
                  <input
                    type="checkbox"
                    id={def.key}
                    checked={Boolean(value)}
                    onChange={(e) => handleChange(def.key, e.target.checked)}
                    disabled={loading}
                  />
                ) : def.type === 'int' ? (
                  <Input
                    type="number"
                    id={def.key}
                    value={value}
                    onChange={(e) => handleChange(def.key, parseInt(e.target.value, 10) || 0)}
                    min={def.min}
                    max={def.max}
                    disabled={loading}
                  />
                ) : def.type === 'float' ? (
                  <Input
                    type="number"
                    step="0.01"
                    id={def.key}
                    value={value}
                    onChange={(e) => handleChange(def.key, parseFloat(e.target.value) || 0)}
                    min={def.min}
                    max={def.max}
                    disabled={loading}
                  />
                ) : (
                  <Input
                    type="text"
                    id={def.key}
                    value={value}
                    onChange={(e) => handleChange(def.key, e.target.value)}
                    disabled={loading}
                  />
                )}
              </div>
            )
          })}
        </div>

        <div className="modal-actions" style={{ marginTop: '1.5rem', display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
          <Button variant="outline" onClick={onClose} disabled={loading}>
            Annuler
          </Button>
          <Button variant="primary" onClick={handleSave} disabled={loading}>
            {loading ? <Loading size="small" /> : 'Sauvegarder'}
          </Button>
        </div>
      </div>
    </Modal>
  )
}

