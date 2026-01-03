import { useState, useCallback } from 'react'
import { strategiesService } from '../services/api'
import type { Strategy } from '@trading-app/shared'
import { useFocusEffect } from '@react-navigation/native'

export const useStrategies = () => {
    const [strategies, setStrategies] = useState<Strategy[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const fetchStrategies = useCallback(async () => {
        try {
            setIsLoading(true)
            setError(null)
            const data = await strategiesService.getAll()
            // @ts-ignore - The API returns { results: Strategy[], count: number, ... } but type definition might vary
            const results = data.results || data
            setStrategies(Array.isArray(results) ? results : [])
        } catch (e) {
            console.error('Error fetching strategies:', e)
            setError('Impossible de charger les stratégies')
        } finally {
            setIsLoading(false)
        }
    }, [])

    useFocusEffect(
        useCallback(() => {
            fetchStrategies()
        }, [fetchStrategies])
    )

    const toggleStrategy = async (id: number, isActive: boolean) => {
        try {
            await strategiesService.toggleActive(id, isActive)
            // Optimistic update
            setStrategies(prev => prev.map(s =>
                s.id === id ? { ...s, is_active: isActive } : s
            ))
        } catch (e) {
            console.error('Error toggling strategy:', e)
            // Revert on error
            fetchStrategies()
        }
    }

    return {
        strategies,
        isLoading,
        error,
        refresh: fetchStrategies,
        toggleStrategy
    }
}
