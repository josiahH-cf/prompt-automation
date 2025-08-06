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

# Check if running as administrator for better error messaging
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Warning "Not running as administrator. If you encounter permission errors, try running as administrator."
}

# Ensure pipx command
$global:pipxCommand = $null
$pipxCmd = Get-Command pipx -ErrorAction SilentlyContinue
if ($pipxCmd) { $global:pipxCommand = 'pipx' } else { $global:pipxCommand = 'python -m pipx' }

# Get project root
$scriptDir = $PSScriptRoot
$projectRoot = Split-Path -Parent $scriptDir

# Handle WSL path issues
if ($projectRoot -like "\\wsl.localhost\*") {
    Write-Warning "Detected installation from WSL path in Windows environment"
    Info "Copying project to Windows temp directory for installation..."
    
    $tempProjectDir = Join-Path $env:TEMP "prompt-automation-install"
    if (Test-Path $tempProjectDir) {
        Remove-Item $tempProjectDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $tempProjectDir -Force | Out-Null
    
    # Copy essential files
    $filesToCopy = @('pyproject.toml', 'README.md', 'LICENSE', 'src', 'prompts', 'MANIFEST.in')
    foreach ($file in $filesToCopy) {
        $sourcePath = Join-Path $projectRoot $file
        $destPath = Join-Path $tempProjectDir $file
        if (Test-Path $sourcePath) {
            if ((Get-Item $sourcePath).PSIsContainer) {
                Copy-Item -Path $sourcePath -Destination $destPath -Recurse -Force
            } else {
                Copy-Item -Path $sourcePath -Destination $destPath -Force
            }
        }
    }
    $projectRoot = $tempProjectDir
}

$pyprojectPath = Join-Path $projectRoot 'pyproject.toml'
if (-not (Test-Path $pyprojectPath)) { Fail "pyproject.toml not found at $pyprojectPath" }

# Force clean uninstall of existing installation
Info "Checking for existing prompt-automation installation..."
try {
    if ($global:pipxCommand -eq 'python -m pipx') {
        $listOutput = & python -m pipx list 2>&1 | Out-String
    } else {
        $listOutput = & $global:pipxCommand list 2>&1 | Out-String
    }
    
    if ($listOutput -match "prompt-automation") {
        Info "Existing installation found. Removing it completely..."
        
        # Try to uninstall gracefully first
        try {
            if ($global:pipxCommand -eq 'python -m pipx') {
                & python -m pipx uninstall prompt-automation 2>&1 | Out-Null
            } else {
                & $global:pipxCommand uninstall prompt-automation 2>&1 | Out-Null
            }
            Info "Graceful uninstall completed"
        } catch {
            Write-Warning "Graceful uninstall failed: $($_.Exception.Message)"
        }
        
        # Clean up pipx trash directory which often causes permission issues
        $pipxTrashDir = Join-Path $env:USERPROFILE 'pipx\trash'
        if (Test-Path $pipxTrashDir) {
            Info "Cleaning pipx trash directory to prevent permission issues..."
            try {
                # Stop any processes that might be using the files
                Get-Process | Where-Object { $_.ProcessName -like "*prompt-automation*" } | Stop-Process -Force -ErrorAction SilentlyContinue
                Start-Sleep -Seconds 1  # Give processes time to fully terminate
                
                # Only take ownership and modify permissions if running as admin and files are in user directory
                if ($isAdmin -and $pipxTrashDir -like "$env:USERPROFILE*") {
                    Debug "Running as admin - attempting to take ownership of trash files"
                    try {
                        takeown /f "$pipxTrashDir" /r /d y 2>&1 | Out-Null
                        icacls "$pipxTrashDir" /grant "$env:USERNAME:(F)" /t 2>&1 | Out-Null
                    } catch {
                        Write-Warning "Could not take ownership of trash files: $($_.Exception.Message)"
                    }
                }
                
                # Safe removal of trash directory contents - don't force ownership changes on system files
                Get-ChildItem $pipxTrashDir -Recurse -Force -ErrorAction SilentlyContinue | ForEach-Object {
                    try {
                        # Only modify files in user directory to avoid system-level changes
                        if ($_.FullName -like "$env:USERPROFILE*") {
                            if ($_.PSIsContainer) {
                                Remove-Item $_.FullName -Recurse -Force -ErrorAction Stop
                            } else {
                                Remove-Item $_.FullName -Force -ErrorAction Stop
                            }
                        } else {
                            Debug "Skipping file outside user directory: $($_.FullName)"
                        }
                    } catch {
                        # Try gentle attribute reset only for user files
                        if ($_.FullName -like "$env:USERPROFILE*") {
                            try {
                                attrib -r -s -h "$($_.FullName)" 2>&1 | Out-Null
                                Remove-Item $_.FullName -Force -ErrorAction Stop
                            } catch {
                                Debug "Could not remove locked file: $($_.FullName) - $($_.Exception.Message)"
                            }
                        } else {
                            Debug "Skipping system file: $($_.FullName)"
                        }
                    }
                }
                
                Info "Pipx trash directory cleaned (user files only)"
            } catch {
                Write-Warning "Could not fully clean pipx trash: $($_.Exception.Message)"
                Write-Warning "This is usually safe to ignore - pipx will handle cleanup on next run"
            }
        }
        
        # Force remove the venv directory if it still exists
        $pipxVenvDir = Join-Path $env:USERPROFILE 'pipx\venvs\prompt-automation'
        if (Test-Path $pipxVenvDir) {
            Info "Force removing venv directory: $pipxVenvDir"
            try {
                # Stop any processes that might be using the venv
                Get-Process | Where-Object { $_.Path -like "*$pipxVenvDir*" } | Stop-Process -Force -ErrorAction SilentlyContinue
                Start-Sleep -Seconds 2  # Give processes time to fully terminate
                
                # Only take ownership if running as admin and target is in user directory
                if ($isAdmin -and $pipxVenvDir -like "$env:USERPROFILE*") {
                    Debug "Running as admin - attempting to take ownership of venv directory"
                    try {
                        takeown /f "$pipxVenvDir" /r /d y 2>&1 | Out-Null
                        icacls "$pipxVenvDir" /grant "$env:USERNAME:(F)" /t 2>&1 | Out-Null
                    } catch {
                        Write-Warning "Could not take ownership of venv directory: $($_.Exception.Message)"
                    }
                }
                
                # Safe removal with retry - only for user directories
                if ($pipxVenvDir -like "$env:USERPROFILE*") {
                    $retryCount = 0
                    while ((Test-Path $pipxVenvDir) -and ($retryCount -lt 3)) {
                        try {
                            Remove-Item $pipxVenvDir -Recurse -Force -ErrorAction Stop
                            Info "Successfully removed venv directory"
                            break
                        } catch {
                            $retryCount++
                            Debug "Attempt $retryCount failed to remove venv: $($_.Exception.Message)"
                            if ($retryCount -lt 3) {
                                Start-Sleep -Seconds 2
                            }
                        }
                    }
                    
                    if (Test-Path $pipxVenvDir) {
                        Write-Warning "Could not completely remove venv directory. Some files may be locked."
                        Write-Warning "This is usually safe to ignore - pipx will recreate on next install"
                        # Try to remove contents at least
                        try {
                            Get-ChildItem $pipxVenvDir -Recurse -Force -ErrorAction SilentlyContinue | Where-Object { $_.FullName -like "$env:USERPROFILE*" } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
                        } catch {
                            Debug "Could not clean venv contents: $($_.Exception.Message)"
                        }
                    }
                } else {
                    Write-Warning "Venv directory is outside user profile - skipping removal for safety: $pipxVenvDir"
                }
            } catch {
                Write-Warning "Could not clean venv directory: $($_.Exception.Message)"
                Write-Warning "This is usually safe to ignore - pipx will handle cleanup on next run"
            }
        }
        
        # Wait a moment for file system to settle
        Start-Sleep -Seconds 1
        
    } else {
        Info "No existing installation found"
    }
} catch {
    Write-Warning "Could not check for existing installation: $($_.Exception.Message)"
}

# Install fresh
Info "Installing prompt-automation from local source..."
$installSuccess = $false

# Try pipx first with enhanced error handling
try {
    Debug "Attempting pipx install with command: $global:pipxCommand"
    
    if ($global:pipxCommand -eq 'python -m pipx') {
        $pipxOutput = & python -m pipx install "$projectRoot" 2>&1
    } else {
        $pipxOutput = & $global:pipxCommand install "$projectRoot" 2>&1
    }
    
    Debug "pipx install output: $pipxOutput"
    
    if ($LASTEXITCODE -eq 0) { 
        $installSuccess = $true
        Info "Installation successful with pipx"
    } else {
        Write-Warning "pipx install failed with exit code: $LASTEXITCODE"
        Write-Warning "Output: $pipxOutput"
        
        # Check if it's a permission error in trash cleanup (common issue)
        if ($pipxOutput -match "PermissionError.*trash" -or $pipxOutput -match "Access is denied.*trash") {
            Write-Warning "This appears to be a permission error during pipx trash cleanup."
            Write-Warning "The application may actually be installed despite the error."
            
            # Check if the application was actually installed
            try {
                $verifyOutput = & $global:pipxCommand list 2>&1
                if ($verifyOutput -match "prompt-automation") {
                    Info "Application appears to be successfully installed despite trash cleanup error"
                    $installSuccess = $true
                } else {
                    Write-Warning "Application was not installed due to the error"
                }
            } catch {
                Debug "Could not verify installation status: $($_.Exception.Message)"
            }
        }
    }
} catch {
    Write-Warning "pipx install failed: $($_.Exception.Message)"
}

# If initial install failed, try with --force
if (-not $installSuccess) {
    Write-Warning "Initial install failed. Trying with --force flag..."
    try {
        if ($global:pipxCommand -eq 'python -m pipx') {
            & python -m pipx install --force "$projectRoot"
        } else {
            & $global:pipxCommand install --force "$projectRoot"
        }
        if ($LASTEXITCODE -eq 0) {
            $installSuccess = $true
            Info "Installation successful with pipx --force"
        }
    } catch {
        Write-Warning "pipx install --force failed: $($_.Exception.Message)"
    }
}

# If pipx completely fails, try direct pip install as fallback
if (-not $installSuccess) {
    Write-Warning "pipx installation failed. Trying direct pip install as fallback..."
    try {
        & python -m pip install --user --force-reinstall "$projectRoot"
        if ($LASTEXITCODE -eq 0) {
            $installSuccess = $true
            Info "Installation successful with pip --user"
            Write-Warning "Installed with pip instead of pipx. The 'prompt-automation' command may not be in PATH."
            Write-Warning "You may need to run it as 'python -m prompt_automation' instead."
        }
    } catch {
        Write-Warning "pip install failed: $($_.Exception.Message)"
    }
}

if (-not $installSuccess) {
    Fail 'All installation methods failed. Please check the logs and try running the installer as administrator.'
}

# Clean up temp directory if used
if ($projectRoot -like "*temp*prompt-automation-install*") {
    try {
        Remove-Item $projectRoot -Recurse -Force -ErrorAction SilentlyContinue
        Debug "Cleaned up temporary installation directory"
    } catch {
        Debug "Could not clean up temp directory: $_"
    }
}

# Verify command
$promptAutomationCmd = Get-Command prompt-automation -ErrorAction SilentlyContinue
if ($promptAutomationCmd) {
    Info "[OK] prompt-automation command is available"
    try { 
        # Test with help instead of version since --version isn't supported
        $help = & prompt-automation --help 2>&1 | Select-Object -First 1
        if ($help) { Info "   Command working: Help available" }
        # Reset exit code after help command
        $global:LASTEXITCODE = 0
    } catch { 
        Debug "Could not get help: $($_.Exception.Message)"
        # Reset exit code after failed help command
        $global:LASTEXITCODE = 0
    }
} else {
    Write-Warning 'prompt-automation command not found in PATH.'
    
    # Try to test if it's available as a module
    try {
        & python -c "import prompt_automation; print('Module import successful')" 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Info "[OK] prompt-automation module is available via 'python -m prompt_automation'"
            
            # Test the module
            try {
                $moduleHelp = & python -m prompt_automation --help 2>&1 | Select-Object -First 1
                if ($moduleHelp) { Info "   Module working: Help available" }
                # Reset exit code after help command
                $global:LASTEXITCODE = 0
            } catch {
                Debug "Could not get module help: $($_.Exception.Message)"
                # Reset exit code after failed help command
                $global:LASTEXITCODE = 0
            }
        } else {
            Write-Warning "prompt-automation module not available either. Installation may have failed."
        }
    } catch {
        Write-Warning "Could not test module availability: $($_.Exception.Message)"
    }
    
    Write-Warning 'You may need to restart your terminal or use "python -m prompt_automation" instead.'
}

# Display summary
Info "`n=== Installation Summary ==="
Show-ComponentStatus -ComponentName 'Python'
Show-ComponentStatus -ComponentName 'pipx'
Show-ComponentStatus -ComponentName 'fzf'
Show-ComponentStatus -ComponentName 'espanso'
Show-ComponentStatus -ComponentName 'AutoHotkey'
Show-ComponentStatus -ComponentName 'prompt-automation'

Stop-Transcript | Out-Null
Info "Installation complete. Log saved to $LogFile"

# Explicitly set success exit code
exit 0
