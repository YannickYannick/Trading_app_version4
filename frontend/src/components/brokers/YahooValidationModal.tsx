/**
 * Modal pour la validation Yahoo avec barre de progression
 */
import { useState, useEffect, useRef } from 'react'
import Modal from '@components/common/Modal'
import Button from '@components/common/Button'
import { brokerService } from '@services'
import './YahooValidationModal.css'

interface YahooValidationModalProps {
  isOpen: boolean
  onClose: () => void
  onComplete?: (result: any) => void
  limit?: number
  reset?: boolean
}

export default function YahooValidationModal({
  isOpen,
  onClose,
  onComplete,
  limit = 100,
  reset = false,
}: YahooValidationModalProps) {
  const [isValidating, setIsValidating] = useState(false)
  const [progress, setProgress] = useState(0)
  const [current, setCurrent] = useState(0)
  const [total, setTotal] = useState(0)
  const [status, setStatus] = useState<'idle' | 'running' | 'completed' | 'error'>('idle')
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<any>(null)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  const startTimeRef = useRef<number | null>(null)

  const startValidation = async () => {
    setIsValidating(true)
    setStatus('running')
    setProgress(0)
    setCurrent(0)
    setTotal(0)
    setError(null)
    setResult(null)
    startTimeRef.current = Date.now()

    try {
      // Lancer la validation
      const validationPromise = brokerService.validateYahooSymbols({
        limit,
        reset,
      })

      // Simuler le progrès pendant que la validation se fait
      // On ne peut pas vraiment tracker le progrès réel sans WebSockets,
      // donc on simule un progrès basé sur le temps écoulé
      intervalRef.current = setInterval(() => {
        if (startTimeRef.current) {
          const elapsed = Date.now() - startTimeRef.current
          // Estimation: ~500ms par asset en moyenne
          const estimatedTotal = limit * 500
          const simulatedProgress = Math.min(95, (elapsed / estimatedTotal) * 100)
          setProgress(simulatedProgress)
          setCurrent(Math.floor((simulatedProgress / 100) * limit))
          setTotal(limit)
        }
      }, 200) // Mettre à jour toutes les 200ms

      // Attendre la réponse
      const result = await validationPromise

      // Arrêter la simulation
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }

      // Mettre à jour avec les vraies valeurs
      setProgress(100)
      setCurrent(result.processed || limit)
      setTotal(result.processed || limit)
      setStatus('completed')
      setResult(result)

      if (result.success) {
        if (onComplete) {
          onComplete(result)
        }
      } else {
        setStatus('error')
        setError(result.error || 'Erreur inconnue')
      }
    } catch (err: any) {
      // Arrêter la simulation
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }

      setStatus('error')
      const errorMsg =
        err.response?.data?.error ||
        err.response?.data?.message ||
        err.message ||
        'Erreur lors de la validation'
      setError(errorMsg)
    } finally {
      setIsValidating(false)
    }
  }

  const handleClose = () => {
    if (status === 'running') {
      const confirmed = window.confirm(
        'La validation est en cours. Êtes-vous sûr de vouloir fermer?'
      )
      if (!confirmed) return
      // Arrêter la validation si confirmé
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      setIsValidating(false)
    }
    // Réinitialiser l'état quand on ferme
    setStatus('idle')
    setProgress(0)
    setCurrent(0)
    setTotal(0)
    setError(null)
    setResult(null)
    setIsValidating(false)
    startTimeRef.current = null
    onClose()
  }

  // Réinitialiser l'état quand le modal s'ouvre
  useEffect(() => {
    if (isOpen && status !== 'running') {
      setStatus('idle')
      setProgress(0)
      setCurrent(0)
      setTotal(0)
      setError(null)
      setResult(null)
      setIsValidating(false)
      startTimeRef.current = null
    }
  }, [isOpen]) // Se déclenche quand isOpen change

  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [])

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const elapsedTime =
    startTimeRef.current && status === 'running'
      ? Math.floor((Date.now() - startTimeRef.current) / 1000)
      : 0

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Validation des symboles Yahoo Finance"
      size="medium"
    >
      <div className="yahoo-validation-modal">
        {status === 'idle' && (
          <div className="yahoo-validation-start">
            <p>
              Cette opération va valider les symboles Yahoo Finance pour les assets.
            </p>
            <p>
              <strong>Paramètres:</strong>
            </p>
            <ul>
              <li>Limite: {limit} assets</li>
              <li>Reset: {reset ? 'Oui' : 'Non'}</li>
            </ul>
            <div className="yahoo-validation-actions">
              <Button onClick={startValidation} variant="primary" disabled={isValidating}>
                Démarrer la validation
              </Button>
              <Button onClick={handleClose} variant="outline">
                Annuler
              </Button>
            </div>
          </div>
        )}

        {(status === 'running' || status === 'completed') && (
          <div className="yahoo-validation-progress">
            <div className="yahoo-validation-progress-header">
              <h3>
                {status === 'running' ? 'Validation en cours...' : 'Validation terminée!'}
              </h3>
              {status === 'running' && (
                <span className="yahoo-validation-time">⏱️ {formatTime(elapsedTime)}</span>
              )}
            </div>

            <div className="yahoo-validation-progress-bar-container">
              <div className="yahoo-validation-progress-bar">
                <div
                  className="yahoo-validation-progress-bar-fill"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <div className="yahoo-validation-progress-text">
                {current} / {total} assets traités ({Math.round(progress)}%)
              </div>
            </div>

            {result && status === 'completed' && (
              <div className="yahoo-validation-results">
                <div className="yahoo-validation-result-item">
                  <span className="yahoo-validation-result-label">✅ Assets validés:</span>
                  <span className="yahoo-validation-result-value">{result.validated}</span>
                </div>
                <div className="yahoo-validation-result-item">
                  <span className="yahoo-validation-result-label">❌ Non trouvés:</span>
                  <span className="yahoo-validation-result-value">{result.not_found}</span>
                </div>
                <div className="yahoo-validation-result-item">
                  <span className="yahoo-validation-result-label">⚠️ Erreurs:</span>
                  <span className="yahoo-validation-result-value">{result.failed}</span>
                </div>
                {result.details && (
                  <div className="yahoo-validation-result-details">
                    <p>
                      <strong>Détails:</strong>
                    </p>
                    <ul>
                      <li>Y4 (MIC): {result.details.y4_matches || 0}</li>
                      <li>Y3 (Nom): {result.details.y3_matches || 0}</li>
                      <li>Y0 (Symbole): {result.details.y0_matches || 0}</li>
                    </ul>
                  </div>
                )}
              </div>
            )}

            <div className="yahoo-validation-actions">
              {status === 'completed' && (
                <Button onClick={handleClose} variant="primary">
                  Fermer
                </Button>
              )}
            </div>
          </div>
        )}

        {status === 'error' && (
          <div className="yahoo-validation-error">
            <p className="yahoo-validation-error-message">❌ {error}</p>
            <div className="yahoo-validation-actions">
              <Button onClick={handleClose} variant="outline">
                Fermer
              </Button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  )
}

