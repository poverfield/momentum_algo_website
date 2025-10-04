# Run the Flask backend API
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Push-Location $PSScriptRoot
try {
  $env:PYTHONIOENCODING = 'utf-8'
  if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error 'python not found in PATH. Please install Python 3 and ensure python is available.'
  }
  Write-Host 'Starting backend on http://127.0.0.1:5000'
  python app.py
}
finally {
  Pop-Location
}
