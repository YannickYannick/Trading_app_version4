/**
 * Service pour les Positions (shared)
 */
import type { AxiosInstance } from 'axios'
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

/**
 * Factory function pour créer le service positions
 */
export function createPositionService(apiClient: AxiosInstance) {
  return {
    async getAll(filters?: PositionFilters): Promise<ApiResponse<Position>> {
      const response = await apiClient.get<ApiResponse<Position>>('/positions/', {
        params: filters,
      })
      return response.data
    },

    async getById(id: number): Promise<Position> {
      const response = await apiClient.get<Position>(`/positions/${id}/`)
      return response.data
    },

    async getOpen(filters?: Omit<PositionFilters, 'status'>): Promise<Position[]> {
      const response = await apiClient.get<ApiResponse<Position>>('/positions/', {
        params: { ...filters, status: 'OPEN' },
      })
      return response.data.results
    },

    async getClosed(filters?: Omit<PositionFilters, 'status'>): Promise<Position[]> {
      const response = await apiClient.get<ApiResponse<Position>>('/positions/', {
        params: { ...filters, status: 'CLOSED' },
      })
      return response.data.results
    },

    async getSummary(): Promise<{
      total_positions: number
      open_positions: number
      closed_positions: number
      total_pnl: number
      total_value: number
    }> {
      const response = await apiClient.get('/positions/summary/')
      return response.data
    },

    async create(data: PositionCreateData): Promise<Position> {
      const response = await apiClient.post<Position>('/positions/', data)
      return response.data
    },

    async update(id: number, data: Partial<Position>): Promise<Position> {
      const response = await apiClient.patch<Position>(`/positions/${id}/`, data)
      return response.data
    },

    async close(id: number, closePrice?: number): Promise<Position> {
      const response = await apiClient.post<Position>(`/positions/${id}/close/`, {
        close_price: closePrice,
      })
      return response.data
    },

    async delete(id: number): Promise<void> {
      await apiClient.delete(`/positions/${id}/`)
    },

    async updateStopLoss(id: number, stopLoss: number): Promise<Position> {
      return this.update(id, { stop_loss: stopLoss } as Partial<Position>)
    },

    async updateTakeProfit(id: number, takeProfit: number): Promise<Position> {
      return this.update(id, { take_profit: takeProfit } as Partial<Position>)
    },
  }
}

