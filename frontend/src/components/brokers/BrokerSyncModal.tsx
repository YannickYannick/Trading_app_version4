/**
 * Modal de synchronisation broker
 */
import { useState } from 'react'
import Button from '@components/common/Button'
import Loading from '@components/common/Loading'
import Badge from '@components/common/Badge'
import { brokerService } from '@services'
import { formatDate } from '@utils/format'
import type { BrokerAccount, BrokerSyncLog } from '@types'
import './BrokerSyncModal.css'

interface BrokerSyncModalProps {
  account: BrokerAccount
  onSuccess: () => void
  onClose: () => void
}

type SyncType = 'ASSETS' | 'PRICES' | 'POSITIONS' | 'TRADES'

export default function BrokerSyncModal({ account, onSuccess, onClose }: BrokerSyncModalProps) {
  const [loading, setLoading] = useState(false)
  const [syncType, setSyncType] = useState<SyncType>('ASSETS')
  const [result, setResult] = useState<BrokerSyncLog | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSync = async () => {
    setLoading(true)
    setResult(null)
    setError(null)

    try {
      const response = await brokerService.sync(account.id, {
        sync_type: syncType,
        force: false,
      })
      setResult(response)
      onSuccess()
    } catch (err: any) {
      setError(err.error || err.message || 'Erreur lors de la synchronisation')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="broker-sync-modal">
      <div className="broker-sync-info">
        <p>
          <strong>Broker:</strong> {account.broker.name}
        </p>
        <p>
          <strong>Compte:</strong> {account.account_name}
        </p>
      </div>

      <div className="broker-sync-type">
        <label className="broker-sync-label">Type de synchronisation</label>
        <select
          value={syncType}
          onChange={(e) => setSyncType(e.target.value as SyncType)}
          className="broker-sync-select"
          disabled={loading}
        >
          <option value="ASSETS">Assets (Tous les types - AllAssets)</option>
          <option value="PRICES">Prix</option>
          <option value="POSITIONS">Positions</option>
          <option value="TRADES">Trades</option>
        </select>
        <p className="broker-sync-description">
          {syncType === 'ASSETS' && 'Récupère la liste complète de tous les actifs tradables (Stocks, ETF, FX, CFD, Crypto) et les synchronise dans AllAssets'}
          {syncType === 'PRICES' && 'Met à jour les prix actuels des actifs'}
          {syncType === 'POSITIONS' && 'Récupère toutes les positions ouvertes'}
          {syncType === 'TRADES' && "Récupère l'historique des transactions"}
        </p>
      </div>

      <div className="broker-sync-actions">
        <Button onClick={handleSync} disabled={loading} variant="primary" fullWidth>
          {loading ? <Loading size="sm" /> : 'Lancer la synchronisation'}
        </Button>
      </div>

      {error && (
        <div className="broker-sync-error">
          <Badge variant="danger">Erreur</Badge>
          <p>{error}</p>
        </div>
      )}

      {result && (
        <div className="broker-sync-result">
          <div className="broker-sync-result-header">
            <Badge variant={result.status === 'SUCCESS' ? 'success' : 'danger'}>
              {result.status}
            </Badge>
            <p className="broker-sync-message">
              {result.status === 'SUCCESS'
                ? 'Synchronisation terminée avec succès'
                : 'Synchronisation échouée'}
            </p>
          </div>
          <div className="broker-sync-stats">
            <div className="broker-sync-stat">
              <span className="broker-sync-stat-label">Éléments synchronisés:</span>
              <span className="broker-sync-stat-value">{result.records_synced}</span>
            </div>
            {result.completed_at && (
              <div className="broker-sync-stat">
                <span className="broker-sync-stat-label">Terminé le:</span>
                <span className="broker-sync-stat-value">
                  {formatDate(result.completed_at)}
                </span>
              </div>
            )}
          </div>
          {result.error_message && (
            <div className="broker-sync-error-message">
              <strong>Erreur:</strong> {result.error_message}
            </div>
          )}
        </div>
      )}

      <div className="broker-sync-actions">
        <Button onClick={onClose} variant="outline" fullWidth>
          Fermer
        </Button>
      </div>
    </div>
  )
}

