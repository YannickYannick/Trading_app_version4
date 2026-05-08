/**
 * Service pour les Strategies
 */
import apiClient from './api/client'
import type { ApiResponse, Strategy, StrategyPerformance, ApiError } from '@types'

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

/** Réponse POST /strategies/from_portfolio/ */
export interface CreateStrategiesFromPortfolioResponse {
  created: Strategy[]
  created_count: number
  skipped_existing: Array<{ all_asset_id: number; symbol: string }>
  skipped_no_broker_account: Array<{ all_asset_id: number; symbol: string; broker_id: number }>
  errors: Array<{ all_asset_id: number; symbol: string; error: string }>
}

export const strategyService = {
  /**
   * Récupérer toutes les stratégies
   */
  async getAll(filters?: StrategyFilters): Promise<ApiResponse<Strategy>> {
    const response = await apiClient.get<ApiResponse<Strategy>>('/strategies/', {
      params: filters,
    })
    return response.data
  },

  /**
   * Récupérer une stratégie par ID
   */
  async getById(id: number): Promise<Strategy> {
    const response = await apiClient.get<Strategy>(`/strategies/${id}/`)
    return response.data
  },

  /**
   * Récupérer les stratégies actives
   */
  async getActive(): Promise<Strategy[]> {
    const response = await apiClient.get<ApiResponse<Strategy>>('/strategies/', {
      params: { is_active: true },
    })
    return response.data.results
  },

  /**
   * Créer une stratégie
   */
  async create(data: StrategyCreateData): Promise<Strategy> {
    const response = await apiClient.post<Strategy>('/strategies/', data)
    return response.data
  },

  /**
   * Créer en masse des stratégies pour les actifs du portefeuille (positions + ordres BUY).
   */
  async createFromPortfolio(): Promise<CreateStrategiesFromPortfolioResponse> {
    const response = await apiClient.post<CreateStrategiesFromPortfolioResponse>(
      '/strategies/from_portfolio/'
    )
    return response.data
  },

  /**
   * Mettre à jour une stratégie
   */
  async update(id: number, data: Partial<Strategy>): Promise<Strategy> {
    const response = await apiClient.patch<Strategy>(`/strategies/${id}/`, data)
    return response.data
  },

  /**
   * Activer/Désactiver une stratégie
   */
  async toggleActive(id: number, isActive: boolean): Promise<Strategy> {
    return this.update(id, { is_active: isActive })
  },

  /**
   * Supprimer une stratégie
   */
  async delete(id: number): Promise<void> {
    await apiClient.delete(`/strategies/${id}/`)
  },

  /**
   * Récupérer les performances d'une stratégie
   */
  async getPerformance(strategyId: number): Promise<ApiResponse<StrategyPerformance>> {
    const response = await apiClient.get<ApiResponse<StrategyPerformance>>(
      `/strategies/${strategyId}/performance/`
    )
    return response.data
  },

  /**
   * Récupérer toutes les performances
   */
  async getAllPerformance(): Promise<ApiResponse<StrategyPerformance>> {
    const response = await apiClient.get<ApiResponse<StrategyPerformance>>('/strategy-performance/')
    return response.data
  },
}

export default strategyService

