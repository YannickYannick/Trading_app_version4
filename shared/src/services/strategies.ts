/**
 * Service pour les Strategies (shared)
 */
import type { AxiosInstance } from 'axios'
import type { ApiResponse, Strategy, StrategyPerformance } from '../types'

export interface StrategyFilters {
  is_active?: boolean
  strategy_type?: string
  search?: string
  page?: number
  page_size?: number
}

export interface StrategyCreateData {
  name: string
  description?: string
  risk_level?: 'LOW' | 'MEDIUM' | 'HIGH'
  max_position_size?: number
  max_daily_loss?: number
  parameters?: Record<string, any>
  is_active?: boolean
  is_automated?: boolean
  strategy_type?: string
}

/**
 * Factory function pour créer le service strategies
 */
export function createStrategyService(apiClient: AxiosInstance) {
  return {
    async getAll(filters?: StrategyFilters): Promise<ApiResponse<Strategy>> {
      const response = await apiClient.get<ApiResponse<Strategy>>('/strategies/', {
        params: filters,
      })
      return response.data
    },

    async getById(id: number): Promise<Strategy> {
      const response = await apiClient.get<Strategy>(`/strategies/${id}/`)
      return response.data
    },

    async getActive(): Promise<Strategy[]> {
      const response = await apiClient.get<ApiResponse<Strategy>>('/strategies/', {
        params: { is_active: true },
      })
      return response.data.results
    },

    async create(data: StrategyCreateData): Promise<Strategy> {
      const response = await apiClient.post<Strategy>('/strategies/', data)
      return response.data
    },

    async update(id: number, data: Partial<Strategy>): Promise<Strategy> {
      const response = await apiClient.patch<Strategy>(`/strategies/${id}/`, data)
      return response.data
    },

    async toggleActive(id: number, isActive: boolean): Promise<Strategy> {
      return this.update(id, { is_active: isActive })
    },

    async delete(id: number): Promise<void> {
      await apiClient.delete(`/strategies/${id}/`)
    },

    async getPerformance(strategyId: number): Promise<ApiResponse<StrategyPerformance>> {
      const response = await apiClient.get<ApiResponse<StrategyPerformance>>(
        `/strategies/${strategyId}/performance/`
      )
      return response.data
    },

    async getAllPerformance(): Promise<ApiResponse<StrategyPerformance>> {
      const response = await apiClient.get<ApiResponse<StrategyPerformance>>('/strategy-performance/')
      return response.data
    },
  }
}

