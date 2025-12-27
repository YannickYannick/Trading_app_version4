/**
 * Service pour les Brokers
 */
import apiClient from './api/client'
import type { ApiResponse, Broker, BrokerAccount, BrokerSyncLog, ApiError } from '@types'

export interface BrokerAccountCreateData {
  broker: number
  account_name: string
  account_id: string
  api_key?: string
  api_secret?: string
  client_id?: string
  client_secret?: string
  is_sandbox?: boolean
  extra_credentials?: Record<string, any>
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

