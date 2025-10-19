import React, { useEffect, useState } from 'react'
import { refreshPositions } from '../lib/api'

export default function Positions() {
  const [rows, setRows] = useState([])
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

  async function loadLive() {
    setLoading(true)
    try {
      const { positions } = await refreshPositions()
      setRows(positions || [])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadLive() }, [])

  return (
    <div className="page">
      <div className="card">
        <h2>Positions</h2>
        <div className="controls">
          <button onClick={loadLive} disabled={loading}>{loading ? 'Reloading...' : 'Reload'}</button>
        </div>
        {rows.length === 0 ? (
          <div>No positions in Alpaca</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Symbol</th><th>Qty</th><th>Entry Price</th><th>Current</th><th>Unrealized %</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <td>{r.symbol}</td>
                  <td>{r.quantity}</td>
                  <td>{formatCurrency(r.entry_price)}</td>
                  <td>{formatCurrency(r.current_price)}</td>
                  <td>{formatPercent(r.unrealized_pnl_pct)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
