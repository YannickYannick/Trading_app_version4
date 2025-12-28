/**
 * Types TypeScript pour l'application Trading
 */

// Export des types d'erreurs
export type { ApiError, ErrorState, ErrorType } from './errors'

// ============================================================================
// Assets
// ============================================================================

export interface Asset {
  id: number
  symbol: string
  name: string
  current_price: number | null
  platform: 'SAXO' | 'BINANCE' | 'IB' | 'OTHER'
  asset_type: string
  market: string
  currency: string
  exchange: string
  is_tradable: boolean
  last_updated: string
  created_at: string
}

export interface AllAsset {
  id: number
  symbol: string
  name: string
  platform: 'SAXO' | 'BINANCE' | 'IB' | 'OTHER'
  asset_type: string
  market: string
  currency: string
  exchange: string
  is_tradable: boolean
  symbole_yahoo: string
  yahoo_validated_at: string | null
  yahoo_validation_method: string
  last_updated: string
  created_at: string
  // Champs spécifiques Saxo
  saxo_uic: number | null
  saxo_exchange_id: string
  saxo_country_code: string
  // Champs spécifiques Binance
  binance_base_asset: string
  binance_quote_asset: string
  binance_status: string
}

// ============================================================================
// Positions
// ============================================================================

export interface Position {
  id: number
  asset: Asset
  size: number
  entry_price: number
  current_price: number | null
  pnl: number
  pnl_percent: number
  side: 'BUY' | 'SELL'
  status: 'OPEN' | 'CLOSED'
  opened_at: string
  closed_at: string | null
  user: number
}

// ============================================================================
// Trades
// ============================================================================

export interface Trade {
  id: number
  asset: Asset
  size: number // Alias pour quantity dans le serializer
  quantity?: number // Nom réel du champ backend
  price: number
  side: 'BUY' | 'SELL'
  timestamp: string // Alias pour executed_at dans le serializer
  executed_at?: string // Nom réel du champ backend
  fees: number
  pnl?: number | null
  position?: number | null // ID de la position
  position_id?: number | null // Alias
  broker_name?: string
  broker_id?: number
  broker?: { id: number; name: string } | null
  user: number
}

// ============================================================================
// Orders
// ============================================================================

export interface Order {
  id: number
  asset: Asset
  order_type: 'MARKET' | 'LIMIT' | 'STOP' | 'STOP_LIMIT'
  side: 'BUY' | 'SELL'
  quantity: number
  price: number | null
  status: 'PENDING' | 'FILLED' | 'CANCELLED' | 'REJECTED'
  filled_quantity: number
  created_at: string
  user: number
}

// ============================================================================
// Strategies
// ============================================================================

export interface Strategy {
  id: number
  name: string
  description: string
  strategy_type: string
  is_active: boolean
  created_at: string
  user: number
}

export interface StrategyPerformance {
  id: number
  strategy: Strategy
  total_return: number
  sharpe_ratio: number | null
  max_drawdown: number | null
  win_rate: number
  period_start: string
  period_end: string
}

// ============================================================================
// Brokers
// ============================================================================

export interface Broker {
  id: number
  name: string
  broker_type: 'SAXO' | 'BINANCE' | 'IB' | 'OTHER'
  is_active: boolean
  api_documentation_url: string | null
}

export interface BrokerAccount {
  id: number
  name: string
  broker: Broker | null
  broker_name?: string | null
  broker_type: 'SAXO' | 'BINANCE' | 'IB' | 'OTHER'
  broker_type_display?: string
  account_id: string
  environment: 'live' | 'simulation'
  environment_display?: string
  
  // Credentials Saxo
  saxo_client_id?: string | null
  saxo_client_secret?: string | null
  saxo_redirect_uri?: string | null
  saxo_environment?: 'live' | 'simulation'
  saxo_access_token?: string | null
  saxo_refresh_token?: string | null
  saxo_token_expires_at?: string | null
  
  // Credentials Binance
  binance_api_key?: string | null
  binance_api_secret?: string | null
  binance_testnet?: boolean
  
  // Credentials génériques
  api_key?: string
  api_secret?: string
  client_id?: string
  client_secret?: string
  access_token?: string
  refresh_token?: string
  token_expires_at?: string | null
  extra_credentials?: Record<string, any>
  
  // Auto-refresh
  auto_refresh_enabled?: boolean
  auto_refresh_frequency?: number
  
  // Balance et statut
  balance?: number | null
  currency?: string
  balance_updated_at?: string | null
  last_sync: string | null
  is_active: boolean
  is_demo?: boolean
  is_sandbox: boolean
  
  // Timestamps
  created_at?: string
  updated_at?: string
  
  user: number
}

export interface BrokerSyncLog {
  id: number
  broker_account: BrokerAccount
  sync_type: 'ASSETS' | 'PRICES' | 'POSITIONS' | 'TRADES'
  status: 'SUCCESS' | 'FAILED' | 'PARTIAL'
  records_synced: number
  started_at: string
  completed_at: string | null
  error_message: string | null
  details: Record<string, any> | null
}

// ============================================================================
// API Responses
// ============================================================================

export interface ApiResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface ApiError {
  error: string
  code?: string
  details?: Record<string, any>
  message?: string
}

// ============================================================================
// Authentication
// ============================================================================

export interface User {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  is_active: boolean
  date_joined: string
}

export interface LoginCredentials {
  username: string
  password: string
}

export interface AuthTokens {
  access: string
  refresh: string
}

export interface RegisterData {
  username: string
  email: string
  password: string
  password_confirm: string
  first_name?: string
  last_name?: string
}

// ============================================================================
// Common
// ============================================================================

export type LoadingState = 'idle' | 'loading' | 'success' | 'error'

export interface PaginationParams {
  page?: number
  page_size?: number
  search?: string
  ordering?: string
}

