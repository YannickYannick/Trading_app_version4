/**
 * Client HTTP de base avec axios
 * Gère les intercepteurs pour l'authentification et les erreurs
 */
import axios, { AxiosInstance, AxiosRequestConfig, AxiosError, InternalAxiosRequestConfig } from 'axios'
import { config } from '@utils/config'
import type { ApiResponse, ApiError } from '@types'

// Créer l'instance axios
const apiClient: AxiosInstance = axios.create({
  baseURL: config.apiBaseUrl,
  timeout: 30000, // 30 secondes
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Pour les cookies de session
})

// Intercepteur pour les requêtes
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Ajouter le token JWT si disponible
    const accessToken = localStorage.getItem('access_token')
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`
    }
    
    // Ajouter le CSRF token pour les requêtes POST/PUT/DELETE
    const csrfToken = getCookie('csrftoken')
    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken
    }
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Intercepteur pour les réponses
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiError>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    
    // Gérer les erreurs 401 (non authentifié)
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      
      // Essayer de rafraîchir le token JWT
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const response = await axios.post(`${config.apiBaseUrl}/auth/jwt/refresh/`, {
            refresh: refreshToken,
          })
          
          const { access } = response.data
          localStorage.setItem('access_token', access)
          
          // Réessayer la requête originale
          originalRequest.headers.Authorization = `Bearer ${access}`
          return apiClient(originalRequest)
        } catch (refreshError) {
          // Refresh token invalide, déconnecter
          handleLogout()
          return Promise.reject(refreshError)
        }
      } else {
        // Pas de refresh token, déconnecter
        handleLogout()
      }
    }
    
    // Gérer les autres erreurs
    if (error.response) {
      // Erreur avec réponse du serveur
      const status = error.response.status
      const data = error.response.data || {}
      
      // Déterminer le type d'erreur
      let errorType = 'UNKNOWN_ERROR'
      if (status >= 400 && status < 500) {
        errorType = 'CLIENT_ERROR'
        if (status === 401) errorType = 'AUTHENTICATION_ERROR'
        if (status === 403) errorType = 'FORBIDDEN_ERROR'
        if (status === 404) errorType = 'NOT_FOUND_ERROR'
        if (status === 422) errorType = 'VALIDATION_ERROR'
      } else if (status >= 500) {
        errorType = 'SERVER_ERROR'
      }
      
      // Obtenir un message d'erreur lisible
      const errorMessage =
        data.error || data.detail || data.message || getDefaultErrorMessage(status)
      
      const apiError: ApiError = {
        error: errorMessage,
        code: errorType,
        message: errorMessage,
        details: data,
        status: status,
        originalError: error,
      }
      
      return Promise.reject(apiError)
    } else if (error.request) {
      // Pas de réponse du serveur (timeout, réseau, etc.)
      return Promise.reject({
        error: 'Impossible de contacter le serveur',
        code: 'NETWORK_ERROR',
        message: 'Vérifiez votre connexion internet',
        originalError: error,
      } as ApiError)
    } else {
      // Erreur lors de la configuration de la requête
      return Promise.reject({
        error: error.message,
        code: 'REQUEST_ERROR',
        message: error.message,
        originalError: error,
      } as ApiError)
    }
  }
)

// Fonction utilitaire pour obtenir un cookie
function getCookie(name: string): string | null {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) {
    return parts.pop()?.split(';').shift() || null
  }
  return null
}

// Fonction pour obtenir un message d'erreur par défaut selon le code HTTP
function getDefaultErrorMessage(status: number): string {
  const defaultMessages: Record<number, string> = {
    400: 'Requête invalide. Vérifiez les données saisies.',
    401: 'Non autorisé. Veuillez vous connecter.',
    403: 'Accès refusé. Vous n\'avez pas les permissions nécessaires.',
    404: 'Ressource non trouvée.',
    422: 'Données invalides. Veuillez vérifier les champs du formulaire.',
    500: 'Erreur serveur. Veuillez réessayer plus tard.',
    502: 'Service temporairement indisponible.',
    503: 'Service en maintenance.',
  }
  
  return defaultMessages[status] || 'Une erreur est survenue.'
}

// Fonction pour gérer la déconnexion
function handleLogout() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  // Rediriger vers la page de login si on n'y est pas déjà
  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

export default apiClient
export type { ApiResponse, ApiError }

