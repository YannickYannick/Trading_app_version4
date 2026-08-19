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

export interface PlaceOrderData {
  broker_account_id: number
  symbol: string
  side: 'BUY' | 'SELL'
  quantity: string
  order_type?: 'MARKET' | 'LIMIT' | 'STOP' | 'STOP_LIMIT'
  price?: string
  stop_price?: string
  asset_id?: number
  all_asset_id?: number  // ID AllAssets (prioritaire sur symbol pour la recherche)
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

export interface OrderCostEstimate {
  spread: {
    bid: number | null
    ask: number | null
    mid: number | null
    spread: number | null
    spread_pct: number | null
    price_info: Record<string, unknown>
    price_info_details: Record<string, unknown>
    display_and_format: Record<string, unknown>
  }
  buy_costs: {
    precheck_ok: boolean
    estimated_commission: number
    commission_currency: string
    trading_cost: number
    spread_cost: number
    error?: string
  }
  sell_costs: {
    precheck_ok: boolean
    estimated_commission: number
    commission_currency: string
    trading_cost: number
    spread_cost: number
    error?: string
  }
  entry_price: number | null
  exit_price: number | null
  quantity: number
  gross_entry_value: number | null
  gross_exit_value: number | null
  total_round_trip_cost: number | null
  estimated_resale_value: number | null
  error?: string
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
   * Ordres encore actifs (PENDING, OPEN, PARTIALLY_FILLED) — aligné sur GET /orders/pending/
   */
  async getActivePendingList(): Promise<Order[]> {
    const response = await apiClient.get<Order[]>('/orders/pending/')
    return Array.isArray(response.data) ? response.data : []
  },

  /**
   * Répare Order.all_asset (et Asset.all_asset si vide) pour les ordres déjà en base.
   */
  async backfillAllAssetLinks(): Promise<{ updated: number; message?: string }> {
    const response = await apiClient.post<{ updated: number; message?: string }>(
      '/orders/backfill-all-asset/'
    )
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

  /**
   * Placer un ordre directement via le broker
   */
  async placeOrder(data: PlaceOrderData): Promise<{
    success: boolean
    message: string
    order: Order
    broker_result?: {
      order_id: string
      message: string
    }
  }> {
    const response = await apiClient.post<{
      success: boolean
      message: string
      order: Order
      broker_result?: {
        order_id: string
        message: string
      }
    }>('/orders/place/', data)
    return response.data
  },

  /**
   * Placer un ordre existant (PENDING) via le broker
   */
  async placeBrokerOrder(id: number): Promise<{
    success: boolean
    message: string
    order: Order
    broker_result?: {
      order_id: string
      message: string
    }
  }> {
    const response = await apiClient.post<{
      success: boolean
      message: string
      order: Order
      broker_result?: {
        order_id: string
        message: string
      }
    }>(`/orders/${id}/place_broker/`)
    return response.data
  },

  /**
   * Annuler un ordre chez le broker
   */
  async cancelBrokerOrder(id: number): Promise<{
    success: boolean
    message: string
    order: Order
  }> {
    const response = await apiClient.post<{
      success: boolean
      message: string
      order: Order
    }>(`/orders/${id}/cancel_broker/`)
    return response.data
  },

  /**
   * Synchroniser les ordres depuis un broker
   */
  async syncOrders(data: SyncOrdersData): Promise<{
    success: boolean
    message: string
    created: number
    updated: number
    errors: string[]
  }> {
    const response = await apiClient.post<{
      success: boolean
      message: string
      created: number
      updated: number
      errors: string[]
    }>('/orders/sync/', data)
    return response.data
  },

  /**
   * Récupérer le prix d'un actif depuis le broker ET Yahoo (en parallèle)
   */
  async getAssetPrice(data: {
    broker_account_id: number
    symbol: string
    all_asset_id?: number
  }): Promise<AssetPriceResponse> {
    const response = await apiClient.post<AssetPriceResponse>('/orders/get_asset_price/', data)
    return response.data
  },

  async estimateCosts(data: {
    broker_account_id: number
    quantity: number
    side: string
    uic?: number
    all_asset_id?: number
    symbol?: string
    asset_type?: string
    order_type?: string
    price?: number
    stop_price?: number
  }): Promise<OrderCostEstimate> {
    const response = await apiClient.post<OrderCostEstimate>('/orders/estimate-costs/', data)
    return response.data
  },
}

export default orderService

