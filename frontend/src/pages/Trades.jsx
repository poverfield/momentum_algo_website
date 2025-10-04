import React, { useEffect, useState } from 'react'
import { getTrades } from '../lib/api'

export default function Trades() {
  const [rows, setRows] = useState([])
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(20)
  const [total, setTotal] = useState(0)

  async function load() {
    const { trades, pagination } = await getTrades({ page, per_page: perPage })
    setRows(trades)
    setTotal(pagination?.total || 0)
  }

  useEffect(() => { load() }, [page, perPage])

  return (
    <div className="page">
      <div className="card">
        <h2>Trades</h2>
        <div className="controls">
          <label>Page <input type="number" min={1} value={page} onChange={e => setPage(+e.target.value)} /></label>
          <label>Per Page <input type="number" min={5} max={100} value={perPage} onChange={e => setPerPage(+e.target.value)} /></label>
          <button onClick={load}>Reload</button>
        </div>
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
                <td>{t.price}</td>
                <td>{t.reason}</td>
                <td>{t.pnl ?? ''}</td>
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
