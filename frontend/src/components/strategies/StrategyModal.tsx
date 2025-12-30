/**
 * Modal pour créer/éditer une stratégie
 */
import { useState, useEffect } from 'react'
import { Modal, Button, Input, Badge, Loading } from '@components/common'
import { strategyService } from '@services'
import type { Strategy } from '@types'
import './StrategyModal.css'

interface StrategyModalProps {
  isOpen: boolean
  onClose: () => void
  strategy?: Strategy | null
  onSuccess: () => void
}

export default function StrategyModal({
  isOpen,
  onClose,
  strategy,
  onSuccess
}: StrategyModalProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  // Form fields
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [riskLevel, setRiskLevel] = useState<'LOW' | 'MEDIUM' | 'HIGH'>('MEDIUM')
  const [maxPositionSize, setMaxPositionSize] = useState<string>('')
  const [maxDailyLoss, setMaxDailyLoss] = useState<string>('')
  const [isActive, setIsActive] = useState(true)
  const [isAutomated, setIsAutomated] = useState(false)

  // Reset form when modal opens/closes or strategy changes
  useEffect(() => {
    if (isOpen) {
      if (strategy) {
        setName(strategy.name || '')
        setDescription(strategy.description || '')
        setRiskLevel(strategy.risk_level || 'MEDIUM')
        setMaxPositionSize(strategy.max_position_size?.toString() || '')
        setMaxDailyLoss(strategy.max_daily_loss?.toString() || '')
        setIsActive(strategy.is_active ?? true)
        setIsAutomated(strategy.is_automated ?? false)
      } else {
        // Reset to defaults for new strategy
        setName('')
        setDescription('')
        setRiskLevel('MEDIUM')
        setMaxPositionSize('')
        setMaxDailyLoss('')
        setIsActive(true)
        setIsAutomated(false)
      }
      setError(null)
      setSuccess(false)
    }
  }, [isOpen, strategy])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(false)

    try {
      const data: any = {
        name: name.trim(),
        description: description.trim(),
        risk_level: riskLevel,
        is_active: isActive,
        is_automated: isAutomated,
        parameters: {}, // Pour l'instant vide, sera étendu plus tard
      }

      if (maxPositionSize) {
        data.max_position_size = parseFloat(maxPositionSize)
      }
      if (maxDailyLoss) {
        data.max_daily_loss = parseFloat(maxDailyLoss)
      }

      if (strategy) {
        await strategyService.update(strategy.id, data)
      } else {
        await strategyService.create(data)
      }

      setSuccess(true)
      setTimeout(() => {
        onSuccess()
        onClose()
      }, 1000)
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Erreur lors de la sauvegarde')
      console.error('Erreur sauvegarde stratégie:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    if (!loading) {
      onClose()
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={strategy ? 'Modifier la stratégie' : 'Créer une stratégie'}
      size="lg"
    >
      <form onSubmit={handleSubmit} className="strategy-modal-form">
        {/* Nom */}
        <div className="form-group">
          <label htmlFor="strategy-name">Nom de la stratégie *</label>
          <Input
            id="strategy-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ex: Stratégie RSI Bitcoin"
            required
            disabled={loading}
            autoFocus
          />
          <small className="form-hint">
            Le nom peut inclure l'algorithme et l'asset (ex: "Stratégie RSI Bitcoin")
          </small>
        </div>

        {/* Description */}
        <div className="form-group">
          <label htmlFor="strategy-description">Description</label>
          <textarea
            id="strategy-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Description de la stratégie..."
            rows={3}
            disabled={loading}
            className="form-textarea"
          />
        </div>

        {/* Niveau de risque */}
        <div className="form-group">
          <label htmlFor="strategy-risk-level">Niveau de risque *</label>
          <select
            id="strategy-risk-level"
            value={riskLevel}
            onChange={(e) => setRiskLevel(e.target.value as 'LOW' | 'MEDIUM' | 'HIGH')}
            className="form-select"
            required
            disabled={loading}
          >
            <option value="LOW">Faible</option>
            <option value="MEDIUM">Moyen</option>
            <option value="HIGH">Élevé</option>
          </select>
          <small className="form-hint">
            Le niveau de risque détermine les paramètres par défaut de la stratégie
          </small>
        </div>

        {/* Taille max position */}
        <div className="form-group">
          <label htmlFor="strategy-max-position">
            Taille maximale d'une position (%)
          </label>
          <Input
            id="strategy-max-position"
            type="number"
            step="0.01"
            min="0"
            max="100"
            value={maxPositionSize}
            onChange={(e) => setMaxPositionSize(e.target.value)}
            placeholder="Ex: 10.0"
            disabled={loading}
          />
          <small className="form-hint">
            Limite la taille maximale d'une position en pourcentage du portefeuille total (0-100%)
          </small>
        </div>

        {/* Perte max journalière */}
        <div className="form-group">
          <label htmlFor="strategy-max-daily-loss">
            Perte maximale journalière (%)
          </label>
          <Input
            id="strategy-max-daily-loss"
            type="number"
            step="0.01"
            min="0"
            max="100"
            value={maxDailyLoss}
            onChange={(e) => setMaxDailyLoss(e.target.value)}
            placeholder="Ex: 5.0"
            disabled={loading}
          />
          <small className="form-hint">
            Si la perte quotidienne dépasse ce pourcentage, la stratégie s'arrêtera automatiquement (0-100%)
          </small>
        </div>

        {/* Statut */}
        <div className="form-group">
          <div className="form-checkbox-group">
            <label className="form-checkbox-label">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                disabled={loading}
                className="form-checkbox"
              />
              <span>Stratégie active</span>
            </label>
          </div>
        </div>

        {/* Automatisation */}
        <div className="form-group">
          <div className="form-checkbox-group">
            <label className="form-checkbox-label">
              <input
                type="checkbox"
                checked={isAutomated}
                onChange={(e) => setIsAutomated(e.target.checked)}
                disabled={loading}
                className="form-checkbox"
              />
              <span>Exécution automatique</span>
            </label>
            <small className="form-hint">
              La stratégie sera exécutée automatiquement selon une fréquence définie
            </small>
          </div>
        </div>

        {/* Erreur */}
        {error && (
          <div className="form-error">
            <Badge variant="danger">Erreur</Badge>
            <p>{error}</p>
          </div>
        )}

        {/* Succès */}
        {success && (
          <div className="form-success">
            <Badge variant="success">Succès</Badge>
            <p>
              Stratégie {strategy ? 'modifiée' : 'créée'} avec succès !
            </p>
          </div>
        )}

        {/* Actions */}
        <div className="form-actions">
          <Button
            type="submit"
            variant="primary"
            fullWidth
            disabled={loading || !name.trim()}
          >
            {loading ? 'Enregistrement...' : strategy ? 'Modifier' : 'Créer la stratégie'}
          </Button>
          <Button
            type="button"
            variant="outline"
            fullWidth
            onClick={handleClose}
            disabled={loading}
          >
            Annuler
          </Button>
        </div>
      </form>
    </Modal>
  )
}

