<#
.SYNOPSIS
Installs the prompt-automation application using pipx.
.DESCRIPTION
This script installs prompt-automation from the local project and verifies that
all components are available.
#>

. "$PSScriptRoot/utils.ps1"

if (-not (Test-ExecutionPolicy)) { Fail "Cannot proceed due to execution policy restrictions." }

$LogDir = Join-Path $env:USERPROFILE '.prompt-automation\logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir 'install-app.log'
Start-Transcript -Path $LogFile -Append | Out-Null
trap { Write-Warning "Error on line $($_.InvocationInfo.ScriptLineNumber). See $LogFile" }

Info "Installing prompt-automation..."

if (-not [System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::Windows)) {
    Fail "This installer must be run on Windows."
}

# Ensure pipx command
$global:pipxCommand = $null
$pipxCmd = Get-Command pipx -ErrorAction SilentlyContinue
if ($pipxCmd) { $global:pipxCommand = 'pipx' } else { $global:pipxCommand = 'python -m pipx' }

# Get project root
$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)
$pyprojectPath = Join-Path $projectRoot 'pyproject.toml'
if (-not (Test-Path $pyprojectPath)) { Fail "pyproject.toml not found at $pyprojectPath" }

if ($global:pipxCommand -eq 'python -m pipx') {
    python -m pipx install --force "$projectRoot"
} else {
    & $global:pipxCommand install --force "$projectRoot"
}
if ($LASTEXITCODE -ne 0) { Fail 'Failed to install prompt-automation from local source.' }

# Verify command
$promptAutomationCmd = Get-Command prompt-automation -ErrorAction SilentlyContinue
if ($promptAutomationCmd) {
    Info "✓ prompt-automation command is available"
    try { $version = & prompt-automation --version 2>&1; Info "   Version: $version" } catch { }
} else {
    Write-Warning 'prompt-automation command not found in PATH. You may need to restart your terminal.'
}

# Display summary
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

Stop-Transcript | Out-Null
Info "Installation complete. Log saved to $LogFile"
