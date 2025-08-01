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
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

if (-not [System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::Windows)) {
    Fail "This installer must be run on Windows."
}

# Ensure Python
Info "Checking for Python installation..."
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCmd) {
    $pythonVersion = & python --version 2>&1
    Info "[OK] Python is already installed: $pythonVersion"
    Debug "Found Python: $pythonVersion at $($pythonCmd.Source)"
} else {
    Info "Python not found. Installing Python3 via winget..."
    if (-not (Install-WingetPackage -PackageId 'Python.Python.3' -PackageName 'Python')) {
        Fail "Failed to install Python. Check winget is available and try again."
    }
    Info "[OK] Python installation completed successfully"
    Refresh-PathEnvironment
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) { Fail 'Python still not found in PATH after installation.' }
}

# Ensure pipx
Info "Checking for pipx..."
$pipxCmd = Get-Command pipx -ErrorAction SilentlyContinue
if ($pipxCmd) {
    Info "[OK] pipx is already installed"
    Debug "Found pipx at $($pipxCmd.Source)"
} else {
    Info "pipx not found. Installing pipx..."
    python -m pip install --user pipx
    if ($LASTEXITCODE -ne 0) { Fail 'pip install pipx failed.' }
    python -m pipx ensurepath
    try {
        # Get user scripts directory using simpler Python approach
        $pythonCmd = 'import sysconfig; print(sysconfig.get_path(\"scripts\", scheme=\"nt_user\"))'
        $userScripts = & python -c $pythonCmd 2>$null
        if ($userScripts -and (Test-Path $userScripts) -and ($env:Path -notlike "*$userScripts*")) { 
            $env:Path += ";$userScripts" 
        }
        
        # Get Python user base directory
        $pythonBaseCmd = 'import site; print(site.USER_BASE)'
        $pythonUserBase = & python -c $pythonBaseCmd 2>$null
        if ($pythonUserBase) {
            $alternateScripts = Join-Path $pythonUserBase 'Scripts'
            if ((Test-Path $alternateScripts) -and ($env:Path -notlike "*$alternateScripts*")) { 
                $env:Path += ";$alternateScripts" 
            }
        }
        
        # Get Python version for standard user scripts path
        $pythonVersionCmd = 'import sys; print(\"Python{}{}\".format(sys.version_info.major, sys.version_info.minor))'
        $pythonVersion = & python -c $pythonVersionCmd 2>$null
        if ($pythonVersion) {
            $standardUserScripts = Join-Path $env:APPDATA "$pythonVersion\Scripts"
            if ((Test-Path $standardUserScripts) -and ($env:Path -notlike "*$standardUserScripts*")) { 
                $env:Path += ";$standardUserScripts" 
            }
        }
        
        # Common Python 3.12 path
        $standardUserScripts312 = Join-Path $env:APPDATA 'Python\Python312\Scripts'
        if ((Test-Path $standardUserScripts312) -and ($env:Path -notlike "*$standardUserScripts312*")) { 
            $env:Path += ";$standardUserScripts312" 
        }
        
        Refresh-PathEnvironment
    } catch {
        Write-Warning 'Could not automatically update PATH. You may need to restart your terminal.'
    }
    $pipxCmd = Get-Command pipx -ErrorAction SilentlyContinue
    if (-not $pipxCmd) { Fail 'pipx still not available after installation.' }
}
$global:pipxCommand = 'pipx'

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
if (-not $ahk) {
    # Check if AutoHotkey is installed but not in PATH
    $ahkPaths = @(
        "${env:ProgramFiles}\AutoHotkey\AutoHotkey.exe",
        "${env:ProgramFiles(x86)}\AutoHotkey\AutoHotkey.exe",
        "${env:LOCALAPPDATA}\Programs\AutoHotkey\AutoHotkey.exe"
    )
    $ahkFound = $false
    foreach ($path in $ahkPaths) {
        if (Test-Path $path) {
            Info "[OK] AutoHotkey found at $path (not in PATH)"
            $ahkFound = $true
            break
        }
    }
    
    if (-not $ahkFound) {
        Info 'AutoHotkey not found. Installing AutoHotkey...'
        $ahkInstalled = Install-WingetPackage -PackageId 'AutoHotkey.AutoHotkey' -PackageName 'AutoHotkey'
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
                $ahkInstalled = $true
            } catch {
                Write-Warning "Alternative AutoHotkey installation also failed: $_"
            }
        }
        Refresh-PathEnvironment
        $ahk = Get-Command AutoHotkey -ErrorAction SilentlyContinue
        if (-not $ahk) {
            # Check again in common locations
            foreach ($path in $ahkPaths) {
                if (Test-Path $path) {
                    Info "[OK] AutoHotkey installed at $path"
                    $ahkFound = $true
                    break
                }
            }
            if (-not $ahkFound) {
                Write-Warning 'AutoHotkey installation may have failed.'
            }
        }
    }
} else {
    Info '[OK] AutoHotkey is already installed'
}

# Copy AHK script to startup
$ahkAvailable = (Get-Command AutoHotkey -ErrorAction SilentlyContinue) -ne $null
if (-not $ahkAvailable) {
    # Check if AutoHotkey is installed in common locations even if not in PATH
    $ahkPaths = @(
        "${env:ProgramFiles}\AutoHotkey\AutoHotkey.exe",
        "${env:ProgramFiles(x86)}\AutoHotkey\AutoHotkey.exe",
        "${env:LOCALAPPDATA}\Programs\AutoHotkey\AutoHotkey.exe"
    )
    foreach ($path in $ahkPaths) {
        if (Test-Path $path) {
            $ahkAvailable = $true
            break
        }
    }
}

if ($ahkAvailable) {
    $ahkSource = Join-Path $scriptDir '..\src\prompt_automation\hotkey\windows.ahk'
    
    # Handle WSL path issue for AutoHotkey script
    if ($ahkSource -like "\\wsl.localhost\*") {
        Info "Copying AutoHotkey script from WSL to Windows..."
        $tempAhkScript = Join-Path $env:TEMP 'prompt-automation-hotkey.ahk'
        try {
            Copy-Item -Path $ahkSource -Destination $tempAhkScript -Force
            $ahkSource = $tempAhkScript
        } catch {
            Write-Warning "Failed to copy AutoHotkey script from WSL: $_"
        }
    }
    
    if (Test-Path $ahkSource) {
        $ahkSource = Resolve-Path $ahkSource
        $startup = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup\prompt-automation.ahk'
        try { 
            Copy-Item -Path $ahkSource -Destination $startup -Force 
            Info "[OK] AutoHotkey script copied to startup folder"
            
            # Clean up temp file if we used it
            if ($ahkSource -like "*temp*prompt-automation-hotkey.ahk") {
                Remove-Item $ahkSource -Force -ErrorAction SilentlyContinue
            }
        } catch { 
            Write-Warning "Failed to copy hotkey script: $_" 
        }
    } else {
        Write-Warning "AutoHotkey source script not found at $ahkSource."
    }
} else {
    Write-Warning 'AutoHotkey is not available - skipping hotkey script setup.'
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
