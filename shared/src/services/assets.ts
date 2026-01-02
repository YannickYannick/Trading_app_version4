/**
 * Service pour les Assets (shared)
 */
import type { AxiosInstance } from 'axios'
import type {
  ApiResponse,
  Asset,
  AllAsset,
  AssetWithChildren,
  AssetsOverviewResponse,
} from '../types'

export interface AssetFilters {
  platform?: 'SAXO' | 'BINANCE' | 'IB' | 'OTHER'
  asset_type?: string
  search?: string
  is_tradable?: boolean
  page?: number
  page_size?: number
  ordering?: string
}

export interface AllAssetFilters {
  platform?: 'SAXO' | 'BINANCE' | 'IB' | 'OTHER'
  asset_type?: string
  search?: string
  symbole_yahoo?: string
  page?: number
  page_size?: number
}

/**
 * Factory function pour créer le service assets
 */
export function createAssetService(apiClient: AxiosInstance) {
  return {
    async getAllAssets(filters?: AllAssetFilters): Promise<ApiResponse<AllAsset>> {
      const response = await apiClient.get<ApiResponse<AllAsset>>('/all-assets/', {
        params: filters,
      })
      return response.data
    },

    async getAllAssetById(id: number): Promise<AllAsset> {
      const response = await apiClient.get<AllAsset>(`/all-assets/${id}/`)
      return response.data
    },

    async searchAllAssets(query: string): Promise<AllAsset[]> {
      const response = await apiClient.get<ApiResponse<AllAsset>>('/all-assets/', {
        params: { search: query },
      })
      return response.data.results
    },

    async getAssets(filters?: AssetFilters): Promise<ApiResponse<Asset>> {
      const response = await apiClient.get<ApiResponse<Asset>>('/assets/', {
        params: filters,
      })
      return response.data
    },

    async getAssetById(id: number): Promise<Asset> {
      const response = await apiClient.get<Asset>(`/assets/${id}/`)
      return response.data
    },

    async getAssetBySymbol(symbol: string): Promise<Asset> {
      const response = await apiClient.get<Asset>(`/assets/by-symbol/${symbol}/`)
      return response.data
    },

    async searchAssets(query: string, filters?: Omit<AssetFilters, 'search'>): Promise<Asset[]> {
      const response = await apiClient.get<ApiResponse<Asset>>('/assets/', {
        params: { ...filters, search: query },
      })
      return response.data.results
    },

    async createAsset(data: Partial<Asset>): Promise<Asset> {
      const response = await apiClient.post<Asset>('/assets/', data)
      return response.data
    },

    async updateAsset(id: number, data: Partial<Asset>): Promise<Asset> {
      const response = await apiClient.patch<Asset>(`/assets/${id}/`, data)
      return response.data
    },

    async updatePrice(id: number, price: number): Promise<Asset> {
      return this.updateAsset(id, { current_price: price })
    },

    async deleteAsset(id: number): Promise<void> {
      await apiClient.delete(`/assets/${id}/`)
    },

    async getPricesBatch(assetIds: number[]): Promise<Record<number, number | null>> {
      const response = await apiClient.post<Record<number, number | null>>('/assets/batch-prices/', {
        asset_ids: assetIds,
      })
      return response.data
    },

    async autocompleteAllAssets(query: string, platform?: string): Promise<{
      id: number
      symbol: string
      name: string
      platform: string
      asset_type: string
      currency: string
      market: string
      text: string
      saxo_uic?: number
    }[]> {
      const params: any = { q: query }
      if (platform) {
        params.platform = platform
      }
      const response = await apiClient.get<{ results: any[] }>('/all-assets/autocomplete/', {
        params,
      })
      return response.data.results
    },

    async getAssetsOverview(includeEmpty: boolean = true): Promise<AssetWithChildren[]> {
      const response = await apiClient.get<AssetsOverviewResponse>('/assets/overview/', {
        params: { include_empty: includeEmpty ? 'true' : 'false' },
      })
      
      if (!response.data.success) {
        throw new Error(response.data.error || 'Erreur lors de la récupération des données')
      }
      
      return response.data.data
    },

    async getAssetsOverviewActive(): Promise<AssetWithChildren[]> {
      return this.getAssetsOverview(false)
    },

    async validateYahoo(allAssetId: number): Promise<{ success: boolean; message?: string; yahoo_symbol?: string; error?: string }> {
      const response = await apiClient.post(
        `/all-assets/${allAssetId}/validate_single_yahoo/`,
        {}
      )
      return response.data
    },

    async syncPriceHistory(
      allAssetId: number,
      days: number = 365,
      interval: string = '1d'
    ): Promise<{ success: boolean; records?: number; message?: string; error?: string }> {
      const response = await apiClient.post(
        `/all-assets/${allAssetId}/sync_price_history/`,
        { days, interval }
      )
      return response.data
    },

    async getYahooCurrentPrice(allAssetId: number): Promise<number | null> {
      try {
        const response = await apiClient.get(`/all-assets/${allAssetId}/current_price/`)
        
        if (response.data.success && response.data.price !== null && response.data.price !== undefined) {
          return response.data.price
        }
        
        // Fallback: essayer depuis l'historique
        try {
          const historyResponse = await apiClient.get(`/all-assets/${allAssetId}/prices/`, {
            params: { days: 1, format: 'list' },
          })
          
          if (historyResponse.data.results && historyResponse.data.results.length > 0) {
            return historyResponse.data.results[0].close || null
          }
        } catch (historyError) {
          // Ignorer
        }
        
        return null
      } catch (error: any) {
        if (
          error?.silent ||
          error?.response?.status === 404 ||
          error?.response?.status === 400
        ) {
          return null
        }
        throw error
      }
    },

    async getPriceHistory(
      allAssetId: number,
      days: number = 365,
      format: 'list' | 'json' = 'list'
    ): Promise<{
      all_asset_id: number
      all_asset_symbol: string
      count: number
      results: Array<{
        date: string
        close: number
        open: number
        high: number
        low: number
        volume: number
        close_price?: number
        open_price?: number
        high_price?: number
        low_price?: number
      }>
    }> {
      try {
        const response = await apiClient.get(`/all-assets/${allAssetId}/prices/`, {
          params: { days, output_format: format },
        })
        return response.data
      } catch (error: any) {
        if (error?.response?.status === 404) {
          return {
            all_asset_id: allAssetId,
            all_asset_symbol: '',
            count: 0,
            results: [],
          }
        }
        throw error
      }
    },
  }
}

