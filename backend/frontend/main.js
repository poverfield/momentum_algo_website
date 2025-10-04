async function json(url, opts) {
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

function $(id) { return document.getElementById(id); }

function setHealth(h) {
  $('health').innerHTML = `
    <div><strong>Status:</strong> ${h.status}</div>
    <div><strong>Timestamp:</strong> ${h.timestamp}</div>
    <div><strong>DB:</strong> ${h.services.database ? 'OK' : 'ERR'}</div>
    <div><strong>Alpaca:</strong> ${h.services.alpaca ? 'OK' : 'ERR'}</div>
  `;
}

function renderTable(tbody, rows, cols) {
  tbody.innerHTML = rows.map(row => `<tr>${cols.map(c => `<td>${row[c] ?? ''}</td>`).join('')}</tr>`).join('');
}

async function loadHealth() {
  try { setHealth(await json('/api/health')); } catch (e) { console.error(e); }
}

async function loadRuns() {
  const page = +$('runs-page').value;
  const perPage = +$('runs-per-page').value;
  const data = await json(`/api/runs?page=${page}&per_page=${perPage}`);
  renderTable(document.querySelector('#runs-table tbody'), data.runs, ['created_at','status','run_date','signals_generated','trades_executed','error_message']);
}

async function loadSignals() {
  const date = $('signals-date').value;
  const symbol = $('signals-symbol').value.trim();
  const page = +$('signals-page').value;
  const perPage = +$('signals-per-page').value;
  const qs = new URLSearchParams({ page, per_page: perPage });
  if (date) qs.set('date', date);
  if (symbol) qs.set('symbol', symbol.toUpperCase());
  const data = await json(`/api/signals?${qs.toString()}`);
  renderTable(document.querySelector('#signals-table tbody'), data.signals, ['signal_date','symbol','signal_strength','momentum_rank','momentum_value','macd_value','rsi_value']);
}

async function loadPositions() {
  const data = await json('/api/positions');
  renderTable(document.querySelector('#positions-table tbody'), data.positions, ['symbol','quantity','entry_price','entry_date','current_price','unrealized_pnl']);
}

async function loadTrades() {
  const page = +$('trades-page').value;
  const perPage = +$('trades-per-page').value;
  const data = await json(`/api/trades?page=${page}&per_page=${perPage}`);
  renderTable(document.querySelector('#trades-table tbody'), data.trades, ['date','symbol','action','quantity','price','reason','pnl']);
}

async function runAlgorithm() {
  try {
    const r = await fetch('/api/algorithm/run', { method: 'POST' });
    const j = await r.json();
    alert('Algorithm run triggered: ' + JSON.stringify(j));
    await loadRuns();
  } catch (e) {
    alert('Run failed: ' + e.message);
  }
}

async function runDiagnostics() {
  const sample = +$('diag-sample').value;
  const days = +$('diag-days').value;
  const data = await json(`/api/diagnostics?sample_n=${sample}&days_back=${days}`);
  $('diagnostics').textContent = JSON.stringify(data, null, 2);
}

$('btn-perf').addEventListener('click', loadPerformance);

async function loadPerformance() {
  try {
    const d = await json('/api/performance/summary');
    const tbody = document.querySelector('#perf-table tbody');
    const rows = [
      ['WoW', d.wow],
      ['MoM', d.mom],
      ['YoY', d.yoy],
    ];
    tbody.innerHTML = rows.map(([label, r]) => `
      <tr>
        <td>${label}</td>
        <td>${r.current}</td>
        <td>${r.prior}</td>
        <td>${r.delta}</td>
        <td>${r.delta_pct ?? ''}</td>
      </tr>
    `).join('');
  } catch (e) {
    console.error(e);
  }
}

$('btn-run').addEventListener('click', runAlgorithm);
$('btn-refresh').addEventListener('click', () => { loadHealth(); loadRuns(); loadSignals(); loadPositions(); loadTrades(); });
$('btn-runs').addEventListener('click', loadRuns);
$('btn-signals').addEventListener('click', loadSignals);
$('btn-positions').addEventListener('click', loadPositions);
$('btn-trades').addEventListener('click', loadTrades);
$('btn-diagnostics').addEventListener('click', runDiagnostics);

// initial load
loadHealth();
loadRuns();
loadSignals();
loadPositions();
loadTrades();
loadPerformance();
