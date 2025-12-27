/**
 * Formulaire de création/modification de broker
 */
import { useState, useEffect } from 'react'
import Button from '@components/common/Button'
import Input from '@components/common/Input'
import Loading from '@components/common/Loading'
import { brokerService } from '@services'
import type { Broker, BrokerAccount, BrokerAccountCreateData } from '@types'
import './BrokerForm.css'

interface BrokerFormProps {
  account: BrokerAccount | null
  brokers: Broker[]
  onSuccess: () => void
  onCancel: () => void
}

export default function BrokerForm({ account, brokers, onSuccess, onCancel }: BrokerFormProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [formData, setFormData] = useState<BrokerAccountCreateData>({
    name: account?.name || '',
    broker: account?.broker?.id || brokers[0]?.id || null,
    broker_type: account?.broker_type || 'SAXO',
    account_id: account?.account_id || '',
    environment: account?.environment || 'simulation',
    
    // Credentials Saxo
    saxo_client_id: account?.saxo_client_id || '',
    saxo_client_secret: account?.saxo_client_secret || '',
    saxo_redirect_uri: account?.saxo_redirect_uri || '',
    saxo_environment: account?.saxo_environment || 'simulation',
    
    // Credentials Binance
    binance_api_key: account?.binance_api_key || '',
    binance_api_secret: account?.binance_api_secret || '',
    binance_testnet: account?.binance_testnet || false,
    
    // Auto-refresh
    auto_refresh_enabled: account?.auto_refresh_enabled ?? true,
    auto_refresh_frequency: account?.auto_refresh_frequency || 45,
    
    // Statut
    is_active: account?.is_active ?? true,
    is_sandbox: account?.is_sandbox ?? true,
  })
  const [showSecrets, setShowSecrets] = useState(false)
  const [selectedBrokerType, setSelectedBrokerType] = useState<'SAXO' | 'BINANCE' | 'IB' | 'OTHER'>(
    account?.broker_type || 'SAXO'
  )

  // Filtrer les brokers par type
  const availableBrokers = brokers.filter((b) => b.broker_type === selectedBrokerType)

  useEffect(() => {
    // Mettre à jour le broker_type quand on change le type sélectionné
    setFormData((prev) => ({ ...prev, broker_type: selectedBrokerType }))
    
    // Si des brokers sont disponibles, sélectionner le premier
    if (availableBrokers.length > 0 && !formData.broker) {
      setFormData((prev) => ({ ...prev, broker: availableBrokers[0].id }))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedBrokerType])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      if (account) {
        // Mise à jour
        await brokerService.updateAccount(account.id, formData)
      } else {
        // Création
        // Le broker est optionnel maintenant, on utilise broker_type directement
        if (!formData.name || !formData.broker_type) {
          throw new Error('Veuillez remplir tous les champs obligatoires')
        }
        await brokerService.createAccount(formData)
      }
      onSuccess()
    } catch (err: any) {
      setError(err.error || err.message || 'Erreur lors de la sauvegarde')
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (field: keyof BrokerAccountCreateData, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  return (
    <form onSubmit={handleSubmit} className="broker-form">
      {error && <div className="broker-form-error">{error}</div>}

      {/* Type de broker */}
      <div className="broker-form-section">
        <label className="broker-form-label">Type de Broker</label>
        <select
          value={selectedBrokerType}
          onChange={(e) => setSelectedBrokerType(e.target.value as any)}
          className="broker-form-select"
          disabled={!!account}
        >
          <option value="SAXO">Saxo Bank</option>
          <option value="BINANCE">Binance</option>
          <option value="IB">Interactive Brokers</option>
          <option value="OTHER">Autre</option>
        </select>
      </div>

      {/* Broker */}
      <div className="broker-form-section">
        <label className="broker-form-label">Broker</label>
        {availableBrokers.length > 0 ? (
          <select
            value={formData.broker || ''}
            onChange={(e) => handleChange('broker', parseInt(e.target.value))}
            className="broker-form-select"
            required
          >
            <option value="">-- Sélectionner un broker --</option>
            {availableBrokers.map((broker) => (
              <option key={broker.id} value={broker.id}>
                {broker.name}
              </option>
            ))}
          </select>
        ) : (
          <div className="broker-form-warning">
            <p>
              ⚠️ Aucun broker de type <strong>{selectedBrokerType}</strong> n'est disponible.
            </p>
            <p className="broker-form-warning-hint">
              Veuillez créer un broker de ce type dans l'administration Django avant de créer un compte.
            </p>
          </div>
        )}
      </div>

      {/* Nom de la configuration */}
      <Input
        label="Nom de la configuration"
        value={formData.name}
        onChange={(e) => handleChange('name', e.target.value)}
        required
        fullWidth
        placeholder="ex: Mon compte Saxo principal"
      />

      {/* Account ID (optionnel) */}
      <Input
        label="ID du compte (optionnel)"
        value={formData.account_id || ''}
        onChange={(e) => handleChange('account_id', e.target.value)}
        fullWidth
        placeholder="ID du compte chez le broker"
      />
      
      {/* Environnement */}
      <div className="broker-form-section">
        <label className="broker-form-label">Environnement</label>
        <select
          value={formData.environment || 'simulation'}
          onChange={(e) => handleChange('environment', e.target.value)}
          className="broker-form-select"
        >
          <option value="simulation">Simulation/Demo</option>
          <option value="live">Live Trading</option>
        </select>
      </div>

      {/* Auto-refresh (pour Saxo) */}
      {selectedBrokerType === 'SAXO' && (
        <>
          <div className="broker-form-section">
            <label className="broker-form-checkbox">
              <input
                type="checkbox"
                checked={formData.auto_refresh_enabled ?? true}
                onChange={(e) => handleChange('auto_refresh_enabled', e.target.checked)}
              />
              <span>Auto-refresh activé</span>
            </label>
          </div>
          {formData.auto_refresh_enabled && (
            <Input
              label="Fréquence auto-refresh (minutes)"
              type="number"
              value={formData.auto_refresh_frequency || 45}
              onChange={(e) => handleChange('auto_refresh_frequency', parseInt(e.target.value))}
              min={15}
              max={55}
              fullWidth
            />
          )}
        </>
      )}

      {/* Credentials selon le type */}
      {selectedBrokerType === 'SAXO' && (
        <>
          <Input
            label="Client ID"
            type="text"
            value={formData.saxo_client_id || ''}
            onChange={(e) => handleChange('saxo_client_id', e.target.value)}
            fullWidth
          />
          <Input
            label="Client Secret"
            type={showSecrets ? 'text' : 'password'}
            value={formData.saxo_client_secret || ''}
            onChange={(e) => handleChange('saxo_client_secret', e.target.value)}
            fullWidth
          />
          <Input
            label="Redirect URI"
            type="url"
            value={formData.saxo_redirect_uri || ''}
            onChange={(e) => handleChange('saxo_redirect_uri', e.target.value)}
            fullWidth
            placeholder="ex: http://localhost:8080/callback"
          />
          <div className="broker-form-section">
            <label className="broker-form-label">Environnement Saxo</label>
            <select
              value={formData.saxo_environment || 'simulation'}
              onChange={(e) => handleChange('saxo_environment', e.target.value)}
              className="broker-form-select"
            >
              <option value="simulation">Simulation</option>
              <option value="live">Live</option>
            </select>
          </div>
        </>
      )}

      {selectedBrokerType === 'BINANCE' && (
        <>
          <Input
            label="API Key"
            type="text"
            value={formData.binance_api_key || ''}
            onChange={(e) => handleChange('binance_api_key', e.target.value)}
            fullWidth
          />
          <Input
            label="API Secret"
            type={showSecrets ? 'text' : 'password'}
            value={formData.binance_api_secret || ''}
            onChange={(e) => handleChange('binance_api_secret', e.target.value)}
            fullWidth
          />
          <div className="broker-form-section">
            <label className="broker-form-checkbox">
              <input
                type="checkbox"
                checked={formData.binance_testnet ?? false}
                onChange={(e) => handleChange('binance_testnet', e.target.checked)}
              />
              <span>Utiliser le testnet Binance</span>
            </label>
          </div>
        </>
      )}

      {/* Afficher/Masquer les secrets */}
      <div className="broker-form-section">
        <label className="broker-form-checkbox">
          <input
            type="checkbox"
            checked={showSecrets}
            onChange={(e) => setShowSecrets(e.target.checked)}
          />
          <span>Afficher les credentials</span>
        </label>
      </div>

      {/* Actions */}
      <div className="broker-form-actions">
        <Button type="submit" variant="primary" disabled={loading} fullWidth>
          {loading ? <Loading size="sm" /> : account ? 'Modifier' : 'Créer'}
        </Button>
        <Button type="button" variant="outline" onClick={onCancel} fullWidth>
          Annuler
        </Button>
      </div>
    </form>
  )
}
