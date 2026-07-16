param(
    [switch]$Installed,
    [string]$ExePath = "",
    [int]$Cycles = 3
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

if (-not $ExePath) {
    if ($Installed) {
        $ExePath = "C:\Program Files\FNLIFTING ENTERPRISE ERP\FNLIFTING ENTERPRISE ERP.exe"
    } else {
        $ExePath = Join-Path $Root "release\win-unpacked\FNLIFTING ENTERPRISE ERP.exe"
    }
}

if (-not (Test-Path $ExePath)) {
    throw "Executavel desktop nao encontrado em $ExePath"
}

$RuntimeDir = Join-Path ([System.IO.Path]::GetTempPath()) ("fnlifting-desktop-relaunch-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
$StartupLog = Join-Path $RuntimeDir "logs\startup.log"
$DesktopLog = Join-Path $RuntimeDir "logs\desktop.log"

$previousUserData = $env:FNLIFTING_USER_DATA_DIR
$previousSmoke = $env:FNLIFTING_DESKTOP_SMOKE_TEST
$previousClose = $env:FNLIFTING_DESKTOP_SMOKE_CLOSE_MS

try {
    $env:FNLIFTING_USER_DATA_DIR = $RuntimeDir
    $env:FNLIFTING_DESKTOP_SMOKE_TEST = "1"
    $env:FNLIFTING_DESKTOP_SMOKE_CLOSE_MS = "2500"

    for ($i = 1; $i -le $Cycles; $i++) {
        if (Test-Path $StartupLog) { Remove-Item -LiteralPath $StartupLog -Force }
        $proc = Start-Process -FilePath $ExePath -PassThru -WindowStyle Hidden
        $deadline = (Get-Date).AddSeconds(180)
        $ready = $false
        do {
            Start-Sleep -Milliseconds 1000
            if (Test-Path $StartupLog) {
                $content = Get-Content -Raw $StartupLog
                if ($content -match "DESKTOP_READY") {
                    $ready = $true
                    break
                }
                if ($content -match "boot failed|migration failed|PermissionError|Acesso negado") {
                    throw "Falha detectada no ciclo $i. Verifique $StartupLog"
                }
            }
            if ($proc.HasExited -and -not $ready) {
                throw "Desktop encerrou antes de ficar pronto no ciclo $i. Verifique $DesktopLog"
            }
        } while ((Get-Date) -lt $deadline)

        if (-not $ready) {
            throw "Timeout aguardando DESKTOP_READY no ciclo $i"
        }

        if (-not $proc.HasExited) {
            Wait-Process -Id $proc.Id -Timeout 30 -ErrorAction SilentlyContinue
        }
        if (-not $proc.HasExited) {
            Stop-Process -Id $proc.Id -Force
        }

        if (Test-Path $DesktopLog) {
            $desktop = Get-Content -Raw $DesktopLog
            if ($desktop -match "boot failed|PermissionError|Acesso negado") {
                throw "Erro encontrado no desktop.log apos ciclo $i"
            }
        }
    }

    $Database = Join-Path $RuntimeDir "data\fnlifting.db"
    if (-not (Test-Path $Database)) {
        throw "Base SQLite nao foi criada em userData isolado: $Database"
    }
    Write-Host "Desktop relaunch smoke OK: $Cycles ciclos em $RuntimeDir" -ForegroundColor Green
}
finally {
    $env:FNLIFTING_USER_DATA_DIR = $previousUserData
    $env:FNLIFTING_DESKTOP_SMOKE_TEST = $previousSmoke
    $env:FNLIFTING_DESKTOP_SMOKE_CLOSE_MS = $previousClose
}
