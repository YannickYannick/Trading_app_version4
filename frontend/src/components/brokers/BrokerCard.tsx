/**
 * Composant Card pour afficher un compte broker
 */
import { useState } from 'react'
import Card from '@components/common/Card'
import Button from '@components/common/Button'
import Badge from '@components/common/Badge'
import Loading from '@components/common/Loading'
import { formatDate } from '@utils/format'
import type { BrokerAccount } from '@types'
import './BrokerCard.css'

export interface BrokerCardProps {
  account: BrokerAccount
  onTest: (id: number) => Promise<void>
  onSync: (id: number, syncType: 'ASSETS' | 'PRICES' | 'POSITIONS' | 'TRADES') => Promise<void>
  onEdit: (account: BrokerAccount) => void
  onDelete: (id: number) => Promise<void>
  isTestLoading?: boolean
  isSyncLoading?: boolean
}

export default function BrokerCard({
  account,
  onTest,
  onSync,
  onEdit,
  onDelete,
  isTestLoading = false,
  isSyncLoading = false,
}: BrokerCardProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [syncType, setSyncType] = useState<'ASSETS' | 'PRICES' | 'POSITIONS' | 'TRADES'>('POSITIONS')

  const handleDelete = async () => {
    try {
      await onDelete(account.id)
      setShowDeleteConfirm(false)
    } catch (err) {
      console.error('Erreur lors de la suppression:', err)
    }
  }

  return (
    <Card className="broker-card" hover>
      <div className="broker-card-header">
        <div>
          <h3 className="broker-card-title">{account.account_name}</h3>
          <div className="broker-card-badges">
            <Badge variant="primary">{account.broker.broker_type}</Badge>
            <Badge variant={account.is_active ? 'success' : 'secondary'}>
              {account.is_active ? 'Actif' : 'Inactif'}
            </Badge>
            {account.is_sandbox && (
              <Badge variant="warning">Simulation</Badge>
            )}
          </div>
        </div>
      </div>

      <div className="broker-card-body">
        <div className="broker-card-info">
          <p>
            <strong>ID Compte:</strong> {account.account_id}
          </p>
          {account.last_sync && (
            <p>
              <strong>Dernière sync:</strong> {formatDate(account.last_sync)}
            </p>
          )}
        </div>

        <div className="broker-card-actions">
          <div className="broker-card-actions-row">
            <Button
              size="sm"
              variant="primary"
              onClick={() => onTest(account.id)}
              disabled={isTestLoading}
            >
              {isTestLoading ? <Loading size="sm" /> : 'Tester'}
            </Button>
            
            <div className="broker-card-sync-group">
              <select
                className="broker-card-sync-select"
                value={syncType}
                onChange={(e) => setSyncType(e.target.value as any)}
                disabled={isSyncLoading}
              >
                <option value="ASSETS">Assets</option>
                <option value="PRICES">Prix</option>
                <option value="POSITIONS">Positions</option>
                <option value="TRADES">Trades</option>
              </select>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => onSync(account.id, syncType)}
                disabled={isSyncLoading}
              >
                {isSyncLoading ? <Loading size="sm" /> : 'Sync'}
              </Button>
            </div>
          </div>

          <div className="broker-card-actions-row">
            <Button
              size="sm"
              variant="outline"
              onClick={() => onEdit(account)}
            >
              Modifier
            </Button>
            
            {showDeleteConfirm ? (
              <div className="broker-card-delete-confirm">
                <span>Confirmer?</span>
                <Button
                  size="sm"
                  variant="danger"
                  onClick={handleDelete}
                >
                  Oui
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setShowDeleteConfirm(false)}
                >
                  Non
                </Button>
              </div>
            ) : (
              <Button
                size="sm"
                variant="danger"
                onClick={() => setShowDeleteConfirm(true)}
              >
                Supprimer
              </Button>
            )}
          </div>
        </div>
      </div>
    </Card>
  )
}

