/**
 * Hook générique pour les appels API
 * Utile pour les appels API simples qui ne nécessitent pas un hook dédié
 */
import { useState, useEffect, useCallback } from 'react'
import type { ApiError } from '@types'

export interface UseApiOptions<T> {
  fetchFn: () => Promise<T>
  autoFetch?: boolean
  dependencies?: any[]
  onSuccess?: (data: T) => void
  onError?: (error: ApiError) => void
}

export function useApi<T>({
  fetchFn,
  autoFetch = true,
  dependencies = [],
  onSuccess,
  onError,
}: UseApiOptions<T>) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(autoFetch)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const result = await fetchFn()
      setData(result)
      onSuccess?.(result)
      return result
    } catch (err: any) {
      const apiError = err as ApiError
      const errorMessage = apiError.error || apiError.message || 'Une erreur est survenue'
      setError(errorMessage)
      setData(null)
      onError?.(apiError)
      throw err
    } finally {
      setLoading(false)
    }
  }, [fetchFn, onSuccess, onError])

  useEffect(() => {
    if (autoFetch) {
      fetch()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoFetch, fetch, ...dependencies])

  return {
    data,
    loading,
    error,
    refetch: fetch,
  }
}

