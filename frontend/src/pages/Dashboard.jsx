import React, { useEffect, useState } from 'react'
import { getHealth, postRun, getRuns, getPositions, getTrades } from '../lib/api'

export default function Dashboard() {
  const [health, setHealth] = useState(null)
  const [runs, setRuns] = useState([])
  const [positions, setPositions] = useState([])
  const [trades, setTrades] = useState([])
  const [loading, setLoading] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const [h, r, p, t] = await Promise.all([
        getHealth(),
        getRuns({ page: 1, per_page: 5 }),
        getPositions(),
        getTrades({ page: 1, per_page: 5 })
      ])
      setHealth(h)
      setRuns(r.runs || [])
      setPositions(p.positions || [])
      setTrades(t.trades || [])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function runNow() {
    try {
      await postRun()
      await load()
      alert('Algorithm run triggered')
    } catch (e) {
      alert('Run failed: ' + e.message)
    }
  }

  return (
    <div className="page">
      <div className="card">
        <div className="row space-between">
          <h2>System Health</h2>
          <div>
            <button onClick={load} disabled={loading}>Refresh</button>{' '}
            <button onClick={runNow}>Run Algorithm Now</button>
          </div>
        </div>
        {health && (
          <div className="kpis">
            <div className="kpi"><div className="kpi-label">DB</div><div className="kpi-value">{health.services.database ? 'OK' : 'ERR'}</div></div>
            <div className="kpi"><div className="kpi-label">Alpaca</div><div className="kpi-value">{health.services.alpaca ? 'OK' : 'ERR'}</div></div>
            <div className="kpi"><div className="kpi-label">Status</div><div className="kpi-value">{health.status}</div></div>
          </div>
        )}
      </div>

      <div className="grid two">
        <div className="card">
          <h3>Recent Runs</h3>
          <table>
            <thead><tr><th>Created</th><th>Status</th><th>Run Date</th><th>Signals</th><th>Trades</th></tr></thead>
            <tbody>
              {runs.map((r,i) => (
                <tr key={i}>
                  <td>{r.created_at}</td>
                  <td>{r.status}</td>
                  <td>{r.run_date}</td>
                  <td>{r.signals_generated}</td>
                  <td>{r.trades_executed}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="card">
          <h3>Current Positions</h3>
          <table>
            <thead><tr><th>Symbol</th><th>Qty</th><th>Entry</th><th>Current</th><th>Unreal. PnL</th></tr></thead>
            <tbody>
              {positions.map((p,i) => (
                <tr key={i}>
                  <td>{p.symbol}</td>
                  <td>{p.quantity}</td>
                  <td>{p.entry_price}</td>
                  <td>{p.current_price ?? ''}</td>
                  <td>{p.unrealized_pnl ?? ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h3>Recent Trades</h3>
        <table>
          <thead><tr><th>Date</th><th>Symbol</th><th>Action</th><th>Qty</th><th>Price</th><th>Reason</th><th>PnL</th></tr></thead>
          <tbody>
            {trades.map((t,i) => (
              <tr key={i}>
                <td>{t.date}</td>
                <td>{t.symbol}</td>
                <td>{t.action}</td>
                <td>{t.quantity}</td>
                <td>{t.price}</td>
                <td>{t.reason}</td>
                <td>{t.pnl ?? ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
