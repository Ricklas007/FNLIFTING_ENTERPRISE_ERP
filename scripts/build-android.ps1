param(
    [switch]$InstallPortableJdk,
    [switch]$InstallPortableAndroidSdk,
    [switch]$AcceptAndroidSdkLicenses,
    [int]$DownloadMaxTimeSeconds = 0,
    [int]$CompileSdkVersion = 35,
    [string]$BuildToolsVersion = "35.0.0",
    [string]$CommandLineToolsRevision = "14742923"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$JdkRuntimeDir = Join-Path $Root ".runtime\android-jdk"
$AndroidSdkRoot = Join-Path $Root ".runtime\android-sdk"
$AndroidUserHome = Join-Path $Root ".runtime\android-home"
$DownloadDir = Join-Path $Root ".runtime\downloads"
$CapacitorNodeShim = Join-Path $Root "scripts\capacitor-os-userinfo-shim.cjs"
$ProjectGradleHome = Join-Path $Root ".runtime\gradle-home"
$PortableJdkUrl = "https://aka.ms/download-jdk/microsoft-jdk-17-windows-x64.zip"
$CommandLineToolsUrl = "https://dl.google.com/android/repository/commandlinetools-win-$CommandLineToolsRevision`_latest.zip"

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

function Invoke-ResumableDownload {
    param(
        [string]$Url,
        [string]$OutputPath,
        [int]$MinimumBytes,
        [string]$Description
    )

    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutputPath) | Out-Null

    $partPath = "$OutputPath.part"
    if (Test-Path -LiteralPath $OutputPath) {
        $existing = Get-Item -LiteralPath $OutputPath
        if ($existing.Length -ge $MinimumBytes) {
            return
        }

        Write-Host "Removing incomplete $Description archive from previous run..."
        Remove-Item -LiteralPath $OutputPath -Force
    }

    if (Test-Path -LiteralPath $partPath) {
        Write-Host "Resuming $Description download in .runtime..."
    }
    else {
        Write-Host "Downloading $Description to .runtime..."
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
            $Url
        )

        if ($DownloadMaxTimeSeconds -gt 0) {
            $curlArgs = @("--max-time", "$DownloadMaxTimeSeconds") + $curlArgs
        }

        & $curl.Source @curlArgs
        if ($LASTEXITCODE -ne 0) {
            throw "$Description download did not finish. Run the same command again to resume it."
        }
    }
    else {
        Invoke-WebRequest -Uri $Url -OutFile $partPath
    }

    $download = Get-Item -LiteralPath $partPath
    if ($download.Length -lt $MinimumBytes) {
        throw "Downloaded $Description archive is unexpectedly small: $($download.Length) bytes."
    }

    Move-Item -LiteralPath $partPath -Destination $OutputPath -Force
}

function Install-PortableJdk {
    New-Item -ItemType Directory -Force -Path $JdkRuntimeDir, $DownloadDir | Out-Null

    $zipPath = Join-Path $DownloadDir "microsoft-jdk17-windows-x64.zip"
    Invoke-ResumableDownload `
        -Url $PortableJdkUrl `
        -OutputPath $zipPath `
        -MinimumBytes 100MB `
        -Description "Microsoft OpenJDK 17"

    $extractDir = Join-Path $JdkRuntimeDir "extract"
    $finalDir = Join-Path $JdkRuntimeDir "jdk-17"

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
        (Join-Path $JdkRuntimeDir "jdk-17"),
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

function Get-SdkManager {
    param([string]$SdkRoot)
    return Join-Path $SdkRoot "cmdline-tools\latest\bin\sdkmanager.bat"
}

function ConvertTo-AndroidLocalPropertiesValue {
    param([string]$Path)

    $normalized = ($Path -replace "\\", "/")
    $builder = [System.Text.StringBuilder]::new()

    foreach ($character in $normalized.ToCharArray()) {
        $codePoint = [int][char]$character
        if ($codePoint -gt 127) {
            [void]$builder.Append(("\u{0:x4}" -f $codePoint))
        }
        else {
            [void]$builder.Append($character)
        }
    }

    return $builder.ToString()
}

function Test-AndroidSdk {
    param([string]$SdkRoot)

    if ([string]::IsNullOrWhiteSpace($SdkRoot)) {
        return $false
    }

    $sdkManager = Get-SdkManager $SdkRoot
    $platformJar = Join-Path $SdkRoot "platforms\android-$CompileSdkVersion\android.jar"
    $aapt2 = Join-Path $SdkRoot "build-tools\$BuildToolsVersion\aapt2.exe"
    $adb = Join-Path $SdkRoot "platform-tools\adb.exe"

    return (Test-Path -LiteralPath $sdkManager) -and
        (Test-Path -LiteralPath $platformJar) -and
        (Test-Path -LiteralPath $aapt2) -and
        (Test-Path -LiteralPath $adb)
}

function Write-AndroidLocalProperties {
    param([string]$SdkRoot)

    $localProperties = Join-Path $Root "android\local.properties"
    $escaped = ConvertTo-AndroidLocalPropertiesValue -Path $SdkRoot
    Set-Content -LiteralPath $localProperties -Value "sdk.dir=$escaped" -Encoding ASCII
}

function Get-CachedGradleExecutable {
    $gradleCommand = Get-Command gradle.bat -ErrorAction SilentlyContinue
    if (-not $gradleCommand) {
        $gradleCommand = Get-Command gradle -ErrorAction SilentlyContinue
    }

    if ($gradleCommand -and $gradleCommand.Source) {
        return $gradleCommand.Source
    }

    $searchRoots = @()
    if ($env:GRADLE_USER_HOME) {
        $searchRoots += (Join-Path $env:GRADLE_USER_HOME "wrapper\dists")
    }
    $searchRoots += (Join-Path $Root ".runtime\gradle-home\wrapper\dists")
    $searchRoots += (Join-Path $env:USERPROFILE ".gradle\wrapper\dists")

    foreach ($searchRoot in $searchRoots | Where-Object { $_ } | Select-Object -Unique) {
        if (-not (Test-Path -LiteralPath $searchRoot)) {
            continue
        }

        $cachedGradle = Get-ChildItem -LiteralPath $searchRoot -Recurse -Filter "gradle.bat" -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match "\\gradle-[^\\]+\\bin\\gradle\.bat$" } |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1

        if ($cachedGradle) {
            return $cachedGradle.FullName
        }
    }

    return $null
}

function Invoke-AndroidGradle {
    param([string[]]$Arguments)

    $cachedGradle = Get-CachedGradleExecutable
    if ($cachedGradle) {
        Write-Host "Using cached Gradle executable=$cachedGradle"
        & $cachedGradle @Arguments
        return
    }

    Write-Host "Using Gradle wrapper because no cached Gradle executable was found..."
    & .\gradlew.bat @Arguments
}

function Invoke-CapacitorSync {
    $previousNodeOptions = $env:NODE_OPTIONS
    $shimOption = "--require=$CapacitorNodeShim"

    try {
        if (Test-Path -LiteralPath $CapacitorNodeShim) {
            $env:NODE_OPTIONS = (($shimOption, $previousNodeOptions) | Where-Object { $_ }) -join " "
        }

        & npm run mobile:sync
        if ($LASTEXITCODE -ne 0) {
            throw "Capacitor sync failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        $env:NODE_OPTIONS = $previousNodeOptions
    }
}

function Invoke-SdkManager {
    param(
        [string]$SdkRoot,
        [string[]]$Arguments,
        [switch]$WithYesInput
    )

    $sdkManager = Get-SdkManager $SdkRoot
    if (-not (Test-Path -LiteralPath $sdkManager)) {
        throw "sdkmanager.bat was not found at $sdkManager"
    }

    if ($WithYesInput) {
        $yes = ("y`r`n" * 200)
        $tempInput = Join-Path $env:TEMP "fnlifting-android-licenses.txt"
        Set-Content -LiteralPath $tempInput -Value $yes -Encoding ASCII
        try {
            $cmdLine = "`"$sdkManager`" --sdk_root=`"$SdkRoot`" $($Arguments -join ' ') < `"$tempInput`""
            & cmd.exe /c $cmdLine
        }
        finally {
            Remove-Item -LiteralPath $tempInput -Force -ErrorAction SilentlyContinue
        }
    }
    else {
        & $sdkManager "--sdk_root=$SdkRoot" @Arguments
    }

    if ($LASTEXITCODE -ne 0) {
        throw "sdkmanager failed with exit code $LASTEXITCODE"
    }
}

function Install-PortableAndroidSdk {
    if (-not $AcceptAndroidSdkLicenses) {
        throw @"
Android SDK is not installed.

This script can install a portable Android SDK into .runtime/android-sdk, but Google Android SDK licenses must be accepted explicitly.

Run:

  powershell -ExecutionPolicy Bypass -File scripts/build-android.ps1 -InstallPortableJdk -InstallPortableAndroidSdk -AcceptAndroidSdkLicenses

or:

  npm run android:build:portable:accept-licenses
"@
    }

    New-Item -ItemType Directory -Force -Path $AndroidSdkRoot, $DownloadDir | Out-Null

    $zipPath = Join-Path $DownloadDir "commandlinetools-win-$CommandLineToolsRevision`_latest.zip"
    Invoke-ResumableDownload `
        -Url $CommandLineToolsUrl `
        -OutputPath $zipPath `
        -MinimumBytes 40MB `
        -Description "Android command-line tools"

    $extractDir = Join-Path $AndroidSdkRoot "cmdline-tools-extract"
    $latestDir = Join-Path $AndroidSdkRoot "cmdline-tools\latest"

    if (Test-Path -LiteralPath $extractDir) {
        Remove-Item -LiteralPath $extractDir -Recurse -Force
    }
    if (Test-Path -LiteralPath $latestDir) {
        Remove-Item -LiteralPath $latestDir -Recurse -Force
    }

    New-Item -ItemType Directory -Force -Path $extractDir, (Split-Path -Parent $latestDir) | Out-Null
    Expand-Archive -LiteralPath $zipPath -DestinationPath $extractDir -Force

    $toolsRoot = Get-ChildItem -LiteralPath $extractDir -Directory |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "bin\sdkmanager.bat") } |
        Select-Object -First 1

    if (-not $toolsRoot) {
        $toolsRoot = Get-ChildItem -LiteralPath $extractDir -Directory -Recurse |
            Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "bin\sdkmanager.bat") } |
            Select-Object -First 1
    }

    if (-not $toolsRoot) {
        throw "Android command-line tools archive was downloaded, but sdkmanager.bat was not found inside it."
    }

    Move-Item -LiteralPath $toolsRoot.FullName -Destination $latestDir
    Remove-Item -LiteralPath $extractDir -Recurse -Force

    $env:ANDROID_HOME = $AndroidSdkRoot
    $env:ANDROID_SDK_ROOT = $AndroidSdkRoot
    $env:PATH = (Join-Path $AndroidSdkRoot "cmdline-tools\latest\bin") + [IO.Path]::PathSeparator +
        (Join-Path $AndroidSdkRoot "platform-tools") + [IO.Path]::PathSeparator + $env:PATH

    $androidUserDir = Join-Path $env:USERPROFILE ".android"
    New-Item -ItemType Directory -Force -Path $androidUserDir | Out-Null
    New-Item -ItemType File -Force -Path (Join-Path $androidUserDir "repositories.cfg") | Out-Null

    Write-Host "Accepting Android SDK licenses because -AcceptAndroidSdkLicenses was provided..."
    Invoke-SdkManager -SdkRoot $AndroidSdkRoot -Arguments @("--licenses") -WithYesInput

    Write-Host "Installing Android SDK platform-tools, platform android-$CompileSdkVersion and build-tools $BuildToolsVersion..."
    Invoke-SdkManager -SdkRoot $AndroidSdkRoot -Arguments @(
        "platform-tools",
        "platforms;android-$CompileSdkVersion",
        "build-tools;$BuildToolsVersion"
    )

    if (-not (Test-AndroidSdk $AndroidSdkRoot)) {
        throw "Portable Android SDK install finished, but required packages were not found."
    }

    Write-AndroidLocalProperties -SdkRoot $AndroidSdkRoot
    return $AndroidSdkRoot
}

function Resolve-AndroidSdkRoot {
    $candidates = @()

    if ($env:ANDROID_HOME) {
        $candidates += $env:ANDROID_HOME
    }
    if ($env:ANDROID_SDK_ROOT) {
        $candidates += $env:ANDROID_SDK_ROOT
    }

    $candidates += @(
        $AndroidSdkRoot,
        (Join-Path $env:LOCALAPPDATA "Android\Sdk"),
        "C:\Android\Sdk",
        "C:\Program Files\Android\Sdk"
    )

    foreach ($candidate in $candidates | Where-Object { $_ } | Select-Object -Unique) {
        if (Test-AndroidSdk $candidate) {
            $resolved = (Resolve-Path -LiteralPath $candidate).Path
            Write-AndroidLocalProperties -SdkRoot $resolved
            return $resolved
        }
    }

    if ($InstallPortableAndroidSdk) {
        return (Install-PortableAndroidSdk)
    }

    throw @"
No valid Android SDK was found.

Install Android Studio/SDK and set ANDROID_HOME, or run:

  npm run android:build:portable:accept-licenses

The portable Android SDK mode stores tools in .runtime/android-sdk and writes android/local.properties.
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

try {
    $sdkRoot = Resolve-AndroidSdkRoot
}
catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

$env:ANDROID_HOME = $sdkRoot
$env:ANDROID_SDK_ROOT = $sdkRoot
$env:ANDROID_USER_HOME = $AndroidUserHome
$env:PATH = (Join-Path $sdkRoot "platform-tools") + [IO.Path]::PathSeparator +
    (Join-Path $sdkRoot "cmdline-tools\latest\bin") + [IO.Path]::PathSeparator + $env:PATH
New-Item -ItemType Directory -Force -Path $AndroidUserHome | Out-Null

Write-Host "Using ANDROID_HOME=$sdkRoot"
Write-Host "Using ANDROID_USER_HOME=$AndroidUserHome"

$previousGradleUserHome = $env:GRADLE_USER_HOME
$env:GRADLE_USER_HOME = $ProjectGradleHome
New-Item -ItemType Directory -Force -Path $ProjectGradleHome | Out-Null
Write-Host "Using GRADLE_USER_HOME=$ProjectGradleHome"

Push-Location $Root
try {
    Invoke-CapacitorSync

    Push-Location (Join-Path $Root "android")
    try {
        Invoke-AndroidGradle -Arguments @("assembleDebug")
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
    $env:GRADLE_USER_HOME = $previousGradleUserHome
}
