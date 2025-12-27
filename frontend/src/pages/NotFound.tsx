/**
 * Page 404 - Page non trouvée
 */
import { Link } from 'react-router-dom'
import { Button, Card } from '@components/common'
import './NotFound.css'

export default function NotFound() {
  return (
    <div className="not-found-page">
      <Card className="not-found-card">
        <div className="not-found-content">
          <h1 className="not-found-code">404</h1>
          <h2 className="not-found-title">Page non trouvée</h2>
          <p className="not-found-message">
            La page que vous recherchez n'existe pas ou a été déplacée.
          </p>
          <div className="not-found-actions">
            <Link to="/">
              <Button variant="primary">Retour au Dashboard</Button>
            </Link>
            <Link to="/positions">
              <Button variant="outline">Voir les Positions</Button>
            </Link>
          </div>
        </div>
      </Card>
    </div>
  )
}

