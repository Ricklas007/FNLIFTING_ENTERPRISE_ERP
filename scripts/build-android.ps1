param(
    [switch]$InstallPortableJdk,
    [int]$DownloadMaxTimeSeconds = 0
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$RuntimeDir = Join-Path $Root ".runtime\android-jdk"
$DownloadDir = Join-Path $Root ".runtime\downloads"
$PortableJdkUrl = "https://aka.ms/download-jdk/microsoft-jdk-17-windows-x64.zip"

function Test-JdkHome {
    param([string]$JdkHome)

    if ([string]::IsNullOrWhiteSpace($JdkHome)) {
        return $false
    }

    $java = Join-Path $JdkHome "bin\java.exe"
    $javac = Join-Path $JdkHome "bin\javac.exe"

    return (Test-Path -LiteralPath $java) -and (Test-Path -LiteralPath $javac)
}

function Get-JdkFromCommand {
    $javac = Get-Command javac.exe -ErrorAction SilentlyContinue
    if (-not $javac) {
        $javac = Get-Command javac -ErrorAction SilentlyContinue
    }

    if ($javac -and $javac.Source) {
        return (Split-Path -Parent (Split-Path -Parent $javac.Source))
    }

    return $null
}

function Install-PortableJdk {
    New-Item -ItemType Directory -Force -Path $RuntimeDir, $DownloadDir | Out-Null

    $zipPath = Join-Path $DownloadDir "microsoft-jdk17-windows-x64.zip"
    $partPath = "$zipPath.part"
    if (Test-Path -LiteralPath $zipPath) {
        $existing = Get-Item -LiteralPath $zipPath
        if ($existing.Length -lt 100MB) {
            Write-Host "Removing incomplete portable JDK archive from previous run..."
            Remove-Item -LiteralPath $zipPath -Force
        }
    }

    if (-not (Test-Path -LiteralPath $zipPath)) {
        if (Test-Path -LiteralPath $partPath) {
            Write-Host "Resuming Microsoft OpenJDK 17 download in .runtime..."
        }
        else {
            Write-Host "Downloading Microsoft OpenJDK 17 to .runtime..."
        }

        $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
        if ($curl) {
            $curlArgs = @(
                "-L",
                "--fail",
                "--retry", "2",
                "--connect-timeout", "30",
                "--speed-limit", "10240",
                "--speed-time", "60",
                "-C", "-",
                "--output", $partPath,
                $PortableJdkUrl
            )

            if ($DownloadMaxTimeSeconds -gt 0) {
                $curlArgs = @("--max-time", "$DownloadMaxTimeSeconds") + $curlArgs
            }

            & $curl.Source @curlArgs
            if ($LASTEXITCODE -ne 0) {
                throw "Portable JDK download did not finish. Run 'npm run android:build:portable' again to resume it."
            }
        }
        else {
            Invoke-WebRequest -Uri $PortableJdkUrl -OutFile $partPath
        }

        $download = Get-Item -LiteralPath $partPath
        if ($download.Length -lt 100MB) {
            throw "Downloaded JDK archive is unexpectedly small: $($download.Length) bytes."
        }

        Move-Item -LiteralPath $partPath -Destination $zipPath -Force
    }

    $extractDir = Join-Path $RuntimeDir "extract"
    $finalDir = Join-Path $RuntimeDir "jdk-17"

    if (Test-Path -LiteralPath $extractDir) {
        Remove-Item -LiteralPath $extractDir -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $extractDir | Out-Null

    Expand-Archive -LiteralPath $zipPath -DestinationPath $extractDir -Force

    $jdkHome = Get-ChildItem -LiteralPath $extractDir -Directory |
        Where-Object { Test-JdkHome $_.FullName } |
        Select-Object -First 1

    if (-not $jdkHome) {
        throw "Portable JDK archive was downloaded, but no valid JDK home was found inside it."
    }

    if (Test-Path -LiteralPath $finalDir) {
        Remove-Item -LiteralPath $finalDir -Recurse -Force
    }
    Move-Item -LiteralPath $jdkHome.FullName -Destination $finalDir
    Remove-Item -LiteralPath $extractDir -Recurse -Force

    return $finalDir
}

function Resolve-JdkHome {
    $candidates = @()

    if ($env:JAVA_HOME) {
        $candidates += $env:JAVA_HOME
    }

    $commandHome = Get-JdkFromCommand
    if ($commandHome) {
        $candidates += $commandHome
    }

    $candidates += @(
        (Join-Path $RuntimeDir "jdk-17"),
        "C:\Program Files\Android\Android Studio\jbr",
        "C:\Program Files\Android\Android Studio\jre",
        "C:\Program Files\Eclipse Adoptium\jdk-17",
        "C:\Program Files\Java\jdk-17"
    )

    foreach ($candidate in $candidates | Where-Object { $_ } | Select-Object -Unique) {
        if (Test-JdkHome $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    if ($InstallPortableJdk) {
        return (Install-PortableJdk)
    }

    throw @"
No valid JDK was found.

Install JDK 17+ and set JAVA_HOME, install Android Studio, or run:

  npm run android:build:portable

The portable mode downloads JDK 17 into .runtime/android-jdk, which is ignored by Git.
"@
}

try {
    $jdkHome = Resolve-JdkHome
}
catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

$env:JAVA_HOME = $jdkHome
$env:PATH = (Join-Path $jdkHome "bin") + [IO.Path]::PathSeparator + $env:PATH

Write-Host "Using JAVA_HOME=$jdkHome"
& java -version

Push-Location $Root
try {
    & npm run mobile:sync
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    Push-Location (Join-Path $Root "android")
    try {
        & .\gradlew.bat assembleDebug
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }
    finally {
        Pop-Location
    }
}
finally {
    Pop-Location
}
