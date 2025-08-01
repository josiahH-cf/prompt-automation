<#
.SYNOPSIS
Master installation script for prompt-automation on Windows.
.DESCRIPTION
Orchestrates dependency installation, application install, hotkey setup and
basic verification. Handles logging, execution policy checks and WSL path
scenarios.
#>

. "$PSScriptRoot/utils.ps1"

if (-not (Test-ExecutionPolicy)) { Fail "Cannot proceed due to execution policy restrictions." }

# Set up logging
$LogDir = Join-Path $env:USERPROFILE '.prompt-automation\logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir 'install.log'
Start-Transcript -Path $LogFile -Append | Out-Null
trap { Write-Warning "Error on line $($_.InvocationInfo.ScriptLineNumber). See $LogFile" }

Info "Starting prompt-automation installation..."

# Ensure we are running on Windows. If not, fall back to WSL-compatible installer
if (-not [System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::Windows)) {
    Write-Warning 'Non-Windows environment detected. Running WSL-compatible installer if available.'
    $wslScript = Join-Path $PSScriptRoot 'install-wsl-compatible.ps1'
    if (Test-Path $wslScript) {
        & $wslScript
        Stop-Transcript | Out-Null
        exit $LASTEXITCODE
    } else {
        Fail 'This installer must be run on Windows.'
    }
}

# Run dependency installer
$depScript = Join-Path $PSScriptRoot 'install-dependencies.ps1'
if (Test-Path $depScript) {
    Info 'Installing dependencies...'
    & $depScript
    if ($LASTEXITCODE -ne 0) { Fail 'Dependency installation failed.' }
} else {
    Fail 'install-dependencies.ps1 not found.'
}

# Install the application from local source
$appScript = Join-Path $PSScriptRoot 'install-prompt-automation.ps1'
if (Test-Path $appScript) {
    Info 'Installing prompt-automation application...'
    & $appScript
    if ($LASTEXITCODE -ne 0) { Fail 'Application installation failed.' }
} else {
    Fail 'install-prompt-automation.ps1 not found.'
}

# Verify hotkey setup
$hotkeyScript = Join-Path $PSScriptRoot 'troubleshoot-hotkeys.ps1'
if (Test-Path $hotkeyScript) {
    Info 'Verifying hotkey registration...'
    & $hotkeyScript -Status
}

# Summary status
Info "\n=== Installation Summary ==="
$components = @(
    @{Name='Python'; Command='python'; Status=(Get-Command python -ErrorAction SilentlyContinue) -ne $null},
    @{Name='pipx'; Command='pipx'; Status=(Get-Command pipx -ErrorAction SilentlyContinue) -ne $null},
    @{Name='fzf'; Command='fzf'; Status=(Get-Command fzf -ErrorAction SilentlyContinue) -ne $null},
    @{Name='espanso'; Command='espanso'; Status=(Get-Command espanso -ErrorAction SilentlyContinue) -ne $null},
    @{Name='AutoHotkey'; Command='AutoHotkey'; Status=(Get-Command AutoHotkey -ErrorAction SilentlyContinue) -ne $null},
    @{Name='prompt-automation'; Command='prompt-automation'; Status=(Get-Command prompt-automation -ErrorAction SilentlyContinue) -ne $null}
)
foreach ($component in $components) {
    $status = if ($component.Status) { '[OK] Installed' } else { '[FAIL] Not found' }
    $color = if ($component.Status) { 'Green' } else { 'Red' }
    Write-Host "- $($component.Name): " -NoNewline
    Write-Host $status -ForegroundColor $color
}

Info "\nFor troubleshooting tips see docs or run scripts/troubleshoot-hotkeys.ps1 --Fix"

Stop-Transcript | Out-Null
Info "Installation log saved to $LogFile"
