import { useState, useEffect, useCallback } from 'react'
import strategyExecutionService, { StrategyExecution } from '../services/strategyExecutionService'

export function useStrategyExecutions() {
    const [executions, setExecutions] = useState<StrategyExecution[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const fetchExecutions = useCallback(async () => {
        try {
            setLoading(true)
            const data = await strategyExecutionService.getRecent()
            setExecutions(data)
            setError(null)
            console.log('📊 Loaded executions:', data.length, 'items')
        } catch (err: any) {
            console.error('❌ Error loading executions:', err)
            setError(err.message || 'Erreur lors du chargement des exécutions')
        } finally {
            setLoading(false)
        }
    }, [])

    // Chargement initial
    useEffect(() => {
        fetchExecutions()
    }, [fetchExecutions])

    const executeAll = useCallback(async () => {
        try {
            console.log('▶️ Executing all strategies...')
            const result = await strategyExecutionService.executeAll()
            console.log('✅ Executed all strategies:', result)

            // Rafraîchir une seule fois après l'exécution
            await fetchExecutions()

            return result
        } catch (err: any) {
            console.error('❌ Error executing strategies:', err)
            setError(err.message || 'Erreur lors de l\'exécution')
            throw err
        }
    }, [fetchExecutions])

    return {
        executions,
        loading,
        error,
        refetch: fetchExecutions,
        executeAll,
    }
}
