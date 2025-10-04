import React, { useEffect, useState } from 'react'
import { getPerformanceSummary } from '../lib/api'

export default function Performance() {
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const d = await getPerformanceSummary()
      setSummary(d)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const rows = summary ? [
    ['WoW', summary.wow],
    ['MoM', summary.mom],
    ['YoY', summary.yoy],
  ] : []

  return (
    <div className="page">
      <div className="card">
        <div className="row space-between">
          <h2>Performance (PnL)</h2>
          <button onClick={load} disabled={loading}>Reload</button>
        </div>
        <table>
          <thead>
            <tr>
              <th>Period</th><th>Current</th><th>Prior</th><th>Delta</th><th>Delta %</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([label, r]) => (
              <tr key={label}>
                <td>{label}</td>
                <td>{r?.current ?? ''}</td>
                <td>{r?.prior ?? ''}</td>
                <td>{r?.delta ?? ''}</td>
                <td>{r?.delta_pct ?? ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
