<#
.SYNOPSIS
Point this Windows user profile at the installed MediaLens local AI folders.

.DESCRIPTION
Developer convenience script only. It updates the per-user MediaLens
settings.ini so dev runs and installed runs use the same local AI model,
runtime, and Python bootstrap folders under %APPDATA%\MediaLens.
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$SettingsPath = (Join-Path $env:APPDATA "MediaLens\settings.ini"),
    [string]$MediaLensAppData = (Join-Path $env:APPDATA "MediaLens")
)

$ErrorActionPreference = "Stop"

function Set-IniValue {
    param(
        [string[]]$Lines,
        [string]$Section,
        [string]$Key,
        [string]$Value
    )

    $sectionHeader = "[$Section]"
    $sectionStart = -1
    for ($i = 0; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i].Trim() -ieq $sectionHeader) {
            $sectionStart = $i
            break
        }
    }

    if ($sectionStart -lt 0) {
        if ($Lines.Count -gt 0 -and $Lines[-1].Trim() -ne "") {
            $Lines += ""
        }
        $Lines += $sectionHeader
        $Lines += "$Key=$Value"
        return $Lines
    }

    $sectionEnd = $Lines.Count
    for ($i = $sectionStart + 1; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i].Trim().StartsWith("[") -and $Lines[$i].Trim().EndsWith("]")) {
            $sectionEnd = $i
            break
        }
    }

    for ($i = $sectionStart + 1; $i -lt $sectionEnd; $i++) {
        if ($Lines[$i] -match "^\s*$([regex]::Escape($Key))\s*=") {
            $Lines[$i] = "$Key=$Value"
            return $Lines
        }
    }

    $before = @()
    if ($sectionEnd -gt 0) {
        $before = $Lines[0..($sectionEnd - 1)]
    }
    $after = @()
    if ($sectionEnd -lt $Lines.Count) {
        $after = $Lines[$sectionEnd..($Lines.Count - 1)]
    }
    return @($before + "$Key=$Value" + $after)
}

function Remove-IniSection {
    param(
        [string[]]$Lines,
        [string]$Section
    )

    $sectionHeader = "[$Section]"
    $sectionStart = -1
    for ($i = 0; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i].Trim() -ieq $sectionHeader) {
            $sectionStart = $i
            break
        }
    }
    if ($sectionStart -lt 0) {
        return $Lines
    }

    $sectionEnd = $Lines.Count
    for ($i = $sectionStart + 1; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i].Trim().StartsWith("[") -and $Lines[$i].Trim().EndsWith("]")) {
            $sectionEnd = $i
            break
        }
    }

    $out = @()
    if ($sectionStart -gt 0) {
        $out += $Lines[0..($sectionStart - 1)]
    }
    if ($sectionEnd -lt $Lines.Count) {
        $out += $Lines[$sectionEnd..($Lines.Count - 1)]
    }
    return $out
}

$modelsDir = Join-Path $MediaLensAppData "local_ai_models"
$runtimeRoot = Join-Path $MediaLensAppData "ai-runtimes"
$pythonRoot = Join-Path $MediaLensAppData "python\cpython-3.12.10"

New-Item -ItemType Directory -Force -Path $modelsDir, $runtimeRoot, $pythonRoot | Out-Null

$settingsDir = Split-Path -Parent $SettingsPath
New-Item -ItemType Directory -Force -Path $settingsDir | Out-Null

$lines = @()
if (Test-Path -LiteralPath $SettingsPath) {
    $lines = @(Get-Content -LiteralPath $SettingsPath)
}

$lines = Set-IniValue -Lines $lines -Section "ai_caption" -Key "models_dir" -Value ($modelsDir -replace "\\", "/")
$lines = Set-IniValue -Lines $lines -Section "ai_caption" -Key "runtime_root" -Value ($runtimeRoot -replace "\\", "/")
$lines = Set-IniValue -Lines $lines -Section "ai_caption" -Key "python_bootstrap_root" -Value ($pythonRoot -replace "\\", "/")
$lines = Remove-IniSection -Lines $lines -Section "ai_caption/runtime_python"

if ($PSCmdlet.ShouldProcess($SettingsPath, "Point MediaLens local AI paths at installed app-data folders")) {
    Set-Content -LiteralPath $SettingsPath -Value $lines -Encoding UTF8
}

Write-Host "MediaLens local AI paths now point to:"
Write-Host "  Models:  $modelsDir"
Write-Host "  Runtimes: $runtimeRoot"
Write-Host "  Python:   $pythonRoot"
