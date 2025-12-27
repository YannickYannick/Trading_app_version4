import { Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Positions from './pages/Positions'
import Trades from './pages/Trades'
import Assets from './pages/Assets'

function App() {
  return (
    <div className="app">
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/positions" element={<Positions />} />
        <Route path="/trades" element={<Trades />} />
        <Route path="/assets" element={<Assets />} />
      </Routes>
    </div>
  )
}

export default App

