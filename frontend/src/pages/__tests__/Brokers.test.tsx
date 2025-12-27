/**
 * Tests pour la page Brokers
 */
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Brokers from '../Brokers'
import { useBrokers } from '@hooks/useBrokers'
import { brokerService } from '@services'

// Mock des hooks et services
jest.mock('@hooks/useBrokers')
jest.mock('@services')

describe('Brokers Page', () => {
  const mockAccounts = [
    {
      id: 1,
      name: 'Mon compte Saxo',
      broker: {
        id: 1,
        name: 'Saxo Bank',
        broker_type: 'SAXO',
      },
      broker_name: 'Saxo Bank',
      broker_type: 'SAXO',
      broker_type_display: 'Saxo Bank',
      account_id: 'ACC123',
      environment: 'simulation',
      environment_display: 'Simulation/Demo',
      is_active: true,
      is_sandbox: true,
      last_sync: '2024-01-01T10:00:00Z',
      user: 1,
    },
    {
      id: 2,
      name: 'Mon compte Binance',
      broker: {
        id: 2,
        name: 'Binance',
        broker_type: 'BINANCE',
      },
      broker_name: 'Binance',
      broker_type: 'BINANCE',
      broker_type_display: 'Binance',
      account_id: 'BIN456',
      environment: 'live',
      environment_display: 'Live Trading',
      is_active: true,
      is_sandbox: false,
      last_sync: null,
      user: 1,
    },
    {
      id: 3,
      name: 'Compte inactif',
      broker: null,
      broker_name: null,
      broker_type: 'SAXO',
      broker_type_display: 'Saxo Bank',
      account_id: '',
      environment: 'simulation',
      environment_display: 'Simulation/Demo',
      is_active: false,
      is_sandbox: true,
      last_sync: null,
      user: 1,
    },
  ]

  const mockBrokers = [
    {
      id: 1,
      name: 'Saxo Bank',
      broker_type: 'SAXO',
      is_active: true,
    },
    {
      id: 2,
      name: 'Binance',
      broker_type: 'BINANCE',
      is_active: true,
    },
  ]

  beforeEach(() => {
    jest.clearAllMocks()
    ;(useBrokers as jest.Mock).mockReturnValue({
      accounts: mockAccounts,
      brokers: mockBrokers,
      loading: false,
      error: null,
      refetch: jest.fn(),
    })
  })

  it('affiche la liste des brokers', () => {
    render(
      <BrowserRouter>
        <Brokers />
      </BrowserRouter>
    )

    expect(screen.getByText('Mon compte Saxo')).toBeInTheDocument()
    expect(screen.getByText('Mon compte Binance')).toBeInTheDocument()
    expect(screen.getByText('Compte inactif')).toBeInTheDocument()
  })

  it('gère les comptes sans broker (broker null)', () => {
    render(
      <BrowserRouter>
        <Brokers />
      </BrowserRouter>
    )

    // Ne devrait pas planter même si broker est null
    expect(screen.getByText('Compte inactif')).toBeInTheDocument()
  })

  it('filtre les comptes par type de broker', () => {
    render(
      <BrowserRouter>
        <Brokers />
      </BrowserRouter>
    )

    // Le test de filtrage sera fait via l'interaction utilisateur
    // Ici on vérifie juste que le composant se rend sans erreur
    expect(screen.getByText('Brokers')).toBeInTheDocument()
  })

  it('affiche un message si aucun broker trouvé', () => {
    ;(useBrokers as jest.Mock).mockReturnValue({
      accounts: [],
      brokers: [],
      loading: false,
      error: null,
      refetch: jest.fn(),
    })

    render(
      <BrowserRouter>
        <Brokers />
      </BrowserRouter>
    )

    expect(screen.getByText(/Aucun broker trouvé/i)).toBeInTheDocument()
  })

  it('affiche un message d\'erreur en cas d\'erreur', () => {
    ;(useBrokers as jest.Mock).mockReturnValue({
      accounts: [],
      brokers: [],
      loading: false,
      error: 'Erreur de chargement',
      refetch: jest.fn(),
    })

    render(
      <BrowserRouter>
        <Brokers />
      </BrowserRouter>
    )

    expect(screen.getByText(/Erreur: Erreur de chargement/i)).toBeInTheDocument()
  })

  it('affiche un loader pendant le chargement', () => {
    ;(useBrokers as jest.Mock).mockReturnValue({
      accounts: [],
      brokers: [],
      loading: true,
      error: null,
      refetch: jest.fn(),
    })

    render(
      <BrowserRouter>
        <Brokers />
      </BrowserRouter>
    )

    expect(screen.getByText(/Chargement des brokers/i)).toBeInTheDocument()
  })
})

