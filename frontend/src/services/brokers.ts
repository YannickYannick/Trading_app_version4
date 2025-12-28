/**
 * Service pour les Brokers
 */
import apiClient from './api/client'
import type { ApiResponse, Broker, BrokerAccount, BrokerSyncLog, ApiError } from '@types'

export interface BrokerAccountCreateData {
  // Identifiants
  name: string
  broker?: number | null
  broker_type: 'SAXO' | 'BINANCE' | 'IB' | 'OTHER'
  account_id?: string
  environment?: 'live' | 'simulation'
  
  // Credentials Saxo
  saxo_client_id?: string
  saxo_client_secret?: string
  saxo_redirect_uri?: string
  saxo_environment?: 'live' | 'simulation'
  saxo_access_token?: string
  saxo_refresh_token?: string
  saxo_token_expires_at?: string | null
  
  // Credentials Binance
  binance_api_key?: string
  binance_api_secret?: string
  binance_testnet?: boolean
  
  // Credentials génériques (pour compatibilité)
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
  
  // Statut
  is_active?: boolean
  is_demo?: boolean
  is_sandbox?: boolean
}

export interface TestConnectionResponse {
  success: boolean
  message: string
  error?: string
}

export interface SyncRequest {
  sync_type: 'ASSETS' | 'PRICES' | 'POSITIONS' | 'TRADES'
  force?: boolean
}

export const brokerService = {
  /**
   * Récupérer tous les brokers
   */
  async getAll(): Promise<ApiResponse<Broker>> {
    const response = await apiClient.get<ApiResponse<Broker>>('/brokers/')
    return response.data
  },

  /**
   * Récupérer un broker par ID
   */
  async getById(id: number): Promise<Broker> {
    const response = await apiClient.get<Broker>(`/brokers/${id}/`)
    return response.data
  },

  /**
   * Récupérer tous les comptes broker
   */
  async getAccounts(): Promise<ApiResponse<BrokerAccount>> {
    const response = await apiClient.get<ApiResponse<BrokerAccount>>('/broker-accounts/')
    return response.data
  },

  /**
   * Récupérer un compte broker par ID
   */
  async getAccountById(id: number): Promise<BrokerAccount> {
    const response = await apiClient.get<BrokerAccount>(`/broker-accounts/${id}/`)
    return response.data
  },

  /**
   * Créer un compte broker
   */
  async createAccount(data: BrokerAccountCreateData): Promise<BrokerAccount> {
    const response = await apiClient.post<BrokerAccount>('/broker-accounts/', data)
    return response.data
  },

  /**
   * Mettre à jour un compte broker
   */
  async updateAccount(id: number, data: Partial<BrokerAccountCreateData>): Promise<BrokerAccount> {
    const response = await apiClient.patch<BrokerAccount>(`/broker-accounts/${id}/`, data)
    return response.data
  },

  /**
   * Supprimer un compte broker
   */
  async deleteAccount(id: number): Promise<void> {
    await apiClient.delete(`/broker-accounts/${id}/`)
  },

  /**
   * Tester la connexion à un broker
   */
  async testConnection(accountId: number): Promise<TestConnectionResponse> {
    const response = await apiClient.post<TestConnectionResponse>(
      `/broker-accounts/${accountId}/test-connection/`
    )
    return response.data
  },

  /**
   * Récupérer le solde EUR d'un compte broker
   */
  async getBalanceEur(accountId: number): Promise<{
    success: boolean
    balance_eur: number
    currency: string
    all_balances: Record<string, number>
    timestamp?: string
    error?: string
  }> {
    const response = await apiClient.get<{
      success: boolean
      balance_eur: number
      currency: string
      all_balances: Record<string, number>
      timestamp?: string
      error?: string
    }>(`/broker-accounts/${accountId}/balance-eur/`)
    return response.data
  },

  /**
   * Rafraîchir le solde d'un compte broker
   */
  async refreshBalance(accountId: number): Promise<{
    success: boolean
    balance_eur: number
    currency: string
    all_balances: Record<string, number>
    account: BrokerAccount
    error?: string
  }> {
    const response = await apiClient.post<{
      success: boolean
      balance_eur: number
      currency: string
      all_balances: Record<string, number>
      account: BrokerAccount
      error?: string
    }>(`/broker-accounts/${accountId}/refresh-balance/`)
    return response.data
  },

  /**
   * Récupérer les credentials (masqués) d'un compte broker
   */
  async getCredentials(accountId: number): Promise<{
    broker_type: string
    credentials_dict: Record<string, any>
    raw_fields: Record<string, any>
    has_api_key: boolean
    has_api_secret: boolean
    testnet: boolean
    environment: string
  }> {
    const response = await apiClient.get<{
      broker_type: string
      credentials_dict: Record<string, any>
      raw_fields: Record<string, any>
      has_api_key: boolean
      has_api_secret: boolean
      testnet: boolean
      environment: string
    }>(`/broker-accounts/${accountId}/credentials/`)
    return response.data
  },

  /**
   * Obtenir l'URL d'authentification Saxo (OAuth2)
   */
  async getSaxoAuthUrl(accountId: number): Promise<{ auth_url: string; state: string }> {
    const response = await apiClient.get<{ success: boolean; auth_url: string; state: string }>(
      `/broker-accounts/${accountId}/saxo-auth-url/`
    )
    return response.data
  },

  /**
   * Échanger le code d'autorisation Saxo contre des tokens
   */
  async exchangeSaxoAuthCode(accountId: number, code: string, state?: string): Promise<BrokerAccount> {
    const response = await apiClient.post<BrokerAccount>(`/broker-accounts/${accountId}/saxo-exchange-code/`, {
      code,
      state,
    })
    return response.data
  },

  /**
   * Rafraîchir le token Saxo
   */
  async refreshSaxoToken(accountId: number): Promise<BrokerAccount> {
    const response = await apiClient.post<BrokerAccount>(`/broker-accounts/${accountId}/saxo-refresh-token/`)
    return response.data
  },

  /**
   * Supprimer les tokens Saxo
   */
  async deleteSaxoTokens(accountId: number): Promise<BrokerAccount> {
    const response = await apiClient.post<BrokerAccount>(`/broker-accounts/${accountId}/saxo-delete-tokens/`)
    return response.data
  },

  /**
   * Récupérer les assets depuis Saxo
   */
  async getSaxoAssets(
    accountId: number,
    options?: {
      asset_type?: string
      keywords?: string
      limit?: number
    }
  ): Promise<{
    success: boolean
    count: number
    assets: Array<{
      symbol: string
      name: string
      asset_type: string
      exchange: string
      currency: string
      is_tradable: boolean
      broker_id: string | null
    }>
    error?: string
  }> {
    const params = new URLSearchParams()
    if (options?.asset_type) params.append('asset_type', options.asset_type)
    if (options?.keywords) params.append('keywords', options.keywords)
    if (options?.limit) params.append('limit', options.limit.toString())

    try {
      const response = await apiClient.get<{
        success: boolean
        count: number
        assets: Array<{
          symbol: string
          name: string
          asset_type: string
          exchange: string
          currency: string
          is_tradable: boolean
          broker_id: string | null
        }>
      }>(`/broker-accounts/${accountId}/saxo-assets/?${params.toString()}`)
      return response.data
    } catch (error: any) {
      return {
        success: false,
        count: 0,
        assets: [],
        error: error.response?.data?.error || error.message || 'Failed to fetch Saxo assets',
      }
    }
  },

  /**
   * Récupérer les positions depuis Saxo
   */
  async getSaxoPositions(accountId: number): Promise<{
    success: boolean
    count: number
    positions: Array<{
      symbol: string
      quantity: number
      entry_price: number
      current_price: number | null
      unrealized_pnl: number | null
      currency: string
      side: string
      broker_id: string | null
    }>
    error?: string
  }> {
    try {
      const response = await apiClient.get<{
        success: boolean
        count: number
        positions: Array<{
          symbol: string
          quantity: number
          entry_price: number
          current_price: number | null
          unrealized_pnl: number | null
          currency: string
          side: string
          broker_id: string | null
        }>
      }>(`/broker-accounts/${accountId}/saxo-positions/`)
      return response.data
    } catch (error: any) {
      return {
        success: false,
        count: 0,
        positions: [],
        error: error.response?.data?.error || error.message || 'Failed to fetch Saxo positions',
      }
    }
  },

  /**
   * Synchroniser les données depuis un broker
   */
  async sync(accountId: number, syncRequest: SyncRequest): Promise<BrokerSyncLog> {
    const response = await apiClient.post<BrokerSyncLog>(
      `/broker-accounts/${accountId}/sync/`,
      syncRequest
    )
    return response.data
  },

  /**
   * Récupérer les logs de synchronisation
   */
  async getSyncLogs(accountId?: number): Promise<ApiResponse<BrokerSyncLog>> {
    const params = accountId ? { broker_account: accountId } : {}
    const response = await apiClient.get<ApiResponse<BrokerSyncLog>>('/broker-sync-logs/', {
      params,
    })
    return response.data
  },

  /**
   * Récupérer le dernier log de synchronisation
   */
  async getLastSyncLog(accountId: number, syncType?: string): Promise<BrokerSyncLog | null> {
    const params: Record<string, any> = { broker_account: accountId }
    if (syncType) {
      params.sync_type = syncType
    }
    
    const response = await apiClient.get<ApiResponse<BrokerSyncLog>>('/broker-sync-logs/', {
      params: { ...params, page_size: 1, ordering: '-started_at' },
    })
    
    return response.data.results[0] || null
  },
}

export default brokerService

