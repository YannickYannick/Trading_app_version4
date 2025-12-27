/**
 * Service pour les Orders
 */
import apiClient from './api/client'
import type { ApiResponse, Order, ApiError } from '@types'

export interface OrderFilters {
  status?: 'PENDING' | 'FILLED' | 'CANCELLED' | 'REJECTED'
  asset_id?: number
  broker_id?: number
  order_type?: 'MARKET' | 'LIMIT' | 'STOP' | 'STOP_LIMIT'
  page?: number
  page_size?: number
  ordering?: string
}

export interface OrderCreateData {
  asset: number
  order_type: 'MARKET' | 'LIMIT' | 'STOP' | 'STOP_LIMIT'
  side: 'BUY' | 'SELL'
  quantity: number
  price?: number
  stop_price?: number
  broker_id?: number
}

export const orderService = {
  /**
   * Récupérer tous les ordres
   */
  async getAll(filters?: OrderFilters): Promise<ApiResponse<Order>> {
    const response = await apiClient.get<ApiResponse<Order>>('/orders/', {
      params: filters,
    })
    return response.data
  },

  /**
   * Récupérer un ordre par ID
   */
  async getById(id: number): Promise<Order> {
    const response = await apiClient.get<Order>(`/orders/${id}/`)
    return response.data
  },

  /**
   * Récupérer les ordres en attente
   */
  async getPending(filters?: Omit<OrderFilters, 'status'>): Promise<Order[]> {
    const response = await apiClient.get<ApiResponse<Order>>('/orders/', {
      params: { ...filters, status: 'PENDING' },
    })
    return response.data.results
  },

  /**
   * Créer un ordre
   */
  async create(data: OrderCreateData): Promise<Order> {
    const response = await apiClient.post<Order>('/orders/', data)
    return response.data
  },

  /**
   * Mettre à jour un ordre
   */
  async update(id: number, data: Partial<Order>): Promise<Order> {
    const response = await apiClient.patch<Order>(`/orders/${id}/`, data)
    return response.data
  },

  /**
   * Annuler un ordre
   */
  async cancel(id: number): Promise<Order> {
    const response = await apiClient.post<Order>(`/orders/${id}/cancel/`)
    return response.data
  },

  /**
   * Supprimer un ordre
   */
  async delete(id: number): Promise<void> {
    await apiClient.delete(`/orders/${id}/`)
  },
}

export default orderService

