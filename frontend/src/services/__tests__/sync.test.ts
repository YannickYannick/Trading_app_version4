/**
 * Tests pour les synchronisations
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

describe('Synchronizations', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Sync Assets', () => {
    it('should sync assets successfully', async () => {
      const mockResponse = {
        data: {
          success: true,
          message: 'Assets synchronized successfully',
          sync_log: {
            id: 1,
            status: 'SUCCESS',
            records_synced: 100,
            started_at: '2024-12-27T10:00:00Z',
            completed_at: '2024-12-27T10:01:00Z',
          },
          details: {
            created: 50,
            updated: 50,
          },
        },
      }
      ;(apiClient.post as any).mockResolvedValue(mockResponse)

      const result = await brokerService.sync(1, { sync_type: 'ASSETS' })
      expect(result.status).toBe('SUCCESS')
      expect(result.records_synced).toBe(100)
    })

    it('should handle sync errors', async () => {
      const mockError = {
        response: {
          data: {
            success: false,
            message: 'Authentication failed',
            error: 'Token expired',
            error_type: 'AUTHENTICATION_ERROR',
          },
          status: 401,
        },
      }
      ;(apiClient.post as any).mockRejectedValue(mockError)

      try {
        await brokerService.sync(1, { sync_type: 'ASSETS' })
      } catch (error: any) {
        expect(error.response.data.success).toBe(false)
        expect(error.response.data.error_type).toBe('AUTHENTICATION_ERROR')
      }
    })
  })

  describe('Sync Positions', () => {
    it('should sync positions successfully', async () => {
      const mockResponse = {
        data: {
          success: true,
          message: 'Positions synchronized successfully',
          sync_log: {
            id: 2,
            status: 'SUCCESS',
            records_synced: 5,
          },
          details: {
            created: 2,
            updated: 3,
          },
        },
      }
      ;(apiClient.post as any).mockResolvedValue(mockResponse)

      const result = await brokerService.sync(1, { sync_type: 'POSITIONS' })
      expect(result.status).toBe('SUCCESS')
      expect(result.records_synced).toBe(5)
    })
  })

  describe('Sync Trades', () => {
    it('should sync trades successfully', async () => {
      const mockResponse = {
        data: {
          success: true,
          message: 'Trades synchronized successfully',
          sync_log: {
            id: 3,
            status: 'SUCCESS',
            records_synced: 20,
          },
          details: {
            created: 15,
            updated: 5,
          },
        },
      }
      ;(apiClient.post as any).mockResolvedValue(mockResponse)

      const result = await brokerService.sync(1, { sync_type: 'TRADES' })
      expect(result.status).toBe('SUCCESS')
      expect(result.records_synced).toBe(20)
    })
  })

  describe('Sync Prices', () => {
    it('should sync prices successfully', async () => {
      const mockResponse = {
        data: {
          success: true,
          message: 'Prices synchronized successfully',
          sync_log: {
            id: 4,
            status: 'SUCCESS',
            records_synced: 50,
          },
          details: {
            updated: 50,
          },
        },
      }
      ;(apiClient.post as any).mockResolvedValue(mockResponse)

      const result = await brokerService.sync(1, { sync_type: 'PRICES' })
      expect(result.status).toBe('SUCCESS')
      expect(result.records_synced).toBe(50)
    })
  })

  describe('Sync with force option', () => {
    it('should sync with force option', async () => {
      const mockResponse = {
        data: {
          success: true,
          message: 'Assets synchronized successfully',
          sync_log: {
            id: 5,
            status: 'SUCCESS',
            records_synced: 100,
          },
        },
      }
      ;(apiClient.post as any).mockResolvedValue(mockResponse)

      const result = await brokerService.sync(1, { sync_type: 'ASSETS', force: true })
      expect(result.status).toBe('SUCCESS')
    })
  })

  describe('Get Sync Logs', () => {
    it('should get sync logs', async () => {
      const mockResponse = {
        data: {
          count: 2,
          results: [
            {
              id: 1,
              sync_type: 'ASSETS',
              status: 'SUCCESS',
              records_synced: 100,
              started_at: '2024-12-27T10:00:00Z',
              completed_at: '2024-12-27T10:01:00Z',
            },
            {
              id: 2,
              sync_type: 'POSITIONS',
              status: 'SUCCESS',
              records_synced: 5,
              started_at: '2024-12-27T10:02:00Z',
              completed_at: '2024-12-27T10:03:00Z',
            },
          ],
        },
      }
      ;(apiClient.get as any).mockResolvedValue(mockResponse)

      const result = await brokerService.getSyncLogs(1)
      expect(result.results).toHaveLength(2)
      expect(result.results[0].sync_type).toBe('ASSETS')
    })

    it('should get all sync logs when accountId is not provided', async () => {
      const mockResponse = {
        data: {
          count: 10,
          results: [],
        },
      }
      ;(apiClient.get as any).mockResolvedValue(mockResponse)

      const result = await brokerService.getSyncLogs()
      expect(result.count).toBe(10)
    })
  })

  describe('Get Last Sync Log', () => {
    it('should get last sync log', async () => {
      const mockResponse = {
        data: {
          count: 1,
          results: [
            {
              id: 1,
              sync_type: 'ASSETS',
              status: 'SUCCESS',
              records_synced: 100,
              started_at: '2024-12-27T10:00:00Z',
            },
          ],
        },
      }
      ;(apiClient.get as any).mockResolvedValue(mockResponse)

      const result = await brokerService.getLastSyncLog(1, 'ASSETS')
      expect(result).not.toBeNull()
      expect(result?.sync_type).toBe('ASSETS')
      expect(result?.status).toBe('SUCCESS')
    })

    it('should return null when no logs found', async () => {
      const mockResponse = {
        data: {
          count: 0,
          results: [],
        },
      }
      ;(apiClient.get as any).mockResolvedValue(mockResponse)

      const result = await brokerService.getLastSyncLog(1)
      expect(result).toBeNull()
    })
  })
})

