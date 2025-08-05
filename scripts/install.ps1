<#
.SYNOPSIS
Master installation script for prompt-automation on Windows.
.DESCRIPTION
Orchestrates dependency installation, application install, hotkey setup and
basic verification. Handles logging, execution policy checks and WSL path
scenarios.
#>

# Import utility functions
$utilsPath = Join-Path $PSScriptRoot 'utils.ps1'
if (Test-Path $utilsPath) {
    . $utilsPath
} else {
    Write-Host "ERROR: utils.ps1 not found at $utilsPath" -ForegroundColor Red
    exit 1
}

if (-not (Test-ExecutionPolicy)) { Fail "Cannot proceed due to execution policy restrictions." }

# Set up logging
$LogDir = Join-Path $env:USERPROFILE '.prompt-automation\logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir 'install.log'
Start-Transcript -Path $LogFile -Append | Out-Null
trap { Write-Warning "Error on line $($_.InvocationInfo.ScriptLineNumber). See $LogFile" }

Info "Starting prompt-automation installation..."

# Record default hotkey mapping and enable GUI mode
$cfgDir = Join-Path $env:USERPROFILE '.prompt-automation'
New-Item -ItemType Directory -Force -Path $cfgDir | Out-Null
'{"hotkey": "ctrl+shift+j"}' | Set-Content (Join-Path $cfgDir 'hotkey.json')
'PROMPT_AUTOMATION_GUI=1' | Set-Content (Join-Path $cfgDir 'environment')

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
    $depExitCode = $LASTEXITCODE
    Debug "Dependency script exit code: $depExitCode"
    
    if ($depExitCode -ne 0) { 
        Write-Warning "Dependency installation script returned exit code: $depExitCode"
        
        # Check if critical components are actually available despite the error
        $pythonAvailable = (Get-Command python -ErrorAction SilentlyContinue) -ne $null
        $pipxAvailable = (Get-Command pipx -ErrorAction SilentlyContinue) -ne $null
        
        # Also check if pipx is available as a Python module
        if (-not $pipxAvailable -and $pythonAvailable) {
            try {
                $pipxModuleTest = & python -m pipx --version 2>&1
                if ($LASTEXITCODE -eq 0) {
                    $pipxAvailable = $true
                    Debug "pipx is available via 'python -m pipx'"
                }
            } catch {
                Debug "pipx module not available: $_"
            }
        }
        
        if ($pythonAvailable -and $pipxAvailable) {
            Write-Warning "Core dependencies (Python and pipx) appear to be available despite error code."
            Write-Warning "Continuing with installation..."
        } elseif ($pythonAvailable) {
            Write-Warning "Python is available but pipx may have issues."
            Write-Warning "Attempting to continue - some features may not work properly."
        } else {
            Write-Warning "Missing critical dependencies:"
            if (-not $pythonAvailable) { Write-Warning "  - Python not found" }
            if (-not $pipxAvailable) { Write-Warning "  - pipx not found" }
            Fail 'Critical dependencies are missing. Cannot continue with installation.' 
        }
    }
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

# Set up global hotkey with GUI mode
Info 'Setting up global hotkey...'
try {
    $env:PYTHONPATH = (Resolve-Path (Join-Path $PSScriptRoot '..\src')).Path
    python -c "import prompt_automation.hotkeys; prompt_automation.hotkeys.update_system_hotkey('ctrl+shift+j')"
    Info 'Global hotkey configured successfully'
} catch {
    Write-Warning "Failed to configure global hotkey: $($_.Exception.Message)"
    Write-Warning "You can set it up manually later with: prompt-automation --assign-hotkey"
}

# Verify hotkey setup
$hotkeyScript = Join-Path $PSScriptRoot 'troubleshoot-hotkeys.ps1'
if (Test-Path $hotkeyScript) {
    Info 'Verifying hotkey registration...'
    & $hotkeyScript -Status
    # Reset exit code after hotkey status check
    $global:LASTEXITCODE = 0
}

# Summary status
Info "\n=== Installation Summary ==="
Show-ComponentStatus -ComponentName 'Python'
Show-ComponentStatus -ComponentName 'pipx'
Show-ComponentStatus -ComponentName 'fzf'
Show-ComponentStatus -ComponentName 'espanso'
Show-ComponentStatus -ComponentName 'AutoHotkey'
Show-ComponentStatus -ComponentName 'prompt-automation'

# Check startup configuration
Info "`n=== Startup Configuration ==="
$startupStatus = Test-StartupConfiguration

Write-Host "- AutoHotkey startup: " -NoNewline
if ($startupStatus.AutoHotkey) { 
    Write-Host "[OK] Configured" -ForegroundColor Green 
} else { 
    Write-Host "[FAIL] Not configured" -ForegroundColor Red 
}

Write-Host "- espanso service: " -NoNewline
if ($startupStatus.Espanso) { 
    Write-Host "[OK] Configured" -ForegroundColor Green 
} elseif (Get-Command espanso -ErrorAction SilentlyContinue) {
    # Check if espanso is at least running
    try {
        $espansoRunning = & espanso status 2>&1
        # Reset exit code after espanso status
        $global:LASTEXITCODE = 0
        if ($espansoRunning -match "espanso is running") {
            Write-Host "[INFO] Running manually" -ForegroundColor Cyan
        } else {
            Write-Host "[WARN] Available but not running" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[WARN] Available but status unknown" -ForegroundColor Yellow
        # Reset exit code after failed espanso status
        $global:LASTEXITCODE = 0
    }
} else {
    Write-Host "[N/A] Not installed" -ForegroundColor Gray
}

if ($startupStatus.Issues.Count -gt 0) {
    # Filter out espanso service issues if espanso is actually running
    $filteredIssues = @()
    foreach ($issue in $startupStatus.Issues) {
        if ($issue -like "*espanso service not registered*") {
            # Check if espanso is running - if so, this isn't really an issue
            try {
                $espansoRunning = & espanso status 2>&1
                # Reset exit code after espanso status check
                $global:LASTEXITCODE = 0
                if (-not ($espansoRunning -match "espanso is running")) {
                    $filteredIssues += $issue
                }
            } catch {
                $filteredIssues += $issue
                # Reset exit code after failed espanso status
                $global:LASTEXITCODE = 0
            }
        } else {
            $filteredIssues += $issue
        }
    }
    
    if ($filteredIssues.Count -gt 0) {
        Info "`nStartup issues detected:"
        foreach ($issue in $filteredIssues) {
            Write-Host "  ! $issue" -ForegroundColor Yellow
        }
        Info "Run 'scripts\troubleshoot-hotkeys.ps1 --Fix' to resolve these issues"
    }
}

# Health check
Info "`n=== Health Check ==="
$env:PYTHONPATH = (Resolve-Path (Join-Path $PSScriptRoot '..\src')).Path
$healthScript = @"
import sys
try:
    import prompt_automation.cli, prompt_automation.gui
    print('OK')
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
"@
python -c $healthScript
if ($LASTEXITCODE -ne 0) { Fail 'Health check failed.' }

Info "\nFor troubleshooting tips see docs or run scripts/troubleshoot-hotkeys.ps1 --Fix"

Stop-Transcript | Out-Null
Info "Installation log saved to $LogFile"

# Explicitly set success exit code
exit 0
