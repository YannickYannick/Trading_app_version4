/**
 * Header de l'application
 */
import { Link } from 'react-router-dom'
import './Header.css'

function Header() {
  return (
    <header className="header">
      <div className="header-content">
        <Link to="/" className="header-logo">
          Trading App
        </Link>
        <nav className="header-nav">
          <Link to="/" className="header-nav-link">
            Dashboard
          </Link>
          <Link to="/positions" className="header-nav-link">
            Positions
          </Link>
          <Link to="/trades" className="header-nav-link">
            Trades
          </Link>
          <Link to="/assets" className="header-nav-link">
            Assets
          </Link>
        </nav>
      </div>
    </header>
  )
}

export default Header

