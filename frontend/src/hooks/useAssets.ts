/**
 * Hook pour gérer les assets
 */
import { useState, useEffect, useCallback } from 'react'
import { assetService, AssetFilters } from '@services'
import type { Asset, AllAsset, ApiError } from '@types'

export interface UseAssetsOptions extends AssetFilters {
  autoFetch?: boolean
}

export function useAssets(options: UseAssetsOptions = {}) {
  const { autoFetch = true, ...filters } = options
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(autoFetch)
  const [error, setError] = useState<string | null>(null)
  const [total, setTotal] = useState(0)

  const fetchAssets = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await assetService.getAssets(filters)
      setAssets(response.results)
      setTotal(response.count)
    } catch (err: any) {
      const apiError = err as ApiError
      setError(apiError.error || apiError.message || 'Erreur lors du chargement des assets')
      setAssets([])
    } finally {
      setLoading(false)
    }
  }, [JSON.stringify(filters)])

  useEffect(() => {
    if (autoFetch) {
      fetchAssets()
    }
  }, [autoFetch, fetchAssets])

  return {
    assets,
    loading,
    error,
    total,
    refetch: fetchAssets,
  }
}

export function useAllAssets(filters?: Omit<UseAssetsOptions, 'platform'>) {
  const { autoFetch = true, ...restFilters } = filters || {}
  const [assets, setAssets] = useState<AllAsset[]>([])
  const [loading, setLoading] = useState(autoFetch)
  const [error, setError] = useState<string | null>(null)
  const [total, setTotal] = useState(0)

  const fetchAssets = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await assetService.getAllAssets(restFilters)
      setAssets(response.results)
      setTotal(response.count)
    } catch (err: any) {
      const apiError = err as ApiError
      setError(apiError.error || apiError.message || 'Erreur lors du chargement des assets')
      setAssets([])
    } finally {
      setLoading(false)
    }
  }, [JSON.stringify(restFilters)])

  useEffect(() => {
    if (autoFetch) {
      fetchAssets()
    }
  }, [autoFetch, fetchAssets])

  return {
    assets,
    loading,
    error,
    total,
    refetch: fetchAssets,
  }
}

