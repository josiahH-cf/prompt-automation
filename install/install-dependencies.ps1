<#
.SYNOPSIS
Installs required dependencies for prompt-automation on Windows.
.DESCRIPTION
This script installs Python, pipx, fzf, espanso and AutoHotkey. It also copies the
AutoHotkey script into the startup folder so hotkeys are available after login.
#>

. "$PSScriptRoot/utils.ps1"

if (-not (Test-ExecutionPolicy)) { Fail "Cannot proceed due to execution policy restrictions." }

$LogDir = Join-Path $env:USERPROFILE '.prompt-automation\logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir 'install-deps.log'
Start-Transcript -Path $LogFile -Append | Out-Null
trap { Write-Warning "Error on line $($_.InvocationInfo.ScriptLineNumber). See $LogFile" }

Info "Starting dependency installation..."

# Get script directory for later use
$scriptDir = $PSScriptRoot

if (-not [System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::Windows)) {
    Fail "This installer must be run on Windows."
}

# Ensure Python
Info "Checking for Python installation..."

# First do a comprehensive test
$pythonResults = Test-PythonAvailability
if ($pythonResults.WorkingPython) {
    $workingPython = $pythonResults.WorkingPython
    Info "[OK] Python is available via '$($workingPython.Command)' command"
    Info "Version: $($workingPython.Version)"
    Info "Location: $($workingPython.Path)"
    
    # Make sure 'python' alias is available if needed
    if ($workingPython.Command -ne 'python') {
        Set-Alias -Name python -Value $workingPython.Path -Scope Script -Force
        Debug "Created 'python' alias for current script"
    }
} else {
    Info "Python not found via standard commands. Installing Python3 via winget..."
    $pythonInstalled = Install-WingetPackage -PackageId 'Python.Python.3' -PackageName 'Python'
    
    # Force refresh PATH and search for Python regardless of winget result
    Refresh-PathEnvironment
    Start-Sleep -Seconds 3  # Give system time to update
    
    # Try comprehensive detection again
    $pythonResults = Test-PythonAvailability
    if ($pythonResults.WorkingPython) {
        $workingPython = $pythonResults.WorkingPython
        Info "[OK] Python is now available via '$($workingPython.Command)' command"
        Info "Version: $($workingPython.Version)"
        Info "Location: $($workingPython.Path)"
        
        # Make sure 'python' alias is available
        if ($workingPython.Command -ne 'python') {
            Set-Alias -Name python -Value $workingPython.Path -Scope Script -Force
            Debug "Created 'python' alias for current script"
        }
    } else {
        Info "Still no Python found. Attempting comprehensive search..."
        if (Find-PythonInstallation) {
            Info "[OK] Python found and configured via comprehensive search"
        } else {
            Write-Warning "No working Python installation found after all attempts."
            Write-Warning ""
            Show-PythonDiagnostics
            Write-Warning ""
            Write-Warning "To fix this manually:"
            Write-Warning "1. Download Python from: https://python.org/downloads/"
            Write-Warning "2. During installation, CHECK 'Add Python to PATH'"
            Write-Warning "3. Or install from Microsoft Store: 'Python 3.12'"
            Write-Warning "4. Then restart this script"
            Write-Warning ""
            
            $continue = Read-Host "Do you want to continue without Python? Some features will not work. (y/n)"
            if ($continue -ne 'y' -and $continue -ne 'Y' -and $continue -ne 'yes') {
                Fail "Python installation is required. Please install Python and restart the script."
            }
            Write-Warning "Continuing without Python - pipx and prompt-automation installation will be skipped."
        }
    }
}

# Ensure pipx
$pythonAvailable = (Get-Command python -ErrorAction SilentlyContinue) -ne $null
if (-not $pythonAvailable) {
    Write-Warning "Python is not available - skipping pipx installation"
    Write-Warning "pipx requires Python to be installed and available in PATH"
} else {
    Info "Checking for pipx..."
    $pipxCmd = Get-Command pipx -ErrorAction SilentlyContinue
    if ($pipxCmd) {
        Info "[OK] pipx is already installed"
        Debug "Found pipx at $($pipxCmd.Source)"
    } else {
        Info "pipx not found. Installing pipx..."
        try {
            python -m pip install --user pipx
            if ($LASTEXITCODE -ne 0) { 
                Write-Warning 'pip install pipx failed. Trying alternative installation...'
                python -m pip install --user --upgrade pip
                python -m pip install --user pipx
                if ($LASTEXITCODE -ne 0) {
                    Write-Warning 'pipx installation failed after retry.'
                }
            }
            
            # Try to run pipx ensurepath
            try {
                python -m pipx ensurepath
                Info "Executed pipx ensurepath to configure PATH"
            } catch {
                Debug "Could not run pipx ensurepath: $_"
            }
            
            # Add common pipx paths to current session
            try {
                # Get user scripts directory using simpler Python approach
                $pythonCmd = 'import sysconfig; print(sysconfig.get_path(\"scripts\", scheme=\"nt_user\"))'
                $userScripts = & python -c $pythonCmd 2>$null
                if ($userScripts -and (Test-Path $userScripts) -and ($env:Path -notlike "*$userScripts*")) { 
                    $env:Path = "$userScripts;$env:Path"
                    Debug "Added user scripts to PATH: $userScripts"
                }
                
                # Get Python user base directory
                $pythonBaseCmd = 'import site; print(site.USER_BASE)'
                $pythonUserBase = & python -c $pythonBaseCmd 2>$null
                if ($pythonUserBase) {
                    $alternateScripts = Join-Path $pythonUserBase 'Scripts'
                    if ((Test-Path $alternateScripts) -and ($env:Path -notlike "*$alternateScripts*")) { 
                        $env:Path = "$alternateScripts;$env:Path"
                        Debug "Added user base scripts to PATH: $alternateScripts"
                    }
                }
                
                # Get Python version for standard user scripts path
                $pythonVersionCmd = 'import sys; print(\"Python{}{}\".format(sys.version_info.major, sys.version_info.minor))'
                $pythonVersion = & python -c $pythonVersionCmd 2>$null
                if ($pythonVersion) {
                    $standardUserScripts = Join-Path $env:APPDATA "$pythonVersion\Scripts"
                    if ((Test-Path $standardUserScripts) -and ($env:Path -notlike "*$standardUserScripts*")) { 
                        $env:Path = "$standardUserScripts;$env:Path"
                        Debug "Added standard user scripts to PATH: $standardUserScripts"
                    }
                }
                
                # Common Python 3.12 path
                $standardUserScripts312 = Join-Path $env:APPDATA 'Python\Python312\Scripts'
                if ((Test-Path $standardUserScripts312) -and ($env:Path -notlike "*$standardUserScripts312*")) { 
                    $env:Path = "$standardUserScripts312;$env:Path"
                    Debug "Added Python 3.12 scripts to PATH: $standardUserScripts312"
                }
                
                Refresh-PathEnvironment
            } catch {
                Write-Warning 'Could not automatically update PATH for pipx. You may need to restart your terminal.'
            }
            
            # Test if pipx is now available
            $pipxCmd = Get-Command pipx -ErrorAction SilentlyContinue
            if ($pipxCmd) {
                Info "[OK] pipx is now available"
                Debug "Found pipx at $($pipxCmd.Source)"
            } else {
                Write-Warning 'pipx still not available after installation.'
                Write-Warning 'Try running: python -m pipx --help'
                Write-Warning 'Or restart your terminal and run: pipx ensurepath'
                # Set up pipx as a Python module command for this session
                $global:pipxCommand = 'python -m pipx'
                Info "Will use 'python -m pipx' for this session"
            }
        } catch {
            Write-Warning "Failed to install pipx: $_"
            Write-Warning "You may need to install pipx manually:"
            Write-Warning "1. python -m pip install --user pipx"
            Write-Warning "2. python -m pipx ensurepath"
            Write-Warning "3. Restart your terminal"
        }
    }
    $global:pipxCommand = if (Get-Command pipx -ErrorAction SilentlyContinue) { 'pipx' } else { 'python -m pipx' }
}

# Install fzf
Info 'Checking for fzf...'
$fzfCmd = Get-Command fzf -ErrorAction SilentlyContinue
if (-not $fzfCmd) {
    Info 'fzf not found. Installing fzf and ripgrep...'
    Install-WingetPackage -PackageId 'BurntSushi.ripgrep.MSVC' -PackageName 'ripgrep'
    $fzfInstalled = $false
    if (Install-WingetPackage -PackageId 'junegunn.fzf' -PackageName 'fzf') { $fzfInstalled = $true }
    elseif (Install-WingetPackage -PackageId 'fzf' -PackageName 'fzf') { $fzfInstalled = $true }
    if (-not $fzfInstalled) {
        $chocoCmd = Get-Command choco -ErrorAction SilentlyContinue
        if ($chocoCmd) {
            choco install fzf -y
            if ($LASTEXITCODE -eq 0) { $fzfInstalled = $true }
        }
        if (-not $fzfInstalled) {
            Write-Warning 'fzf installation failed via all methods.'
        }
    }
    if ($fzfInstalled) { Info '[OK] fzf installed successfully' }
    Refresh-PathEnvironment
} else {
    Info '[OK] fzf is already installed'
}

# Install espanso
Info 'Checking for espanso...'
$espansoCmd = Get-Command espanso -ErrorAction SilentlyContinue
if (-not $espansoCmd) {
    Info 'espanso not found. Installing espanso...'
    if (-not (Install-WingetPackage -PackageId 'Espanso.Espanso' -PackageName 'espanso')) {
        Fail 'Failed to install espanso.'
    }
    Refresh-PathEnvironment
    $espansoCmd = Get-Command espanso -ErrorAction SilentlyContinue
    if ($espansoCmd) {
        Info 'Setting up espanso for first-time use...'
        try {
            & espanso start 2>&1 | Out-Null
            Start-Sleep -Seconds 3
            $espansoStatus = & espanso status 2>&1
            if ($espansoStatus -match 'espanso is running') { Info '[OK] espanso service started successfully' }
        } catch { Write-Warning 'Could not start espanso automatically.' }
    }
} else {
    Info '[OK] espanso is already installed'
}

# Install AutoHotkey
Info 'Checking for AutoHotkey...'
$ahk = Get-Command AutoHotkey -ErrorAction SilentlyContinue
$ahkPaths = @(
    "${env:ProgramFiles}\AutoHotkey\AutoHotkey.exe",
    "${env:ProgramFiles(x86)}\AutoHotkey\AutoHotkey.exe",
    "${env:LOCALAPPDATA}\Programs\AutoHotkey\AutoHotkey.exe"
)

$ahkFound = $false
if ($ahk) {
    Info "[OK] AutoHotkey is already installed and in PATH"
    $ahkFound = $true
} else {
    # Check if AutoHotkey is installed but not in PATH
    foreach ($path in $ahkPaths) {
        if (Test-Path $path) {
            Info "[OK] AutoHotkey found at $path (not in PATH)"
            $ahkFound = $true
            # Try to add AutoHotkey to PATH
            if (Add-AutoHotkeyToPath) {
                Debug "Successfully added AutoHotkey to PATH"
            }
            break
        }
    }
}

if (-not $ahkFound) {
    Info 'AutoHotkey not found. Installing AutoHotkey...'
    $ahkInstalled = Install-WingetPackage -PackageId 'AutoHotkey.AutoHotkey' -PackageName 'AutoHotkey'
    
    # Give system time to register the installation
    Start-Sleep -Seconds 2
    Refresh-PathEnvironment
    
    # Check if installation was successful
    $ahk = Get-Command AutoHotkey -ErrorAction SilentlyContinue
    if ($ahk) {
        Info "[OK] AutoHotkey is now available in PATH"
        $ahkFound = $true
    } else {
        # Check in common locations
        foreach ($path in $ahkPaths) {
            if (Test-Path $path) {
                Info "[OK] AutoHotkey installed at $path"
                $ahkFound = $true
                break
            }
        }
    }
    
    if (-not $ahkFound) {
        if (-not $ahkInstalled) {
            # Try alternative installation method
            Info 'Trying alternative AutoHotkey installation...'
            try {
                $ahkUrl = 'https://www.autohotkey.com/download/ahk-install.exe'
                $ahkInstaller = Join-Path $env:TEMP 'ahk-install.exe'
                Info 'Downloading AutoHotkey installer...'
                Invoke-WebRequest -Uri $ahkUrl -OutFile $ahkInstaller -UseBasicParsing
                Info 'Running AutoHotkey installer...'
                Start-Process -FilePath $ahkInstaller -ArgumentList '/S' -Wait
                Remove-Item $ahkInstaller -Force -ErrorAction SilentlyContinue
                
                # Check again after alternative installation
                Start-Sleep -Seconds 2
                foreach ($path in $ahkPaths) {
                    if (Test-Path $path) {
                        Info "[OK] AutoHotkey installed successfully via alternative method at $path"
                        $ahkFound = $true
                        break
                    }
                }
            } catch {
                Write-Warning "Alternative AutoHotkey installation also failed: $_"
            }
        }
        
        if (-not $ahkFound) {
            Write-Warning 'AutoHotkey installation appears to have failed.'
            Write-Warning 'You can install it manually from: https://www.autohotkey.com'
            Write-Warning 'Hotkey functionality will not be available until AutoHotkey is installed.'
        }
    }
}

# Configure startup applications
Info "Configuring applications for automatic startup..."
$startupConfigured = Configure-StartupApplications -ConfigureAutoHotkey -ConfigureEspanso

if ($startupConfigured) {
    Info "[OK] Startup applications configured successfully"
} else {
    Write-Warning "Some startup configuration may have failed - check logs for details"
}

# Verify startup configuration
$startupStatus = Test-StartupConfiguration
if ($startupStatus.AutoHotkey) {
    Info "[OK] AutoHotkey script is configured for startup"
} else {
    Write-Warning "AutoHotkey startup configuration failed"
}

if ($startupStatus.Espanso) {
    Info "[OK] espanso service is configured for startup"
} elseif (Get-Command espanso -ErrorAction SilentlyContinue) {
    Write-Warning "espanso is installed but not configured for startup"
}

if ($startupStatus.Issues.Count -gt 0) {
    Write-Warning "Startup configuration issues found:"
    foreach ($issue in $startupStatus.Issues) {
        Write-Warning "  - $issue"
    }
}

# Install prompt-automation application
Info 'Installing prompt-automation application...'
$projectRoot = Split-Path -Parent $scriptDir
Debug "Project root: $projectRoot"

# Check if we're trying to install from WSL path in Windows
if ($projectRoot -like "\\wsl.localhost\*") {
    Write-Warning "Detected installation from WSL path in Windows environment"
    Info "The project is located in WSL, but pipx is running in Windows"
    Info "This requires copying the project to a Windows-accessible location"
    
    # Create a temporary directory in Windows
    $tempProjectDir = Join-Path $env:TEMP "prompt-automation-install"
    if (Test-Path $tempProjectDir) {
        Remove-Item $tempProjectDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $tempProjectDir -Force | Out-Null
    
    try {
        Info "Copying project files from WSL to Windows temp directory..."
        # Copy essential files for installation
        $filesToCopy = @(
            'pyproject.toml',
            'README.md',
            'LICENSE',
            'src'
        )
        
        foreach ($file in $filesToCopy) {
            $sourcePath = Join-Path $projectRoot $file
            $destPath = Join-Path $tempProjectDir $file
            
            if (Test-Path $sourcePath) {
                if ((Get-Item $sourcePath).PSIsContainer) {
                    # It's a directory
                    Copy-Item -Path $sourcePath -Destination $destPath -Recurse -Force
                    Info "   Copied directory: $file"
                } else {
                    # It's a file
                    Copy-Item -Path $sourcePath -Destination $destPath -Force
                    Info "   Copied file: $file"
                }
            } else {
                Write-Warning "   Source not found: $sourcePath"
            }
        }
        
        # Use the Windows temp directory for installation
        $installPath = $tempProjectDir
        Info "Installing from Windows temp directory: $installPath"
        
    } catch {
        Write-Warning "Failed to copy project files: $_"
        Write-Warning "Trying direct WSL path installation anyway..."
        $installPath = $projectRoot
    }
} else {
    # Normal Windows path
    $installPath = $projectRoot
}

try {
    # First, ensure pipx is working
    $pipxVersion = & pipx --version 2>&1
    Debug "pipx version: $pipxVersion"
    
    # Install the package
    Info "Installing from: $installPath"
    if ($global:pipxCommand -eq 'python -m pipx') {
        $installOutput = & python -m pipx install --force "$installPath" 2>&1
    } else {
        $installOutput = & pipx install --force "$installPath" 2>&1
    }
    
    Debug "pipx install output: $installOutput"
    
    # Clean up temp directory if we used it
    if ($installPath -like "*temp*prompt-automation-install*") {
        try {
            Remove-Item $tempProjectDir -Recurse -Force -ErrorAction SilentlyContinue
            Debug "Cleaned up temporary installation directory"
        } catch {
            Debug "Could not clean up temp directory: $_"
        }
    }
    
    if ($LASTEXITCODE -ne 0) { 
        Write-Warning "pipx install failed with exit code: $LASTEXITCODE"
        Write-Warning "Output: $installOutput"
        Write-Warning 'Failed to install prompt-automation from local source, but dependencies are installed.' 
    } else {
        Info "[OK] prompt-automation installed successfully"
        
        # Force PATH refresh
        Refresh-PathEnvironment
        
        # Wait a moment for system to update
        Start-Sleep -Seconds 2
        
        # Test the installation with multiple approaches
        $promptAutomationCmd = Get-Command prompt-automation -ErrorAction SilentlyContinue
        if ($promptAutomationCmd) {
            try { 
                $version = & prompt-automation --version 2>&1
                Info "   Version: $version" 
                Info "   Location: $($promptAutomationCmd.Source)"
            } catch { 
                Info "   prompt-automation command is available at $($promptAutomationCmd.Source)"
            }
        } else {
            # Check common pipx installation paths
            Write-Warning "prompt-automation command not found in current PATH"
            Debug "Current PATH: $env:PATH"
            
            # Get pipx venv path
            try {
                $pipxList = & pipx list 2>&1
                Debug "pipx list output: $pipxList"
                if ($pipxList -match 'prompt-automation') {
                    Info "   prompt-automation is installed in pipx"
                    
                    # Try to get the actual installation path from pipx
                    $pipxInfo = & pipx show prompt-automation 2>&1
                    Debug "pipx show prompt-automation: $pipxInfo"
                }
            } catch {
                Debug "Could not check pipx list: $_"
            }
            
            # Check user scripts directories
            $userScriptPaths = @(
                "${env:APPDATA}\Python\Python312\Scripts",
                "${env:LOCALAPPDATA}\Programs\Python\Python312\Scripts",
                "${env:USERPROFILE}\.local\bin"
            )
            
            $foundPath = $null
            foreach ($path in $userScriptPaths) {
                $promptCmd = Join-Path $path 'prompt-automation.exe'
                Debug "Checking for prompt-automation at: $promptCmd"
                if (Test-Path $promptCmd) {
                    Info "   Found prompt-automation at: $promptCmd"
                    $foundPath = $path
                    
                    # Test if we can run it directly
                    try {
                        $testVersion = & "$promptCmd" --version 2>&1
                        Info "   Direct execution successful: $testVersion"
                    } catch {
                        Write-Warning "   Found executable but failed to run: $_"
                    }
                    break
                }
            }
            
            # Also check pipx's default installation directory
            $pipxHome = $env:PIPX_HOME
            if (-not $pipxHome) {
                $pipxHome = Join-Path $env:USERPROFILE '.local'
            }
            $pipxBin = Join-Path $pipxHome 'bin'
            $pipxPromptCmd = Join-Path $pipxBin 'prompt-automation.exe'
            Debug "Checking pipx bin directory: $pipxPromptCmd"
            if (Test-Path $pipxPromptCmd) {
                Info "   Found prompt-automation in pipx bin: $pipxPromptCmd"
                $foundPath = $pipxBin
                try {
                    $testVersion = & "$pipxPromptCmd" --version 2>&1
                    Info "   Direct execution successful: $testVersion"
                } catch {
                    Write-Warning "   Found executable but failed to run: $_"
                }
            }
            
            if ($foundPath) {
                Info "   You may need to add $foundPath to your PATH or restart your terminal"
                Info "   To temporarily add to PATH for this session, run:"
                Info "   `$env:PATH += ';$foundPath'"
            } else {
                Write-Warning 'prompt-automation executable not found in expected locations.'
                Write-Warning 'Searching all common Python script directories...'
                
                # Broader search
                $searchPaths = @(
                    $env:APPDATA,
                    $env:LOCALAPPDATA,
                    $env:USERPROFILE
                )
                
                foreach ($searchRoot in $searchPaths) {
                    if (Test-Path $searchRoot) {
                        $found = Get-ChildItem -Path $searchRoot -Recurse -Name 'prompt-automation.exe' -ErrorAction SilentlyContinue | Select-Object -First 3
                        foreach ($foundFile in $found) {
                            $fullPath = Join-Path $searchRoot $foundFile
                            Info "   Found prompt-automation.exe at: $fullPath"
                        }
                    }
                }
                
                Write-Warning 'You may need to:'
                Write-Warning '1. Restart your terminal to refresh PATH'
                Write-Warning '2. Or run: pipx ensurepath'
                Write-Warning '3. Or manually add the pipx Scripts directory to your PATH'
                Write-Warning '4. Or reinstall: pipx uninstall prompt-automation && pipx install .'
            }
        }
    }
} catch {
    Write-Warning "Failed to install prompt-automation: $_"
    Write-Warning "Exception details: $($_.Exception.Message)"
}

Stop-Transcript | Out-Null
Info ""
Info "=== Installation Summary ==="
Info "Dependencies installation complete. Log saved to $LogFile"
Info ""

# Final check and provide specific instructions if needed
$finalCheck = Get-Command prompt-automation -ErrorAction SilentlyContinue
if (-not $finalCheck) {
    Write-Warning "prompt-automation is still not in PATH after installation."
    Write-Warning "To manually fix this, try these commands in order:"
    Write-Warning ""
    Write-Warning "1. First, try running pipx ensurepath and restart your terminal:"
    Write-Warning "   pipx ensurepath"
    Write-Warning ""
    Write-Warning "2. If that doesn't work, try adding pipx's bin directory to your PATH:"
    Write-Warning "   For current session: `$env:PATH += ';' + (pipx environment --value PIPX_BIN_DIR)"
    Write-Warning ""
    Write-Warning "3. Or manually add to your user PATH in Windows:"
    Write-Warning "   - Open Settings > Advanced System Settings > Environment Variables"
    Write-Warning "   - Edit your user PATH variable"
    Write-Warning "   - Add the directory where prompt-automation.exe was found (see above)"
    Write-Warning ""
    Write-Warning "4. As a last resort, you can run the command directly using its full path"
}

Info "Next steps:"
Info "1. Restart your terminal to ensure PATH is updated"
Info "2. Test the application: prompt-automation"
Info "3. Use Ctrl+Shift+J hotkey to launch the application"
Info "4. If you encounter issues, run: scripts\troubleshoot-hotkeys.ps1"

# Determine exit code based on critical dependencies
$pythonResults = Test-PythonAvailability
$pythonAvailable = $pythonResults.WorkingPython -ne $null
$pipxAvailable = (Get-Command pipx -ErrorAction SilentlyContinue) -ne $null

# If pipx command is not available, check if we can use python -m pipx
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

Debug "Final dependency check: Python=$pythonAvailable, pipx=$pipxAvailable"

if ($pythonAvailable) {
    if ($pythonResults.WorkingPython) {
        Debug "Python available via: $($pythonResults.WorkingPython.Command) ($($pythonResults.WorkingPython.Version))"
    }
    Info "[OK] Python is available"
    
    if ($pipxAvailable) {
        Debug "Core dependencies (Python and pipx) are available - exiting with success code"
        Info "[OK] Core dependencies are available"
        exit 0
    } else {
        Debug "Python available but pipx missing - allowing installation to continue"
        Write-Warning "Python is available but pipx installation had issues"
        Write-Warning "You can try installing pipx manually: python -m pip install --user pipx"
        exit 0  # Allow installation to continue since Python is available
    }
} else {
    Debug "Critical dependencies missing - exiting with error code"
    Write-Warning "Python is not available"
    Write-Warning ""
    Write-Warning "Python installation diagnostics:"
    Show-PythonDiagnostics | Out-Null
    Write-Warning ""
    if (-not $pipxAvailable) { Write-Warning "pipx is also not available" }
    exit 1
}
