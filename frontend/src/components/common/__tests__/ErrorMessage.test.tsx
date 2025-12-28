/**
 * Tests pour le composant ErrorMessage
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import ErrorMessage from '../ErrorMessage'

describe('ErrorMessage', () => {
  it('should not render when error is null', () => {
    const { container } = render(<ErrorMessage error={null} />)
    expect(container.firstChild).toBeNull()
  })

  it('should render string error', () => {
    render(<ErrorMessage error="Test error" />)
    expect(screen.getByText(/Test error/)).toBeInTheDocument()
  })

  it('should render ApiError object', () => {
    const error = {
      error: 'Error message',
      message: 'Error message',
      code: 'TEST_ERROR',
    }
    render(<ErrorMessage error={error} />)
    expect(screen.getByText(/Error message/)).toBeInTheDocument()
  })

  it('should show retry button when onRetry is provided', () => {
    const onRetry = vi.fn()
    render(<ErrorMessage error="Test error" onRetry={onRetry} />)
    const retryButton = screen.getByText(/Réessayer/)
    expect(retryButton).toBeInTheDocument()
  })

  it('should show dismiss button when onDismiss is provided', () => {
    const onDismiss = vi.fn()
    render(<ErrorMessage error="Test error" onDismiss={onDismiss} />)
    const dismissButton = screen.getByLabelText(/Fermer/)
    expect(dismissButton).toBeInTheDocument()
  })

  it('should show details when showDetails is true', () => {
    const error = {
      error: 'Error message',
      message: 'Error message',
      details: { field: 'test' },
    }
    render(<ErrorMessage error={error} showDetails={true} />)
    expect(screen.getByText(/Détails techniques/)).toBeInTheDocument()
  })
})

