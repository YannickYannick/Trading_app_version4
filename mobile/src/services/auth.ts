import { ApiClient, AuthService } from '@trading-app/shared'
import { config } from '../config/constants'
import { MobileStorageAdapter } from '../api/storage'

// Initialiser l'adaptateur de stockage mobile
const storageAdapter = new MobileStorageAdapter()

// Initialiser le client API avec la config et le stockage
export const apiClient = new ApiClient({
    baseUrl: config.apiBaseUrl,
    timeout: config.timeout,
}, storageAdapter)

// Initialiser le service d'auth partagé
export const authService = new AuthService(apiClient, storageAdapter)

// Exporter l'instance axios pour usage direct si nécessaire (déconseillé, préférer les services)
export const axiosInstance = apiClient.getInstance()
