/**
 * Error Boundary pour capturer les erreurs de rendu React
 */
import React, { Component, ErrorInfo, ReactNode } from 'react'
import Button from './Button'
import './ErrorBoundary.css'

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
    
    // Appeler le callback si fourni
    if (this.props.onError) {
      this.props.onError(error, errorInfo)
    }

    // Ici, on pourrait envoyer l'erreur à un service de logging
    // logErrorToService(error, errorInfo)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
  }

  handleReload = () => {
    window.location.reload()
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="error-boundary">
          <div className="error-boundary-content">
            <div className="error-boundary-icon">
              <i className="fas fa-exclamation-triangle"></i>
            </div>
            <h2 className="error-boundary-title">Une erreur est survenue</h2>
            <p className="error-boundary-message">
              Désolé, une erreur inattendue s'est produite. Veuillez rafraîchir la page ou
              contacter le support si le problème persiste.
            </p>

            <details className="error-boundary-details">
              <summary className="error-boundary-details-summary">Détails de l'erreur</summary>
              <pre className="error-boundary-details-content">
                {this.state.error?.toString()}
                {this.state.error?.stack}
              </pre>
            </details>

            <div className="error-boundary-actions">
              <Button variant="primary" onClick={this.handleReset}>
                <i className="fas fa-redo me-1"></i>
                Réessayer
              </Button>
              <Button variant="outline" onClick={this.handleReload}>
                <i className="fas fa-refresh me-1"></i>
                Rafraîchir la page
              </Button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary

