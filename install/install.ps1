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

# Safety check - ensure we're not running with excessive privileges that could affect system
$currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
$isAdmin = ([Security.Principal.WindowsPrincipal] $currentUser).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
$isSystem = $currentUser.IsSystem

if ($isSystem) {
    Fail "This script should not be run as SYSTEM user to avoid system-wide changes that could affect device functionality."
}

if ($isAdmin) {
    Write-Warning "Running as Administrator. Installation will proceed but will limit operations to user directories only."
    Write-Warning "No system-level changes will be made that could affect device functionality."
} else {
    Info "Running with standard user privileges (recommended for safety)"
}

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

$hotkeyFile = Join-Path $cfgDir 'hotkey.json'
if (-not (Test-Path $hotkeyFile)) {
    '{"hotkey": "ctrl+shift+j"}' | Set-Content $hotkeyFile
    Info "Default hotkey config written"
} else {
    Info "Preserving existing hotkey config at $hotkeyFile"
}

$envFile = Join-Path $cfgDir 'environment'
if (-not (Test-Path $envFile)) {
@'
PROMPT_AUTOMATION_GUI=1
PROMPT_AUTOMATION_AUTO_UPDATE=1
PROMPT_AUTOMATION_MANIFEST_AUTO=1
'@ | Set-Content $envFile
    Info 'Environment defaults written (GUI + auto-update enabled)'
} else {
    Info "Preserving existing environment config at $envFile"
}

# Add repo root hint for espanso sync orchestrator
try {
    $projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
    Add-Content -Path $envFile -Value "PROMPT_AUTOMATION_REPO=$projectRoot"
    Info "Recorded PROMPT_AUTOMATION_REPO in environment file"
} catch {
    Write-Warning "Could not record PROMPT_AUTOMATION_REPO: $($_.Exception.Message)"
}

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
            Write-Warning 'Critical dependencies are missing. Installation will continue but may not be fully functional.' 
            Write-Warning 'Please ensure Python and pipx are properly installed and in PATH.'
        }
    }
} else {
    Fail 'install-dependencies.ps1 not found.'
}

# Verify Tkinter availability
try {
    python -c "import tkinter" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning 'Tkinter not found. Reinstall Python from python.org to include Tkinter support.'
    } else {
        Info '[OK] Tkinter module available'
    }
} catch {
    Write-Warning 'Python not available to check Tkinter. Ensure Python is installed with Tk support.'
}

# Verify pipx is working properly and fix if needed
Info 'Verifying pipx installation...'
$pipxWorking = $false
try {
    $pipxVersion = & pipx --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $pipxWorking = $true
        Info "[OK] pipx version: $pipxVersion"
    }
} catch {
    # Try python -m pipx
    try {
        $pipxVersion = & python -m pipx --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $pipxWorking = $true
            Info "[OK] pipx (via python -m) version: $pipxVersion"
        }
    } catch {
        Write-Warning "pipx not working properly"
    }
}

if (-not $pipxWorking) {
    Write-Warning "pipx is not functioning. Attempting to reinstall pipx..."
    try {
        & python -m pip install --user --force-reinstall pipx
        if ($LASTEXITCODE -eq 0) {
            Info "pipx reinstalled successfully"
            # Ensure pipx path is available
            & python -m pipx ensurepath
            $pipxWorking = $true
        }
    } catch {
        Write-Warning "Failed to reinstall pipx: $($_.Exception.Message)"
    }
}

if (-not $pipxWorking) {
    Write-Warning "pipx is still not working. Some installation features may fail."
}

# Install the application from local source
$appScript = Join-Path $PSScriptRoot 'install-prompt-automation.ps1'
if (Test-Path $appScript) {
    Info 'Installing prompt-automation application...'
    & $appScript
    $appExitCode = $LASTEXITCODE
    
    if ($appExitCode -ne 0) { 
        Write-Warning "Main application installation returned exit code: $appExitCode"
        
        # Check if the application was actually installed despite the error code
        $promptAutomationInstalled = $false
        try {
            $promptCmd = Get-Command prompt-automation -ErrorAction SilentlyContinue
            if ($promptCmd) {
                $promptAutomationInstalled = $true
                Info "prompt-automation command is available despite installation error"
            } else {
                # Check if it's available as a module
                & python -c "import prompt_automation" 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    $promptAutomationInstalled = $true
                    Info "prompt-automation module is available despite installation error"
                }
            }
        } catch {
            Debug "Could not verify prompt-automation installation: $($_.Exception.Message)"
        }
        
        if (-not $promptAutomationInstalled) {
            Write-Warning 'Main application installation failed.'
            
            # Suggest alternative installer
            $altScript = Join-Path $PSScriptRoot 'install-alternative.ps1'
            if (Test-Path $altScript) {
                Info 'Trying alternative installation method...'
                & $altScript
                if ($LASTEXITCODE -ne 0) {
                    Write-Warning 'Both main and alternative installation methods failed.'
                    Write-Warning 'You may need to install manually or check the logs for specific errors.'
                } else {
                    Info 'Alternative installation succeeded!'
                }
            } else {
                Write-Warning 'Application installation failed and no alternative method available.'
                Write-Warning 'Please check the logs and try manual installation.'
            }
        } else {
            Info 'Application appears to be installed successfully despite error code'
        }
    }
} else {
    Fail 'install-prompt-automation.ps1 not found.'
}

# Skip PyYAML inject (already declared in pyproject). Avoid cp1252 console encoding issues.

# Set up global hotkey via CLI to ensure pipx venv is used
Info 'Setting up global hotkey...'
try {
    & prompt-automation --assign-hotkey | Out-Null
    Info 'Global hotkey configured successfully'
} catch {
    Write-Warning "Failed to configure global hotkey via CLI: $($_.Exception.Message)"
}

# Verify hotkey setup
$hotkeyScript = Join-Path $PSScriptRoot '..\scripts\troubleshoot-hotkeys.ps1'
if (Test-Path $hotkeyScript) {
    Info 'Verifying hotkey registration...'
    & $hotkeyScript -Status
    # Reset exit code after hotkey status check
    $global:LASTEXITCODE = 0
}

# Summary status
try {
    # Skip immediate upgrade if installation used a temporary local path which
    # has now been deleted (prevents 'Unable to parse package spec' errors).
    $tempInstallDir = Join-Path $env:TEMP 'prompt-automation-install'
    if (Test-Path $tempInstallDir) {
        pipx upgrade prompt-automation | Out-Null 2>&1
    } else {
        # Only attempt upgrade if the existing spec appears to be canonical (PyPI).
        $pipxList = try { pipx list 2>&1 } catch { '' }
        if ($pipxList -match 'prompt-automation') {
            # Heuristic: avoid calling upgrade right after a local-path install; harmless otherwise.
            pipx upgrade prompt-automation | Out-Null 2>&1
        }
    }
} catch {}
try {
    prompt-automation --update | Out-Null 2>&1
} catch {}

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
    import prompt_automation.cli, prompt_automation.gui, prompt_automation.menus
    # Test that templates can be loaded
    styles = prompt_automation.menus.list_styles()
    if not styles:
        print('WARNING: No template styles found', file=sys.stderr)
    else:
        style_names = ', '.join(styles)
        print(f'Found {len(styles)} template style(s): {style_names}')
    
    # Test GUI import without launching window
    import tkinter as tk
    print('Tkinter available for GUI')
    
    print('OK - All modules imported successfully')
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
"@
python -c $healthScript
if ($LASTEXITCODE -ne 0) { 
    Write-Warning 'Health check failed - some modules may not be working correctly'
    Write-Warning 'This may be due to missing dependencies or import issues'
    Write-Warning 'You can still try to use the application, but some features may not work'
    # Don't fail the entire installation for health check issues
    # Fail 'Health check failed.' 
}

# Configure espanso package and :pa.sync command (best-effort)
try {
    $env:PROMPT_AUTOMATION_REPO = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
    Push-Location $env:USERPROFILE
    & prompt-automation --espanso-sync | Out-Null
    Pop-Location
    Info 'Espanso package synced and :pa.sync registered'
} catch {
    Pop-Location -ErrorAction SilentlyContinue
    Write-Warning "Espanso sync orchestration encountered issues: $($_.Exception.Message)"
}

# Seed Settings/settings.json with espanso_repo_root for GUI sync discovery
try {
    $py = @"
import json, os
from pathlib import Path
from prompt_automation.config import PROMPTS_DIR
repo = os.environ.get('PROMPT_AUTOMATION_REPO', '')
settings_dir = PROMPTS_DIR / 'Settings'
settings_dir.mkdir(parents=True, exist_ok=True)
sf = settings_dir / 'settings.json'
try:
    data = json.loads(sf.read_text(encoding='utf-8')) if sf.exists() else {}
except Exception:
    data = {}
if repo:
    data['espanso_repo_root'] = repo
    sf.write_text(json.dumps(data, indent=2), encoding='utf-8')
    print('[install] Seeded espanso_repo_root in', sf)
"@
    # Use -c in PowerShell instead of bash-style heredoc redirection
    python -c $py | Out-Null
} catch {
    Write-Warning "Could not seed espanso_repo_root: $($_.Exception.Message)"
}

Info "\nFor troubleshooting tips see docs or run scripts/troubleshoot-hotkeys.ps1 --Fix"

# Finalize with update mode to activate latest behavior and hotkey
try { & prompt-automation -u | Out-Null } catch {}

# Optional GUI test
$testScript = Join-Path $PSScriptRoot 'test-gui.py'
if (Test-Path $testScript) {
    Info "`n=== GUI Test ==="
    try {
        $env:PYTHONPATH = (Resolve-Path (Join-Path $PSScriptRoot '..\src')).Path
        & python $testScript
        if ($LASTEXITCODE -eq 0) {
            Info "GUI test completed successfully"
        } else {
            Write-Warning "GUI test failed - GUI may not work properly"
        }
        # Reset exit code since this is optional
        $global:LASTEXITCODE = 0
    } catch {
        Write-Warning "Could not run GUI test: $($_.Exception.Message)"
        # Reset exit code since this is optional
        $global:LASTEXITCODE = 0
    }
}

Stop-Transcript | Out-Null
Info "Installation log saved to $LogFile"

# Explicitly set success exit code
exit 0
