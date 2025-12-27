/**
 * Tests pour le formulaire BrokerForm
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import BrokerForm from '../BrokerForm'
import { brokerService } from '@services'

jest.mock('@services')

describe('BrokerForm', () => {
  const mockBrokers = [
    { id: 1, name: 'Saxo Bank', broker_type: 'SAXO' },
    { id: 2, name: 'Binance', broker_type: 'BINANCE' },
  ]

  const mockOnSuccess = jest.fn()
  const mockOnCancel = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
    ;(brokerService.createAccount as jest.Mock).mockResolvedValue({ id: 1 })
    ;(brokerService.updateAccount as jest.Mock).mockResolvedValue({ id: 1 })
  })

  it('affiche le formulaire de création', () => {
    render(
      <BrokerForm
        account={null}
        brokers={mockBrokers}
        onSuccess={mockOnSuccess}
        onCancel={mockOnCancel}
      />
    )

    expect(screen.getByText(/Nouveau Broker|Modifier le Broker/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Nom de la configuration/i)).toBeInTheDocument()
  })

  it('affiche le formulaire de modification', () => {
    const mockAccount = {
      id: 1,
      name: 'Mon compte',
      broker: { id: 1, name: 'Saxo Bank', broker_type: 'SAXO' },
      broker_type: 'SAXO',
      account_id: 'ACC123',
      environment: 'simulation',
      is_active: true,
      is_sandbox: true,
    }

    render(
      <BrokerForm
        account={mockAccount as any}
        brokers={mockBrokers}
        onSuccess={mockOnSuccess}
        onCancel={mockOnCancel}
      />
    )

    const nameInput = screen.getByLabelText(/Nom de la configuration/i) as HTMLInputElement
    expect(nameInput.value).toBe('Mon compte')
  })

  it('gère les brokers null ou undefined', () => {
    render(
      <BrokerForm
        account={null}
        brokers={[]}
        onSuccess={mockOnSuccess}
        onCancel={mockOnCancel}
      />
    )

    // Ne devrait pas planter même si aucun broker n'est disponible
    expect(screen.getByText(/Aucun broker de type/i)).toBeInTheDocument()
  })

  it('affiche les champs spécifiques Saxo', () => {
    render(
      <BrokerForm
        account={null}
        brokers={mockBrokers}
        onSuccess={mockOnSuccess}
        onCancel={mockOnCancel}
      />
    )

    // Sélectionner Saxo
    const typeSelect = screen.getByLabelText(/Type de Broker/i) as HTMLSelectElement
    fireEvent.change(typeSelect, { target: { value: 'SAXO' } })

    expect(screen.getByLabelText(/Client ID/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Client Secret/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Redirect URI/i)).toBeInTheDocument()
  })

  it('affiche les champs spécifiques Binance', () => {
    render(
      <BrokerForm
        account={null}
        brokers={mockBrokers}
        onSuccess={mockOnSuccess}
        onCancel={mockOnCancel}
      />
    )

    // Sélectionner Binance
    const typeSelect = screen.getByLabelText(/Type de Broker/i) as HTMLSelectElement
    fireEvent.change(typeSelect, { target: { value: 'BINANCE' } })

    expect(screen.getByLabelText(/API Key/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/API Secret/i)).toBeInTheDocument()
    expect(screen.getByText(/Utiliser le testnet Binance/i)).toBeInTheDocument()
  })

  it('valide les champs obligatoires', async () => {
    render(
      <BrokerForm
        account={null}
        brokers={mockBrokers}
        onSuccess={mockOnSuccess}
        onCancel={mockOnCancel}
      />
    )

    const submitButton = screen.getByText(/Créer/i)
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/Veuillez remplir tous les champs obligatoires/i)).toBeInTheDocument()
    })
  })

  it('soumet le formulaire avec les bonnes données', async () => {
    render(
      <BrokerForm
        account={null}
        brokers={mockBrokers}
        onSuccess={mockOnSuccess}
        onCancel={mockOnCancel}
      />
    )

    // Remplir le formulaire
    fireEvent.change(screen.getByLabelText(/Nom de la configuration/i), {
      target: { value: 'Mon compte Binance' },
    })
    fireEvent.change(screen.getByLabelText(/Type de Broker/i), {
      target: { value: 'BINANCE' },
    })
    fireEvent.change(screen.getByLabelText(/API Key/i), {
      target: { value: 'test-api-key' },
    })
    fireEvent.change(screen.getByLabelText(/API Secret/i), {
      target: { value: 'test-api-secret' },
    })

    const submitButton = screen.getByText(/Créer/i)
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(brokerService.createAccount).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Mon compte Binance',
          broker_type: 'BINANCE',
          binance_api_key: 'test-api-key',
          binance_api_secret: 'test-api-secret',
        })
      )
      expect(mockOnSuccess).toHaveBeenCalled()
    })
  })

  it('gère les erreurs de soumission', async () => {
    ;(brokerService.createAccount as jest.Mock).mockRejectedValue({
      error: 'Erreur de création',
    })

    render(
      <BrokerForm
        account={null}
        brokers={mockBrokers}
        onSuccess={mockOnSuccess}
        onCancel={mockOnCancel}
      />
    )

    fireEvent.change(screen.getByLabelText(/Nom de la configuration/i), {
      target: { value: 'Mon compte' },
    })
    fireEvent.change(screen.getByLabelText(/Type de Broker/i), {
      target: { value: 'BINANCE' },
    })

    const submitButton = screen.getByText(/Créer/i)
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/Erreur de création/i)).toBeInTheDocument()
    })
  })
})

