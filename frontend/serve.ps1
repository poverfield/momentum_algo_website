# Run the React frontend (Vite)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Push-Location $PSScriptRoot
try {
  if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Error 'npm not found. Please install Node.js (which includes npm) and ensure it is in PATH.'
  }
  if (-not (Test-Path node_modules)) {
    Write-Host 'Installing frontend dependencies (npm install)...'
    npm install
  }
  Write-Host 'Starting frontend on http://127.0.0.1:5173 (proxying /api to http://127.0.0.1:5000)'
  npm run dev
}
finally {
  Pop-Location
}
