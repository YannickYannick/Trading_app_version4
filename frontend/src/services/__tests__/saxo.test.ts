/**
 * Tests pour l'intégration Saxo Bank
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { brokerService } from '../brokers'
import apiClient from '../api/client'

// Mock du client API
vi.mock('../api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

describe('Saxo Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('OAuth2 Authentication', () => {
    it('should get auth URL', async () => {
      const mockResponse = {
        data: {
          success: true,
          auth_url: 'https://live.logonvalidation.net/authorize?client_id=test&redirect_uri=test',
          state: 'test-state-123',
        },
      }
      ;(apiClient.get as any).mockResolvedValue(mockResponse)

      const result = await brokerService.getSaxoAuthUrl(1)
      expect(result.auth_url).toContain('logonvalidation.net')
      expect(result.state).toBe('test-state-123')
    })

    it('should exchange code for tokens', async () => {
      const mockResponse = {
        data: {
          id: 1,
          saxo_access_token: 'access-token-123',
          saxo_refresh_token: 'refresh-token-123',
          broker_type: 'SAXO',
        },
      }
      ;(apiClient.post as any).mockResolvedValue(mockResponse)

      const result = await brokerService.exchangeSaxoAuthCode(1, 'auth-code-123')
      expect(result.saxo_access_token).toBe('access-token-123')
      expect(result.saxo_refresh_token).toBe('refresh-token-123')
    })

    it('should refresh token', async () => {
      const mockResponse = {
        data: {
          id: 1,
          saxo_access_token: 'new-access-token-123',
          saxo_refresh_token: 'new-refresh-token-123',
          broker_type: 'SAXO',
        },
      }
      ;(apiClient.post as any).mockResolvedValue(mockResponse)

      const result = await brokerService.refreshSaxoToken(1)
      expect(result.saxo_access_token).toBe('new-access-token-123')
    })

    it('should delete tokens', async () => {
      const mockResponse = {
        data: {
          id: 1,
          saxo_access_token: null,
          saxo_refresh_token: null,
          broker_type: 'SAXO',
        },
      }
      ;(apiClient.post as any).mockResolvedValue(mockResponse)

      const result = await brokerService.deleteSaxoTokens(1)
      expect(result.saxo_access_token).toBeNull()
      expect(result.saxo_refresh_token).toBeNull()
    })
  })

  describe('Data Retrieval', () => {
    it('should get balance', async () => {
      const mockResponse = {
        data: {
          success: true,
          balance_eur: 1250.75,
          currency: 'EUR',
          all_balances: { EUR: 1250.75 },
        },
      }
      ;(apiClient.get as any).mockResolvedValue(mockResponse)

      const result = await brokerService.getBalanceEur(1)
      expect(result.success).toBe(true)
      expect(result.balance_eur).toBe(1250.75)
      expect(result.currency).toBe('EUR')
    })

    it('should get assets', async () => {
      const mockResponse = {
        data: {
          success: true,
          count: 2,
          assets: [
            {
              symbol: 'AAPL',
              name: 'Apple Inc.',
              asset_type: 'Stock',
              exchange: 'NASDAQ',
              currency: 'USD',
              is_tradable: true,
              broker_id: '123',
            },
            {
              symbol: 'MSFT',
              name: 'Microsoft Corporation',
              asset_type: 'Stock',
              exchange: 'NASDAQ',
              currency: 'USD',
              is_tradable: true,
              broker_id: '456',
            },
          ],
        },
      }
      ;(apiClient.get as any).mockResolvedValue(mockResponse)

      const result = await brokerService.getSaxoAssets(1, { asset_type: 'Stock', limit: 100 })
      expect(result.success).toBe(true)
      expect(result.count).toBe(2)
      expect(result.assets).toHaveLength(2)
      expect(result.assets[0].symbol).toBe('AAPL')
    })

    it('should get positions', async () => {
      const mockResponse = {
        data: {
          success: true,
          count: 1,
          positions: [
            {
              symbol: 'AAPL',
              quantity: 10,
              entry_price: 150.0,
              current_price: 155.0,
              unrealized_pnl: 50.0,
              currency: 'USD',
              side: 'Buy',
              broker_id: 'pos-123',
            },
          ],
        },
      }
      ;(apiClient.get as any).mockResolvedValue(mockResponse)

      const result = await brokerService.getSaxoPositions(1)
      expect(result.success).toBe(true)
      expect(result.count).toBe(1)
      expect(result.positions).toHaveLength(1)
      expect(result.positions[0].symbol).toBe('AAPL')
      expect(result.positions[0].quantity).toBe(10)
    })

    it('should handle errors when getting assets', async () => {
      const mockError = {
        response: {
          data: {
            error: 'Authentication failed',
          },
        },
      }
      ;(apiClient.get as any).mockRejectedValue(mockError)

      const result = await brokerService.getSaxoAssets(1)
      expect(result.success).toBe(false)
      expect(result.error).toBe('Authentication failed')
      expect(result.assets).toHaveLength(0)
    })

    it('should handle errors when getting positions', async () => {
      const mockError = {
        response: {
          data: {
            error: 'Token expired',
          },
        },
      }
      ;(apiClient.get as any).mockRejectedValue(mockError)

      const result = await brokerService.getSaxoPositions(1)
      expect(result.success).toBe(false)
      expect(result.error).toBe('Token expired')
      expect(result.positions).toHaveLength(0)
    })
  })

  describe('Connection Test', () => {
    it('should test connection successfully', async () => {
      const mockResponse = {
        data: {
          success: true,
          message: 'Connection successful',
        },
      }
      ;(apiClient.post as any).mockResolvedValue(mockResponse)

      const result = await brokerService.testConnection(1)
      expect(result.success).toBe(true)
      expect(result.message).toBe('Connection successful')
    })

    it('should handle connection errors', async () => {
      const mockError = {
        response: {
          data: {
            success: false,
            error: 'Authentication failed',
          },
        },
      }
      ;(apiClient.post as any).mockRejectedValue(mockError)

      try {
        await brokerService.testConnection(1)
      } catch (error: any) {
        expect(error.response.data.success).toBe(false)
        expect(error.response.data.error).toBe('Authentication failed')
      }
    })
  })
})

