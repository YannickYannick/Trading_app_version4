/**
 * Composant pour afficher les erreurs de manière cohérente
 */
import React from 'react'
import Button from './Button'
import type { ApiError, ErrorType } from '@types/errors'
import './ErrorMessage.css'

interface ErrorMessageProps {
  error: ApiError | string | null
  onRetry?: () => void
  onDismiss?: () => void
  className?: string
  showDetails?: boolean
}

const ErrorMessage: React.FC<ErrorMessageProps> = ({
  error,
  onRetry,
  onDismiss,
  className = '',
  showDetails = false,
}) => {
  if (!error) return null

  // Normaliser l'erreur
  const normalizedError: ApiError =
    typeof error === 'string'
      ? {
          error: error,
          message: error,
          code: 'UNKNOWN_ERROR',
        }
      : error

  const getErrorType = (): ErrorType => {
    if (normalizedError.code === 'NETWORK_ERROR') return 'network'
    if (normalizedError.status === 401 || normalizedError.code === 'AUTHENTICATION_ERROR') return 'auth'
    if (normalizedError.status && normalizedError.status >= 400 && normalizedError.status < 500) return 'client'
    if (normalizedError.status && normalizedError.status >= 500) return 'server'
    if (normalizedError.code === 'VALIDATION_ERROR') return 'validation'
    return 'unknown'
  }

  const errorType = getErrorType()

  const getErrorIcon = () => {
    switch (errorType) {
      case 'network':
        return 'fa-wifi'
      case 'auth':
        return 'fa-lock'
      case 'client':
        return 'fa-exclamation-triangle'
      case 'server':
        return 'fa-server'
      case 'validation':
        return 'fa-check-circle'
      default:
        return 'fa-exclamation-circle'
    }
  }

  const getErrorVariant = () => {
    switch (errorType) {
      case 'network':
        return 'warning'
      case 'auth':
        return 'danger'
      case 'client':
        return 'warning'
      case 'server':
        return 'danger'
      case 'validation':
        return 'warning'
      default:
        return 'danger'
    }
  }

  const errorMessage = normalizedError.message || normalizedError.error || 'Une erreur est survenue'

  return (
    <div className={`error-message error-message--${getErrorVariant()} ${className}`}>
      <div className="error-message-content">
        <div className="error-message-icon">
          <i className={`fas ${getErrorIcon()}`}></i>
        </div>
        <div className="error-message-text">
          <strong>Erreur :</strong> {errorMessage}
        </div>
        {onDismiss && (
          <button
            type="button"
            className="error-message-close"
            onClick={onDismiss}
            aria-label="Fermer"
          >
            <i className="fas fa-times"></i>
          </button>
        )}
      </div>

      {showDetails && normalizedError.details && (
        <details className="error-message-details">
          <summary className="error-message-details-summary">Détails techniques</summary>
          <pre className="error-message-details-content">
            {JSON.stringify(normalizedError.details, null, 2)}
          </pre>
        </details>
      )}

      {onRetry && (
        <div className="error-message-actions">
          <Button size="sm" variant="primary" onClick={onRetry}>
            <i className="fas fa-redo me-1"></i>
            Réessayer
          </Button>
        </div>
      )}
    </div>
  )
}

export default ErrorMessage

