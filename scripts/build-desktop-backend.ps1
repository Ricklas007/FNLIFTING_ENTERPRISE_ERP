param(
    [switch]$CleanOnly,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"
$Dist = Join-Path $Root "backend-dist"

if (-not (Test-Path $Python)) {
    throw "Ambiente Python do backend nao encontrado. Execute .\scripts\setup.ps1 primeiro."
}

if (Test-Path $Dist) {
    Remove-Item -LiteralPath $Dist -Recurse -Force
}

if ($CleanOnly) {
    Write-Host "backend-dist removido." -ForegroundColor Green
    exit 0
}

Push-Location $Root
try {
    if (-not $SkipInstall) {
        $hasPyInstaller = $false
        try {
            & $Python -c "import PyInstaller" 2>$null
            $hasPyInstaller = $LASTEXITCODE -eq 0
        } catch {
            $hasPyInstaller = $false
        }
        if (-not $hasPyInstaller) {
            & $Python -m pip install "pyinstaller>=6.10,<7"
        }
    }

    $AlembicData = (Join-Path $Backend "alembic") + ";alembic"
    $PdfAssetData = (Join-Path $Backend "app\pdf\assets") + ";app\pdf\assets"

    & $Python -m PyInstaller `
        --noconfirm `
        --clean `
        --onedir `
        --name FNLiftingBackend `
        --distpath backend-dist `
        --workpath .runtime\pyinstaller-work `
        --specpath .runtime\pyinstaller-spec `
        --add-data $AlembicData `
        --add-data $PdfAssetData `
        --hidden-import "uvicorn.logging" `
        --hidden-import "uvicorn.loops.auto" `
        --hidden-import "uvicorn.protocols.http.auto" `
        --hidden-import "uvicorn.protocols.websockets.auto" `
        --hidden-import "uvicorn.lifespan.on" `
        --hidden-import "sqlalchemy.dialects.sqlite" `
        --collect-submodules "reportlab.graphics.barcode" `
        --exclude-module pytest `
        --exclude-module pip `
        backend\desktop_runtime.py

    $Exe = Join-Path $Dist "FNLiftingBackend\FNLiftingBackend.exe"
    if (-not (Test-Path $Exe)) {
        throw "Backend standalone nao foi gerado em $Exe"
    }
    Write-Host "Backend standalone gerado: $Exe" -ForegroundColor Green
}
finally {
    Pop-Location
}
