/**
 * Types pour la gestion des erreurs
 */
export interface ApiError {
  error: string
  code?: string
  message?: string
  details?: any
  status?: number
  originalError?: any
}

export interface ErrorState {
  error: ApiError | null
  hasError: boolean
}

export type ErrorType = 'network' | 'auth' | 'client' | 'server' | 'validation' | 'unknown'



