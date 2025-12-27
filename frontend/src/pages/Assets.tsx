import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, Asset } from '../services/api'

export default function Assets() {
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    const fetchAssets = async () => {
      try {
        const data = await api.getAssets(search)
        setAssets(data)
      } catch (error) {
        console.error('Error fetching assets:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchAssets()
  }, [search])

  return (
    <div className="page">
      <header>
        <Link to="/">← Retour</Link>
        <h1>Assets</h1>
      </header>

      <div className="search-bar">
        <input
          type="text"
          placeholder="Rechercher un asset..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <main>
        {loading ? (
          <p>Chargement...</p>
        ) : assets.length > 0 ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Nom</th>
                <th>Type</th>
                <th>Prix actuel</th>
                <th>Devise</th>
                <th>Exchange</th>
              </tr>
            </thead>
            <tbody>
              {assets.map((asset) => (
                <tr key={asset.id}>
                  <td><strong>{asset.symbol}</strong></td>
                  <td>{asset.name}</td>
                  <td>{asset.asset_type}</td>
                  <td>{asset.current_price || '-'}</td>
                  <td>{asset.currency}</td>
                  <td>{asset.exchange || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>Aucun asset trouvé</p>
        )}
      </main>
    </div>
  )
}

