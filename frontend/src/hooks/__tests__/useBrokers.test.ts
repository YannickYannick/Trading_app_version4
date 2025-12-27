/**
 * Tests pour le hook useBrokers
 */
import { renderHook, waitFor } from '@testing-library/react'
import { useBrokers } from '../useBrokers'
import { brokerService } from '@services'

jest.mock('@services')

describe('useBrokers', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('charge les brokers et comptes par défaut', async () => {
    const mockBrokers = {
      results: [
        { id: 1, name: 'Saxo Bank', broker_type: 'SAXO' },
        { id: 2, name: 'Binance', broker_type: 'BINANCE' },
      ],
      count: 2,
    }

    const mockAccounts = {
      results: [
        {
          id: 1,
          name: 'Mon compte',
          broker: { id: 1, name: 'Saxo Bank', broker_type: 'SAXO' },
          broker_type: 'SAXO',
          is_active: true,
        },
      ],
      count: 1,
    }

    ;(brokerService.getAll as jest.Mock).mockResolvedValue(mockBrokers)
    ;(brokerService.getAccounts as jest.Mock).mockResolvedValue(mockAccounts)

    const { result } = renderHook(() => useBrokers({ autoFetch: true }))

    expect(result.current.loading).toBe(true)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.brokers).toHaveLength(2)
    expect(result.current.accounts).toHaveLength(1)
  })

  it('filtre les brokers par type', async () => {
    const mockBrokers = {
      results: [
        { id: 1, name: 'Saxo Bank', broker_type: 'SAXO' },
        { id: 2, name: 'Binance', broker_type: 'BINANCE' },
      ],
      count: 2,
    }

    ;(brokerService.getAll as jest.Mock).mockResolvedValue(mockBrokers)
    ;(brokerService.getAccounts as jest.Mock).mockResolvedValue({ results: [], count: 0 })

    const { result } = renderHook(() =>
      useBrokers({ autoFetch: true, brokerType: 'SAXO' })
    )

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.brokers).toHaveLength(1)
    expect(result.current.brokers[0].broker_type).toBe('SAXO')
  })

  it('gère les erreurs de chargement', async () => {
    ;(brokerService.getAll as jest.Mock).mockRejectedValue({
      error: 'Erreur de chargement',
    })
    ;(brokerService.getAccounts as jest.Mock).mockRejectedValue({
      error: 'Erreur de chargement',
    })

    const { result } = renderHook(() => useBrokers({ autoFetch: true }))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBeTruthy()
    expect(result.current.brokers).toHaveLength(0)
    expect(result.current.accounts).toHaveLength(0)
  })

  it('ne charge pas automatiquement si autoFetch est false', () => {
    const { result } = renderHook(() => useBrokers({ autoFetch: false }))

    expect(result.current.loading).toBe(false)
    expect(brokerService.getAll).not.toHaveBeenCalled()
    expect(brokerService.getAccounts).not.toHaveBeenCalled()
  })
})

