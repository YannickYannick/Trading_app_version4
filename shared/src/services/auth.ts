import { StorageAdapter } from './storage'
import type { LoginCredentials, RegisterData, AuthTokens, User } from '../types'
import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosError } from 'axios'

// Interface pour les erreurs API (reprise de @types/errors)
export interface ApiError {
  error: string
  code: string
  message: string
  details?: any
  status?: number
  originalError?: any
}

// Configuration pour l'API client
export interface ApiConfig {
  baseUrl: string
  timeout?: number
  /** Défaut `false`. Sur React Native, `true` peut provoquer AxiosError: Network Error (cookies inutiles avec JWT). */
  withCredentials?: boolean
}

// Client API abstrait
export class ApiClient {
  private instance: AxiosInstance
  private storage: StorageAdapter
  private config: ApiConfig

  constructor(config: ApiConfig, storage: StorageAdapter) {
    this.config = config
    this.storage = storage

    const withCredentials = config.withCredentials ?? false

    this.instance = axios.create({
      baseURL: config.baseUrl,
      timeout: config.timeout || 30000,
      headers: {
        'Content-Type': 'application/json',
      },
      withCredentials,
    })

    this.setupInterceptors()
  }

  private setupInterceptors() {
    // Request Interceptor
    this.instance.interceptors.request.use(
      async (config: InternalAxiosRequestConfig) => {
        const token = await this.storage.getItem('access_token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Response Interceptor
    this.instance.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

        // Refresh Token logic
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true

          try {
            const refreshToken = await this.storage.getItem('refresh_token')
            if (refreshToken) {
              const response = await axios.post(
                `${this.config.baseUrl}/auth/jwt/refresh/`,
                { refresh: refreshToken },
                { withCredentials: this.config.withCredentials ?? false },
              )

              const { access } = response.data
              await this.storage.setItem('access_token', access) // Await in case it's async

              originalRequest.headers.Authorization = `Bearer ${access}`
              return this.instance(originalRequest)
            }
          } catch (refreshError) {
            // Failed to refresh - clear tokens
            await this.storage.removeItem('access_token')
            await this.storage.removeItem('refresh_token')
            return Promise.reject(refreshError)
          }
        }
        return Promise.reject(error)
      }
    )
  }

  public getInstance(): AxiosInstance {
    return this.instance
  }
}

// Service d'authentification partagé
export class AuthService {
  private api: AxiosInstance
  private storage: StorageAdapter

  constructor(apiClient: ApiClient, storage: StorageAdapter) {
    this.api = apiClient.getInstance()
    this.storage = storage
  }

  async loginJWT(credentials: LoginCredentials): Promise<AuthTokens> {
    const response = await this.api.post<AuthTokens>('/auth/jwt/login/', credentials)

    if (response.data.access && response.data.refresh) {
      await this.storage.setItem('access_token', response.data.access)
      await this.storage.setItem('refresh_token', response.data.refresh)
    }

    return response.data
  }

  async logout(): Promise<void> {
    try {
      await this.api.post('/auth/logout/')
    } catch (e) {
      console.warn('Logout error', e)
    } finally {
      await this.storage.removeItem('access_token')
      await this.storage.removeItem('refresh_token')
    }
  }

  async isAuthenticated(): Promise<boolean> {
    const token = await this.storage.getItem('access_token')
    return !!token
  }

  // ... autres méthodes (register, profile, etc.)
}


