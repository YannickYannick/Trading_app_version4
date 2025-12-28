/**
 * Tests pour la connexion frontend ↔ backend
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import apiClient from '../client'
import { authService } from '../auth'
import {
  testBackendConnection,
  testAuthentication,
  testCRUDEndpoint,
  testTokenRefresh,
  testErrorHandling,
} from '../connection'

// Mock du client API
vi.mock('../client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

// Mock du service d'authentification
vi.mock('../auth', () => ({
  authService: {
    loginJWT: vi.fn(),
    getRefreshToken: vi.fn(),
    refreshToken: vi.fn(),
    getAccessToken: vi.fn(),
    isAuthenticated: vi.fn(),
  },
}))

describe('Connection Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  describe('testBackendConnection', () => {
    it('should return true when backend is accessible', async () => {
      // Mock une réponse réussie
      ;(apiClient.get as any).mockResolvedValue({ status: 200 })

      const result = await testBackendConnection()
      expect(result).toBe(true)
    })

    it('should return false on network error', async () => {
      // Mock une erreur réseau
      ;(apiClient.get as any).mockRejectedValue({
        code: 'NETWORK_ERROR',
        message: 'Connection failed',
      })

      const result = await testBackendConnection()
      expect(result).toBe(false)
    })

    it('should return true even on 401 (backend is accessible)', async () => {
      // Mock une erreur 401 (backend répond mais non authentifié)
      ;(apiClient.get as any).mockRejectedValue({
        response: { status: 401 },
        code: 'UNAUTHORIZED',
      })

      const result = await testBackendConnection()
      expect(result).toBe(true)
    })
  })

  describe('testAuthentication', () => {
    it('should return success when authentication succeeds', async () => {
      ;(authService.loginJWT as any).mockResolvedValue({
        access: 'mock-access-token',
        refresh: 'mock-refresh-token',
      })

      const result = await testAuthentication('testuser', 'testpass')
      expect(result.success).toBe(true)
      expect(result.token).toBe('mock-access-token')
    })

    it('should return error when authentication fails', async () => {
      ;(authService.loginJWT as any).mockRejectedValue({
        error: 'Invalid credentials',
        code: 'AUTH_ERROR',
      })

      const result = await testAuthentication('invalid', 'invalid')
      expect(result.success).toBe(false)
      expect(result.error).toBeTruthy()
    })
  })

  describe('testCRUDEndpoint', () => {
    it('should test GET endpoint successfully', async () => {
      ;(apiClient.get as any).mockResolvedValue({ status: 200, data: [] })
      ;(authService.isAuthenticated as any).mockReturnValue(true)

      const result = await testCRUDEndpoint()
      expect(result.success).toBe(true)
      expect(result.details?.list).toBe(true)
    })

    it('should handle GET endpoint errors', async () => {
      ;(apiClient.get as any).mockRejectedValue({
        response: { status: 500 },
      })
      ;(authService.isAuthenticated as any).mockReturnValue(true)

      const result = await testCRUDEndpoint()
      expect(result.success).toBe(false)
      expect(result.details?.list).toBe(false)
    })
  })

  describe('testTokenRefresh', () => {
    it('should refresh token successfully', async () => {
      ;(authService.getRefreshToken as any).mockReturnValue('mock-refresh-token')
      ;(authService.refreshToken as any).mockResolvedValue({
        access: 'new-access-token',
        refresh: 'new-refresh-token',
      })

      const result = await testTokenRefresh()
      expect(result.success).toBe(true)
    })

    it('should fail when no refresh token available', async () => {
      ;(authService.getRefreshToken as any).mockReturnValue(null)

      const result = await testTokenRefresh()
      expect(result.success).toBe(false)
      expect(result.error).toContain('No refresh token')
    })
  })

  describe('testErrorHandling', () => {
    it('should handle 404 errors correctly', async () => {
      ;(apiClient.get as any).mockRejectedValue({
        response: { status: 404 },
      })

      const result = await testErrorHandling()
      expect(result.errors['404']).toBe(true)
    })

    it('should handle 400 errors correctly', async () => {
      ;(apiClient.post as any).mockRejectedValue({
        response: { status: 400 },
      })

      const result = await testErrorHandling()
      expect(result.errors['400']).toBe(true)
    })

    it('should handle 401 errors correctly', async () => {
      ;(authService.getAccessToken as any).mockReturnValue(null)
      ;(apiClient.get as any).mockRejectedValue({
        response: { status: 401 },
      })

      const result = await testErrorHandling()
      expect(result.errors['401']).toBe(true)
    })
  })
})

