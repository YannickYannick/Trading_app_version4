/**
 * Hook pour gérer les trades
 */
import { useState, useEffect, useCallback } from 'react'
import { tradeService, TradeFilters } from '@services'
import type { Trade, ApiError } from '@types'

export interface UseTradesOptions extends TradeFilters {
  autoFetch?: boolean
}

export function useTrades(options: UseTradesOptions = {}) {
  const { autoFetch = true, ...filters } = options
  const [trades, setTrades] = useState<Trade[]>([])
  const [loading, setLoading] = useState(autoFetch)
  const [error, setError] = useState<string | null>(null)
  const [total, setTotal] = useState(0)
  const [statistics, setStatistics] = useState<{
    total_trades: number
    total_volume: number
    total_fees: number
    buy_trades: number
    sell_trades: number
    win_rate: number
  } | null>(null)

  const fetchTrades = useCallback(async () => {
    const t0 = typeof performance !== 'undefined' ? performance.now() : Date.now()
    try {
      setLoading(true)
      setError(null)
      const response = await tradeService.getAll(filters)
      setTrades(response.results)
      setTotal(response.count)
    } catch (err: any) {
      const apiError = err as ApiError
      setError(apiError.error || apiError.message || 'Erreur lors du chargement des trades')
      setTrades([])
    } finally {
      setLoading(false)
      if (import.meta.env.DEV) {
        const t1 = typeof performance !== 'undefined' ? performance.now() : Date.now()
        // eslint-disable-next-line no-console
        console.info(`[HOOK PERF] useTrades.fetchTrades in ${Math.round(t1 - t0)}ms`)
      }
    }
  }, [JSON.stringify(filters)])

  const fetchStatistics = useCallback(async () => {
    const t0 = typeof performance !== 'undefined' ? performance.now() : Date.now()
    try {
      const data = await tradeService.getStatistics(filters)
      setStatistics(data)
    } catch (err) {
      console.error('Erreur lors du chargement des statistiques:', err)
    } finally {
      if (import.meta.env.DEV) {
        const t1 = typeof performance !== 'undefined' ? performance.now() : Date.now()
        // eslint-disable-next-line no-console
        console.info(`[HOOK PERF] useTrades.fetchStatistics in ${Math.round(t1 - t0)}ms`)
      }
    }
  }, [JSON.stringify(filters)])

  useEffect(() => {
    if (autoFetch) {
      fetchTrades()
      fetchStatistics()
    }
  }, [autoFetch, fetchTrades, fetchStatistics])

  return {
    trades,
    loading,
    error,
    total,
    statistics,
    refetch: fetchTrades,
  }
}

