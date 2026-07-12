$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    python -m venv (Join-Path $Backend ".venv")
}

& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $Backend "requirements-dev.txt")

Push-Location $Backend
try { & $Python seed.py } finally { Pop-Location }

Push-Location $Frontend
try { npm install } finally { Pop-Location }

Write-Host "FNLIFTING ERP preparado com sucesso." -ForegroundColor Green
Write-Host "Execute .\scripts\start-dev.ps1 para iniciar." -ForegroundColor Cyan

