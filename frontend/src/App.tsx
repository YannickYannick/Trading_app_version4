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
import Orders from '@pages/Orders'
import Strategies from '@pages/Strategies'
import StrategiesV2 from '@pages/StrategiesV2'
import StrategiesV3 from '@pages/StrategiesV3'
import StrategiesV4 from '@pages/StrategiesV4'
import StrategiesV5 from '@pages/StrategiesV5'
import Brokers from '@pages/Brokers'
import Settings from '@pages/Settings'
import AIAdvisor from '@pages/AIAdvisor'
import Blog from '@pages/Blog'
import BlogArticle from '@pages/BlogArticle'

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

        {/* Orders */}
        <Route path="orders" element={<Orders />} />

        {/* Strategies */}
        <Route path="strategies" element={<Strategies />} />
        <Route path="strategies-v2" element={<StrategiesV2 />} />
        <Route path="strategies-v3" element={<StrategiesV3 />} />
        <Route path="strategies-v4" element={<StrategiesV4 />} />
        <Route path="strategies-v5" element={<StrategiesV5 />} />

        {/* Brokers */}
        <Route path="brokers" element={<Brokers />} />

        {/* Settings */}
        <Route path="settings" element={<Settings />} />

        {/* AI Advisor */}
        <Route path="ai-advisor" element={<AIAdvisor />} />

        {/* Blog */}
        <Route path="blog" element={<Blog />} />
        <Route path="blog/:slug" element={<BlogArticle />} />

        {/* Route 404 */}
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}

export default App

