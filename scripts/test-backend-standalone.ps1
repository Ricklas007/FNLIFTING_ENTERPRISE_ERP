param(
    [string]$RuntimeDir = ""
)

$ErrorActionPreference = "Stop"
function Normalize-ProcessPathEnvironment {
    $vars = [System.Environment]::GetEnvironmentVariables("Process")
    if ($vars.Contains("PATH") -and $vars.Contains("Path")) {
        $pathValue = [string]$vars["Path"]
        if (-not $pathValue) { $pathValue = [string]$vars["PATH"] }
        [System.Environment]::SetEnvironmentVariable("PATH", $null, "Process")
        [System.Environment]::SetEnvironmentVariable("Path", $pathValue, "Process")
    }
}
$Root = Split-Path -Parent $PSScriptRoot
$Exe = Join-Path $Root "backend-dist\FNLiftingBackend\FNLiftingBackend.exe"

if (-not (Test-Path $Exe)) {
    throw "Backend standalone nao encontrado. Execute npm run desktop:backend:build primeiro."
}

if (-not $RuntimeDir) {
    $RuntimeDir = Join-Path ([System.IO.Path]::GetTempPath()) ("fnlifting-backend-smoke-" + [Guid]::NewGuid().ToString("N"))
}

$Data = Join-Path $RuntimeDir "data"
$Logs = Join-Path $RuntimeDir "logs"
New-Item -ItemType Directory -Force -Path $Data, $Logs | Out-Null

$env:APP_ENV = "desktop"
$env:ENVIRONMENT = "desktop"
$env:DESKTOP_MODE = "true"
$env:DEBUG = "false"
$env:DATA_DIR = $Data
$env:UPLOAD_DIR = Join-Path $RuntimeDir "uploads"
$env:CERTIFICATE_DIR = Join-Path $RuntimeDir "certificates"
$env:REPORT_DIR = Join-Path $RuntimeDir "reports"
$env:INVOICE_DIR = Join-Path $RuntimeDir "invoices"
$env:RECEIPT_DIR = Join-Path $RuntimeDir "receipts"
$env:BACKUP_DIR = Join-Path $RuntimeDir "backups"
$env:LOG_DIR = $Logs
$env:EXPORT_DIR = Join-Path $RuntimeDir "exports"
$env:MAP_DIR = Join-Path $RuntimeDir "maps"
$env:MAP_CACHE_DIR = Join-Path $RuntimeDir "map-cache"
$env:TEMP_DIR = Join-Path $RuntimeDir "temp"
$env:ATTACHMENT_DIR = Join-Path $RuntimeDir "attachments"
$env:DATABASE_URL = "sqlite:///$((Join-Path $Data 'fnlifting.db').Replace('\','/'))"
$env:SECRET_KEY = "standalone-smoke-secret-key-with-more-than-32-chars"
$env:BACKUP_ENCRYPTION_KEY = "standalone-smoke-backup-key-with-more-than-32-chars"
$env:CORS_ORIGINS = "http://127.0.0.1:19080"
$env:ALLOWED_HOSTS = "127.0.0.1,localhost"

& $Exe migrate
if ($LASTEXITCODE -ne 0) { throw "migrate falhou" }

& $Exe seed
if ($LASTEXITCODE -ne 0) { throw "seed falhou" }

$env:HOST = "127.0.0.1"
$env:PORT = "19081"
$ServerLog = Join-Path $Logs "serve.log"
$ServerErr = Join-Path $Logs "serve.err.log"
Normalize-ProcessPathEnvironment
$proc = Start-Process -FilePath $Exe -ArgumentList @("serve") -RedirectStandardOutput $ServerLog -RedirectStandardError $ServerErr -WindowStyle Hidden -PassThru
try {
    $deadline = (Get-Date).AddSeconds(120)
    do {
        Start-Sleep -Milliseconds 900
        try {
            $ready = Invoke-RestMethod -Uri "http://127.0.0.1:19081/ready" -TimeoutSec 3
            if ($ready.status -eq "ready") {
                Write-Host "Backend standalone smoke OK em $RuntimeDir" -ForegroundColor Green
                exit 0
            }
        } catch {
            if ($proc.HasExited) {
                throw "Backend encerrou antes do readiness. Verifique $ServerErr"
            }
        }
    } while ((Get-Date) -lt $deadline)
    throw "Timeout aguardando /ready"
}
finally {
    if ($proc -and -not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force
    }
}
