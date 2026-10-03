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
$PreflightTemp = Join-Path $Root ".runtime\preflight-tmp"
$PytestBaseTemp = Join-Path $Root ".runtime\preflight-pytest-basetemp"
$RuntimeDir = Join-Path $Root ".runtime"
$GateLockPath = Join-Path $RuntimeDir "fnlifting-gate.lock"

if (-not (Test-Path $Python)) {
    throw "Ambiente Python nao encontrado. Execute .\scripts\setup.ps1 primeiro."
}

New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
try {
    $GateLockStream = [System.IO.File]::Open(
        $GateLockPath,
        [System.IO.FileMode]::OpenOrCreate,
        [System.IO.FileAccess]::ReadWrite,
        [System.IO.FileShare]::None
    )
}
catch {
    throw "Outro gate de release/preflight ja esta em execucao. Aguarde terminar antes de iniciar outro processo que use o mesmo SQLite."
}
$GateLockStream.SetLength(0)
$GateLockMessage = [System.Text.Encoding]::UTF8.GetBytes("prod-preflight pid=$PID started=$(Get-Date -Format o)")
$GateLockStream.Write($GateLockMessage, 0, $GateLockMessage.Length)
$GateLockStream.Flush()

Push-Location $Backend
try {
    New-Item -ItemType Directory -Force -Path $PreflightTemp | Out-Null
    $previousTemp = $env:TEMP
    $previousTmp = $env:TMP
    $env:TEMP = $PreflightTemp
    $env:TMP = $PreflightTemp

    & $Python -m compileall -q app seed.py tools
    if ($LASTEXITCODE -ne 0) { throw "compileall failed with exit code $LASTEXITCODE" }

    $Args = @("tools\preflight.py")
    if ($FailOnWarn) { $Args += "--fail-on-warn" }
    & $Python @Args
    if ($LASTEXITCODE -ne 0) { throw "backend preflight failed with exit code $LASTEXITCODE" }

    if (-not $SkipTests) {
        & $Python -m pytest --basetemp $PytestBaseTemp
        if ($LASTEXITCODE -ne 0) { throw "pytest failed with exit code $LASTEXITCODE" }
    }
}
finally {
    $env:TEMP = $previousTemp
    $env:TMP = $previousTmp
    Pop-Location
}

if (-not $SkipFrontendBuild) {
    Push-Location $Frontend
    try {
        npm run build
        if ($LASTEXITCODE -ne 0) { throw "frontend build failed with exit code $LASTEXITCODE" }
    }
    finally {
        Pop-Location
    }
}

Write-Host "Preflight de producao concluido." -ForegroundColor Green
