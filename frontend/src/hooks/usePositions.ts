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
    }
  }, [JSON.stringify(filters)])

  const fetchSummary = useCallback(async () => {
    try {
      const data = await positionService.getSummary()
      setSummary(data)
    } catch (err) {
      console.error('Erreur lors du chargement du résumé:', err)
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

