param(
    [switch]$FailOnWarn,
    [switch]$SkipTests,
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

Push-Location $Backend
try {
    & $Python -m compileall -q app seed.py tools
    $Args = @("tools\preflight.py")
    if ($FailOnWarn) { $Args += "--fail-on-warn" }
    & $Python @Args
    if (-not $SkipTests) {
        & $Python -m pytest
    }
}
finally {
    Pop-Location
}

if (-not $SkipFrontendBuild) {
    Push-Location $Frontend
    try {
        npm run build
    }
    finally {
        Pop-Location
    }
}

Write-Host "Preflight de producao concluido." -ForegroundColor Green
