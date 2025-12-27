import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, Trade } from '../services/api'

export default function Trades() {
  const [trades, setTrades] = useState<Trade[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchTrades = async () => {
      try {
        const data = await api.getRecentTrades()
        setTrades(data)
      } catch (error) {
        console.error('Error fetching trades:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchTrades()
  }, [])

  return (
    <div className="page">
      <header>
        <Link to="/">← Retour</Link>
        <h1>Trades récents</h1>
      </header>

      <main>
        {loading ? (
          <p>Chargement...</p>
        ) : trades.length > 0 ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Asset</th>
                <th>Type</th>
                <th>Quantité</th>
                <th>Prix</th>
                <th>Total</th>
                <th>Frais</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade) => (
                <tr key={trade.id}>
                  <td>{new Date(trade.executed_at).toLocaleString()}</td>
                  <td>{trade.asset_symbol}</td>
                  <td className={trade.trade_type.toLowerCase()}>{trade.trade_type}</td>
                  <td>{trade.quantity}</td>
                  <td>{trade.price}</td>
                  <td>{trade.total_value?.toFixed(2)}</td>
                  <td>{trade.fees}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>Aucun trade récent</p>
        )}
      </main>
    </div>
  )
}

