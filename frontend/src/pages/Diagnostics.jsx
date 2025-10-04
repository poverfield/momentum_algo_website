import React, { useState } from 'react'
import { getDiagnostics } from '../lib/api'

export default function Diagnostics() {
  const [sampleN, setSampleN] = useState(50)
  const [daysBack, setDaysBack] = useState(600)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)

  async function run() {
    setLoading(true)
    try {
      const d = await getDiagnostics({ sample_n: sampleN, days_back: daysBack })
      setData(d)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <div className="card">
        <h2>Diagnostics</h2>
        <div className="controls">
          <label>Sample N <input type="number" min={5} max={200} value={sampleN} onChange={e => setSampleN(+e.target.value)} /></label>
          <label>Days Back <input type="number" min={200} max={1200} value={daysBack} onChange={e => setDaysBack(+e.target.value)} /></label>
          <button onClick={run} disabled={loading}>Run</button>
        </div>
        {data && (
          <div>
            <table>
              <thead>
                <tr><th>Metric</th><th>Value</th></tr>
              </thead>
              <tbody>
                <tr><td>Sample Size</td><td>{data.sample_size}</td></tr>
                <tr><td>Days</td><td>{data.days}</td></tr>
                <tr><td>MACD OK</td><td>{data.macd_ok_count}</td></tr>
                <tr><td>RSI OK</td><td>{data.rsi_ok_count}</td></tr>
                <tr><td>Both OK</td><td>{data.both_ok_count}</td></tr>
              </tbody>
            </table>
            <div className="card">
              <h3>Samples</h3>
              <div className="grid two">
                <div>
                  <h4>MACD OK</h4>
                  <div>{(data.macd_ok_sample || []).join(', ')}</div>
                </div>
                <div>
                  <h4>RSI OK</h4>
                  <div>{(data.rsi_ok_sample || []).join(', ')}</div>
                </div>
              </div>
              <div style={{marginTop: '8px'}}>
                <h4>Both OK</h4>
                <div>{(data.both_ok_sample || []).join(', ')}</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
