$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Ambiente não preparado. Execute .\scripts\setup.ps1 primeiro."
}

$BackendLog = Join-Path $Backend "server.log"
$BackendError = Join-Path $Backend "server-error.log"
$BackendProcess = Start-Process -FilePath $Python `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000") `
    -WorkingDirectory $Backend -RedirectStandardOutput $BackendLog -RedirectStandardError $BackendError `
    -WindowStyle Hidden -PassThru

Write-Host "Backend iniciado em http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "Frontend em http://localhost:5173 (Ctrl+C encerra ambos)" -ForegroundColor Cyan

Push-Location $Frontend
try {
    npm run dev
}
finally {
    Pop-Location
    if (-not $BackendProcess.HasExited) { Stop-Process -Id $BackendProcess.Id }
}

