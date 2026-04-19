[CmdletBinding()]
param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$pyInstallerExe = Join-Path $repoRoot ".venv\Scripts\pyinstaller.exe"
$pyiWorkRoot = Join-Path $repoRoot ".pyinstaller-temp"
$pyiWorkDir = Join-Path $pyiWorkRoot "MediaLens"
$pyiDistRoot = Join-Path $repoRoot ".pyinstaller-dist"
$pyiDistDir = Join-Path $pyiDistRoot ([Guid]::NewGuid().ToString("N"))
$distDir = Join-Path $pyiDistDir "MediaLens"
$isccExe = "C:\Users\glenb\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
$installerPath = Join-Path $repoRoot "MediaLens_Setup.exe"

function Resolve-RequiredMediaTool {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$EnvVar
    )

    $envPath = [Environment]::GetEnvironmentVariable($EnvVar)
    if (-not [string]::IsNullOrWhiteSpace($envPath) -and (Test-Path -LiteralPath $envPath -PathType Leaf)) {
        return (Resolve-Path -LiteralPath $envPath).Path
    }

    $repoCandidate = Join-Path $repoRoot "tools\ffmpeg\bin\$Name.exe"
    if (Test-Path -LiteralPath $repoCandidate -PathType Leaf) {
        return (Resolve-Path -LiteralPath $repoCandidate).Path
    }

    $pathMatches = @(where.exe $Name 2>$null)
    if ($LASTEXITCODE -eq 0 -and $pathMatches.Count -gt 0) {
        return $pathMatches[0]
    }

    throw "Missing required media tool '$Name'. Install FFmpeg locally, place '$Name.exe' under 'tools\ffmpeg\bin', or set $EnvVar to the executable path."
}

if (-not (Test-Path $pyInstallerExe)) {
    throw "Missing venv PyInstaller at '$pyInstallerExe'. Create/install the project .venv before building."
}

if (-not (Test-Path $isccExe)) {
    throw "Inno Setup compiler not found at '$isccExe'."
}

if ($Clean -and (Test-Path $pyiWorkDir)) {
    Write-Host "Removing cached PyInstaller work directory..."
    Remove-Item -LiteralPath $pyiWorkDir -Recurse -Force
}

Write-Host "Building MediaLens bundle with project .venv PyInstaller..."
New-Item -ItemType Directory -Path $pyiWorkDir -Force | Out-Null
New-Item -ItemType Directory -Path $pyiDistDir -Force | Out-Null
& $pyInstallerExe (Join-Path $repoRoot "MediaLens.spec") --noconfirm --workpath $pyiWorkDir --distpath $pyiDistDir
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code $LASTEXITCODE."
}

if (-not (Test-Path $distDir)) {
    throw "Expected application bundle at '$distDir' was not created."
}

$bundledWorkerRegistry = @(
    (Join-Path $distDir "_internal\app\mediamanager\ai_captioning\model_registry.py"),
    (Join-Path $distDir "app\mediamanager\ai_captioning\model_registry.py")
) | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if (-not $bundledWorkerRegistry) {
    throw "PyInstaller bundle is missing local AI worker source files. Check MediaLens.spec datas."
}

$bundledRequirements = @(
    "requirements-local-ai-wd-swinv2.txt",
    "requirements-local-ai-internlm-xcomposer2.txt",
    "requirements-local-ai-gemma.txt"
)
foreach ($requirementsFile in $bundledRequirements) {
    $matches = @(
        (Join-Path $distDir "_internal\$requirementsFile"),
        (Join-Path $distDir $requirementsFile)
    ) | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf }
    if ($matches.Count -eq 0) {
        throw "PyInstaller bundle is missing '$requirementsFile'. Check MediaLens.spec datas."
    }
}

$forbiddenLocalAiPackages = @(
    "accelerate",
    "huggingface_hub",
    "onnxruntime",
    "safetensors",
    "sentencepiece",
    "tokenizers",
    "torch",
    "torchvision",
    "transformers"
)
foreach ($packageName in $forbiddenLocalAiPackages) {
    $matches = @(
        (Join-Path $distDir "_internal\$packageName"),
        (Join-Path $distDir "$packageName")
    ) | Where-Object { Test-Path -LiteralPath $_ }
    if ($matches.Count -gt 0) {
        throw "PyInstaller bundle unexpectedly includes local AI runtime package '$packageName'. Keep model dependencies in per-model runtimes."
    }
}

$ffmpegExe = Resolve-RequiredMediaTool -Name "ffmpeg" -EnvVar "MEDIALENS_FFMPEG_PATH"
$ffprobeExe = Resolve-RequiredMediaTool -Name "ffprobe" -EnvVar "MEDIALENS_FFPROBE_PATH"
$mediaToolDest = Join-Path $distDir "tools\ffmpeg\bin"
New-Item -ItemType Directory -Path $mediaToolDest -Force | Out-Null
Copy-Item -LiteralPath $ffmpegExe -Destination (Join-Path $mediaToolDest "ffmpeg.exe") -Force
Copy-Item -LiteralPath $ffprobeExe -Destination (Join-Path $mediaToolDest "ffprobe.exe") -Force
Write-Host "Bundled media tools:"
Write-Host "  ffmpeg: $ffmpegExe"
Write-Host "  ffprobe: $ffprobeExe"

$pythonBootstrapName = "python-3.12.10-amd64.exe"
$pythonBootstrapSource = Join-Path $repoRoot "tools\python\$pythonBootstrapName"
if (Test-Path -LiteralPath $pythonBootstrapSource -PathType Leaf) {
    $pythonBootstrapDest = Join-Path $distDir "tools\python"
    New-Item -ItemType Directory -Path $pythonBootstrapDest -Force | Out-Null
    Copy-Item -LiteralPath $pythonBootstrapSource -Destination (Join-Path $pythonBootstrapDest $pythonBootstrapName) -Force
    Write-Host "Bundled local AI Python bootstrap: $pythonBootstrapSource"
}
else {
    Write-Host "Local AI Python bootstrap not bundled; installed apps will download it on first model install."
}

$qtConfSource = Join-Path $repoRoot "qt.conf"
if (Test-Path $qtConfSource) {
    Copy-Item -LiteralPath $qtConfSource -Destination (Join-Path $distDir "qt.conf") -Force
}

Write-Host "Compiling MediaLens installer with Inno Setup..."
Push-Location $repoRoot
try {
    & $isccExe "/DMyBuildSourceDir=$distDir" "installer.iss"
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup compile failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}

if (-not (Test-Path $installerPath)) {
    throw "Expected installer at '$installerPath' was not created."
}

$installer = Get-Item $installerPath
Write-Host "Build complete:"
Write-Host "  Bundle: $distDir"
Write-Host "  Installer: $($installer.FullName)"
Write-Host "  Size: $($installer.Length) bytes"
