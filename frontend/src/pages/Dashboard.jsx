import React, { useEffect, useState } from 'react'
  import { getHealth, postRun, getRuns, refreshPositions, getTrades, getAccount } from '../lib/api'

  export default function Dashboard() {
    const [health, setHealth] = useState(null)
    const [runs, setRuns] = useState([])
    const [positions, setPositions] = useState([])
    const [trades, setTrades] = useState([])
    const [account, setAccount] = useState(null)
    const [syncedAt, setSyncedAt] = useState('')
    const [loading, setLoading] = useState(false)

  function formatCurrency(value) {
    if (value === null || value === undefined || value === '') return ''
    const num = Number(value)
    if (Number.isNaN(num)) return ''
    const isNegative = num < 0 || Object.is(num, -0)
    const absNum = Math.abs(num)
    const withCommas = absNum.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    return `${isNegative ? '-' : ''}$${withCommas}`
  }

  function formatPercent(value) {
    if (value === null || value === undefined || value === '') return ''
    const num = Number(value)
    if (Number.isNaN(num)) return ''
    const isNegative = num < 0 || Object.is(num, -0)
    const absNum = Math.abs(num)
    return `${isNegative ? '-' : ''}${absNum.toFixed(2)}%`
  }

  function formatEst(dateStr) {
    if (!dateStr) return ''
    try {
      const d = new Date(dateStr)
      return d.toLocaleString('en-US', { timeZone: 'America/New_York' }) + ' ET'
    } catch {
      return dateStr
    }
  }

  async function load() {
    setLoading(true)
    try {
      const [h, r, p, t, a] = await Promise.all([
        getHealth(),
        getRuns({ page: 1, per_page: 5 }),
        refreshPositions(),
        getTrades({ page: 1, per_page: 5 }),
        getAccount()
      ])
      setHealth(h)
      setRuns(r.runs || [])
      setPositions(p.positions || [])
      setSyncedAt(p.synced_at || '')
      setTrades(t.trades || [])
      setAccount(a && !a.error ? a : null)
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
            <button onClick={load} disabled={loading}>{loading ? 'Refreshing...' : 'Refresh'}</button>{' '}
            <button onClick={runNow}>Run Algorithm Now</button>
          </div>
        </div>
        {account && (
          <div className="kpis">
            <div className="kpi"><div className="kpi-label">Portfolio</div><div className="kpi-value">{formatCurrency(account.portfolio_value)}</div></div>
            <div className="kpi"><div className="kpi-label">Cash</div><div className="kpi-value">{formatCurrency(account.cash)}</div></div>
            <div className="kpi"><div className="kpi-label">Buying Power</div><div className="kpi-value">{formatCurrency(account.buying_power)}</div></div>
          </div>
        )}
        {health && (
          <div className="kpis">
            <div className="kpi"><div className="kpi-label">DB</div><div className="kpi-value">{health.services.database ? 'OK' : 'ERR'}</div></div>
            <div className="kpi"><div className="kpi-label">Alpaca</div><div className="kpi-value">{health.services.alpaca ? 'OK' : 'ERR'}</div></div>
            <div className="kpi"><div className="kpi-label">Status</div><div className="kpi-value">{health.status}</div></div>
            {syncedAt && (
              <div className="kpi"><div className="kpi-label">Data Synced At</div><div className="kpi-value">{formatEst(syncedAt)}</div></div>
            )}
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
                  <td>{formatEst(r.created_at)}</td>
                  <td>{r.status}</td>
                  <td>{formatEst(r.run_date)}</td>
                  <td>{r.signals_generated}</td>
                  <td>{r.trades_executed}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="card">
          <h3>Current Positions</h3>
          {positions.length === 0 ? (
            <div>No positions in Alpaca</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Symbol</th><th>Qty</th><th>Entry Price</th><th>Current</th><th>Unrealized %</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((p,i) => (
                  <tr key={i}>
                    <td>{p.symbol}</td>
                    <td>{p.quantity}</td>
                    <td>{formatCurrency(p.entry_price)}</td>
                    <td>{formatCurrency(p.current_price)}</td>
                    <td>{formatPercent(p.unrealized_pnl_pct)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
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
