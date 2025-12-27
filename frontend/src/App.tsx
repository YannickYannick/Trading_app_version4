import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from '@components/layout/Layout'
import ProtectedRoute from '@routes/ProtectedRoute'
import Login from '@pages/Login'
import NotFound from '@pages/NotFound'
import Dashboard from '@pages/Dashboard'
import Positions from '@pages/Positions'
import PositionDetail from '@pages/PositionDetail'
import Trades from '@pages/Trades'
import TradeDetail from '@pages/TradeDetail'
import Assets from '@pages/Assets'
import AssetDetail from '@pages/AssetDetail'
import Brokers from '@pages/Brokers'
import Settings from '@pages/Settings'

function App() {
  return (
    <Routes>
      {/* Route publique : Login */}
      <Route path="/login" element={<Login />} />

      {/* Routes protégées avec Layout */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        {/* Route par défaut : Dashboard */}
        <Route index element={<Dashboard />} />

        {/* Dashboard */}
        <Route path="dashboard" element={<Navigate to="/" replace />} />

        {/* Positions */}
        <Route path="positions" element={<Positions />} />
        <Route path="positions/:id" element={<PositionDetail />} />

        {/* Trades */}
        <Route path="trades" element={<Trades />} />
        <Route path="trades/:id" element={<TradeDetail />} />

        {/* Assets */}
        <Route path="assets" element={<Assets />} />
        <Route path="assets/:id" element={<AssetDetail />} />

        {/* Brokers */}
        <Route path="brokers" element={<Brokers />} />

        {/* Settings */}
        <Route path="settings" element={<Settings />} />

        {/* Route 404 */}
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}

export default App

