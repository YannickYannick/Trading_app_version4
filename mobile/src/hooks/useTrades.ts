import { useState, useCallback } from 'react'
import { tradesService } from '../services/api'
import type { Trade } from '@trading-app/shared'
import { useFocusEffect } from '@react-navigation/native'

export const useTrades = () => {
    const [trades, setTrades] = useState<Trade[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const fetchTrades = useCallback(async () => {
        try {
            setIsLoading(true)
            setError(null)
            const data = await tradesService.getAll({ page_size: 50, ordering: '-timestamp' })
            setTrades(Array.isArray(data.results) ? data.results : [])
        } catch (e) {
            console.error('Error fetching trades:', e)
            setError('Impossible de charger les trades')
        } finally {
            setIsLoading(false)
        }
    }, [])

    useFocusEffect(
        useCallback(() => {
            fetchTrades()
        }, [fetchTrades])
    )

    return {
        trades,
        isLoading,
        error,
        refresh: fetchTrades
    }
}
