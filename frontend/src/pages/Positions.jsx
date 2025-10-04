import React, { useEffect, useState } from 'react'
import { getPositions } from '../lib/api'

export default function Positions() {
  const [rows, setRows] = useState([])

  async function load() {
    const { positions } = await getPositions()
    setRows(positions || [])
  }

  useEffect(() => { load() }, [])

  return (
    <div className="page">
      <div className="card">
        <h2>Positions</h2>
        <div className="controls">
          <button onClick={load}>Reload</button>
        </div>
        <table>
          <thead>
            <tr>
              <th>Symbol</th><th>Qty</th><th>Entry Price</th><th>Entry Date</th><th>Current</th><th>Unrealized PnL</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td>{r.symbol}</td>
                <td>{r.quantity}</td>
                <td>{r.entry_price}</td>
                <td>{r.entry_date}</td>
                <td>{r.current_price ?? ''}</td>
                <td>{r.unrealized_pnl ?? ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
