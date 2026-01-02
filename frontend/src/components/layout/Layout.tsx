/**
 * Layout principal de l'application
 */
import { Outlet } from 'react-router-dom'
import Header from './Header'
import Sidebar from './Sidebar'
import './Layout.css'

function Layout() {
  return (
    <div className="layout">
      <Sidebar />
      <div className="layout-content">
        <main className="layout-main">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default Layout

