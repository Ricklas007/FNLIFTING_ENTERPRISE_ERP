param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 4173,
    [int]$Workers = 2,
    [switch]$SkipMigrations,
    [switch]$SkipFrontendBuild
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Ambiente Python nao encontrado. Execute .\scripts\setup.ps1 primeiro."
}

if (-not $env:ENVIRONMENT) { $env:ENVIRONMENT = "production" }
if (-not $env:DEBUG) { $env:DEBUG = "false" }
if (-not $env:AUTO_CREATE_SCHEMA) { $env:AUTO_CREATE_SCHEMA = "false" }
if (-not $env:CORS_ORIGINS) {
    $env:CORS_ORIGINS = "http://localhost:$FrontendPort,http://127.0.0.1:$FrontendPort"
}
if (-not $env:ALLOWED_HOSTS) {
    $env:ALLOWED_HOSTS = "localhost,127.0.0.1"
}

$EnvFile = Join-Path $Backend ".env"
$SecretFromFile = ""
if (Test-Path $EnvFile) {
    $SecretLine = Get-Content $EnvFile | Where-Object { $_ -match "^SECRET_KEY=" } | Select-Object -First 1
    if ($SecretLine) { $SecretFromFile = $SecretLine -replace "^SECRET_KEY=", "" }
}
$EffectiveSecret = if ($env:SECRET_KEY) { $env:SECRET_KEY } else { $SecretFromFile }
if (-not $EffectiveSecret -or $EffectiveSecret.Length -lt 32 -or $EffectiveSecret -match "replace-with|troque-por|change-this-key") {
    throw "Defina SECRET_KEY forte em backend\.env ou na variavel de ambiente antes de iniciar producao."
}

if (-not $SkipMigrations) {
    & (Join-Path $PSScriptRoot "migrate.ps1")
}

if (-not $SkipFrontendBuild) {
    Push-Location $Frontend
    try {
        $env:VITE_API_URL = "http://127.0.0.1:$BackendPort/api/v1"
        npm run build
    }
    finally {
        Pop-Location
    }
}

$BackendLog = Join-Path $Backend "server-prod.log"
$BackendError = Join-Path $Backend "server-prod-error.log"
$BackendProcess = Start-Process -FilePath $Python `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$BackendPort", "--workers", "$Workers") `
    -WorkingDirectory $Backend -RedirectStandardOutput $BackendLog -RedirectStandardError $BackendError `
    -WindowStyle Hidden -PassThru

Write-Host "Backend producao iniciado em http://127.0.0.1:$BackendPort" -ForegroundColor Cyan
Write-Host "Frontend producao em http://localhost:$FrontendPort (Ctrl+C encerra ambos)" -ForegroundColor Cyan

Push-Location $Frontend
try {
    npm run preview -- --host 0.0.0.0 --port $FrontendPort
}
finally {
    Pop-Location
    if (-not $BackendProcess.HasExited) { Stop-Process -Id $BackendProcess.Id }
}
