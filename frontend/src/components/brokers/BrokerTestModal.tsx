/**
 * Modal de test de connexion broker
 */
import { useState } from 'react'
import Button from '@components/common/Button'
import Loading from '@components/common/Loading'
import Badge from '@components/common/Badge'
import { brokerService } from '@services'
import type { BrokerAccount } from '@types'
import './BrokerTestModal.css'

interface BrokerTestModalProps {
  account: BrokerAccount
  onClose: () => void
}

export default function BrokerTestModal({ account, onClose }: BrokerTestModalProps) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{
    success: boolean
    message: string
    error?: string
    details?: any
  } | null>(null)

  const handleTest = async () => {
    setLoading(true)
    setResult(null)

    try {
      const response = await brokerService.testConnection(account.id)
      setResult(response)
    } catch (err: any) {
      setResult({
        success: false,
        message: err.error || err.message || 'Erreur lors du test',
        error: err.error || err.message,
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="broker-test-modal">
      <div className="broker-test-info">
        <p>
          <strong>Broker:</strong> {account.broker_name || account.broker?.name || account.broker_type_display || account.broker_type || 'N/A'}
        </p>
        <p>
          <strong>Compte:</strong> {account.name}
        </p>
      </div>

      <div className="broker-test-actions">
        <Button onClick={handleTest} disabled={loading} variant="primary" fullWidth>
          {loading ? <Loading size="sm" /> : 'Tester la connexion'}
        </Button>
      </div>

      {result && (
        <div className={`broker-test-result ${result.success ? 'success' : 'error'}`}>
          <div className="broker-test-result-header">
            <Badge variant={result.success ? 'success' : 'danger'}>
              {result.success ? 'Succès' : 'Échec'}
            </Badge>
            <p className="broker-test-message">{result.message}</p>
          </div>
          {result.error && (
            <div className="broker-test-error">
              <strong>Erreur:</strong> {result.error}
            </div>
          )}
          {result.details && (
            <div className="broker-test-details">
              <strong>Détails:</strong>
              <pre>{JSON.stringify(result.details, null, 2)}</pre>
            </div>
          )}
        </div>
      )}

      <div className="broker-test-actions">
        <Button onClick={onClose} variant="outline" fullWidth>
          Fermer
        </Button>
      </div>
    </div>
  )
}

