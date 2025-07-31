# PowerShell install script for prompt-automation
param(
    [switch]$TroubleshootHotkeys
)

# Show help if requested
if ($args -contains "-h" -or $args -contains "--help" -or $args -contains "-?" -or $args -contains "help") {
    Write-Host ""
    Write-Host "prompt-automation Installation Script" -ForegroundColor Green
    Write-Host "=====================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "This script installs prompt-automation and its dependencies on Windows." -ForegroundColor White
    Write-Host ""
    Write-Host "USAGE:" -ForegroundColor Yellow
    Write-Host "  .\install.ps1                    # Normal installation"
    Write-Host "  .\install.ps1 -TroubleshootHotkeys        # Troubleshoot hotkey issues"
    Write-Host "  .\install.ps1 -TroubleshootHotkeys -Fix   # Try to fix hotkey issues"
    Write-Host "  .\install.ps1 -TroubleshootHotkeys -Status # Check hotkey status only"
    Write-Host "  .\install.ps1 -TroubleshootHotkeys -Restart # Restart AutoHotkey script"
    Write-Host ""
    Write-Host "FLAGS:" -ForegroundColor Yellow
    Write-Host "  -TroubleshootHotkeys    Run hotkey troubleshooting instead of installation"
    Write-Host ""
    Write-Host "TROUBLESHOOTING OPTIONS:" -ForegroundColor Yellow
    Write-Host "  -Fix       Attempt to automatically fix common hotkey issues"
    Write-Host "  -Status    Show detailed status information only"
    Write-Host "  -Restart   Restart the AutoHotkey script"
    Write-Host ""
    Write-Host "EXAMPLES:" -ForegroundColor Yellow
    Write-Host "  # Normal installation:"
    Write-Host "  .\install.ps1" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  # If Ctrl+Shift+J hotkey isn't working:"
    Write-Host "  .\install.ps1 -TroubleshootHotkeys" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  # Try to fix hotkey issues automatically:"
    Write-Host "  .\install.ps1 -TroubleshootHotkeys -Fix" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "The script will install Python, pipx, fzf, espanso, AutoHotkey, and prompt-automation."
    Write-Host ""
    exit 0
}

# Check if running as Administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Check and handle execution policy
function Test-ExecutionPolicy {
    $currentPolicy = Get-ExecutionPolicy -Scope CurrentUser
    $restrictivePolicies = @('Restricted', 'AllSigned')
    
    if ($currentPolicy -in $restrictivePolicies) {
        Write-Host "Current execution policy is '$currentPolicy' which may prevent this script from running." -ForegroundColor Yellow
        Write-Host "This script needs to run unsigned PowerShell scripts." -ForegroundColor Yellow
        
        if (Test-Administrator) {
            Write-Host "You are running as Administrator." -ForegroundColor Green
            $response = Read-Host "Would you like to temporarily set the execution policy to RemoteSigned for this session? (y/n)"
            
            if ($response -eq 'y' -or $response -eq 'Y' -or $response -eq 'yes') {
                try {
                    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process -Force
                    Write-Host "Execution policy temporarily set to RemoteSigned for this session." -ForegroundColor Green
                    return $true
                } catch {
                    Write-Host "Failed to set execution policy: $_" -ForegroundColor Red
                    return $false
                }
            }
        } else {
            Write-Host "You are not running as Administrator." -ForegroundColor Yellow
            Write-Host "To fix this execution policy issue, you have several options:" -ForegroundColor Yellow
            Write-Host "1. Run PowerShell as Administrator and execute: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process" -ForegroundColor Cyan
            Write-Host "2. Or run this script with: PowerShell -ExecutionPolicy Bypass -File install.ps1" -ForegroundColor Cyan
            Write-Host "3. Or run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Cyan
            
            $response = Read-Host "Would you like to restart this script as Administrator to fix the execution policy? (y/n)"
            
            if ($response -eq 'y' -or $response -eq 'Y' -or $response -eq 'yes') {
                $scriptPath = $MyInvocation.MyCommand.Definition
                Write-Host "Restarting as Administrator..." -ForegroundColor Green
                Start-Process PowerShell -ArgumentList "-ExecutionPolicy", "Bypass", "-File", "`"$scriptPath`"" -Verb RunAs
                exit 0
            }
        }
        
        Write-Host "Execution policy was not changed. The script may fail to run properly." -ForegroundColor Yellow
        $continue = Read-Host "Do you want to continue anyway? (y/n)"
        if ($continue -ne 'y' -and $continue -ne 'Y' -and $continue -ne 'yes') {
            Write-Host "Installation cancelled by user." -ForegroundColor Red
            exit 1
        }
    }
    
    return $true
}

# Run execution policy check
if (-not (Test-ExecutionPolicy)) {
    Write-Host "Cannot proceed due to execution policy restrictions." -ForegroundColor Red
    exit 1
}

function Info($msg) { 
    Write-Host $msg -ForegroundColor Green 
    # Logging is handled by Start-Transcript
}
function Debug($msg) { 
    Write-Host "[DEBUG] $msg" -ForegroundColor Cyan 
    # Logging is handled by Start-Transcript
}
function Fail($msg) { 
    Write-Host $msg -ForegroundColor Red
    # Logging is handled by Start-Transcript
    exit 1 
}

# Function to refresh PATH from environment variables
function Refresh-PathEnvironment {
    Debug "Refreshing PATH environment variables..."
    try {
        $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
        $userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
        $env:Path = "$machinePath;$userPath"
        Debug "PATH refreshed successfully"
    } catch {
        Debug "Error refreshing PATH: $_"
        Write-Warning "Could not refresh PATH environment. Some commands may not be found."
    }
}

# Function to install a package via winget with retry logic
function Install-WingetPackage {
    param(
        [string]$PackageId,
        [string]$PackageName,
        [int]$MaxRetries = 2
    )
    
    Info "Installing $PackageName..."
    for ($i = 1; $i -le $MaxRetries; $i++) {
        if ($MaxRetries -gt 1) {
            Debug "Attempting to install $PackageName (attempt $i/$MaxRetries)..."
        }
        Debug "Executing: winget install -e --id $PackageId --accept-source-agreements --accept-package-agreements"
        
        try {
            winget install -e --id $PackageId --accept-source-agreements --accept-package-agreements
            
            if ($LASTEXITCODE -eq 0) {
                Info "✓ $PackageName installed successfully"
                Debug "$PackageName installation completed successfully"
                return $true
            } else {
                Debug "winget $PackageName exit code: $LASTEXITCODE"
                
                # Special handling for AutoHotkey installation issues
                if ($PackageName -eq "AutoHotkey" -and $LASTEXITCODE -ne 0) {
                    Write-Warning "AutoHotkey installation returned exit code $LASTEXITCODE"
                    Write-Warning "This often indicates UAC permission dialogs were cancelled or other permission issues."
                }
                
                if ($i -lt $MaxRetries) {
                    Write-Warning "Installation attempt $i failed for $PackageName. Retrying in 3 seconds..."
                    Start-Sleep -Seconds 3
                }
            }
        } catch {
            Debug "Exception during $PackageName installation: $_"
            if ($PackageName -eq "AutoHotkey") {
                Write-Warning "AutoHotkey installation encountered an exception: $_"
                Write-Warning "This may be due to cancelled UAC dialogs or permission issues."
            }
            if ($i -lt $MaxRetries) {
                Write-Warning "Installation attempt $i failed for $PackageName due to exception. Retrying in 3 seconds..."
                Start-Sleep -Seconds 3
            }
        }
    }
    
    Write-Warning "Failed to install $PackageName after $MaxRetries attempts."
    if ($PackageName -eq "AutoHotkey") {
        Write-Warning "For AutoHotkey, this is often caused by:"
        Write-Warning "• Cancelled UAC permission dialogs"
        Write-Warning "• Insufficient administrator privileges"
        Write-Warning "• Installation conflicts with existing AutoHotkey versions"
    }
    return $false
}

# Troubleshooting hotkeys functionality
function Invoke-TroubleshootHotkeys {
    param(
        [switch]$Fix,
        [switch]$Status,
        [switch]$Restart
    )

    function Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
    function Error($msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red }

    Info "=== prompt-automation Hotkey Troubleshooting ==="
    Info ""

    # Check if AutoHotkey is installed
    $ahkCmd = Get-Command AutoHotkey -ErrorAction SilentlyContinue
    if ($ahkCmd) {
        Info "✓ AutoHotkey is installed at: $($ahkCmd.Source)"
        try {
            $ahkVersion = & $ahkCmd.Source --version 2>&1
            Debug "  Version: $ahkVersion"
        } catch {
            Debug "  Could not determine version"
        }
    } else {
        Error "✗ AutoHotkey is not installed or not in PATH"
        Info ""
        Info "AutoHotkey installation options:"
        Info "1. Via winget (recommended): winget install -e --id AutoHotkey.AutoHotkey"
        Info "2. Download from: https://www.autohotkey.com/"
        Info "3. Via Chocolatey: choco install autohotkey"
        Info ""
        Warn "Common installation issues:"
        Warn "• UAC permission dialogs must be accepted"
        Warn "• Installation may require Administrator privileges"
        Warn "• Some antivirus software may block AutoHotkey"
        Warn "• Previous AutoHotkey installations may cause conflicts"
        Info ""
        
        if ($Fix) {
            Info "Attempting to install AutoHotkey via winget..."
            try {
                winget install -e --id AutoHotkey.AutoHotkey --accept-source-agreements --accept-package-agreements
                if ($LASTEXITCODE -eq 0) {
                    Info "✓ AutoHotkey installation attempted successfully"
                    Info "You may need to restart your terminal to use AutoHotkey"
                } else {
                    Error "✗ AutoHotkey installation failed with exit code: $LASTEXITCODE"
                    Warn "This often indicates UAC dialogs were cancelled or permission issues"
                }
            } catch {
                Error "✗ AutoHotkey installation failed with exception: $_"
            }
        }
        return
    }

    # Check if the script exists in startup
    $startupScript = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup\prompt-automation.ahk'
    if (Test-Path $startupScript) {
        Info "✓ AutoHotkey script found in startup folder"
        Debug "  Location: $startupScript"
    } else {
        Error "✗ AutoHotkey script not found in startup folder"
        Debug "  Expected location: $startupScript"
        
        if ($Fix) {
            Info "Attempting to fix by copying the script..."
            $sourceScript = Join-Path (Split-Path $MyInvocation.MyCommand.Definition) '..\src\prompt_automation\hotkey\windows.ahk'
            if (Test-Path $sourceScript) {
                Copy-Item -Path $sourceScript -Destination $startupScript -Force
                Info "✓ Script copied to startup folder"
            } else {
                Error "✗ Source script not found at: $sourceScript"
            }
        }
    }

    # Check if AutoHotkey process is running
    $ahkProcess = Get-Process -Name "AutoHotkey*" -ErrorAction SilentlyContinue
    if ($ahkProcess) {
        Info "✓ AutoHotkey process is running:"
        foreach ($proc in $ahkProcess) {
            Debug "  PID: $($proc.Id), Name: $($proc.ProcessName), Path: $($proc.Path)"
        }
    } else {
        Warn "⚠ No AutoHotkey processes found running"
        Info "  The script should start automatically after login"
        
        if ($Fix -or $Restart) {
            Info "Starting AutoHotkey script manually..."
            if (Test-Path $startupScript) {
                try {
                    Start-Process -FilePath $ahkCmd.Source -ArgumentList "`"$startupScript`"" -NoNewWindow
                    Start-Sleep -Seconds 2
                    $ahkProcess = Get-Process -Name "AutoHotkey*" -ErrorAction SilentlyContinue
                    if ($ahkProcess) {
                        Info "✓ AutoHotkey script started successfully"
                    } else {
                        Error "✗ Failed to start AutoHotkey script"
                    }
                } catch {
                    Error "✗ Error starting AutoHotkey: $_"
                }
            }
        }
    }

    # Check if prompt-automation command is available
    $paCmd = Get-Command prompt-automation -ErrorAction SilentlyContinue
    if ($paCmd) {
        Info "✓ prompt-automation command is available"
        Debug "  Location: $($paCmd.Source)"
        
        # Test the command
        try {
            $version = & prompt-automation --version 2>&1
            Debug "  Version: $version"
        } catch {
            Warn "⚠ prompt-automation command exists but may not work properly: $_"
        }
    } else {
        Error "✗ prompt-automation command not found"
        Info "  Install with: pipx install prompt-automation"
        Info "  Or from local source: pipx install --force ."
    }

    # Check for potential conflicts
    Info ""
    Info "=== Checking for potential conflicts ==="

    # Check espanso
    $espansoCmd = Get-Command espanso -ErrorAction SilentlyContinue
    if ($espansoCmd) {
        try {
            $espansoStatus = & espanso status 2>&1
            if ($espansoStatus -match "espanso is running") {
                Warn "⚠ espanso is running - this may conflict with AutoHotkey"
                Info "  If you experience issues, try: espanso stop"
            } else {
                Info "✓ espanso is installed but not running"
            }
        } catch {
            Debug "Could not check espanso status"
        }
    }

    # Check for other AutoHotkey scripts
    $startupDir = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
    $ahkFiles = Get-ChildItem -Path $startupDir -Filter "*.ahk" -ErrorAction SilentlyContinue
    if ($ahkFiles.Count -gt 1) {
        Warn "⚠ Multiple AutoHotkey scripts found in startup:"
        foreach ($file in $ahkFiles) {
            Debug "  $($file.FullName)"
        }
        Info "  Multiple scripts may cause conflicts"
    }

    Info ""
    if ($Status) {
        Info "Status check complete."
    } elseif ($Fix) {
        Info "Fix attempt complete. Try the hotkey now: Ctrl+Shift+J"
    } elseif ($Restart) {
        Info "Restart attempt complete. Try the hotkey now: Ctrl+Shift+J"
    } else {
        Info "Diagnosis complete. Use the following flags for actions:"
        Info "  --troubleshoot-hotkeys -Fix     : Attempt to fix common issues"
        Info "  --troubleshoot-hotkeys -Restart : Restart the AutoHotkey script"
        Info "  --troubleshoot-hotkeys -Status  : Just show status information"
    }

    Info ""
    Info "Manual troubleshooting steps:"
    Info "1. Log out and log back in to ensure startup scripts run"
    Info "2. Manually run the AutoHotkey script: AutoHotkey `"$startupScript`""
    Info "3. Check if other applications are using Ctrl+Shift+J"
    Info "4. Try running 'prompt-automation' directly from command prompt"
}

# Handle troubleshoot hotkeys flag early, before logging setup
if ($TroubleshootHotkeys) {
    # Parse additional parameters for troubleshooting
    $Fix = $args -contains "-Fix"
    $Status = $args -contains "-Status" 
    $Restart = $args -contains "-Restart"
    
    # If no specific action is specified, run basic troubleshooting
    if (-not ($Fix -or $Status -or $Restart)) {
        Invoke-TroubleshootHotkeys
    } else {
        Invoke-TroubleshootHotkeys -Fix:$Fix -Status:$Status -Restart:$Restart
    }
    
    exit 0
}

$LogDir = Join-Path $env:USERPROFILE '.prompt-automation\logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir 'install.log'
$global:pipxCommand = $null  # Initialize pipx command variable
Start-Transcript -Path $LogFile -Append | Out-Null
trap { Write-Warning "Error on line $($_.InvocationInfo.ScriptLineNumber). See $LogFile" }

Info "Starting prompt-automation installation..."
Info ""
Info "This installer will set up the following components:"
Info "  • Python (if not already installed)"
Info "  • pipx (Python application installer)"
Info "  • fzf (fuzzy finder for quick searching)"
Info "  • espanso (text expander for shortcuts)"
Info "  • AutoHotkey (keyboard shortcuts)"
Info "  • prompt-automation (the main application)"
Info ""
Info "The installation may take several minutes. Please be patient..."
Info ""
Debug "PowerShell Version: $($PSVersionTable.PSVersion)"
Debug "OS: $([System.Environment]::OSVersion.VersionString)"
Debug "User: $env:USERNAME"
Debug "User: $env:USERNAME"
Debug "Running as Administrator: $(Test-Administrator)"
Debug "Current Execution Policy: $(Get-ExecutionPolicy -Scope CurrentUser)"
Debug "Log file: $LogFile"

if (-not [System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::Windows)) {
    Fail "This installer must be run on Windows."
}
Debug "Windows platform confirmed"

# Ensure Python
Info "Checking for Python installation..."
Debug "Checking for Python installation..."
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCmd) {
    $pythonVersion = & python --version 2>&1
    Info "✓ Python is already installed: $pythonVersion"
    Debug "Found Python: $pythonVersion at $($pythonCmd.Source)"
} else {
    Info "Python not found. Installing Python3 via winget..."
    Info "This may take a few minutes - please wait..."
    if (-not (Install-WingetPackage -PackageId "Python.Python.3" -PackageName "Python")) {
        Fail "Failed to install Python. Check winget is available and try running 'winget install -e --id Python.Python.3' manually."
    }
    Info "✓ Python installation completed successfully"
    Debug "Python installation completed"
    # Refresh PATH to find newly installed Python
    Refresh-PathEnvironment
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        Debug "Python found after installation at $($pythonCmd.Source)"
    } else {
        Fail "Python still not found in PATH after installation. You may need to restart your terminal or add Python to PATH manually."
    }
}

# Ensure pipx
Info "Checking for pipx (Python package installer)..."
Debug "Checking for pipx installation..."
$pipxCmd = Get-Command pipx -ErrorAction SilentlyContinue
if ($pipxCmd) {
    Info "✓ pipx is already installed"
    Debug "Found pipx at $($pipxCmd.Source)"
} else {
    Info "pipx not found. Installing pipx..."
    Info "This will allow us to install Python applications in isolated environments."
    Debug "Executing: python -m pip install --user pipx"
    python -m pip install --user pipx
    if ($LASTEXITCODE -ne 0) { 
        Debug "pip install pipx exit code: $LASTEXITCODE"
        Fail "pip install pipx failed. Check that Python and pip are working correctly." 
    }
    Info "Setting up pipx PATH configuration..."
    Debug "pipx installation completed, ensuring PATH..."
    python -m pipx ensurepath
    
    # Try to update PATH for current session - use multiple methods
    try {
        # Method 1: Use sysconfig to get the scripts directory
        $userScripts = python -c "import sysconfig; print(sysconfig.get_path('scripts', scheme='nt_user'))" 2>$null
        if ($userScripts -and (Test-Path $userScripts)) {
            Debug "Adding to PATH: $userScripts"
            if ($env:Path -notlike "*$userScripts*") {
                $env:Path += ";$userScripts"
            }
        }
        
        # Method 2: Try common locations for Python user scripts
        $pythonUserBase = python -c "import site; print(site.USER_BASE)" 2>$null
        if ($pythonUserBase) {
            $alternateScripts = Join-Path $pythonUserBase "Scripts"
            if ((Test-Path $alternateScripts) -and ($env:Path -notlike "*$alternateScripts*")) {
                Debug "Adding alternate scripts path to PATH: $alternateScripts"
                $env:Path += ";$alternateScripts"
            }
        }
        
        # Method 3: Standard Windows Python user scripts location - use more dynamic version detection
        $pythonVersion = python -c "import sys; print(f'Python{sys.version_info.major}{sys.version_info.minor}')" 2>$null
        if ($pythonVersion) {
            $standardUserScripts = Join-Path $env:APPDATA "$pythonVersion\Scripts"
            if ((Test-Path $standardUserScripts) -and ($env:Path -notlike "*$standardUserScripts*")) {
                Debug "Adding standard user scripts path to PATH: $standardUserScripts"
                $env:Path += ";$standardUserScripts"
            }
        }
        
        # Method 4: Also try Python312 for backward compatibility
        $standardUserScripts312 = Join-Path $env:APPDATA "Python\Python312\Scripts"
        if ((Test-Path $standardUserScripts312) -and ($env:Path -notlike "*$standardUserScripts312*")) {
            Debug "Adding Python312 scripts path to PATH: $standardUserScripts312"
            $env:Path += ";$standardUserScripts312"
        }
        
        # Refresh PATH from environment variables
        Refresh-PathEnvironment
        
    } catch {
        Debug "Error updating PATH: $_"
        Write-Warning "Could not automatically update PATH. You may need to restart your terminal."
    }
    
    # Verify pipx is now available
    $pipxCmd = Get-Command pipx -ErrorAction SilentlyContinue
    if (-not $pipxCmd) {
        # Give more specific guidance
        Write-Warning "pipx still not found in PATH after installation."
        Write-Warning "This is common and can be resolved by:"
        Write-Warning "1. Restarting your PowerShell session/terminal"
        Write-Warning "2. Running: `$env:Path += ';' + (python -c `"import site; print(site.USER_BASE + '\\Scripts')`")"
        Write-Warning "3. Or manually running: python -m pipx ensurepath"
        
        # Try one more time with explicit path construction
        try {
            $pythonUserBase = python -c "import site; print(site.USER_BASE)" 2>$null
            if ($pythonUserBase) {
                $pipxPath = Join-Path $pythonUserBase "Scripts\pipx.exe"
                if (Test-Path $pipxPath) {
                    Debug "Found pipx executable at: $pipxPath"
                    # Use full path for pipx installation
                    Debug "Using full path for pipx installation"
                    $global:pipxCommand = $pipxPath
                } else {
                    Fail "pipx executable not found at expected location: $pipxPath. Please restart your terminal and try again."
                }
            } else {
                Fail "Could not determine Python user base directory. Please restart your terminal and try again."
            }
        } catch {
            Fail "pipx installation verification failed. Please restart your terminal or run 'python -m pipx ensurepath' manually, then run this script again."
        }
    } else {
        Debug "pipx verified at $($pipxCmd.Source)"
        $global:pipxCommand = "pipx"
    }
}

# Install fzf
Info "Checking for fzf (fuzzy finder tool)..."
Debug "Checking for fzf installation..."
$fzfCmd = Get-Command fzf -ErrorAction SilentlyContinue
if ($fzfCmd) {
    Info "✓ fzf is already installed"
    Debug "Found fzf at $($fzfCmd.Source)"
} else {
    Info "fzf not found. Installing fzf and dependencies..."
    Info "fzf is a command-line fuzzy finder that helps with quick file and text searching."
    Debug "First installing ripgrep as a dependency..."
    Install-WingetPackage -PackageId "BurntSushi.ripgrep.MSVC" -PackageName "ripgrep"
    
    Debug "Now installing fzf..."
    # Try multiple package sources for fzf since winget might not have it
    $fzfInstalled = $false
    
    # First try winget with the correct package ID
    if (Install-WingetPackage -PackageId "junegunn.fzf" -PackageName "fzf") {
        $fzfInstalled = $true
    } elseif (Install-WingetPackage -PackageId "fzf" -PackageName "fzf") {
        $fzfInstalled = $true  
    }
    
    if (-not $fzfInstalled) {
        Write-Warning "Failed to install fzf via winget. Trying alternative method..."
        
        # Try installing from GitHub releases or Chocolatey
        $chocoCmd = Get-Command choco -ErrorAction SilentlyContinue
        if ($chocoCmd) {
            Info "Trying to install fzf via Chocolatey..."
            Debug "Trying fzf installation via Chocolatey..."
            choco install fzf -y
            if ($LASTEXITCODE -eq 0) {
                Info "✓ fzf installed successfully via Chocolatey"
                Debug "fzf installed successfully via Chocolatey"
                $fzfInstalled = $true
            }
        }
        
        if (-not $fzfInstalled) {
            Write-Warning "fzf installation failed via all methods. You may need to install it manually from https://github.com/junegunn/fzf/releases or install Chocolatey first."
            Write-Warning "The installation will continue, but some features may not work optimally without fzf."
        }
    } else {
        Info "✓ fzf installed successfully"
    }
    
    # Refresh PATH to find newly installed fzf
    Refresh-PathEnvironment
}

# Install espanso
Info "Checking for espanso (text expander)..."
Debug "Checking for espanso installation..."
$espansoCmd = Get-Command espanso -ErrorAction SilentlyContinue
if ($espansoCmd) {
    Info "✓ espanso is already installed"
    Debug "Found espanso at $($espansoCmd.Source)"
    
    # Check if espanso service is running
    Info "Checking espanso service status..."
    try {
        $espansoStatus = & espanso status 2>&1
        if ($espansoStatus -match "espanso is running") {
            Info "✓ espanso service is already running"
        } else {
            Info "espanso is installed but not running. Starting espanso service..."
            Info "You may see permission dialogs - please accept them to allow espanso to work."
            & espanso start 2>&1 | Out-Null
            Start-Sleep -Seconds 2
            Info "✓ espanso service started"
        }
    } catch {
        Write-Warning "Could not check espanso status. You may need to start it manually with 'espanso start'"
    }
} else {
    Info "espanso not found. Installing espanso..."
    Info "espanso is a text expander that will provide quick access to your prompts via shortcuts."
    if (-not (Install-WingetPackage -PackageId "Espanso.Espanso" -PackageName "espanso")) {
        Fail "Failed to install espanso. Try running 'winget install -e --id Espanso.Espanso' manually."
    }
    Info "✓ espanso installed successfully"
    
    # Refresh PATH and get espanso command
    Refresh-PathEnvironment
    $espansoCmd = Get-Command espanso -ErrorAction SilentlyContinue
    
    if ($espansoCmd) {
        Info "Setting up espanso for first-time use..."
        Info "You will see permission dialogs - please accept them to allow espanso to monitor your keyboard."
        
        try {
            # Start espanso service
            Info "Starting espanso service..."
            & espanso start 2>&1 | Out-Null
            Start-Sleep -Seconds 3
            
            # Check if it started successfully
            $espansoStatus = & espanso status 2>&1
            if ($espansoStatus -match "espanso is running") {
                Info "✓ espanso service started successfully"
                Info ""
                Info "🎉 espanso is now active! Try typing ':espanso' to test it."
                Info "   (You should see it expand to 'Hi there!')"
                Info ""
                Info "NOTE: Both espanso and AutoHotkey will be monitoring keyboard input."
                Info "      If you experience system instability, you may want to use only one of them."
                Info "      You can disable espanso with 'espanso stop' if needed."
                Info ""
            } else {
                Write-Warning "espanso may not have started properly. You can start it manually with 'espanso start'"
            }
        } catch {
            Write-Warning "Could not start espanso automatically. Please run 'espanso start' manually after installation."
        }
    } else {
        Write-Warning "espanso command not found after installation. You may need to restart your terminal."
    }
}

# Install AutoHotkey v2
Info "Checking for AutoHotkey (hotkey automation tool)..."
Debug "Checking for AutoHotkey installation..."
$ahk = Get-Command AutoHotkey -ErrorAction SilentlyContinue
if ($ahk) {
    Info "✓ AutoHotkey is already installed"
    Debug "Found AutoHotkey at $($ahk.Source)"
} else {
    Info "AutoHotkey not found. Installing AutoHotkey..."
    Info "AutoHotkey will provide keyboard shortcuts for quick access to prompts."
    Info "Note: You may see permission dialogs during AutoHotkey installation - please accept them."
    
    # Try to install AutoHotkey with better error handling
    $ahkInstalled = $false
    try {
        if (Install-WingetPackage -PackageId "AutoHotkey.AutoHotkey" -PackageName "AutoHotkey") {
            $ahkInstalled = $true
            Info "✓ AutoHotkey installed successfully"
            Debug "AutoHotkey installation completed, refreshing PATH..."
        }
    } catch {
        Debug "AutoHotkey installation encountered an error: $_"
        Write-Warning "AutoHotkey installation encountered issues, but may have partially completed."
        Write-Warning "This is often due to UAC permission dialogs being cancelled."
    }
    
    # Refresh PATH to find newly installed AutoHotkey
    Refresh-PathEnvironment
    $ahk = Get-Command AutoHotkey -ErrorAction SilentlyContinue
    if ($ahk) {
        Debug "AutoHotkey found after installation at $($ahk.Source)"
        $ahkInstalled = $true
        Info "✓ AutoHotkey is now available"
    }
    
    if (-not $ahkInstalled) {
        Write-Warning "AutoHotkey installation may have failed or was cancelled."
        Write-Warning "This often happens when UAC permission dialogs are cancelled."
        Write-Warning "You can try installing manually with: winget install AutoHotkey.AutoHotkey"
        Write-Warning "Or download from https://www.autohotkey.com/"
        Write-Warning "The installation will continue, but hotkey functionality will not work without AutoHotkey."
    }
    
    if (-not $ahk) { 
        Write-Warning "AutoHotkey not found in PATH after installation. You may need to restart your terminal or add AutoHotkey to PATH manually."
        Write-Warning "The installation will continue, but hotkey functionality may not work until AutoHotkey is properly installed."
    }
}

# Copy AHK script to Startup (if AutoHotkey source exists and AutoHotkey is available)
$ahkAvailable = (Get-Command AutoHotkey -ErrorAction SilentlyContinue) -ne $null
if (-not $ahkAvailable) {
    Write-Warning "AutoHotkey is not available - skipping hotkey script setup."
    Write-Warning "Install AutoHotkey first, then manually copy the script to your startup folder."
    Write-Warning "Script location: src\prompt_automation\hotkey\windows.ahk"
    Write-Warning "Startup folder: $($env:APPDATA)\Microsoft\Windows\Start Menu\Programs\Startup\"
} else {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
    $ahkSource = Join-Path $scriptDir '..\src\prompt_automation\hotkey\windows.ahk'
    Debug "Looking for AHK source at: $ahkSource"

    if (-not (Test-Path $ahkSource)) {
        Write-Warning "AutoHotkey source script not found at $ahkSource. Skipping hotkey setup."
        Write-Warning "You may need to manually set up hotkeys later or check the project structure."
    } else {
        $ahkSource = Resolve-Path $ahkSource
        Debug "Resolved AHK source path: $ahkSource"

        $startup = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup\prompt-automation.ahk'
        Debug "Target startup location: $startup"

        try {
            Copy-Item -Path $ahkSource -Destination $startup -Force
            if (Test-Path $startup) {
                Info "✓ AutoHotkey shortcuts registered for startup"
                Info "   Hotkeys will be available after you log out and back in, or you can run the script manually."
                Debug "Successfully copied AHK script to startup folder"
            } else {
                Write-Warning "Failed to register AutoHotkey script - file not found after copy"
            }
        } catch {
            Debug "Exception during AHK script copy: $($_.Exception.Message)"
            Write-Warning "Failed to register AutoHotkey script: $_"
        }
    }
}

# Install prompt-automation
Info ""
Info "Installing prompt-automation (the main application)..."
Info "This will install the command-line tool that manages your prompt templates."

# Ensure we have a pipx command available
if (-not $global:pipxCommand) {
    $pipxCmd = Get-Command pipx -ErrorAction SilentlyContinue
    if ($pipxCmd) {
        $global:pipxCommand = "pipx"
    } else {
        $global:pipxCommand = "python -m pipx"
    }
}

# Get the project root directory (parent of scripts directory)
$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)
Debug "Project root directory: $projectRoot"

# Verify pyproject.toml exists
$pyprojectPath = Join-Path $projectRoot "pyproject.toml"
if (-not (Test-Path $pyprojectPath)) {
    Fail "pyproject.toml not found at $pyprojectPath. Make sure you're running this script from the correct location."
}
Debug "Found pyproject.toml at: $pyprojectPath"

Debug "Executing: $global:pipxCommand install --force `"$projectRoot`""
if ($global:pipxCommand -eq "python -m pipx") {
    python -m pipx install --force "$projectRoot"
} else {
    & $global:pipxCommand install --force "$projectRoot"
}
if ($LASTEXITCODE -ne 0) { 
    Debug "pipx install exit code: $LASTEXITCODE"
    Fail "Failed to install prompt-automation from local source. Try running 'pipx install --force `"$projectRoot`"' manually." 
}
Info "✓ prompt-automation installed successfully"
Debug "prompt-automation installation completed"

# Verify installation
Info "Verifying installation..."
Debug "Verifying prompt-automation installation..."
$promptAutomationCmd = Get-Command prompt-automation -ErrorAction SilentlyContinue
if ($promptAutomationCmd) {
    Info "✓ prompt-automation command is available"
    Debug "prompt-automation found at $($promptAutomationCmd.Source)"
    try {
        $version = & prompt-automation --version 2>&1
        Info "   Version: $version"
        Debug "prompt-automation version: $version"
    } catch {
        Debug "Could not get version information: $_"
    }
} else {
    Write-Warning "prompt-automation command not found in PATH. You may need to restart your terminal."
}

Info ""
Info "🎉 Installation complete!"
Info ""
Info "Next steps:"
Info "1. You may need to log out and back in for hotkeys to activate"
Info "2. Try typing ':espanso' to test the text expander"
Info "3. Use 'prompt-automation --help' to see available commands"
Info "4. Press Ctrl+Shift+J to test the hotkey (after restart/relogin)"
Info ""
Info "Troubleshooting:"
Info "• If Ctrl+Shift+J doesn't work, run: .\install.ps1 -TroubleshootHotkeys"
Info "• For automatic fixes, try: .\install.ps1 -TroubleshootHotkeys -Fix"
Info "• If AutoHotkey installation was cancelled (UAC dialog), install manually:"
Info "  - Download from https://www.autohotkey.com/"
Info "  - Or run: winget install AutoHotkey.AutoHotkey"
Info "  - Then copy the script to startup folder manually"
Info "• If you experience system issues, you can disable espanso with 'espanso stop'"
Info "• AutoHotkey script location: $($env:APPDATA)\Microsoft\Windows\Start Menu\Programs\Startup\prompt-automation.ahk"
Info "• Check logs at: $LogFile"
Info ""
Debug "Installation process completed successfully"

# Display installation summary
Info ""
Info "=== Installation Summary ==="
$components = @(
    @{Name="Python"; Command="python"; Status=(Get-Command python -ErrorAction SilentlyContinue) -ne $null},
    @{Name="pipx"; Command="pipx"; Status=(Get-Command pipx -ErrorAction SilentlyContinue) -ne $null},
    @{Name="fzf"; Command="fzf"; Status=(Get-Command fzf -ErrorAction SilentlyContinue) -ne $null},
    @{Name="espanso"; Command="espanso"; Status=(Get-Command espanso -ErrorAction SilentlyContinue) -ne $null},
    @{Name="AutoHotkey"; Command="AutoHotkey"; Status=(Get-Command AutoHotkey -ErrorAction SilentlyContinue) -ne $null},
    @{Name="prompt-automation"; Command="prompt-automation"; Status=(Get-Command prompt-automation -ErrorAction SilentlyContinue) -ne $null}
)

foreach ($component in $components) {
    $status = if ($component.Status) { "[OK] Installed" } else { "[FAIL] Not found" }
    $color = if ($component.Status) { "Green" } else { "Red" }
    Write-Host "- $($component.Name): " -NoNewline
    Write-Host $status -ForegroundColor $color
}

$failedComponents = $components | Where-Object { -not $_.Status }
if ($failedComponents.Count -gt 0) {
    Info ""
    Write-Warning "Some components were not successfully installed. You may need to:"
    Write-Warning "1. Restart your terminal/PowerShell session"
    Write-Warning "2. Log out and log back in"
    Write-Warning "3. Check the installation log at: $LogFile"
    Write-Warning "4. Install missing components manually"
    
    # Check specifically for AutoHotkey failure and provide targeted guidance
    $ahkFailed = $failedComponents | Where-Object { $_.Name -eq "AutoHotkey" }
    if ($ahkFailed) {
        Info ""
        Write-Warning "AutoHotkey installation appears to have failed. This often happens when:"
        Write-Warning "• UAC permission dialogs are cancelled during installation"
        Write-Warning "• The user doesn't have sufficient privileges"
        Write-Warning ""
        Write-Warning "To fix AutoHotkey installation:"
        Write-Warning "1. Run PowerShell as Administrator"
        Write-Warning "2. Execute: winget install AutoHotkey.AutoHotkey"
        Write-Warning "3. Accept any UAC prompts that appear"
        Write-Warning "4. Alternatively, download and install from https://www.autohotkey.com/"
        Write-Warning ""
        Write-Warning "After installing AutoHotkey, you can manually copy the hotkey script:"
        Write-Warning "From: src\prompt_automation\hotkey\windows.ahk"
        Write-Warning "To: $($env:APPDATA)\Microsoft\Windows\Start Menu\Programs\Startup\prompt-automation.ahk"
    }
}

Debug "Detailed Summary:"
Debug "- Python: $(if (Get-Command python -ErrorAction SilentlyContinue) { 'Found' } else { 'Not found' })"
Debug "- pipx: $(if (Get-Command pipx -ErrorAction SilentlyContinue) { 'Found' } else { 'Not found' })"
Debug "- fzf: $(if (Get-Command fzf -ErrorAction SilentlyContinue) { 'Found' } else { 'Not found' })"
Debug "- espanso: $(if (Get-Command espanso -ErrorAction SilentlyContinue) { 'Found' } else { 'Not found' })"
Debug "- AutoHotkey: $(if (Get-Command AutoHotkey -ErrorAction SilentlyContinue) { 'Found' } else { 'Not found' })"
Debug "- prompt-automation: $(if (Get-Command prompt-automation -ErrorAction SilentlyContinue) { 'Found' } else { 'Not found' })"

Stop-Transcript | Out-Null
Info "Installation log saved to $LogFile"
Info "You can view the log for detailed information about the installation process."
Info "If you encounter any issues, please refer to the log for troubleshooting."
Info "Thank you for using prompt-automation!"
