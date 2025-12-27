import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'

interface PositionSummary {
  total_positions: number
  total_value: number
  total_pnl: number
}

export default function Dashboard() {
  const [summary, setSummary] = useState<PositionSummary | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const data = await api.getPositionSummary()
        setSummary(data)
      } catch (error) {
        console.error('Error fetching summary:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchSummary()
  }, [])

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Trading Dashboard</h1>
        <nav>
          <Link to="/positions">Positions</Link>
          <Link to="/trades">Trades</Link>
          <Link to="/assets">Assets</Link>
        </nav>
      </header>

      <main className="dashboard-content">
        {loading ? (
          <p>Chargement...</p>
        ) : summary ? (
          <div className="summary-cards">
            <div className="card">
              <h3>Positions ouvertes</h3>
              <p className="value">{summary.total_positions}</p>
            </div>
            <div className="card">
              <h3>Valeur totale</h3>
              <p className="value">{summary.total_value?.toFixed(2)} €</p>
            </div>
            <div className="card">
              <h3>P&L Total</h3>
              <p className={`value ${summary.total_pnl >= 0 ? 'positive' : 'negative'}`}>
                {summary.total_pnl?.toFixed(2)} €
              </p>
            </div>
          </div>
        ) : (
          <p>Aucune donnée disponible</p>
        )}
      </main>
    </div>
  )
}

