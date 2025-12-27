import axios from 'axios'

const API_BASE_URL = '/api'

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
})

// Types
export interface Asset {
  id: number
  symbol: string
  name: string
  asset_type: string
  currency: string
  exchange: string
  current_price: number | null
  is_active: boolean
}

export interface Position {
  id: number
  asset: number
  asset_symbol: string
  asset_name: string
  broker: number
  broker_name: string
  side: 'LONG' | 'SHORT'
  quantity: number
  entry_price: number
  current_price: number | null
  stop_loss: number | null
  take_profit: number | null
  is_open: boolean
  pnl: number | null
  pnl_percent: number | null
  opened_at: string
}

export interface Trade {
  id: number
  asset: number
  asset_symbol: string
  broker: number
  broker_name: string
  trade_type: 'BUY' | 'SELL'
  quantity: number
  price: number
  fees: number
  total_value: number
  executed_at: string
}

export interface PositionSummary {
  total_positions: number
  total_value: number
  total_pnl: number
}

// API functions
export const api = {
  // Assets
  async getAssets(search?: string): Promise<Asset[]> {
    const params = search ? { search } : {}
    const response = await client.get('/assets/', { params })
    return response.data.results || response.data
  },

  async getAsset(id: number): Promise<Asset> {
    const response = await client.get(`/assets/${id}/`)
    return response.data
  },

  // Positions
  async getPositions(): Promise<Position[]> {
    const response = await client.get('/positions/')
    return response.data.results || response.data
  },

  async getOpenPositions(): Promise<Position[]> {
    const response = await client.get('/positions/open/')
    return response.data
  },

  async getPositionSummary(): Promise<PositionSummary> {
    const response = await client.get('/positions/summary/')
    return response.data
  },

  // Trades
  async getTrades(): Promise<Trade[]> {
    const response = await client.get('/trades/')
    return response.data.results || response.data
  },

  async getRecentTrades(): Promise<Trade[]> {
    const response = await client.get('/trades/recent/')
    return response.data
  },
}

export default api

