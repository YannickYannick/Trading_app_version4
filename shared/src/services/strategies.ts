import { ApiClient } from '../services/auth'
import type { Strategy, StrategyPerformance, ApiResponse } from '../types'

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
  algorithm_type?: string
  all_asset_id?: number
}

export class StrategiesService {
  private api: any

  constructor(apiClient: ApiClient) {
    this.api = apiClient.getInstance()
  }

  /**
   * Récupérer toutes les stratégies
   */
  async getAll(filters?: StrategyFilters): Promise<ApiResponse<Strategy>> {
    const response = await this.api.get('/strategies/', {
      params: filters,
    })
    return response.data
  }

  /**
   * Récupérer une stratégie par ID
   */
  async getById(id: number): Promise<Strategy> {
    const response = await this.api.get(`/strategies/${id}/`)
    return response.data
  }

  /**
   * Récupérer les stratégies actives
   */
  async getActive(): Promise<Strategy[]> {
    const response = await this.api.get('/strategies/', {
      params: { is_active: true },
    })
    return response.data.results
  }

  /**
   * Créer une stratégie
   */
  async create(data: StrategyCreateData): Promise<Strategy> {
    const response = await this.api.post('/strategies/', data)
    return response.data
  }

  /**
   * Mettre à jour une stratégie
   */
  async update(id: number, data: Partial<Strategy>): Promise<Strategy> {
    const response = await this.api.patch(`/strategies/${id}/`, data)
    return response.data
  }

  /**
   * Activer/Désactiver une stratégie
   */
  async toggleActive(id: number, isActive: boolean): Promise<Strategy> {
    return this.update(id, { is_active: isActive })
  }

  /**
   * Supprimer une stratégie
   */
  async delete(id: number): Promise<void> {
    await this.api.delete(`/strategies/${id}/`)
  }

  /**
   * Récupérer les performances d'une stratégie
   */
  async getPerformance(strategyId: number): Promise<ApiResponse<StrategyPerformance>> {
    const response = await this.api.get(
      `/strategies/${strategyId}/performance/`
    )
    return response.data
  }

  /**
   * Récupérer toutes les performances
   */
  async getAllPerformance(): Promise<ApiResponse<StrategyPerformance>> {
    const response = await this.api.get('/strategy-performance/')
    return response.data
  }
}


