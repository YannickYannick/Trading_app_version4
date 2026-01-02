/**
 * Service pour les Assets
 */
import apiClient from './api/client'
import type { ApiResponse, Asset, AllAsset, ApiError, AssetWithChildren, AssetsOverviewResponse } from '@types'

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

export const assetService = {
  /**
   * Récupérer tous les assets (AllAssets)
   */
  async getAllAssets(filters?: AllAssetFilters): Promise<ApiResponse<AllAsset>> {
    const response = await apiClient.get<ApiResponse<AllAsset>>('/all-assets/', {
      params: filters,
    })
    return response.data
  },

  /**
   * Récupérer un AllAsset par ID
   */
  async getAllAssetById(id: number): Promise<AllAsset> {
    const response = await apiClient.get<AllAsset>(`/all-assets/${id}/`)
    return response.data
  },

  /**
   * Rechercher des AllAssets
   */
  async searchAllAssets(query: string): Promise<AllAsset[]> {
    const response = await apiClient.get<ApiResponse<AllAsset>>('/all-assets/', {
      params: { search: query },
    })
    return response.data.results
  },

  /**
   * Récupérer les assets enrichis (Asset)
   */
  async getAssets(filters?: AssetFilters): Promise<ApiResponse<Asset>> {
    const response = await apiClient.get<ApiResponse<Asset>>('/assets/', {
      params: filters,
    })
    return response.data
  },

  /**
   * Récupérer un asset par ID
   */
  async getAssetById(id: number): Promise<Asset> {
    const response = await apiClient.get<Asset>(`/assets/${id}/`)
    return response.data
  },

  /**
   * Récupérer un asset par symbole
   */
  async getAssetBySymbol(symbol: string): Promise<Asset> {
    const response = await apiClient.get<Asset>(`/assets/by-symbol/${symbol}/`)
    return response.data
  },

  /**
   * Rechercher des assets
   */
  async searchAssets(query: string, filters?: Omit<AssetFilters, 'search'>): Promise<Asset[]> {
    const response = await apiClient.get<ApiResponse<Asset>>('/assets/', {
      params: { ...filters, search: query },
    })
    return response.data.results
  },

  /**
   * Créer un asset
   */
  async createAsset(data: Partial<Asset>): Promise<Asset> {
    const response = await apiClient.post<Asset>('/assets/', data)
    return response.data
  },

  /**
   * Mettre à jour un asset
   */
  async updateAsset(id: number, data: Partial<Asset>): Promise<Asset> {
    const response = await apiClient.patch<Asset>(`/assets/${id}/`, data)
    return response.data
  },

  /**
   * Mettre à jour le prix d'un asset
   */
  async updatePrice(id: number, price: number): Promise<Asset> {
    return this.updateAsset(id, { current_price: price })
  },

  /**
   * Supprimer un asset
   */
  async deleteAsset(id: number): Promise<void> {
    await apiClient.delete(`/assets/${id}/`)
  },

  /**
   * Récupérer les prix en batch
   */
  async getPricesBatch(assetIds: number[]): Promise<Record<number, number | null>> {
    const response = await apiClient.post<Record<number, number | null>>('/assets/batch-prices/', {
      asset_ids: assetIds,
    })
    return response.data
  },

  /**
   * Autocomplétion pour AllAssets (placement d'ordres)
   */
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

  /**
   * Récupérer la vue d'ensemble DataTree (Assets avec Positions et Orders groupés)
   * 
   * Retourne une structure hiérarchique où chaque asset est un parent
   * avec ses positions et orders comme enfants (children).
   * 
   * @param includeEmpty - Inclure les assets sans positions ni orders (défaut: true)
   */
  async getAssetsOverview(includeEmpty: boolean = true): Promise<AssetWithChildren[]> {
    const response = await apiClient.get<AssetsOverviewResponse>('/assets/overview/', {
      params: { include_empty: includeEmpty ? 'true' : 'false' },
    })
    
    if (!response.data.success) {
      throw new Error(response.data.error || 'Erreur lors de la récupération des données')
    }
    
    return response.data.data
  },

  /**
   * Récupérer la vue d'ensemble DataTree (uniquement les assets avec des positions/orders)
   */
  async getAssetsOverviewActive(): Promise<AssetWithChildren[]> {
    return this.getAssetsOverview(false)
  },

  /**
   * Valider le symbole Yahoo pour un AllAsset
   */
  async validateYahoo(allAssetId: number): Promise<{ success: boolean; message?: string; yahoo_symbol?: string; error?: string }> {
    const response = await apiClient.post<{ success: boolean; message?: string; yahoo_symbol?: string; error?: string }>(
      `/all-assets/${allAssetId}/validate_single_yahoo/`,
      {}
    )
    return response.data
  },

  /**
   * Synchroniser l'historique des prix pour un AllAsset
   */
  async syncPriceHistory(
    allAssetId: number,
    days: number = 365,
    interval: string = '1d'
  ): Promise<{ success: boolean; records?: number; message?: string; error?: string }> {
    const response = await apiClient.post<{ success: boolean; records?: number; message?: string; error?: string }>(
      `/all-assets/${allAssetId}/sync_price_history/`,
      { days, interval }
    )
    return response.data
  },

  /**
   * Récupérer le prix Yahoo actuel (dernier prix disponible)
   * Récupère directement depuis Yahoo Finance, pas depuis l'historique stocké
   */
  async getYahooCurrentPrice(allAssetId: number): Promise<number | null> {
    try {
      // Essayer d'abord l'endpoint current_price qui récupère directement depuis Yahoo
      const response = await apiClient.get<{
        success: boolean
        all_asset_id: number
        all_asset_symbol: string
        yahoo_symbol: string
        price: number
        currency: string
        message?: string
      }>(`/all-assets/${allAssetId}/current_price/`)
      
      if (response.data.success && response.data.price !== null && response.data.price !== undefined) {
        return response.data.price
      }
      
      // Fallback: essayer depuis l'historique si current_price échoue
      try {
        const historyResponse = await apiClient.get<{
          all_asset_id: number
          all_asset_symbol: string
          count: number
          results: Array<{ date: string; close: number; open: number; high: number; low: number; volume: number }>
        }>(`/all-assets/${allAssetId}/prices/`, {
          params: { days: 1, format: 'list' },
        })
        
        // Prendre le premier résultat (le plus récent)
        if (historyResponse.data.results && historyResponse.data.results.length > 0) {
          return historyResponse.data.results[0].close || null
        }
      } catch (historyError) {
        // Ignorer l'erreur de l'historique
      }
      
      return null
    } catch (error: any) {
      // Ignorer silencieusement les 404 (AllAsset n'existe pas)
      if (error?.response?.status === 404) {
        return null
      }
      // Logger les autres erreurs mais ne pas bloquer
      console.error(`Error fetching Yahoo price for AllAsset ${allAssetId}:`, error)
      return null
    }
  },

  /**
   * Récupérer l'historique des prix pour un AllAsset
   */
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
      const response = await apiClient.get<{
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
      }>(`/all-assets/${allAssetId}/prices/`, {
        params: { days, format },
      })
      return response.data
    } catch (error: any) {
      console.error(`Error fetching price history for AllAsset ${allAssetId}:`, error)
      return {
        all_asset_id: allAssetId,
        all_asset_symbol: '',
        count: 0,
        results: [],
      }
    }
  },
}

export default assetService

