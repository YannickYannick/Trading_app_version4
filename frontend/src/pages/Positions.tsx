import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, Position } from '../services/api'

export default function Positions() {
  const [positions, setPositions] = useState<Position[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchPositions = async () => {
      try {
        const data = await api.getOpenPositions()
        setPositions(data)
      } catch (error) {
        console.error('Error fetching positions:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchPositions()
  }, [])

  return (
    <div className="page">
      <header>
        <Link to="/">← Retour</Link>
        <h1>Positions</h1>
      </header>

      <main>
        {loading ? (
          <p>Chargement...</p>
        ) : positions.length > 0 ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>Asset</th>
                <th>Side</th>
                <th>Quantité</th>
                <th>Prix d'entrée</th>
                <th>Prix actuel</th>
                <th>P&L</th>
                <th>P&L %</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((position) => (
                <tr key={position.id}>
                  <td>{position.asset_symbol}</td>
                  <td className={position.side.toLowerCase()}>{position.side}</td>
                  <td>{position.quantity}</td>
                  <td>{position.entry_price}</td>
                  <td>{position.current_price || '-'}</td>
                  <td className={position.pnl >= 0 ? 'positive' : 'negative'}>
                    {position.pnl?.toFixed(2) || '-'}
                  </td>
                  <td className={position.pnl_percent >= 0 ? 'positive' : 'negative'}>
                    {position.pnl_percent?.toFixed(2) || '-'}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>Aucune position ouverte</p>
        )}
      </main>
    </div>
  )
}

