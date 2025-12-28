/**
 * Fonctions de test pour la connexion frontend ↔ backend
 */
import apiClient from './client'
import { authService } from './auth'
import type { ApiError } from '@types'

/**
 * Teste la connexion au backend
 * @returns true si la connexion réussit, false sinon
 */
export const testBackendConnection = async (): Promise<boolean> => {
  try {
    // Tester l'endpoint health check qui ne nécessite pas d'authentification
    const response = await apiClient.get('/health/')
    
    // Si on a une réponse 200, le backend est accessible
    return response.status === 200 && response.data?.status === 'ok'
  } catch (error: any) {
    // Si c'est une erreur réseau (pas de réponse), le backend n'est pas accessible
    if (error.code === 'NETWORK_ERROR' || error.code === 'ECONNREFUSED' || !error.response) {
      console.error('Backend connection failed:', error)
      return false
    }
    // Si on a une réponse HTTP (même erreur), le backend est accessible mais l'endpoint peut être différent
    // On peut aussi essayer /ping/ comme fallback
    try {
      const pingResponse = await apiClient.get('/ping/')
      return pingResponse.status === 200 && pingResponse.data?.pong === true
    } catch {
      return false
    }
  }
}

/**
 * Teste l'authentification avec des credentials
 * @param username - Nom d'utilisateur
 * @param password - Mot de passe
 * @returns Résultat de l'authentification
 */
export const testAuthentication = async (
  username: string,
  password: string
): Promise<{ success: boolean; error?: string; token?: string }> => {
  try {
    const response = await authService.loginJWT({ username, password })
    
    if (response.access) {
      return {
        success: true,
        token: response.access,
      }
    }
    
    return {
      success: false,
      error: 'No token received',
    }
  } catch (error: any) {
    const apiError = error as ApiError
    return {
      success: false,
      error: apiError.error || apiError.message || 'Authentication failed',
    }
  }
}

/**
 * Teste un endpoint CRUD (exemple avec broker-accounts)
 */
export const testCRUDEndpoint = async (): Promise<{
  success: boolean
  error?: string
  details?: {
    list?: boolean
    create?: boolean
    read?: boolean
    update?: boolean
    delete?: boolean
  }
}> => {
  const details: {
    list?: boolean
    create?: boolean
    read?: boolean
    update?: boolean
    delete?: boolean
  } = {}

  try {
    // Test GET (list)
    try {
      const listResponse = await apiClient.get('/broker-accounts/')
      details.list = listResponse.status === 200
    } catch (error) {
      details.list = false
    }

    // Note: Pour tester CREATE, UPDATE, DELETE, il faudrait créer des données de test
    // On ne fait que tester que l'endpoint répond
    
    return {
      success: details.list === true,
      details,
    }
  } catch (error: any) {
    const apiError = error as ApiError
    return {
      success: false,
      error: apiError.error || apiError.message || 'CRUD test failed',
      details,
    }
  }
}

/**
 * Teste le refresh token automatique
 */
export const testTokenRefresh = async (): Promise<{
  success: boolean
  error?: string
}> => {
  try {
    const refreshToken = authService.getRefreshToken()
    
    if (!refreshToken) {
      return {
        success: false,
        error: 'No refresh token available',
      }
    }

    const tokens = await authService.refreshToken()
    
    if (tokens.access) {
      return {
        success: true,
      }
    }
    
    return {
      success: false,
      error: 'No access token received',
    }
  } catch (error: any) {
    const apiError = error as ApiError
    return {
      success: false,
      error: apiError.error || apiError.message || 'Token refresh failed',
    }
  }
}

/**
 * Teste la gestion des erreurs HTTP
 */
export const testErrorHandling = async (): Promise<{
  success: boolean
  errors: {
    '404'?: boolean
    '401'?: boolean
    '400'?: boolean
  }
}> => {
  const errors: { '404'?: boolean; '401'?: boolean; '400'?: boolean } = {}

  // Test 404
  try {
    await apiClient.get('/nonexistent-endpoint-12345/')
    errors['404'] = false
  } catch (error: any) {
    errors['404'] = error.response?.status === 404 || error.code === 'NOT_FOUND'
  }

  // Test 401 (si on n'est pas authentifié)
  const token = authService.getAccessToken()
  if (!token) {
    try {
      await apiClient.get('/broker-accounts/')
      errors['401'] = false
    } catch (error: any) {
      errors['401'] = error.response?.status === 401 || error.code === 'UNAUTHORIZED'
    }
  } else {
    errors['401'] = true // On a un token, donc pas d'erreur 401 attendue
  }

  // Test 400 (Bad Request) - avec des données invalides
  try {
    await apiClient.post('/broker-accounts/', { invalid: 'data' })
    errors['400'] = false
  } catch (error: any) {
    errors['400'] = error.response?.status === 400 || error.code === 'BAD_REQUEST'
  }

  return {
    success: errors['404'] === true && errors['400'] === true,
    errors,
  }
}

/**
 * Exécute tous les tests de connexion
 */
export const runAllConnectionTests = async (credentials?: {
  username: string
  password: string
}): Promise<{
  backendConnection: boolean
  authentication?: { success: boolean; error?: string }
  crud?: { success: boolean; error?: string; details?: any }
  tokenRefresh?: { success: boolean; error?: string }
  errorHandling?: { success: boolean; errors?: any }
}> => {
  const results: any = {}

  // Test 1: Connexion backend
  console.log('🔍 Testing backend connection...')
  results.backendConnection = await testBackendConnection()
  console.log(results.backendConnection ? '✅ Backend connection OK' : '❌ Backend connection failed')

  // Test 2: Authentification (si credentials fournis)
  if (credentials) {
    console.log('🔐 Testing authentication...')
    results.authentication = await testAuthentication(credentials.username, credentials.password)
    console.log(
      results.authentication.success
        ? '✅ Authentication OK'
        : `❌ Authentication failed: ${results.authentication.error}`
    )
  }

  // Test 3: CRUD (nécessite authentification)
  if (results.authentication?.success || authService.isAuthenticated()) {
    console.log('📝 Testing CRUD endpoint...')
    results.crud = await testCRUDEndpoint()
    console.log(
      results.crud.success
        ? '✅ CRUD endpoint OK'
        : `❌ CRUD endpoint failed: ${results.crud.error}`
    )
  }

  // Test 4: Token refresh (nécessite authentification)
  if (results.authentication?.success || authService.isAuthenticated()) {
    console.log('🔄 Testing token refresh...')
    results.tokenRefresh = await testTokenRefresh()
    console.log(
      results.tokenRefresh.success
        ? '✅ Token refresh OK'
        : `❌ Token refresh failed: ${results.tokenRefresh.error}`
    )
  }

  // Test 5: Gestion des erreurs
  console.log('⚠️ Testing error handling...')
  results.errorHandling = await testErrorHandling()
  console.log(
    results.errorHandling.success
      ? '✅ Error handling OK'
      : '❌ Error handling has issues'
  )

  return results
}

export default {
  testBackendConnection,
  testAuthentication,
  testCRUDEndpoint,
  testTokenRefresh,
  testErrorHandling,
  runAllConnectionTests,
}

