import React from 'react'
import { Routes, Route, Link, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Runs from './pages/Runs'
import Signals from './pages/Signals'
import Positions from './pages/Positions'
import Trades from './pages/Trades'
import Diagnostics from './pages/Diagnostics'
import Performance from './pages/Performance'

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>Momentum Algo</h1>
        <nav>
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/runs">Runs</NavLink>
          <NavLink to="/signals">Signals</NavLink>
          <NavLink to="/positions">Positions</NavLink>
          <NavLink to="/trades">Trades</NavLink>
          <NavLink to="/diagnostics">Diagnostics</NavLink>
          <NavLink to="/performance">Performance</NavLink>
        </nav>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/runs" element={<Runs />} />
          <Route path="/signals" element={<Signals />} />
          <Route path="/positions" element={<Positions />} />
          <Route path="/trades" element={<Trades />} />
          <Route path="/diagnostics" element={<Diagnostics />} />
          <Route path="/performance" element={<Performance />} />
        </Routes>
      </main>
      <footer className="app-footer">Paper trading is enabled. Extended-hours eligible.</footer>
    </div>
  )
}
