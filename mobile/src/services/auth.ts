import { ApiClient, AuthService } from '@trading-app/shared'
import { config } from '../config/constants'
import { MobileStorageAdapter } from '../api/storage'

/** Stockage partagé (tokens) pour tout le mobile — une seule instance. */
export const storage = new MobileStorageAdapter()

export const apiClient = new ApiClient(
    {
        baseUrl: config.apiBaseUrl,
        timeout: config.timeout,
    },
    storage,
)

export const authService = new AuthService(apiClient, storage)

// Exporter l'instance axios pour usage direct si nécessaire (déconseillé, préférer les services)
export const axiosInstance = apiClient.getInstance()
