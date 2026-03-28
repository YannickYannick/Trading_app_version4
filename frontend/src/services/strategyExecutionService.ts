import apiClient from './api/client'

export interface StrategyExecution {
    id: number
    strategy: number
    strategy_id: number
    strategy_name: string
    started_at: string
    completed_at: string | null
    duration: number | null
    status: 'running' | 'completed' | 'failed'
    signal: 'BUY' | 'SELL' | 'HOLD' | 'NONE'
    signal_price: number | null
    signal_quantity: number | null
    output: string
    error: string
}

export interface ExecuteAllResponse {
    total_strategies: number
    results: Array<{
        strategy_id: number
        strategy_name: string
        status: 'success' | 'error'
        execution_id: number
        signal?: string
        error?: string
    }>
}

const strategyExecutionService = {
    /**
     * Récupère tous les logs d'exécution
     */
    async getAll(): Promise<StrategyExecution[]> {
        const response = await apiClient.get('/strategy-executions/')
        return response.data.results || response.data
    },

    /**
     * Récupère les logs récents (20 derniers)
     */
    async getRecent(): Promise<StrategyExecution[]> {
        const response = await apiClient.get('/strategy-executions/recent/')
        return response.data
    },

    /**
     * Exécute toutes les stratégies actives
     */
    async executeAll(): Promise<ExecuteAllResponse> {
        const response = await apiClient.post('/strategies/execute_all/')
        return response.data
    },

    /**
     * Exécute une stratégie spécifique
     */
    async execute(strategyId: number): Promise<any> {
        const response = await apiClient.post(`/strategies/${strategyId}/execute/`)
        return response.data
    },
}

export default strategyExecutionService
