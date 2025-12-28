/**
 * Modal pour synchroniser les assets depuis les brokers
 */
import { useState, useEffect } from 'react'
import Button from '@components/common/Button'
import Loading from '@components/common/Loading'
import Badge from '@components/common/Badge'
import Modal from '@components/common/Modal'
import { brokerService } from '@services'
import { formatDate } from '@utils/format'
import type { BrokerAccount } from '@types'
import './SyncAssetsModal.css'

interface SyncAssetsModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess?: () => void
}

export default function SyncAssetsModal({ isOpen, onClose, onSuccess }: SyncAssetsModalProps) {
  const [accounts, setAccounts] = useState<BrokerAccount[]>([])
  const [loading, setLoading] = useState(false)
  const [loadingAccounts, setLoadingAccounts] = useState(true)
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen) {
      loadAccounts()
    }
  }, [isOpen])

  const loadAccounts = async () => {
    setLoadingAccounts(true)
    try {
      const accountsList = await brokerService.getAccounts()
      // Filtrer seulement les comptes actifs
      const activeAccounts = accountsList.filter(acc => acc.is_active)
      setAccounts(activeAccounts)
      if (activeAccounts.length > 0 && !selectedAccountId) {
        setSelectedAccountId(activeAccounts[0].id)
      }
    } catch (err: any) {
      setError(err.error || err.message || 'Erreur lors du chargement des comptes')
    } finally {
      setLoadingAccounts(false)
    }
  }

  const handleSync = async () => {
    if (!selectedAccountId) return

    setLoading(true)
    setResult(null)
    setError(null)

    try {
      const response = await brokerService.sync(selectedAccountId, {
        sync_type: 'ASSETS',
        force: false,
      })
      setResult(response)
      if (onSuccess) {
        onSuccess()
      }
    } catch (err: any) {
      setError(err.error || err.message || 'Erreur lors de la synchronisation')
    } finally {
      setLoading(false)
    }
  }

  const selectedAccount = accounts.find(acc => acc.id === selectedAccountId)

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Synchroniser AllAssets depuis un broker">
      <div className="sync-assets-modal">
        {loadingAccounts ? (
          <Loading text="Chargement des comptes..." />
        ) : accounts.length === 0 ? (
          <div className="sync-assets-no-accounts">
            <p>Aucun compte broker actif disponible.</p>
            <p className="sync-assets-hint">
              Créez un compte broker depuis la page Brokers pour pouvoir synchroniser les assets.
            </p>
          </div>
        ) : (
          <>
            <div className="sync-assets-account-selection">
              <label className="sync-assets-label">Compte broker</label>
              <select
                value={selectedAccountId || ''}
                onChange={(e) => setSelectedAccountId(Number(e.target.value))}
                className="sync-assets-select"
                disabled={loading}
              >
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.name || account.account_name || account.broker_name} - {account.broker_type_display || account.broker_type}
                  </option>
                ))}
              </select>
              {selectedAccount && (
                <div className="sync-assets-account-info">
                  <p>
                    <strong>Type:</strong> {selectedAccount.broker_type_display || selectedAccount.broker_type}
                  </p>
                  <p>
                    <strong>Environnement:</strong> {selectedAccount.environment_display || selectedAccount.environment}
                  </p>
                </div>
              )}
            </div>

            <div className="sync-assets-description">
              <p>
                Cette synchronisation va récupérer <strong>tous les types d'assets</strong> (Stocks, ETF, FX, CFD, Crypto)
                depuis le broker sélectionné et les enregistrer dans le catalogue <strong>AllAssets</strong>.
              </p>
              <p className="sync-assets-warning">
                ⚠️ Cette opération peut prendre quelques minutes selon le nombre d'assets disponibles.
              </p>
            </div>

            <div className="sync-assets-actions">
              <Button
                onClick={handleSync}
                disabled={loading || !selectedAccountId}
                variant="primary"
                fullWidth
              >
                {loading ? <Loading size="sm" /> : 'Lancer la synchronisation AllAssets'}
              </Button>
            </div>

            {error && (
              <div className="sync-assets-error">
                <Badge variant="danger">Erreur</Badge>
                <p>{error}</p>
              </div>
            )}

            {result && (
              <div className="sync-assets-result">
                <div className="sync-assets-result-header">
                  <Badge variant={result.success ? 'success' : 'danger'}>
                    {result.success ? 'SUCCESS' : 'ECHEC'}
                  </Badge>
                  <p className="sync-assets-message">{result.message}</p>
                </div>
                {result.details && (
                  <div className="sync-assets-details">
                    {result.details.total_created && (
                      <div className="sync-assets-stat">
                        <span className="sync-assets-stat-label">Créés:</span>
                        <span className="sync-assets-stat-value">{result.details.total_created}</span>
                      </div>
                    )}
                    {result.details.total_updated && (
                      <div className="sync-assets-stat">
                        <span className="sync-assets-stat-label">Mis à jour:</span>
                        <span className="sync-assets-stat-value">{result.details.total_updated}</span>
                      </div>
                    )}
                    {result.details.by_type && (
                      <div className="sync-assets-by-type">
                        <strong>Par type:</strong>
                        {Object.entries(result.details.by_type).map(([type, data]: [string, any]) => (
                          <div key={type} className="sync-assets-type-stat">
                            {type}: {data.created || 0} créés, {data.updated || 0} mis à jour
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </>
        )}

        <div className="sync-assets-actions">
          <Button onClick={onClose} variant="outline" fullWidth>
            Fermer
          </Button>
        </div>
      </div>
    </Modal>
  )
}

