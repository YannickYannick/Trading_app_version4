/**
 * Hook pour gérer les positions
 */
import { useState, useEffect, useCallback } from 'react'
import { positionService, PositionFilters } from '@services'
import type { Position, ApiError } from '@types'

export interface UsePositionsOptions extends PositionFilters {
  autoFetch?: boolean
}

export function usePositions(options: UsePositionsOptions = {}) {
  const { autoFetch = true, ...filters } = options
  const [positions, setPositions] = useState<Position[]>([])
  const [loading, setLoading] = useState(autoFetch)
  const [error, setError] = useState<string | null>(null)
  const [total, setTotal] = useState(0)
  const [summary, setSummary] = useState<{
    total_positions: number
    open_positions: number
    closed_positions: number
    total_pnl: number
    total_value: number
  } | null>(null)

  const fetchPositions = useCallback(async () => {
    const t0 = typeof performance !== 'undefined' ? performance.now() : Date.now()
    try {
      setLoading(true)
      setError(null)
      const response = await positionService.getAll(filters)
      setPositions(response.results)
      setTotal(response.count)
    } catch (err: any) {
      const apiError = err as ApiError
      setError(apiError.error || apiError.message || 'Erreur lors du chargement des positions')
      setPositions([])
    } finally {
      setLoading(false)
      if (import.meta.env.DEV) {
        const t1 = typeof performance !== 'undefined' ? performance.now() : Date.now()
        // eslint-disable-next-line no-console
        console.info(`[HOOK PERF] usePositions.fetchPositions in ${Math.round(t1 - t0)}ms`)
      }
    }
  }, [JSON.stringify(filters)])

  const fetchSummary = useCallback(async () => {
    const t0 = typeof performance !== 'undefined' ? performance.now() : Date.now()
    try {
      const data = await positionService.getSummary()
      setSummary(data)
    } catch (err) {
      console.error('Erreur lors du chargement du résumé:', err)
    } finally {
      if (import.meta.env.DEV) {
        const t1 = typeof performance !== 'undefined' ? performance.now() : Date.now()
        // eslint-disable-next-line no-console
        console.info(`[HOOK PERF] usePositions.fetchSummary in ${Math.round(t1 - t0)}ms`)
      }
    }
  }, [])

  useEffect(() => {
    if (autoFetch) {
      fetchPositions()
      fetchSummary()
    }
  }, [autoFetch, fetchPositions, fetchSummary])

  const closePosition = useCallback(
    async (id: number, closePrice?: number) => {
      try {
        await positionService.close(id, closePrice)
        await fetchPositions() // Rafraîchir la liste
        await fetchSummary() // Rafraîchir le résumé
      } catch (err: any) {
        const apiError = err as ApiError
        throw new Error(apiError.error || apiError.message || 'Erreur lors de la fermeture')
      }
    },
    [fetchPositions, fetchSummary]
  )

  return {
    positions,
    loading,
    error,
    total,
    summary,
    refetch: fetchPositions,
    closePosition,
  }
}

