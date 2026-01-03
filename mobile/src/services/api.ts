import { AuthService, ApiClient, TradesService, PositionsService, StrategiesService, AssetsService, BrokersService } from '@trading-app/shared'
import { MobileStorageAdapter } from '../api/storage'
import { API_URL } from '../config/constants'

// Instance unique du storage
export const storage = new MobileStorageAdapter()

// Configuration de l'API
const apiClient = new ApiClient({
    baseUrl: API_URL,
    timeout: 30000
}, storage)

export const authService = new AuthService(apiClient, storage)
export const tradesService = new TradesService(apiClient)
export const positionsService = new PositionsService(apiClient)
export const strategiesService = new StrategiesService(apiClient)
export const assetsService = new AssetsService(apiClient)
export const brokersService = new BrokersService(apiClient)



