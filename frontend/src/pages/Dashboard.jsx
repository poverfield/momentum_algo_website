import React, { useEffect, useState } from 'react';
import { getHealth, postRun, getRuns, refreshPositions, getTrades, getAccount } from '../lib/api';

export default function Dashboard() {
  const [health, setHealth] = useState(null);
  const [runs, setRuns] = useState([]);
  const [positions, setPositions] = useState([]);
  const [trades, setTrades] = useState([]);
  const [account, setAccount] = useState(null);
  const [syncedAt, setSyncedAt] = useState('');
  const [loading, setLoading] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [pollTimerId, setPollTimerId] = useState(null);

  function formatCurrency(value) {
    if (value === null || value === undefined || value === '') return '';
    const num = Number(value);
    if (Number.isNaN(num)) return '';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(num);
  }

  function formatMonthDay(dateStr) {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      // Fallback: handle strings like "11/26/2025" as-is
      if (isNaN(d.getTime())) {
        const parts = String(dateStr).split('/');
        return parts.length >= 2 ? `${parts[0]}/${parts[1]}` : String(dateStr);
      }
      return d.toLocaleDateString('en-US', { month: '2-digit', day: '2-digit' });
    } catch {
      const parts = String(dateStr).split('/');
      return parts.length >= 2 ? `${parts[0]}/${parts[1]}` : String(dateStr);
    }
  }

  function formatPercent(value) {
    if (value === null || value === undefined || value === '') return '';
    const num = Number(value);
    if (Number.isNaN(num)) return '';
    const sign = num >= 0 ? '+' : '';
    return `${sign}${num.toFixed(2)}%`;
  }

  function formatEst(dateStr) {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      return d.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: true,
        timeZone: 'America/New_York' 
      }) + ' ET';
    } catch {
      return dateStr;
    }
  }

  function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
      });
    } catch {
      return dateStr;
    }
  }

  async function load() {
    setLoading(true);
    try {
      const [h, r, p, t, a] = await Promise.all([
        getHealth(),
        getRuns({ page: 1, per_page: 5 }),
        refreshPositions(),
        getTrades({ page: 1, per_page: 5 }),
        getAccount()
      ]);
      setHealth(h);
      setRuns(r.runs || []);
      setPositions(p.positions || []);
      setSyncedAt(p.synced_at || '');
      setTrades(t.trades || []);
      setAccount(a && !a.error ? a : null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  // Clear any polling timer on unmount
  useEffect(() => {
    return () => {
      if (pollTimerId) {
        clearInterval(pollTimerId);
      }
    };
  }, [pollTimerId]);

  function startPollingForCompletion(prevCreatedAt) {
    // Poll recent runs until a new run appears (created_at changes)
    const id = setInterval(async () => {
      try {
        const r = await getRuns({ page: 1, per_page: 5 });
        const latest = (r.runs || [])[0];
        if (!latest) return;
        // When a new run record exists, assume it's completed (backend logs only after completion)
        if (!prevCreatedAt || latest.created_at !== prevCreatedAt) {
          setRuns(r.runs || []);
          // Also refresh positions and trades for freshness
          try {
            const [p, t] = await Promise.all([
              refreshPositions(),
              getTrades({ page: 1, per_page: 5 })
            ]);
            setPositions(p.positions || []);
            setSyncedAt(p.synced_at || '');
            setTrades(t.trades || []);
          } catch (_) {
            // Non-fatal
          }
          clearInterval(id);
          setPollTimerId(null);
          setIsRunning(false);
        }
      } catch (e) {
        // If polling fails, stop polling and allow another attempt
        console.error('Polling runs failed:', e);
        clearInterval(id);
        setPollTimerId(null);
        setIsRunning(false);
      }
    }, 3000);
    setPollTimerId(id);
  }

  async function runNow() {
    if (isRunning) return;
    const prevCreatedAt = runs && runs.length > 0 ? runs[0].created_at : null;
    setIsRunning(true);
    try {
      // Trigger run
      await postRun();
      // Begin polling for the new run to appear in history
      startPollingForCompletion(prevCreatedAt);
      console.log('Algorithm run triggered');
    } catch (e) {
      console.error('Run failed:', e);
      setIsRunning(false);
    }
  }

  const dbStatus = health?.services?.database ? 'connected' : 'disconnected';
  const alpacaStatus = health?.services?.alpaca ? 'connected' : 'disconnected';

  return (
    <div className="page">
      {/* Header */}
      <div className="row space-between" style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '20px', fontWeight: 600, color: 'var(--text)' }}>Algo Trading</h1>
        <div className="row" style={{ gap: '8px' }}>
          <button
            type="button"
            onClick={load}
            disabled={loading}
            className="icon"
            aria-label="Refresh data"
            title="Refresh data"
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <path d="M21 12a9 9 0 10-3.51 7.09" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M21 3v6h-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>
      </div>

      {/* System Health */}
      <div className="card">
        <div className="card-header">
          <span aria-hidden>📈</span>
          <h2>System Health</h2>
        </div>
        
        <div className="stats-grid">
          <div className="stat-item">
            <div className="stat-label">Last Data Sync</div>
            <div className="stat-value">{syncedAt ? formatEst(syncedAt) : '--'}</div>
          </div>
          <div className="stat-item">
            <div className="stat-label">Last Algo Run</div>
            <div className="stat-value">
              {runs.length > 0 ? formatEst(runs[0].created_at) : '--'}
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-label">Database</div>
            <div className="row">
              <span className={`status ${dbStatus === 'connected' ? 'success' : 'error'}`}>{dbStatus}</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-label">Alpaca API</div>
            <div className="row">
              <span className={`status ${alpacaStatus === 'connected' ? 'success' : 'error'}`}>{alpacaStatus}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Account Balance */}
      <div className="card">
        <div className="card-header">
          <span aria-hidden>💰</span>
          <h2>Account Balance</h2>
        </div>
        
        {account ? (
          <div className="stats-grid">
            <div className="stat-item">
              <div className="stat-label">Portfolio Value</div>
              <div className="stat-value">{formatCurrency(account.portfolio_value)}</div>
            </div>
            <div className="stat-item">
              <div className="stat-label">Buying Power</div>
              <div className="stat-value">{formatCurrency(account.buying_power)}</div>
            </div>
            <div className="stat-item">
              <div className="stat-label">Cash</div>
              <div className="stat-value">{formatCurrency(account.cash)}</div>
            </div>
          </div>
        ) : (
          <p style={{ color: 'var(--muted)' }}>Loading account information...</p>
        )}
      </div>

            {/* Current Positions */}
            <div className="card">
        <h3 style={{ marginBottom: '12px' }}>Current Positions</h3>
        
        {positions.length > 0 ? (
          <div className="positions-list">
            {([...positions]
              .sort((a, b) => (b.quantity * b.entry_price) - (a.quantity * a.entry_price))
            ).map((p, i, arr) => {
              const invested = p.quantity * p.entry_price;
              const unrealizedAmount = (p.current_price - p.entry_price) * p.quantity;
              const isPositive = p.unrealized_pnl_pct >= 0;
              
              return (
                <div 
                  key={i}
                  className="position-item"
                  style={{
                    paddingBottom: i !== arr.length - 1 ? '12px' : '0',
                    marginBottom: i !== arr.length - 1 ? '12px' : '0',
                    borderBottom: i !== arr.length - 1 ? '1px solid #E5E7EB' : 'none'
                  }}
                >
                  {/* Row 1: Symbol and Unrealized Gains */}
                  <div className="position-row" style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'flex-start',
                    marginBottom: '8px'
                  }}>
                    <div>
                      <div className="position-symbol" style={{
                        fontSize: '14px',
                        fontWeight: 600,
                        color: '#111827',
                        marginBottom: '2px'
                      }}>
                        {p.symbol}
                      </div>
                      <div className="position-invested" style={{
                        fontSize: '12px',
                        color: '#6B7280'
                      }}>
                        {formatCurrency(invested)}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div className="position-pnl-pct" style={{
                        fontSize: '14px',
                        fontWeight: 600,
                        color: isPositive ? '#16A34A' : '#DC2626'
                      }}>
                        {formatPercent(p.unrealized_pnl_pct)}
                      </div>
                      <div className="position-pnl-amount" style={{
                        fontSize: '12px',
                        color: isPositive ? '#16A34A' : '#DC2626'
                      }}>
                        {formatCurrency(unrealizedAmount)}
                      </div>
                    </div>
                  </div>
                  
                  {/* Row 2: Price Comparison */}
                  <div className="position-prices" style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: '12px',
                    color: '#6B7280'
                  }}>
                    <span>Entry: {formatCurrency(p.entry_price)}</span>
                    <span>Current: {formatCurrency(p.current_price)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{ textAlign: 'center', color: 'var(--muted)', padding: '12px' }}>
            No open positions
          </div>
        )}
      </div>

      {/* Recent Runs */}
      <div className="card">
        <div className="row space-between" style={{ marginBottom: '0.75rem' }}>
          <h3>Recent Runs</h3>
          <button onClick={runNow} className="primary" disabled={loading || isRunning}>
            {isRunning ? 'Running…' : 'Run Now'}
          </button>
        </div>
        {isRunning && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            color: 'var(--muted)'
          }}>
            <span className="status" style={{ background: '#EEF2FF', color: '#3730A3' }}>in progress</span>
            <span>Algorithm is running. A new entry will appear in Recent Runs when it completes.</span>
          </div>
        )}
        
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>Status</th>
                <th>Signals</th>
                <th>Trades</th>
              </tr>
            </thead>
            <tbody>
              {runs.length > 0 ? (
                runs.map((run, i) => (
                  <tr key={i}>
                    <td>{formatDate(run.created_at)}</td>
                    <td>{run.status}</td>
                    <td>{run.signals_generated || 0}</td>
                    <td>{run.trades_executed || 0}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="4" style={{ textAlign: 'center', color: 'var(--muted)', padding: '12px' }}>No recent runs found</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent Trades */}
      <div className="card">
        <h3>Recent Trades</h3>
        
        {trades.length > 0 ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Symbol</th>
                  <th>Action</th>
                  <th>Qty</th>
                  <th>Price</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((t, i) => (
                  <tr key={i}>
                    <td>{formatMonthDay(t.date)}</td>
                    <td>{t.symbol}</td>
                    <td>{t.action}</td>
                    <td>{t.quantity}</td>
                    <td>{t.price}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ textAlign: 'center', color: 'var(--muted)', padding: '12px' }}>No recent trades</div>
        )}
      </div>
    </div>
  );
}