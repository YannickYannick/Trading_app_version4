/**
 * Service pour les Trades
 */
import apiClient from './api/client'
import type { ApiResponse, Trade, ApiError } from '@types'

export interface TradeFilters {
  asset_id?: number
  broker_id?: number
  side?: 'BUY' | 'SELL'
  date_from?: string // Format ISO: YYYY-MM-DD
  date_to?: string
  page?: number
  page_size?: number
  ordering?: string
}

export interface TradeCreateData {
  asset: number
  size: number
  price: number
  side: 'BUY' | 'SELL'
  fees?: number
  broker_id?: number
  timestamp?: string
}

export const tradeService = {
  /**
   * Récupérer tous les trades
   */
  async getAll(filters?: TradeFilters): Promise<ApiResponse<Trade>> {
    const response = await apiClient.get<ApiResponse<Trade>>('/trades/', {
      params: filters,
    })
    return response.data
  },

  /**
   * Récupérer un trade par ID
   */
  async getById(id: number): Promise<Trade> {
    const response = await apiClient.get<Trade>(`/trades/${id}/`)
    return response.data
  },

  /**
   * Récupérer les trades récents
   */
  async getRecent(limit: number = 10): Promise<Trade[]> {
    const response = await apiClient.get<ApiResponse<Trade>>('/trades/', {
      params: { page_size: limit, ordering: '-timestamp' },
    })
    return response.data.results
  },

  /**
   * Récupérer les trades par asset
   */
  async getByAsset(assetId: number, filters?: Omit<TradeFilters, 'asset_id'>): Promise<Trade[]> {
    const response = await apiClient.get<ApiResponse<Trade>>('/trades/', {
      params: { ...filters, asset_id: assetId },
    })
    return response.data.results
  },

  /**
   * Récupérer les trades par date
   */
  async getByDateRange(dateFrom: string, dateTo: string, filters?: Omit<TradeFilters, 'date_from' | 'date_to'>): Promise<Trade[]> {
    const response = await apiClient.get<ApiResponse<Trade>>('/trades/', {
      params: { ...filters, date_from: dateFrom, date_to: dateTo },
    })
    return response.data.results
  },

  /**
   * Créer un trade
   */
  async create(data: TradeCreateData): Promise<Trade> {
    const response = await apiClient.post<Trade>('/trades/', data)
    return response.data
  },

  /**
   * Mettre à jour un trade
   */
  async update(id: number, data: Partial<Trade>): Promise<Trade> {
    const response = await apiClient.patch<Trade>(`/trades/${id}/`, data)
    return response.data
  },

  /**
   * Supprimer un trade
   */
  async delete(id: number): Promise<void> {
    await apiClient.delete(`/trades/${id}/`)
  },

  /**
   * Obtenir les statistiques des trades
   */
  async getStatistics(filters?: TradeFilters): Promise<{
    total_trades: number
    total_volume: number
    total_fees: number
    buy_trades: number
    sell_trades: number
    win_rate: number
  }> {
    const response = await apiClient.get('/trades/statistics/', {
      params: filters,
    })
    return response.data
  },
}

export default tradeService

