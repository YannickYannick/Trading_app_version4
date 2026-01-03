/**
 * Service pour les Positions (Refactorisé pour DI)
 */
import { ApiClient } from '../services/auth'
import type { ApiResponse, Position } from '../types'

export interface PositionFilters {
  status?: 'OPEN' | 'CLOSED'
  asset_id?: number
  broker_id?: number
  side?: 'BUY' | 'SELL'
  page?: number
  page_size?: number
  ordering?: string
}

export interface PositionCreateData {
  asset: number
  size: number
  entry_price: number
  side: 'BUY' | 'SELL'
  stop_loss?: number
  take_profit?: number
  broker_id?: number
}

export class PositionsService {
  private api: any

  constructor(apiClient: ApiClient) {
    this.api = apiClient.getInstance()
  }

  /**
   * Récupérer toutes les positions
   */
  async getAll(filters?: PositionFilters): Promise<ApiResponse<Position>> {
    const response = await this.api.get('/positions/', {
      params: filters,
    })
    return response.data
  }

  /**
   * Récupérer une position par ID
   */
  async getById(id: number): Promise<Position> {
    const response = await this.api.get(`/positions/${id}/`)
    return response.data
  }

  /**
   * Récupérer les positions ouvertes
   */
  async getOpen(filters?: Omit<PositionFilters, 'status'>): Promise<Position[]> {
    const response = await this.api.get('/positions/', {
      params: { ...filters, status: 'OPEN' },
    })
    return response.data.results
  }

  /**
   * Récupérer les positions fermées
   */
  async getClosed(filters?: Omit<PositionFilters, 'status'>): Promise<Position[]> {
    const response = await this.api.get('/positions/', {
      params: { ...filters, status: 'CLOSED' },
    })
    return response.data.results
  }

  /**
   * Récupérer le résumé des positions
   */
  async getSummary(): Promise<{
    total_positions: number
    open_positions: number
    closed_positions: number
    total_pnl: number
    total_value: number
  }> {
    const response = await this.api.get('/positions/summary/')
    return response.data
  }

  /**
   * Créer une position
   */
  async create(data: PositionCreateData): Promise<Position> {
    const response = await this.api.post('/positions/', data)
    return response.data
  }

  /**
   * Mettre à jour une position
   */
  async update(id: number, data: Partial<Position>): Promise<Position> {
    const response = await this.api.patch(`/positions/${id}/`, data)
    return response.data
  }

  /**
   * Fermer une position
   */
  async close(id: number, closePrice?: number): Promise<Position> {
    const response = await this.api.post(`/positions/${id}/close/`, {
      close_price: closePrice,
    })
    return response.data
  }

  /**
   * Supprimer une position
   */
  async delete(id: number): Promise<void> {
    await this.api.delete(`/positions/${id}/`)
  }

  /**
   * Mettre à jour le stop loss
   */
  async updateStopLoss(id: number, stopLoss: number): Promise<Position> {
    return this.update(id, { stop_loss: stopLoss })
  }

  /**
   * Mettre à jour le take profit
   */
  async updateTakeProfit(id: number, takeProfit: number): Promise<Position> {
    return this.update(id, { take_profit: takeProfit })
  }
}


