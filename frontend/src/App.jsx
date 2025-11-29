import React from 'react'
import { Routes, Route, Link, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Runs from './pages/Runs'
import Signals from './pages/Signals'
import Trades from './pages/Trades'

export default function App() {
  const links = [
    {
      to: '/',
      end: true,
      label: 'Dashboard',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <path d="M3 12l9-7 9 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M9 21V9h6v12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      )
    },
    {
      to: '/runs',
      label: 'Runs',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <path d="M13 5H6a2 2 0 00-2 2v10a2 2 0 002 2h7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M9 12h11l-3-3m3 3l-3 3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      )
    },
    {
      to: '/signals',
      label: 'Signals',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <path d="M4 12h3v8H4v-8zm6-5h3v13h-3V7zm6 8h3v5h-3v-5z" fill="currentColor"/>
        </svg>
      )
    },
    {
      to: '/trades',
      label: 'Trades',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <path d="M3 6h18M3 12h18M3 18h18" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        </svg>
      )
    }
  ]

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1>Momentum Algo</h1>
          <nav className="nav-desktop">
            {links.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.end}
                className={({ isActive }) =>
                  `nav-link ${isActive ? 'active' : ''}`
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
        </div>
        <nav className="nav-mobile" aria-label="Primary">
          {links.map((link) => (
            <NavLink
              key={`m-${link.to}`}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                `nav-icon ${isActive ? 'active' : ''}`
              }
              aria-label={link.label}
              title={link.label}
            >
              {link.icon}
              <span className="sr-only">{link.label}</span>
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/runs" element={<Runs />} />
          <Route path="/signals" element={<Signals />} />
          <Route path="/trades" element={<Trades />} />
        </Routes>
      </main>
      <footer className="app-footer">Paper trading is enabled. Extended-hours eligible.</footer>
    </div>
  )
}

