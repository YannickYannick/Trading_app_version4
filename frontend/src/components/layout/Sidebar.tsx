/**
 * Sidebar de navigation
 */
import { NavLink, useNavigate } from 'react-router-dom'
import { authService } from '@services'
import './Sidebar.css'

function Sidebar() {
  const navigate = useNavigate()

  const menuItems = [
    { path: '/', label: 'Dashboard', icon: '📊' },
    { path: '/positions', label: 'Positions', icon: '💼' },
    { path: '/trades', label: 'Trades', icon: '📈' },
    { path: '/orders', label: 'Ordres', icon: '📋' },
    { path: '/strategies', label: 'Stratégies', icon: '🎯' },
    { path: '/strategies-v2', label: 'Stratégies V2', icon: '✨' },
    { path: '/assets', label: 'Assets', icon: '💰' },
    { path: '/brokers', label: 'Brokers', icon: '🏦' },
    { path: '/blog', label: 'Blog', icon: '📰' },
    { path: '/settings', label: 'Paramètres', icon: '⚙️' },
  ]

  const handleLogout = async () => {
    try {
      await authService.logout()
      navigate('/login')
    } catch (error) {
      console.error('Erreur lors de la déconnexion:', error)
      // Rediriger quand même vers login
      navigate('/login')
    }
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2 className="sidebar-title">Trading</h2>
      </div>
      <nav className="sidebar-nav">
        {menuItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? 'active' : ''}`
            }
            end={item.path === '/'}
          >
            <span className="sidebar-icon">{item.icon}</span>
            <span className="sidebar-label">{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-footer">
        <button className="sidebar-logout" onClick={handleLogout}>
          <span className="sidebar-icon">🚪</span>
          <span className="sidebar-label">Déconnexion</span>
        </button>
      </div>
    </aside>
  )
}

export default Sidebar

