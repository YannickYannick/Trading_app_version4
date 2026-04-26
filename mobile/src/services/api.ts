import {
    TradesService,
    PositionsService,
    StrategiesService,
    AssetsService,
    BrokersService,
} from '@trading-app/shared'
import { apiClient } from './auth'

export { storage } from './auth'

export const tradesService = new TradesService(apiClient)
export const positionsService = new PositionsService(apiClient)
export const strategiesService = new StrategiesService(apiClient)
export const assetsService = new AssetsService(apiClient)
export const brokersService = new BrokersService(apiClient)
