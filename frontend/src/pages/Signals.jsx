import React, { useEffect, useState } from 'react'
import { getSignals } from '../lib/api'

export default function Signals() {
  const [rows, setRows] = useState([])
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(20)
  const [date, setDate] = useState('')
  const [symbol, setSymbol] = useState('')
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [sortField, setSortField] = useState('')
  const [sortDir, setSortDir] = useState('desc')

  async function load() {
    setLoading(true)
    try {
      const { signals, pagination } = await getSignals({ page, per_page: perPage, date: date || undefined, symbol: symbol || undefined })
      setRows(signals)
      setTotal(pagination?.total || 0)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [page, perPage, date, symbol])

  function sortBy(field) {
    const nextDir = sortField === field && sortDir === 'desc' ? 'asc' : 'desc'
    setSortField(field)
    setSortDir(nextDir)
    setRows(prev => {
      const copy = [...prev]
      copy.sort((a, b) => {
        const av = a[field]
        const bv = b[field]
        if (av == null && bv == null) return 0
        if (av == null) return 1
        if (bv == null) return -1
        if (typeof av === 'number' && typeof bv === 'number') {
          return nextDir === 'asc' ? av - bv : bv - av
        }
        const as = String(av)
        const bs = String(bv)
        return nextDir === 'asc' ? as.localeCompare(bs) : bs.localeCompare(as)
      })
      return copy
    })
  }

  return (
    <div className="page">
      <div className="card">
        <h2>Signals</h2>
        <div className="controls">
          <label>Date <input type="date" value={date} onChange={e => setDate(e.target.value)} /></label>
          <label>Symbol <input value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())} placeholder="AAPL" /></label>
          <label>Page <input type="number" min={1} value={page} onChange={e => setPage(+e.target.value)} /></label>
          <label>Per Page <input type="number" min={5} max={100} value={perPage} onChange={e => setPerPage(+e.target.value)} /></label>
          <button onClick={load} disabled={loading}>{loading ? 'Reloading...' : 'Reload'}</button>
        </div>
        <table>
          <thead>
            <tr>
              <th onClick={() => sortBy('signal_date')} style={{ cursor: 'pointer' }}>
                <abbr title="Date the signal was generated (ET)">Date</abbr>
              </th>
              <th onClick={() => sortBy('symbol')} style={{ cursor: 'pointer' }}>
                <abbr title="Ticker symbol">Symbol</abbr>
              </th>
              <th onClick={() => sortBy('signal_strength')} style={{ cursor: 'pointer' }}>
                <abbr title="Weighted score: 40% Momentum Rank (1 is best), 30% MACD histogram (normalized), 30% RSI above 50 (normalized). Higher is stronger. Signals require bullish MACD & RSI (unless relaxed mode).">Strength</abbr>
              </th>
              <th onClick={() => sortBy('momentum_rank')} style={{ cursor: 'pointer' }}>
                <abbr title="Rank among universe (1 = strongest). Lower rank is better.">Rank</abbr>
              </th>
              <th onClick={() => sortBy('momentum_value')} style={{ cursor: 'pointer' }}>
                <abbr title="12−1 month momentum = 12‑month return minus 1‑month return. Higher positive values indicate stronger momentum (ranked to find top 30).">Momentum</abbr>
              </th>
              <th onClick={() => sortBy('macd_value')} style={{ cursor: 'pointer' }}>
                <abbr title="MACD value; positive and rising tends to be bullish.">MACD</abbr>
              </th>
              <th onClick={() => sortBy('rsi_value')} style={{ cursor: 'pointer' }}>
                <abbr title="RSI (0-100); above ~50 bullish, above ~70 overbought.">RSI</abbr>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td>{r.signal_date}</td>
                <td>{r.symbol}</td>
                <td>{r.signal_strength}</td>
                <td>{r.momentum_rank}</td>
                <td>{r.momentum_value}</td>
                <td>{r.macd_value}</td>
                <td>{r.rsi_value}</td>
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
