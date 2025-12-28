/**
 * Hook pour gérer les erreurs de manière cohérente
 */
import { useState, useCallback } from 'react'
import type { ApiError, ErrorState } from '@types/errors'

interface UseErrorHandlerReturn {
  error: ApiError | null
  hasError: boolean
  handleError: (error: any) => void
  clearError: () => void
  getErrorMessage: () => string | null
}

export const useErrorHandler = (): UseErrorHandlerReturn => {
  const [errorState, setErrorState] = useState<ErrorState>({
    error: null,
    hasError: false,
  })

  const handleError = useCallback((error: any) => {
    console.error('Error caught:', error)

    // Normaliser l'erreur
    const normalizedError: ApiError =
      typeof error === 'string'
        ? {
            error: error,
            message: error,
            code: 'UNKNOWN_ERROR',
          }
        : {
            error: error?.error || error?.message || 'Une erreur est survenue',
            code: error?.code || 'UNKNOWN_ERROR',
            message: error?.message || error?.error || 'Une erreur est survenue',
            details: error?.details || error?.response?.data,
            status: error?.status || error?.response?.status,
            originalError: error,
          }

    setErrorState({
      error: normalizedError,
      hasError: true,
    })
  }, [])

  const clearError = useCallback(() => {
    setErrorState({
      error: null,
      hasError: false,
    })
  }, [])

  const getErrorMessage = useCallback((): string | null => {
    if (!errorState.error) return null
    return errorState.error.message || errorState.error.error || 'Une erreur est survenue'
  }, [errorState.error])

  return {
    error: errorState.error,
    hasError: errorState.hasError,
    handleError,
    clearError,
    getErrorMessage,
  }
}

export default useErrorHandler

