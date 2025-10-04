import React, { useEffect, useState } from 'react'
import { getRuns } from '../lib/api'

export default function Runs() {
  const [rows, setRows] = useState([])
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(20)
  const [status, setStatus] = useState('')
  const [date, setDate] = useState('')
  const [total, setTotal] = useState(0)

  async function load() {
    const { runs, pagination } = await getRuns({ page, per_page: perPage, status: status || undefined, date: date || undefined })
    setRows(runs)
    setTotal(pagination?.total || 0)
  }

  useEffect(() => { load() }, [page, perPage, status, date])

  return (
    <div className="page">
      <div className="card">
        <h2>Algorithm Runs</h2>
        <div className="controls">
          <label>Status
            <select value={status} onChange={e => setStatus(e.target.value)}>
              <option value="">All</option>
              <option value="success">Success</option>
              <option value="error">Error</option>
            </select>
          </label>
          <label>Date <input type="date" value={date} onChange={e => setDate(e.target.value)} /></label>
          <label>Page <input type="number" min={1} value={page} onChange={e => setPage(+e.target.value)} /></label>
          <label>Per Page <input type="number" min={5} max={100} value={perPage} onChange={e => setPerPage(+e.target.value)} /></label>
          <button onClick={load}>Reload</button>
        </div>
        <table>
          <thead>
            <tr>
              <th>Created</th><th>Status</th><th>Run Date</th><th>Signals</th><th>Trades</th><th>Error</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td>{r.created_at}</td>
                <td>{r.status}</td>
                <td>{r.run_date}</td>
                <td>{r.signals_generated}</td>
                <td>{r.trades_executed}</td>
                <td>{r.error_message || ''}</td>
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
