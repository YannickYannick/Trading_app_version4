/**
 * Hook pour gérer les opérations asynchrones avec état de chargement et erreur
 */
import { useState, useCallback } from 'react'
import type { ApiError } from '@types/errors'

interface AsyncState<T> {
  data: T | null
  loading: boolean
  error: ApiError | null
}

interface UseAsyncOperationReturn<T> {
  data: T | null
  loading: boolean
  error: ApiError | null
  execute: (operation: () => Promise<T>) => Promise<{ success: boolean; data?: T; error?: ApiError }>
  reset: () => void
}

export const useAsyncOperation = <T,>(): UseAsyncOperationReturn<T> => {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    loading: false,
    error: null,
  })

  const execute = useCallback(
    async (operation: () => Promise<T>): Promise<{ success: boolean; data?: T; error?: ApiError }> => {
      setState({ data: null, loading: true, error: null })

      try {
        const data = await operation()
        setState({ data, loading: false, error: null })
        return { success: true, data }
      } catch (error: any) {
        // Normaliser l'erreur
        const normalizedError: ApiError = {
          error: error?.error || error?.message || 'Une erreur est survenue',
          code: error?.code || 'UNKNOWN_ERROR',
          message: error?.message || error?.error || 'Une erreur est survenue',
          details: error?.details || error?.response?.data,
          status: error?.status || error?.response?.status,
          originalError: error,
        }

        setState({ data: null, loading: false, error: normalizedError })
        return { success: false, error: normalizedError }
      }
    },
    []
  )

  const reset = useCallback(() => {
    setState({ data: null, loading: false, error: null })
  }, [])

  return {
    ...state,
    execute,
    reset,
  }
}

export default useAsyncOperation

