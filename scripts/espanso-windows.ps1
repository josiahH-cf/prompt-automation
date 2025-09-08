Param(
  [switch]$DisableLocalBase,
  [switch]$BackupAllLocalMatches,
  [switch]$ListLocalMatches
)

$ErrorActionPreference = 'Stop'

Function Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
Function Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
Function Err($msg)  { Write-Host "[ERR]  $msg" -ForegroundColor Red }

if ($ListLocalMatches) {
  $matchDir = Join-Path $env:APPDATA 'espanso\match'
  if (Test-Path $matchDir) {
    Info "Listing local match files under: $matchDir"
    Get-ChildItem -Path $matchDir -Filter '*.yml' | ForEach-Object { Write-Host " - $($_.FullName)" }
  } else {
    Warn "Match directory not found: $matchDir"
  }
  return
}

if ($DisableLocalBase) {
  $basePath = Join-Path $env:APPDATA 'espanso\match\base.yml'
  if (Test-Path $basePath) {
    $backup = "$basePath.bak.$([DateTimeOffset]::Now.ToUnixTimeSeconds())"
    Copy-Item -Path $basePath -Destination $backup -Force
    Remove-Item -Path $basePath -Force
    Info "Backed up and removed local base.yml to avoid duplicates: $backup"
  } else {
    Warn "Local base.yml not found; nothing to disable."
  }
  return
}

if ($BackupAllLocalMatches) {
  $matchDir = Join-Path $env:APPDATA 'espanso\match'
  if (Test-Path $matchDir) {
    $backupDir = "$matchDir.bak.$([DateTimeOffset]::Now.ToUnixTimeSeconds())"
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
    Copy-Item -Path (Join-Path $matchDir '*.yml') -Destination $backupDir -Force -ErrorAction SilentlyContinue
    Remove-Item -Path (Join-Path $matchDir '*.yml') -Force -ErrorAction SilentlyContinue
    Info "Backed up all local *.yml to: $backupDir and removed from $matchDir"
    Info "Note: package-managed snippets are unaffected."
  } else {
    Warn "Match directory not found: $matchDir"
  }
  return
}

Info "Usage: powershell -File scripts/espanso-windows.ps1 -DisableLocalBase | -BackupAllLocalMatches | -ListLocalMatches"
