import React, { useEffect, useState } from 'react'
import { getSignals } from '../lib/api'

export default function Signals() {
  const [rows, setRows] = useState([])
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(20)
  const [date, setDate] = useState('')
  const [symbol, setSymbol] = useState('')
  const [total, setTotal] = useState(0)

  async function load() {
    const { signals, pagination } = await getSignals({ page, per_page: perPage, date: date || undefined, symbol: symbol || undefined })
    setRows(signals)
    setTotal(pagination?.total || 0)
  }

  useEffect(() => { load() }, [page, perPage, date, symbol])

  return (
    <div className="page">
      <div className="card">
        <h2>Signals</h2>
        <div className="controls">
          <label>Date <input type="date" value={date} onChange={e => setDate(e.target.value)} /></label>
          <label>Symbol <input value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())} placeholder="AAPL" /></label>
          <label>Page <input type="number" min={1} value={page} onChange={e => setPage(+e.target.value)} /></label>
          <label>Per Page <input type="number" min={5} max={100} value={perPage} onChange={e => setPerPage(+e.target.value)} /></label>
          <button onClick={load}>Reload</button>
        </div>
        <table>
          <thead>
            <tr>
              <th>Date</th><th>Symbol</th><th>Strength</th><th>Rank</th><th>Momentum</th><th>MACD</th><th>RSI</th>
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
