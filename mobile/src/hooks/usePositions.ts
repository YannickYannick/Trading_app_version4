import { useState, useCallback } from 'react'
import { positionsService } from '../services/api'
import type { Position } from '@trading-app/shared'
import { useFocusEffect } from '@react-navigation/native'

export const usePositions = () => {
    const [positions, setPositions] = useState<Position[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const fetchPositions = useCallback(async () => {
        try {
            setIsLoading(true)
            setError(null)
            const data = await positionsService.getOpen()
            setPositions(Array.isArray(data) ? data : [])
        } catch (e) {
            console.error('Error fetching positions:', e)
            setError('Impossible de charger les positions')
        } finally {
            setIsLoading(false)
        }
    }, [])

    useFocusEffect(
        useCallback(() => {
            fetchPositions()
        }, [fetchPositions])
    )

    return {
        positions,
        isLoading,
        error,
        refresh: fetchPositions
    }
}
