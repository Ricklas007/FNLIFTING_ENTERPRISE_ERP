$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Ambiente Python nao encontrado. Execute .\scripts\setup.ps1 primeiro."
}

Push-Location $Backend
try {
    & $Python -m alembic upgrade head
}
finally {
    Pop-Location
}

Write-Host "Migracoes aplicadas com sucesso." -ForegroundColor Green
