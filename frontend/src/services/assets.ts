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
   * Utilise un cache et une déduplication pour éviter les requêtes multiples
   */
  async getYahooCurrentPrice(allAssetId: number): Promise<number | null> {
    // Vérifier le cache
    const cached = priceCache.get(allAssetId)
    if (cached && Date.now() - cached.timestamp < CACHE_TIMEOUT) {
      return cached.price
    }

    // Vérifier si une requête est déjà en cours pour cet asset
    const inFlight = inFlightRequests.get(allAssetId)
    if (inFlight) {
      return inFlight
    }

    // Créer une nouvelle promesse pour cette requête
    const requestPromise = (async () => {
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
          const price = response.data.price
          priceCache.set(allAssetId, { price, timestamp: Date.now() })
          inFlightRequests.delete(allAssetId)
          return price
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
            const price = historyResponse.data.results[0].close || null
            priceCache.set(allAssetId, { price, timestamp: Date.now() })
            inFlightRequests.delete(allAssetId)
            return price
          }
        } catch (historyError) {
          // Ignorer l'erreur de l'historique
        }
        
        // Mettre en cache null pour éviter les requêtes répétées
        priceCache.set(allAssetId, { price: null, timestamp: Date.now() })
        inFlightRequests.delete(allAssetId)
        return null
      } catch (error: any) {
        // Ignorer silencieusement les 404 et 400 (AllAsset n'existe pas ou pas de symbole Yahoo valide)
        // NE PAS logger ces erreurs car elles sont attendues et polluent la console
        // L'intercepteur axios marque ces erreurs avec silent: true
        if (
          error?.silent ||
          error?.response?.status === 404 ||
          error?.response?.status === 400
        ) {
          // Mettre en cache null pour éviter les requêtes répétées (cache court pour réessayer plus tard si le symbole est validé)
          priceCache.set(allAssetId, { price: null, timestamp: Date.now() })
          inFlightRequests.delete(allAssetId)
          return null
        }
        // Logger seulement les erreurs inattendues (500, 503, etc.)
        if (error?.response?.status >= 500) {
          console.error(`Error fetching Yahoo price for AllAsset ${allAssetId}:`, error)
        }
        inFlightRequests.delete(allAssetId)
        return null
      }
    })()

    // Stocker la promesse pour déduplication
    inFlightRequests.set(allAssetId, requestPromise)
    
    return requestPromise
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
      
      // Log pour debug
      console.log(`[getPriceHistory] Response for asset ${allAssetId}:`, {
        count: response.data.count,
        resultsLength: response.data.results?.length,
        all_asset_symbol: response.data.all_asset_symbol,
      })
      
      return response.data
    } catch (error: any) {
      // Gérer les erreurs d'authentification (401) - ne pas logger, l'intercepteur gère le refresh
      if (error?.response?.status === 401) {
        // L'intercepteur axios devrait gérer le refresh du token automatiquement
        // Si on arrive ici, c'est que le refresh a échoué ou que l'utilisateur n'est pas connecté
        return {
          all_asset_id: allAssetId,
          all_asset_symbol: '',
          count: 0,
          results: [],
        }
      }
      // Ne pas logger les erreurs si c'est juste qu'il n'y a pas d'historique (404 ou message explicite)
      if (error?.response?.status === 404 || error?.response?.data?.message?.includes('No price history')) {
        console.warn(`[getPriceHistory] No price history for asset ${allAssetId} (expected)`)
        return {
          all_asset_id: allAssetId,
          all_asset_symbol: '',
          count: 0,
          results: [],
        }
      }
      console.error(`[getPriceHistory] Error fetching price history for AllAsset ${allAssetId}:`, error)
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

