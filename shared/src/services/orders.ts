/**
 * Service pour les Orders (shared)
 */
import type { AxiosInstance } from 'axios'
import type { ApiResponse, Order } from '../types'

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

export interface PlaceOrderData {
  broker_account_id: number
  symbol: string
  side: 'BUY' | 'SELL'
  quantity: string
  order_type?: 'MARKET' | 'LIMIT' | 'STOP' | 'STOP_LIMIT'
  price?: string
  stop_price?: string
  asset_id?: number
  all_asset_id?: number
}

export interface SyncOrdersData {
  broker_account_id: number
  status?: string
  symbol?: string
}

export interface AssetPriceResponse {
  success: boolean
  broker_price: {
    price: number
    currency: string
    source: string
    error?: string
  }
  yahoo_data: {
    price?: number
    symbol?: string
    available: boolean
    error?: string
    tried_symbols?: string[]
    validated_symbol?: string | null
  }
}

/**
 * Factory function pour créer le service orders
 */
export function createOrderService(apiClient: AxiosInstance) {
  return {
    async getAll(filters?: OrderFilters): Promise<ApiResponse<Order>> {
      const response = await apiClient.get<ApiResponse<Order>>('/orders/', {
        params: filters,
      })
      return response.data
    },

    async getById(id: number): Promise<Order> {
      const response = await apiClient.get<Order>(`/orders/${id}/`)
      return response.data
    },

    async getPending(filters?: Omit<OrderFilters, 'status'>): Promise<Order[]> {
      const response = await apiClient.get<ApiResponse<Order>>('/orders/', {
        params: { ...filters, status: 'PENDING' },
      })
      return response.data.results
    },

    async create(data: OrderCreateData): Promise<Order> {
      const response = await apiClient.post<Order>('/orders/', data)
      return response.data
    },

    async update(id: number, data: Partial<Order>): Promise<Order> {
      const response = await apiClient.patch<Order>(`/orders/${id}/`, data)
      return response.data
    },

    async cancel(id: number): Promise<Order> {
      const response = await apiClient.post<Order>(`/orders/${id}/cancel/`)
      return response.data
    },

    async delete(id: number): Promise<void> {
      await apiClient.delete(`/orders/${id}/`)
    },

    async placeOrder(data: PlaceOrderData): Promise<{
      success: boolean
      message: string
      order: Order
      broker_result?: {
        order_id: string
        message: string
      }
    }> {
      const response = await apiClient.post('/orders/place/', data)
      return response.data
    },

    async placeBrokerOrder(id: number): Promise<{
      success: boolean
      message: string
      order: Order
      broker_result?: {
        order_id: string
        message: string
      }
    }> {
      const response = await apiClient.post(`/orders/${id}/place_broker/`)
      return response.data
    },

    async cancelBrokerOrder(id: number): Promise<{
      success: boolean
      message: string
      order: Order
    }> {
      const response = await apiClient.post(`/orders/${id}/cancel_broker/`)
      return response.data
    },

    async syncOrders(data: SyncOrdersData): Promise<{
      success: boolean
      message: string
      created: number
      updated: number
      errors: string[]
    }> {
      const response = await apiClient.post('/orders/sync/', data)
      return response.data
    },

    async getAssetPrice(data: {
      broker_account_id: number
      symbol: string
      all_asset_id?: number
    }): Promise<AssetPriceResponse> {
      const response = await apiClient.post('/orders/get_asset_price/', data)
      return response.data
    },
  }
}

