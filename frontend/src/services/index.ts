/**
 * Export centralisé de tous les services
 */
export { default as apiClient } from './api/client'
export type { ApiResponse, ApiError } from './api/client'

export * from './api/auth'
export { default as authService } from './api/auth'

export * from './api/connection'

export { default as assetService } from './assets'
export * from './assets'

export { default as positionService } from './positions'
export * from './positions'

export { default as tradeService } from './trades'
export * from './trades'

export { default as orderService } from './orders'
export * from './orders'

export { default as brokerService } from './brokers'
export * from './brokers'

export { default as strategyService } from './strategies'
export * from './strategies'

// Export de l'ancien api.ts pour compatibilité (legacy)
export { default as api } from './api'

