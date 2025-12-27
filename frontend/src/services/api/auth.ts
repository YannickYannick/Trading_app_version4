/**
 * Service d'authentification
 * Gère l'authentification Session et JWT
 */
import apiClient from './client'
import type { LoginCredentials, RegisterData, AuthTokens, User, ApiError } from '@types'

export interface SessionLoginResponse {
  user: User
  // Pas de token pour Session Auth
}

export interface JWTAuthResponse {
  access: string
  refresh: string
  user: User
}

export const authService = {
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
    
    // Stocker les tokens
    if (response.data.access && response.data.refresh) {
      localStorage.setItem('access_token', response.data.access)
      localStorage.setItem('refresh_token', response.data.refresh)
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
      // Nettoyer les tokens
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
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
    const refreshToken = localStorage.getItem('refresh_token')
    if (!refreshToken) {
      throw new Error('No refresh token available')
    }

    const response = await apiClient.post<AuthTokens>('/auth/jwt/refresh/', {
      refresh: refreshToken,
    })

    // Mettre à jour les tokens
    localStorage.setItem('access_token', response.data.access)
    if (response.data.refresh) {
      localStorage.setItem('refresh_token', response.data.refresh)
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
  isAuthenticated(): boolean {
    // Vérifier si on a un token JWT ou une session active
    const hasJWT = !!localStorage.getItem('access_token')
    // Pour Session Auth, on peut vérifier via une requête
    return hasJWT
  },

  /**
   * Obtenir le token d'accès
   */
  getAccessToken(): string | null {
    return localStorage.getItem('access_token')
  },

  /**
   * Obtenir le refresh token
   */
  getRefreshToken(): string | null {
    return localStorage.getItem('refresh_token')
  },
}

export default authService

