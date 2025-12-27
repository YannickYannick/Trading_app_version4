import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from '@components/layout/Layout'
import ProtectedRoute from '@routes/ProtectedRoute'
import Login from '@pages/Login'
import NotFound from '@pages/NotFound'
import Dashboard from '@pages/Dashboard'
import Positions from '@pages/Positions'
import Trades from '@pages/Trades'
import Assets from '@pages/Assets'

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
        {/* TODO: Ajouter PositionDetailPage */}
        {/* <Route path="positions/:id" element={<PositionDetailPage />} /> */}

        {/* Trades */}
        <Route path="trades" element={<Trades />} />
        {/* TODO: Ajouter TradeDetailPage */}
        {/* <Route path="trades/:id" element={<TradeDetailPage />} /> */}

        {/* Assets */}
        <Route path="assets" element={<Assets />} />
        {/* TODO: Ajouter AssetDetailPage */}
        {/* <Route path="assets/:id" element={<AssetDetailPage />} /> */}

        {/* Route 404 */}
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}

export default App

