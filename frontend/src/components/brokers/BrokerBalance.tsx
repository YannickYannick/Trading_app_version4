/**
 * Composant pour afficher le solde EUR d'un compte broker
 */
import { useBrokerBalance } from '@hooks/useBrokerBalance'
import Loading from '@components/common/Loading'
import Badge from '@components/common/Badge'
import Button from '@components/common/Button'
import './BrokerBalance.css'

interface BrokerBalanceProps {
  accountId: number
  showRefresh?: boolean
}

export default function BrokerBalance({ accountId, showRefresh = true }: BrokerBalanceProps) {
  const { balanceEur, allBalances, loading, error, refresh } = useBrokerBalance(accountId)

  return (
    <div className="broker-balance">
      <div className="broker-balance-main">
        <span className="broker-balance-label">Solde EUR:</span>
        {loading ? (
          <Loading size="sm" />
        ) : error ? (
          <Badge variant="danger" className="broker-balance-error">
            <span className="broker-balance-error-icon">⚠️</span>
            {error}
          </Badge>
        ) : (
          <Badge variant="success" className="broker-balance-amount">
            {balanceEur !== null ? `${balanceEur.toFixed(2)} €` : 'N/A'}
          </Badge>
        )}
        {showRefresh && (
          <Button
            size="sm"
            variant="outline"
            onClick={refresh}
            disabled={loading}
            className="broker-balance-refresh"
            title="Rafraîchir le solde"
          >
            🔄
          </Button>
        )}
      </div>

      {/* Afficher les autres devises si disponibles */}
      {allBalances && Object.keys(allBalances).length > 1 && (
        <details className="broker-balance-details">
          <summary className="broker-balance-details-summary">
            💰 Autres devises ({Object.keys(allBalances).length})
          </summary>
          <ul className="broker-balance-details-list">
            {Object.entries(allBalances)
              .filter(([currency]) => currency !== 'EUR' && allBalances[currency] > 0)
              .map(([currency, amount]) => (
                <li key={currency} className="broker-balance-details-item">
                  <span>{currency}:</span>
                  <strong>{amount.toFixed(2)}</strong>
                </li>
              ))}
          </ul>
        </details>
      )}
    </div>
  )
}

