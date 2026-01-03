import { ApiClient } from '../services/auth'
import type { AllAsset, ApiResponse } from '../types'

export class AssetsService {
  private api: any

  constructor(apiClient: ApiClient) {
    this.api = apiClient.getInstance()
  }

  /**
   * Rechercher des actifs (AllAsset)
   */
  async search(query: string): Promise<ApiResponse<AllAsset>> {
    const response = await this.api.get('/all-assets/', {
      params: { search: query, page_size: 20 },
    })
    return response.data
  }

  /**
   * Récupérer un actif par ID
   */
  async getById(id: number): Promise<AllAsset> {
    const response = await this.api.get(`/all-assets/${id}/`)
    return response.data
  }

  /**
   * Récupérer l'historique des prix
   */
  async getPriceHistory(id: number, days: number = 30, format: 'list' | 'dict' = 'list'): Promise<any> {
    console.log(`[AssetsService] Fetching history for asset ${id} at /all-assets/${id}/prices/`)
    const response = await this.api.get(`/all-assets/${id}/prices/`, {
      params: { days, output_format: format }
    })
    return response.data
  }

  /**
   * Valider le symbole Yahoo (POST)
   */
  async validateYahooSymbol(id: number): Promise<any> {
    const response = await this.api.post(`/all-assets/${id}/validate_single_yahoo/`)
    return response.data
  }

  /**
   * Synchroniser l'historique des prix (POST)
   */
  async syncPriceHistory(id: number, days: number = 365): Promise<any> {
    const response = await this.api.post(`/all-assets/${id}/sync_price_history/`, {
      days,
      interval: '1d'
    })
    return response.data
  }
}


