/**
 * Service d'authentification (shared)
 * Version sans localStorage - le stockage est géré par le client HTTP (web/mobile)
 */
import type { AxiosInstance } from 'axios'
import type { LoginCredentials, RegisterData, AuthTokens, User } from '../types'

export interface SessionLoginResponse {
  user: User
  // Pas de token pour Session Auth
}

export interface JWTAuthResponse {
  access: string
  refresh: string
  user: User
}

export interface TokenStorage {
  getAccessToken: () => Promise<string | null>
  getRefreshToken: () => Promise<string | null>
  setAccessToken: (token: string) => Promise<void>
  setRefreshToken: (token: string) => Promise<void>
  removeTokens: () => Promise<void>
}

/**
 * Factory function pour créer le service d'authentification
 */
export function createAuthService(
  apiClient: AxiosInstance,
  tokenStorage?: TokenStorage
) {
  return {
    /**
     * Connexion avec Session Authentication
     */
    async loginSession(credentials: LoginCredentials): Promise<SessionLoginResponse> {
      const response = await apiClient.post<SessionLoginResponse>('/auth/login/', credentials)
      return response.data
    },

    /**
     * Connexion avec JWT Authentication
     */
    async loginJWT(credentials: LoginCredentials): Promise<JWTAuthResponse> {
      const response = await apiClient.post<JWTAuthResponse>('/auth/jwt/login/', credentials)
      
      // Stocker les tokens si tokenStorage fourni
      if (tokenStorage && response.data.access && response.data.refresh) {
        await tokenStorage.setAccessToken(response.data.access)
        await tokenStorage.setRefreshToken(response.data.refresh)
      }
      
      return response.data
    },

    /**
     * Connexion (utilise JWT par défaut)
     */
    async login(credentials: LoginCredentials, useJWT: boolean = true): Promise<SessionLoginResponse | JWTAuthResponse> {
      if (useJWT) {
        return this.loginJWT(credentials)
      } else {
        return this.loginSession(credentials)
      }
    },

    /**
     * Déconnexion
     */
    async logout(): Promise<void> {
      try {
        await apiClient.post('/auth/logout/')
      } catch (error) {
        // Ignorer les erreurs de déconnexion
        console.warn('Logout error:', error)
      } finally {
        // Nettoyer les tokens si tokenStorage fourni
        if (tokenStorage) {
          await tokenStorage.removeTokens()
        }
      }
    },

    /**
     * Inscription
     */
    async register(data: RegisterData): Promise<User> {
      const response = await apiClient.post<User>('/auth/register/', data)
      return response.data
    },

    /**
     * Rafraîchir le token JWT
     */
    async refreshToken(): Promise<AuthTokens> {
      if (!tokenStorage) {
        throw new Error('Token storage not provided')
      }
      
      const refreshToken = await tokenStorage.getRefreshToken()
      if (!refreshToken) {
        throw new Error('No refresh token available')
      }

      const response = await apiClient.post<AuthTokens>('/auth/jwt/refresh/', {
        refresh: refreshToken,
      })

      // Mettre à jour les tokens
      await tokenStorage.setAccessToken(response.data.access)
      if (response.data.refresh) {
        await tokenStorage.setRefreshToken(response.data.refresh)
      }

      return response.data
    },

    /**
     * Vérifier le token JWT
     */
    async verifyToken(token: string): Promise<{ valid: boolean }> {
      try {
        await apiClient.post('/auth/jwt/verify/', { token })
        return { valid: true }
      } catch {
        return { valid: false }
      }
    },

    /**
     * Obtenir l'utilisateur actuel
     */
    async getCurrentUser(): Promise<User> {
      const response = await apiClient.get<User>('/auth/user/')
      return response.data
    },

    /**
     * Vérifier si l'utilisateur est authentifié
     */
    async isAuthenticated(): Promise<boolean> {
      if (!tokenStorage) {
        return false
      }
      const accessToken = await tokenStorage.getAccessToken()
      return !!accessToken
    },

    /**
     * Obtenir le token d'accès
     */
    async getAccessToken(): Promise<string | null> {
      if (!tokenStorage) {
        return null
      }
      return tokenStorage.getAccessToken()
    },

    /**
     * Obtenir le refresh token
     */
    async getRefreshToken(): Promise<string | null> {
      if (!tokenStorage) {
        return null
      }
      return tokenStorage.getRefreshToken()
    },
  }
}

