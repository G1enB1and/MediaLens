[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$pyInstallerExe = Join-Path $repoRoot ".venv\Scripts\pyinstaller.exe"
$pyiWorkRoot = Join-Path $repoRoot ".pyinstaller-temp"
$pyiWorkDir = Join-Path $pyiWorkRoot ([Guid]::NewGuid().ToString("N"))
$pyiDistRoot = Join-Path $repoRoot ".pyinstaller-dist"
$pyiDistDir = Join-Path $pyiDistRoot ([Guid]::NewGuid().ToString("N"))
$distDir = Join-Path $pyiDistDir "MediaLens"
$isccExe = "C:\Users\glenb\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
$installerPath = Join-Path $repoRoot "MediaLens_Setup.exe"

if (-not (Test-Path $pyInstallerExe)) {
    throw "Missing venv PyInstaller at '$pyInstallerExe'. Create/install the project .venv before building."
}

if (-not (Test-Path $isccExe)) {
    throw "Inno Setup compiler not found at '$isccExe'."
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
