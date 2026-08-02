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

function Read-EnvFile {
    param([string]$Path)
    $result = @{}
    if (-not (Test-Path $Path)) {
        return $result
    }
    foreach ($line in Get-Content $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) {
            continue
        }
        $parts = $trimmed.Split("=", 2)
        $result[$parts[0].Trim()] = $parts[1].Trim().Trim('"').Trim("'")
    }
    return $result
}

function Test-Truthy {
    param([string]$Value)
    if ($null -eq $Value) {
        $Value = ""
    }
    return @("1", "true", "yes", "on", "enabled") -contains $Value.ToLowerInvariant()
}

function First-NonEmpty {
    foreach ($value in $args) {
        if ($null -ne $value -and "$value".Length -gt 0) {
            return "$value"
        }
    }
    return ""
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

    $backendEnv = Read-EnvFile "backend/.env"
    $frontendEnv = Read-EnvFile "frontend/.env.local"

    if (-not (Test-CommandExists "docker")) {
        Add-Warning "Docker CLI not available; PostgreSQL/MinIO/staging compose runtime validation is BLOCKED_EXTERNAL"
    }
    else {
        Invoke-Checked "Docker compose base config" {
            docker compose -f docker-compose.yml config *> $null
        }
        Invoke-Checked "Docker compose staging config" {
            if (-not $env:SECRET_KEY) { $env:SECRET_KEY = "readiness-secret-key-with-more-than-32-characters" }
            if (-not $env:BACKUP_ENCRYPTION_KEY) { $env:BACKUP_ENCRYPTION_KEY = "readiness-backup-key-with-more-than-32" }
            if (-not $env:POSTGRES_PASSWORD) { $env:POSTGRES_PASSWORD = "readiness-postgres-password" }
            if (-not $env:MINIO_ROOT_PASSWORD) { $env:MINIO_ROOT_PASSWORD = "readiness-minio-password" }
            docker compose -f docker-compose.yml -f docker-compose.staging.yml config *> $null
        }
    }

    $serpEnabled = Test-Truthy (First-NonEmpty $backendEnv["SERPAPI_ENABLED"] $env:SERPAPI_ENABLED)
    $serpKey = First-NonEmpty $backendEnv["SERPAPI_KEY"] $env:SERPAPI_KEY
    $serpKeySet = [bool]($serpKey -and $serpKey.Length -gt 0)
    if (-not $serpEnabled -or -not $serpKeySet) {
        Add-Warning "SerpApi is REQUIRED_NOT_CONFIGURED for place search; configure only outside Git"
    }
    else {
        Add-Warning "SerpApi key is configured but live provider status is not asserted by this unauthenticated gate; keep latest AUTH_ERROR/CONNECTED evidence in docs"
    }

    $googleKey = First-NonEmpty $frontendEnv["VITE_GOOGLE_MAPS_API_KEY"] $env:VITE_GOOGLE_MAPS_API_KEY $backendEnv["GOOGLE_MAPS_API_KEY"] $env:GOOGLE_MAPS_API_KEY
    $googleKeySet = [bool]$googleKey
    if (-not $googleKeySet) {
        Add-Warning "Google Maps key is REQUIRED_NOT_CONFIGURED for Google renderer; MapLibre fallback remains available"
    }

    if (-not (Test-Path "android/app/build/outputs/apk/debug/app-debug.apk")) {
        Add-Warning "Android APK debug artifact is not present; Android runtime acceptance remains pending"
    }

    if (-not (Test-Path "docs/PHASE_14_CLOUD_ACCEPTANCE.md")) {
        Add-Warning "Phase 14 cloud acceptance document is missing"
    }

    if (-not (Test-Path "docs/PHASE_15_GPS_PILOT_ACCEPTANCE.md")) {
        Add-Warning "Phase 15 GPS pilot acceptance document is missing"
    }

    if (-not (Test-Path "backend/tests/test_gps_pilot_acceptance.py")) {
        Add-Warning "Phase 15 GPS pilot acceptance test is missing"
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
