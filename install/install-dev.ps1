<#
.SYNOPSIS
Developer-friendly installer for prompt-automation.

.DESCRIPTION
Performs an editable install so local code changes take effect immediately,
disables auto-updates during development, and assigns the standard hotkey
(Ctrl+Shift+J) by generating the AutoHotkey/Espanso configs.

Run in an elevated or normal PowerShell:
  ./install/install-dev.ps1

Requires pipx (preferred) or falls back to user pip.
#>

param(
  [switch]$Force
)

function Info($m){ Write-Host $m -ForegroundColor Green }
function Warn($m){ Write-Host $m -ForegroundColor Yellow }
function Fail($m){ Write-Host $m -ForegroundColor Red; exit 1 }

$repoRoot = Resolve-Path "$PSScriptRoot/.."
Push-Location $repoRoot

# Prefer pipx editable install
$pipx = Get-Command pipx -ErrorAction SilentlyContinue
if ($pipx) {
  Info "Installing via pipx (editable) from $repoRoot"
  $cmd = @('pipx','install','--force','--editable', "$repoRoot")
  $p = Start-Process -PassThru -FilePath $cmd[0] -ArgumentList $cmd[1..($cmd.Length-1)] -NoNewWindow -Wait
  if ($p.ExitCode -ne 0) { Warn "pipx install failed (code $($p.ExitCode))" }
} else {
  Warn "pipx not found; falling back to pip user editable install"
  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) {
    & py -m pip install --user -e "$repoRoot" --upgrade
  } else {
    & python -m pip install --user -e "$repoRoot" --upgrade
  }
}

# Disable background auto-updates in dev so local edits aren’t overwritten
[Environment]::SetEnvironmentVariable('PROMPT_AUTOMATION_AUTO_UPDATE', '0', 'User')
[Environment]::SetEnvironmentVariable('PROMPT_AUTOMATION_DEV', '1', 'User')
Info "Set PROMPT_AUTOMATION_AUTO_UPDATE=0 and PROMPT_AUTOMATION_DEV=1 for current user"

# Assign the standard hotkey using multiple fallbacks
try {
  if (Get-Command prompt-automation -ErrorAction SilentlyContinue) {
    & prompt-automation --assign-hotkey
  } elseif (Get-Command prompt_automation -ErrorAction SilentlyContinue) {
    & prompt_automation --assign-hotkey
  } else {
    if (Get-Command py -ErrorAction SilentlyContinue) {
      & py -m prompt_automation --assign-hotkey
    } else {
      & python -m prompt_automation --assign-hotkey
    }
  }
  Info "Hotkey configured. Use Ctrl+Shift+J to open the GUI."
} catch {
  Warn "Hotkey assignment step reported an error: $_"
}

Pop-Location
Info "Developer install complete. Changes to source are now live."

