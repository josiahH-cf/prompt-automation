<#
.SYNOPSIS
Windows-specific installation script for prompt-automation with GUI support.
.DESCRIPTION
This script fixes common Windows installation issues, handles WSL paths,
and ensures GUI dependencies are properly installed.
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
$LogFile = Join-Path $LogDir 'install-gui.log'
Start-Transcript -Path $LogFile -Append | Out-Null
trap { Write-Warning "Error on line $($_.InvocationInfo.ScriptLineNumber). See $LogFile" }

Info "Starting prompt-automation GUI installation for Windows..."

# Step 1: Clean up any existing corrupted installations
Info "Step 1: Cleaning up existing installations..."
try {
    # pipx doesn't support --force flag for uninstall
    pipx uninstall prompt-automation 2>$null
    Write-Host "Removed existing pipx installation" -ForegroundColor Green
} catch {
    Debug "No existing pipx installation found"
}

# Remove corrupted venv if it exists
$venvPath = "$env:USERPROFILE\pipx\venvs\prompt-automation"
if (Test-Path $venvPath) {
    try {
        # Stop any processes that might be using the venv
        Get-Process python* -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        
        # Take ownership and set permissions
        takeown /f $venvPath /r /d y 2>$null | Out-Null
        icacls $venvPath /grant "$env:USERNAME:F" /t 2>$null | Out-Null
        
        Remove-Item $venvPath -Recurse -Force
        Write-Host "Removed corrupted virtual environment" -ForegroundColor Green
    } catch {
        Write-Warning "Could not remove $venvPath - you may need to run as Administrator"
        Write-Host "Please run as Administrator or manually remove: $venvPath" -ForegroundColor Yellow
        Write-Host "Then re-run this script" -ForegroundColor Yellow
        Stop-Transcript | Out-Null
        exit 1
    }
}

# Step 2: Ensure Python and pipx are working
Info "Step 2: Verifying Python and pipx..."
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Fail "Python is not available. Please install Python first."
}

try {
    python -m pipx --version | Out-Null
    $pipxWorking = $true
    Info "pipx is working via 'python -m pipx'"
} catch {
    try {
        pipx --version | Out-Null
        $pipxWorking = $true
        Info "pipx is working via direct command"
    } catch {
        Write-Warning "pipx not working, attempting to install..."
        python -m pip install --user pipx
        python -m pipx ensurepath
        $pipxWorking = $false
    }
}

# Step 3: Handle WSL path issues by copying to Windows temp
$scriptDir = $PSScriptRoot
$projectRoot = Split-Path -Parent $scriptDir
$useTemp = $false

if ($projectRoot -like "\\wsl.localhost\*" -or $projectRoot -like "\\wsl$\*") {
    Info "Step 3: Detected WSL path, copying to Windows temp directory..."
    $tempProjectDir = Join-Path $env:TEMP "prompt-automation-install-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    
    try {
        New-Item -ItemType Directory -Path $tempProjectDir -Force | Out-Null
        
        # Copy essential files for installation
        $filesToCopy = @('pyproject.toml', 'README.md', 'LICENSE', 'src', 'MANIFEST.in')
        foreach ($file in $filesToCopy) {
            $sourcePath = Join-Path $projectRoot $file
            $destPath = Join-Path $tempProjectDir $file
            if (Test-Path $sourcePath) {
                if ((Get-Item $sourcePath).PSIsContainer) {
                    Copy-Item -Path $sourcePath -Destination $destPath -Recurse -Force
                } else {
                    Copy-Item -Path $sourcePath -Destination $destPath -Force
                }
                Debug "Copied $file to temp directory"
            }
        }
        
        # Copy prompts directory if it exists in root
        $promptsSource = Join-Path $projectRoot 'prompts'
        if (Test-Path $promptsSource) {
            Copy-Item -Path $promptsSource -Destination (Join-Path $tempProjectDir 'prompts') -Recurse -Force
            Debug "Copied prompts directory"
        }
        
        $projectRoot = $tempProjectDir
        $useTemp = $true
        Info "Project copied to: $projectRoot"
    } catch {
        Fail "Failed to copy project from WSL path: $_"
    }
} else {
    Info "Step 3: Using local Windows path: $projectRoot"
}

# Step 4: Install the application
Info "Step 4: Installing prompt-automation..."
$pyprojectPath = Join-Path $projectRoot 'pyproject.toml'
if (-not (Test-Path $pyprojectPath)) { 
    Fail "pyproject.toml not found at $pyprojectPath" 
}

try {
    if ($pipxWorking) {
        pipx install -e "$projectRoot"
    } else {
        python -m pipx install -e "$projectRoot"
    }
    
    if ($LASTEXITCODE -ne 0) { 
        throw "pipx installation failed with exit code $LASTEXITCODE"
    }
    Info "prompt-automation installed successfully"
} catch {
    Fail "Failed to install prompt-automation: $_"
}

# Step 5: Install GUI dependencies
Info "Step 5: Installing GUI dependencies..."
try {
    # Install FreeSimpleGUI (open source) first
    python -m pip install FreeSimpleGUI
    Info "FreeSimpleGUI installed successfully"
} catch {
    Write-Warning "Failed to install FreeSimpleGUI, trying PySimpleGUI..."
    try {
        python -m pip install PySimpleGUI
        Info "PySimpleGUI installed successfully"
    } catch {
        Write-Warning "Failed to install GUI libraries. GUI mode may not work."
    }
}

# Step 6: Configure for GUI mode
Info "Step 6: Configuring GUI mode..."
$cfgDir = Join-Path $env:USERPROFILE '.prompt-automation'
New-Item -ItemType Directory -Force -Path $cfgDir | Out-Null

# Set default hotkey and enable GUI mode
'{"hotkey": "ctrl+shift+j"}' | Set-Content (Join-Path $cfgDir 'hotkey.json')
'PROMPT_AUTOMATION_GUI=1' | Set-Content (Join-Path $cfgDir 'environment')
Info "GUI mode enabled by default"

# Step 7: Test the installation
Info "Step 7: Testing installation..."
try {
    $testOutput = prompt-automation --troubleshoot 2>&1
    if ($LASTEXITCODE -eq 0) {
        Info "Basic installation test passed"
    } else {
        Write-Warning "Installation test returned exit code $LASTEXITCODE"
    }
} catch {
    Write-Warning "Could not run basic test: $_"
}

# Test GUI specifically
try {
    Write-Host "Testing GUI mode (this should open a window briefly)..." -ForegroundColor Yellow
    Start-Job -ScriptBlock { 
        Start-Sleep 2
        Get-Process | Where-Object {$_.ProcessName -like "*python*"} | Stop-Process -Force -ErrorAction SilentlyContinue
    } | Out-Null
    
    $env:PROMPT_AUTOMATION_GUI = "1"
    timeout 5 prompt-automation --gui 2>$null
    Info "GUI test completed (window may have closed automatically)"
} catch {
    Write-Warning "GUI test failed: $_"
}

# Step 8: Clean up temp directory
if ($useTemp -and (Test-Path $projectRoot)) {
    try {
        Remove-Item $projectRoot -Recurse -Force
        Debug "Cleaned up temporary directory"
    } catch {
        Debug "Could not clean up temp directory: $_"
    }
}

# Step 9: Final verification and instructions
Info "Installation complete!"
Write-Host ""
Write-Host "=== INSTALLATION SUMMARY ===" -ForegroundColor Green
Write-Host "✓ prompt-automation installed" -ForegroundColor Green
Write-Host "✓ GUI mode enabled by default" -ForegroundColor Green
Write-Host "✓ Default hotkey: Ctrl+Shift+J" -ForegroundColor Green
Write-Host ""
Write-Host "=== NEXT STEPS ===" -ForegroundColor Cyan
Write-Host "1. Test GUI: prompt-automation --gui" -ForegroundColor White
Write-Host "2. Test CLI: prompt-automation --terminal" -ForegroundColor White
Write-Host "3. Set hotkey: prompt-automation --assign-hotkey" -ForegroundColor White
Write-Host ""
Write-Host "=== TROUBLESHOOTING ===" -ForegroundColor Yellow
Write-Host "If GUI doesn't work:" -ForegroundColor White
Write-Host "  - Check logs: $LogFile" -ForegroundColor White
Write-Host "  - Run: prompt-automation --troubleshoot" -ForegroundColor White
Write-Host "  - Ensure no antivirus is blocking Python apps" -ForegroundColor White

Stop-Transcript | Out-Null
