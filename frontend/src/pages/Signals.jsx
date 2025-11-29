import React, { useEffect, useState } from 'react'
import { getTopSignals } from '../lib/api'

export default function Signals() {
  const [rows, setRows] = useState([])
  const [latestDate, setLatestDate] = useState(null)
  const [loading, setLoading] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const { date, items } = await getTopSignals({ limit: 30 })
      setRows(items || [])
      setLatestDate(date || null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  return (
    <div className="page">
      <div className="card">
        <h2>Top 30 Momentum</h2>
        <div className="controls" style={{ justifyContent: 'space-between' }}>
          <div>
            <span>{loading ? 'Loading…' : `Showing up to 30 stocks`}</span>
          </div>
          <div>
            <span>{latestDate ? `As of ${latestDate}` : 'No data yet'}</span>
            <button style={{ marginLeft: 12 }} onClick={load} disabled={loading}>{loading ? 'Reloading…' : 'Reload'}</button>
          </div>
        </div>
        <table>
          <thead>
            <tr>
              <th>
                <abbr title="Ticker symbol">Symbol</abbr>
              </th>
              <th>
                <abbr title="12−1 month momentum = 12‑month return minus 1‑month return. Higher is stronger.">Momentum</abbr>
              </th>
              <th>
                <abbr title="MACD value; positive and rising tends to be bullish.">MACD</abbr>
              </th>
              <th>
                <abbr title="RSI (0-100); above ~50 bullish, above ~70 overbought.">RSI</abbr>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td>{r.symbol}</td>
                <td>{r.momentum_value}</td>
                <td>{r.macd_value}</td>
                <td>{r.rsi_value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
