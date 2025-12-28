/**
 * Tests pour l'intégration Binance
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

describe('Binance Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
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
            error: 'Invalid API key',
          },
        },
      }
      ;(apiClient.post as any).mockRejectedValue(mockError)

      try {
        await brokerService.testConnection(1)
      } catch (error: any) {
        expect(error.response.data.success).toBe(false)
        expect(error.response.data.error).toBe('Invalid API key')
      }
    })
  })

  describe('Data Retrieval', () => {
    it('should get balance', async () => {
      const mockResponse = {
        data: {
          success: true,
          balance_eur: 1250.75,
          currency: 'EUR',
          all_balances: { EUR: 1250.75, BTC: 0.001 },
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
              symbol: 'BTCUSDT',
              name: 'BTC/USDT',
              asset_type: 'CRYPTO',
              exchange: 'Binance',
              currency: 'USDT',
              is_tradable: true,
              broker_id: 'BTCUSDT',
            },
            {
              symbol: 'ETHUSDT',
              name: 'ETH/USDT',
              asset_type: 'CRYPTO',
              exchange: 'Binance',
              currency: 'USDT',
              is_tradable: true,
              broker_id: 'ETHUSDT',
            },
          ],
        },
      }
      ;(apiClient.get as any).mockResolvedValue(mockResponse)

      const result = await brokerService.getBinanceAssets(1, { keywords: 'BTC', limit: 10 })
      expect(result.success).toBe(true)
      expect(result.count).toBe(2)
      expect(result.assets).toHaveLength(2)
      expect(result.assets[0].symbol).toBe('BTCUSDT')
    })

    it('should get positions', async () => {
      const mockResponse = {
        data: {
          success: true,
          count: 1,
          positions: [
            {
              symbol: 'BTCUSDT',
              quantity: 0.001,
              entry_price: 50000.0,
              current_price: 51000.0,
              unrealized_pnl: 1.0,
              currency: 'USDT',
              side: 'Buy',
              broker_id: 'BTCUSDT',
            },
          ],
        },
      }
      ;(apiClient.get as any).mockResolvedValue(mockResponse)

      const result = await brokerService.getBinancePositions(1)
      expect(result.success).toBe(true)
      expect(result.count).toBe(1)
      expect(result.positions).toHaveLength(1)
      expect(result.positions[0].symbol).toBe('BTCUSDT')
      expect(result.positions[0].quantity).toBe(0.001)
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

      const result = await brokerService.getBinanceAssets(1)
      expect(result.success).toBe(false)
      expect(result.error).toBe('Authentication failed')
      expect(result.assets).toHaveLength(0)
    })

    it('should handle errors when getting positions', async () => {
      const mockError = {
        response: {
          data: {
            error: 'Invalid API key',
          },
        },
      }
      ;(apiClient.get as any).mockRejectedValue(mockError)

      const result = await brokerService.getBinancePositions(1)
      expect(result.success).toBe(false)
      expect(result.error).toBe('Invalid API key')
      expect(result.positions).toHaveLength(0)
    })
  })

  describe('Balance Refresh', () => {
    it('should refresh balance successfully', async () => {
      const mockResponse = {
        data: {
          success: true,
          balance_eur: 1500.0,
          currency: 'EUR',
          all_balances: { EUR: 1500.0 },
          account: {
            id: 1,
            balance: 1500.0,
            currency: 'EUR',
          },
        },
      }
      ;(apiClient.post as any).mockResolvedValue(mockResponse)

      const result = await brokerService.refreshBalance(1)
      expect(result.success).toBe(true)
      expect(result.balance_eur).toBe(1500.0)
    })
  })
})

