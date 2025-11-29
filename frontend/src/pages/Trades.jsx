import React, { useEffect, useState } from 'react'
import { getTrades } from '../lib/api'

export default function Trades() {
  const [rows, setRows] = useState([])
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(20)
  const [total, setTotal] = useState(0)
  const [symbol, setSymbol] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

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

  async function load({ pageOverride, perPageOverride } = {}) {
    const effectivePage = pageOverride ?? page
    const effectivePerPage = perPageOverride ?? perPage
    const params = { page: effectivePage, per_page: effectivePerPage }
    if (symbol) params.symbol = symbol.trim().toUpperCase()
    setLoading(true)
    setError('')
    try {
      console.log('[Trades] fetch params:', params)
      const { trades, pagination } = await getTrades(params)
      console.log('[Trades] results:', { count: trades?.length, pagination })
      setRows(trades)
      setTotal(pagination?.total || 0)
    } catch (e) {
      console.error('[Trades] fetch error:', e)
      setError(e?.message || 'Failed to load trades')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [page, perPage])

  // Auto-load when ticker changes (including clearing)
  useEffect(() => {
    const newPage = 1
    setPage(newPage)
    load({ pageOverride: newPage })
  }, [symbol])

  function handleClear() {
    setSymbol('')
    const newPage = 1
    setPage(newPage)
    load({ pageOverride: newPage })
  }

  return (
    <div className="page">
      <div className="card">
        <h2>Trades</h2>
        <div className="controls">
          <label>Ticker <input type="text" placeholder="e.g. AAPL" value={symbol} onChange={e => setSymbol(e.target.value)} /></label>
          <label>Page <input type="number" min={1} value={page} onChange={e => setPage(+e.target.value)} /></label>
          <label>Per Page <input type="number" min={5} max={100} value={perPage} onChange={e => setPerPage(+e.target.value)} /></label>
          <button onClick={handleClear}>Clear</button>
        </div>
        {error && (<div className="error" style={{ color: 'crimson', marginTop: 8 }}>{error}</div>)}
        <table>
          <thead>
            <tr>
              <th>Date</th><th>Symbol</th><th>Action</th><th>Qty</th><th>Price</th><th>Reason</th><th>PnL</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t, i) => (
              <tr key={i}>
                <td>{t.date}</td>
                <td>{t.symbol}</td>
                <td>{t.action}</td>
                <td>{t.quantity}</td>
                <td>{formatCurrency(t.price)}</td>
                <td>{t.reason}</td>
                <td>{
                  t.pnl_pct !== undefined && t.pnl_pct !== null
                    ? formatPercent(t.pnl_pct)
                    : (t.pnl === null || t.pnl === undefined ? '' : formatCurrency(t.pnl))
                }</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="controls">
          <div>Total: {total}</div>
        </div>
      </div>
    </div>
  )
}
