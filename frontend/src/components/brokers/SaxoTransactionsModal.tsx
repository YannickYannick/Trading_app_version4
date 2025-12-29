/**
 * Modal pour afficher les transactions Saxo
 */
import { useState, useEffect } from 'react'
import { brokerService } from '@services'
import Button from '@components/common/Button'
import Loading from '@components/common/Loading'
import Input from '@components/common/Input'
import type { BrokerAccount } from '@types'
import { formatDate } from '@utils/format'
import './SaxoTransactionsModal.css'

interface SaxoTransactionsModalProps {
  account: BrokerAccount
  onClose: () => void
}

export default function SaxoTransactionsModal({ account, onClose }: SaxoTransactionsModalProps) {
  const [loading, setLoading] = useState(false)
  const [transactions, setTransactions] = useState<any[]>([])
  const [error, setError] = useState<string | null>(null)
  // Dates par défaut : 30 derniers jours
  const getDefaultFromDate = () => {
    const date = new Date()
    date.setDate(date.getDate() - 30)
    return date.toISOString().split('T')[0]
  }

  const getDefaultToDate = () => {
    return new Date().toISOString().split('T')[0]
  }

  const [fromDate, setFromDate] = useState(getDefaultFromDate())
  const [toDate, setToDate] = useState(getDefaultToDate())
  const [limit, setLimit] = useState(1000)

  useEffect(() => {
    loadTransactions()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadTransactions = async () => {
    setLoading(true)
    setError(null)

    try {
      const result = await brokerService.getSaxoTransactions(account.id, {
        from_date: fromDate || getDefaultFromDate(),
        to_date: toDate || getDefaultToDate(),
        limit,
      })

      if (result.success) {
        setTransactions(result.transactions || [])
        if (result.transactions.length === 0) {
          setError('Aucune transaction trouvée')
        }
      } else {
        setError(result.error || 'Erreur lors de la récupération des transactions')
        setTransactions([])
      }
    } catch (err: any) {
      setError(err.message || 'Erreur lors de la récupération des transactions')
      setTransactions([])
    } finally {
      setLoading(false)
    }
  }

  const getTransactionTypeLabel = (txn: any) => {
    const txType = txn.TransactionType || ''
    const toOpenOrClose = txn.ToOpenOrClose || ''
    const fundingSubType = txn.FundingSubType || ''
    
    if (toOpenOrClose) {
      return `Position ${toOpenOrClose}`
    }
    if (fundingSubType) {
      return fundingSubType
    }
    return txType || 'Unknown'
  }

  return (
    <div className="saxo-transactions-modal">
      <div className="saxo-transactions-filters">
        <div className="saxo-transactions-filter-group">
          <label>Date de début:</label>
          <Input
            type="date"
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value)}
          />
        </div>
        <div className="saxo-transactions-filter-group">
          <label>Date de fin:</label>
          <Input
            type="date"
            value={toDate}
            onChange={(e) => setToDate(e.target.value)}
          />
        </div>
        <div className="saxo-transactions-filter-group">
          <label>Limite:</label>
          <Input
            type="number"
            value={limit}
            onChange={(e) => setLimit(parseInt(e.target.value) || 1000)}
            min={1}
            max={10000}
          />
        </div>
        <Button onClick={loadTransactions} disabled={loading} variant="primary">
          {loading ? <Loading size="sm" /> : 'Actualiser'}
        </Button>
      </div>

      {error && (
        <div className="saxo-transactions-error">
          <p>{error}</p>
        </div>
      )}

      {loading && transactions.length === 0 ? (
        <Loading text="Chargement des transactions..." />
      ) : transactions.length > 0 ? (
        <div className="saxo-transactions-content">
          <div className="saxo-transactions-header">
            <h3>{transactions.length} transaction(s) trouvée(s)</h3>
          </div>
          <div className="saxo-transactions-table-container">
            <table className="saxo-transactions-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Type</th>
                  <th>TradeId</th>
                  <th>UIC</th>
                  <th>Symbole</th>
                  <th>Quantité</th>
                  <th>Prix</th>
                  <th>Valeur</th>
                  <th>Détails</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((txn, index) => (
                  <tr key={index}>
                    <td>{txn.TradeDate ? formatDate(txn.TradeDate) : '-'}</td>
                    <td>
                      <span className="transaction-type-badge">
                        {getTransactionTypeLabel(txn)}
                      </span>
                    </td>
                    <td>{txn.TradeId || '-'}</td>
                    <td>{txn.Uic || '-'}</td>
                    <td>{txn.Symbol || '-'}</td>
                    <td>{txn.Amount ? parseFloat(txn.Amount).toFixed(2) : '-'}</td>
                    <td>{txn.Price ? parseFloat(txn.Price).toFixed(2) : '-'}</td>
                    <td>
                      {txn.AmountAccountValue
                        ? parseFloat(txn.AmountAccountValue).toFixed(2)
                        : '-'}
                    </td>
                    <td>
                      <details className="transaction-details">
                        <summary>Voir</summary>
                        <pre>{JSON.stringify(txn, null, 2)}</pre>
                      </details>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      <div className="saxo-transactions-actions">
        <Button onClick={onClose} variant="outline">
          Fermer
        </Button>
      </div>
    </div>
  )
}

