import axios from 'axios'

const api = axios.create({
  baseURL: '/',
  headers: { 'Content-Type': 'application/json' }
})

export async function getHealth() {
  const { data } = await api.get('/api/health')
  return data
}

export async function getRuns(params) {
  const { data } = await api.get('/api/runs', { params })
  return data
}

export async function getSignals(params) {
  const { data } = await api.get('/api/signals', { params })
  return data
}

export async function getPositions() {
  const { data } = await api.get('/api/positions')
  return data
}

export async function getTrades(params) {
  const { data } = await api.get('/api/trades', { params })
  return data
}

export async function getDiagnostics(params) {
  const { data } = await api.get('/api/diagnostics', { params })
  return data
}

export async function postRun() {
  const { data } = await api.post('/api/algorithm/run')
  return data
}

export async function getPerformanceSummary() {
  const { data } = await api.get('/api/performance/summary')
  return data
}

export default api
