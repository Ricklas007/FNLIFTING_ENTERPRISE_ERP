param(
    [switch]$SkipTests,
    [switch]$SkipFrontendBuild,
    [switch]$SkipBackendHealth,
    [int]$BackendPort = 8000
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Failures = New-Object System.Collections.Generic.List[string]
$Warnings = New-Object System.Collections.Generic.List[string]

function Add-Failure {
    param([string]$Message)
    $Failures.Add($Message) | Out-Null
}

function Add-Warning {
    param([string]$Message)
    $Warnings.Add($Message) | Out-Null
}

function Invoke-Checked {
    param(
        [string]$Label,
        [scriptblock]$Command
    )
    Write-Host "==> $Label"
    try {
        & $Command
        if ($LASTEXITCODE -ne $null -and $LASTEXITCODE -ne 0) {
            Add-Failure "$Label failed with exit code $LASTEXITCODE"
        }
    }
    catch {
        Add-Failure "$Label failed: $($_.Exception.Message)"
    }
}

function Test-CommandExists {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

Push-Location $Root
try {
    $criticalPatterns = @(
        'TODO',
        'FIXME',
        'WIP',
        'INCOMPLETE',
        'FOUNDATION_ONLY',
        'NOT IMPLEMENTED',
        'BROKEN',
        'NotImplementedError',
        'toast\("Em desenvolvimento',
        'onClick=\{\(\) => \{\}\}',
        'href="#"'
    )

    $scanPaths = @("backend/app", "frontend/src", "desktop", "package.json")
    if (Test-CommandExists "rg") {
        foreach ($pattern in $criticalPatterns) {
            $matches = & rg -n --glob "!**/node_modules/**" --glob "!frontend/src/features/maps/providers/mapStyles.ts" -e $pattern @scanPaths 2>$null
            if ($matches) {
                Add-Failure "Critical marker found for pattern '$pattern': $($matches[0])"
            }
        }
    }
    else {
        Add-Warning "ripgrep not found; marker scan was skipped"
    }

    if (-not (Select-String -Path "README.md" -Pattern "BUILD STATUS: INTERNAL DEVELOPMENT BUILD" -Quiet)) {
        Add-Failure "README.md must declare BUILD STATUS: INTERNAL DEVELOPMENT BUILD"
    }

    $frontendPackage = Get-Content "frontend/package.json" -Raw | ConvertFrom-Json
    if (-not $frontendPackage.dependencies.'maplibre-gl') {
        Add-Failure "frontend/package.json must include maplibre-gl"
    }
    if (-not $frontendPackage.dependencies.pmtiles) {
        Add-Failure "frontend/package.json must include pmtiles"
    }

    if (Select-String -Path "frontend/src/components/RealFleetMap.tsx" -Pattern "angola-map|fallbackPosition|fallback-only|<svg" -Quiet) {
        Add-Failure "Operational fleet map still contains static/fallback drawing implementation"
    }

    if (-not (Test-Path "frontend/src/features/maps/components/GisFleetMap.tsx")) {
        Add-Failure "GIS feature map component is missing"
    }

    if (-not (Test-Path "frontend/public/maps/styles/fnl-dark.json")) {
        Add-Failure "FNL dark MapLibre style metadata is missing"
    }

    if (-not $SkipFrontendBuild) {
        Invoke-Checked "Frontend build" { npm --prefix frontend run build }
    }

    if (-not $SkipTests) {
        Invoke-Checked "Backend tests" { backend\.venv\Scripts\python.exe -m pytest backend\tests -q }
        Invoke-Checked "Alembic current" { Push-Location backend; try { .\.venv\Scripts\python.exe -m alembic current } finally { Pop-Location } }
        Invoke-Checked "Alembic heads" { Push-Location backend; try { .\.venv\Scripts\python.exe -m alembic heads } finally { Pop-Location } }
    }

    if (-not $SkipBackendHealth) {
        try {
            $ready = Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/ready" -TimeoutSec 5
            if ($ready.status -ne "ready") {
                Add-Failure "Backend /ready returned status '$($ready.status)'"
            }
        }
        catch {
            Add-Warning "Backend /ready was not reachable on 127.0.0.1:$BackendPort; run local backend before final release gate"
        }
    }

    Write-Host ""
    Write-Host "Release readiness summary"
    Write-Host "Failures: $($Failures.Count)"
    Write-Host "Warnings: $($Warnings.Count)"
    foreach ($warning in $Warnings) {
        Write-Host "WARN: $warning" -ForegroundColor Yellow
    }
    foreach ($failure in $Failures) {
        Write-Host "FAIL: $failure" -ForegroundColor Red
    }

    if ($Failures.Count -gt 0) {
        exit 1
    }
    exit 0
}
finally {
    Pop-Location
}
