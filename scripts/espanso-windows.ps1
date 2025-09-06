Param(
  [switch]$DisableLocalBase
)

$ErrorActionPreference = 'Stop'

Function Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
Function Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
Function Err($msg)  { Write-Host "[ERR]  $msg" -ForegroundColor Red }

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

Info "Usage: powershell -File scripts/espanso-windows.ps1 -DisableLocalBase"

