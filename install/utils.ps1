# Shared helper functions for prompt-automation PowerShell scripts
function Info($msg) {
    Write-Host $msg -ForegroundColor Green
}
function Debug($msg) {
    Write-Host "[DEBUG] $msg" -ForegroundColor Cyan
}
function Fail($msg) {
    Write-Host $msg -ForegroundColor Red
    exit 1
}
function Test-ComponentAvailability {
    <#
    .SYNOPSIS
    Smart detection for all components used in the installation summary
    .DESCRIPTION
    This function provides intelligent detection that matches the logic used during installation
    #>
    param([string]$ComponentName)
    
    switch ($ComponentName) {
        'Python' {
            # Use the same logic as Test-PythonAvailability but simplified
            $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
            if ($pythonCmd) { return $true }
            
            $python3Cmd = Get-Command python3 -ErrorAction SilentlyContinue  
            if ($python3Cmd) { return $true }
            
            $pyCmd = Get-Command py -ErrorAction SilentlyContinue
            if ($pyCmd) { 
                try {
                    $version = & py --version 2>&1
                    if ($version -match "Python \d+\.\d+") { return $true }
                } catch { }
            }
            return $false
        }
        'AutoHotkey' {
            # Check command in PATH first
            $ahkCmd = Get-Command AutoHotkey -ErrorAction SilentlyContinue
            if ($ahkCmd) { return $true }
            
            # Check standard installation paths
            $standardPaths = @(
                "${env:ProgramFiles}\AutoHotkey\AutoHotkey.exe",
                "${env:ProgramFiles(x86)}\AutoHotkey\AutoHotkey.exe",
                "${env:LOCALAPPDATA}\Programs\AutoHotkey\AutoHotkey.exe"
            )
            
            foreach ($path in $standardPaths) {
                if (Test-Path $path) { return $true }
            }
            
            # Check registry
            try {
                $regKey = Get-ItemProperty -Path "HKLM:\SOFTWARE\AutoHotkey" -ErrorAction SilentlyContinue
                if ($regKey -and $regKey.InstallDir) {
                    $ahkPath = Join-Path $regKey.InstallDir "AutoHotkey.exe"
                    if (Test-Path $ahkPath) { return $true }
                }
            } catch { }
            
            return $false
        }
        default {
            # For other components, use standard Get-Command detection
            $cmd = Get-Command $ComponentName -ErrorAction SilentlyContinue
            return $cmd -ne $null
        }
    }
}

function Add-AutoHotkeyToPath {
    <#
    .SYNOPSIS
    Adds AutoHotkey directory to the user's PATH if it's not already there
    .DESCRIPTION
    Finds AutoHotkey installation and adds its directory to PATH for easier access
    #>
    
    # Find AutoHotkey installation
    $ahkPaths = @(
        "${env:ProgramFiles}\AutoHotkey",
        "${env:ProgramFiles(x86)}\AutoHotkey",
        "${env:LOCALAPPDATA}\Programs\AutoHotkey"
    )
    
    $ahkDir = $null
    foreach ($path in $ahkPaths) {
        $ahkExe = Join-Path $path "AutoHotkey.exe"
        if (Test-Path $ahkExe) {
            $ahkDir = $path
            break
        }
    }
    
    if (-not $ahkDir) {
        Debug "AutoHotkey installation directory not found"
        return $false
    }
    
    # Check if already in PATH
    $currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    if ($currentPath -like "*$ahkDir*") {
        Debug "AutoHotkey directory already in PATH"
        return $true
    }
    
    try {
        # Add to user PATH
        $newPath = if ($currentPath) { "$currentPath;$ahkDir" } else { $ahkDir }
        [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
        
        # Update current session PATH
        $env:PATH = "$env:PATH;$ahkDir"
        
        Info "Added AutoHotkey directory to PATH: $ahkDir"
        Info "Note: New terminals will have AutoHotkey in PATH automatically"
        return $true
    } catch {
        Debug "Failed to add AutoHotkey to PATH: $_"
        return $false
    }
}

function Show-ComponentStatus {
    <#
    .SYNOPSIS
    Display component status using intelligent detection
    #>
    param([string]$ComponentName, [string]$CommandName = $ComponentName)
    
    $isAvailable = Test-ComponentAvailability -ComponentName $ComponentName
    Debug "Component '$ComponentName' availability check: $isAvailable"
    
    $status = if ($isAvailable) { '[OK] Installed' } else { '[FAIL] Not found' }
    $color = if ($isAvailable) { 'Green' } else { 'Red' }
    
    Write-Host "- ${ComponentName}: " -NoNewline
    Write-Host $status -ForegroundColor $color
}

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Configure-StartupApplications {
    <#
    .SYNOPSIS
    Configures all necessary applications and scripts to start automatically on boot
    .DESCRIPTION
    Sets up AutoHotkey script, espanso service, and other components for automatic startup
    #>
    param(
        [switch]$ConfigureEspanso = $true,
        [switch]$ConfigureAutoHotkey = $true,
        [switch]$Force = $false
    )
    
    Info "Configuring startup applications..."
    $startupConfigured = $false
    
    # Configure AutoHotkey startup
    if ($ConfigureAutoHotkey) {
        $startupConfigured = (Setup-AutoHotkeyStartup -Force:$Force) -or $startupConfigured
    }
    
    # Configure espanso startup
    if ($ConfigureEspanso) {
        $startupConfigured = (Setup-EspansoStartup -Force:$Force) -or $startupConfigured
    }
    
    if ($startupConfigured) {
        Info "[OK] Startup applications configured successfully"
        Info "Components will automatically start after next login"
    } else {
        Write-Warning "No startup configuration changes were made"
    }
    
    return $startupConfigured
}

function Setup-AutoHotkeyStartup {
    <#
    .SYNOPSIS
    Sets up AutoHotkey script to start automatically
    #>
    param([switch]$Force)
    
    $startupPath = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
    $startupScript = Join-Path $startupPath 'prompt-automation.ahk'
    
    # Check if already configured
    if ((Test-Path $startupScript) -and -not $Force) {
        Debug "AutoHotkey script already in startup folder"
        return $false
    }
    
    # Find source script
    $scriptDir = $PSScriptRoot
    $sourceScript = Join-Path $scriptDir '..\src\prompt_automation\hotkey\windows.ahk'
    
    # Handle WSL path issues
    if ($sourceScript -like "\\wsl.localhost\*") {
        Debug "Converting WSL path for AutoHotkey script"
        $tempScript = Join-Path $env:TEMP 'prompt-automation-hotkey-temp.ahk'
        try {
            Copy-Item -Path $sourceScript -Destination $tempScript -Force
            $sourceScript = $tempScript
        } catch {
            Error "Failed to copy AutoHotkey script from WSL: $_"
            return $false
        }
    }
    
    if (Test-Path $sourceScript) {
        try {
            # Ensure startup directory exists
            if (-not (Test-Path $startupPath)) {
                New-Item -ItemType Directory -Path $startupPath -Force | Out-Null
            }
            
            Copy-Item -Path $sourceScript -Destination $startupScript -Force
            Info "[OK] AutoHotkey script configured for startup"
            Debug "  Script location: $startupScript"
            
            # Clean up temp file if used
            if ($sourceScript -like "*temp*") {
                Remove-Item $sourceScript -Force -ErrorAction SilentlyContinue
            }
            
            return $true
        } catch {
            Error "Failed to copy AutoHotkey script to startup: $_"
            return $false
        }
    } else {
        Error "AutoHotkey source script not found at: $sourceScript"
        return $false
    }
}

function Setup-EspansoStartup {
    <#
    .SYNOPSIS
    Configures espanso to start automatically as a service
    #>
    param([switch]$Force)
    
    $espansoCmd = Get-Command espanso -ErrorAction SilentlyContinue
    if (-not $espansoCmd) {
        Debug "espanso not found, skipping startup configuration"
        return $false
    }
    
    try {
        # Check if espanso service is already registered
        $serviceStatus = & espanso service status 2>&1
        if ($serviceStatus -match "registered" -and -not $Force) {
            Debug "espanso service already registered"
            return $false
        }
        
        # Register espanso service for startup
        Info "Configuring espanso to start automatically..."
        $registerResult = & espanso service register 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Info "[OK] espanso configured for automatic startup"
            Debug "  Service registered successfully"
            
            # Start the service now
            $startResult = & espanso service start 2>&1
            if ($LASTEXITCODE -eq 0) {
                Info "[OK] espanso service started"
            } else {
                Write-Warning "espanso service registered but failed to start: $startResult"
            }
            
            return $true
        } else {
            Write-Warning "Failed to register espanso service: $registerResult"
            return $false
        }
    } catch {
        Write-Warning "Error configuring espanso startup: $_"
        return $false
    }
}

function Test-StartupConfiguration {
    <#
    .SYNOPSIS
    Tests if startup applications are properly configured
    #>
    $results = @{
        AutoHotkey = $false
        Espanso = $false
        Issues = @()
    }
    
    # Check AutoHotkey startup
    $startupScript = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup\prompt-automation.ahk'
    if (Test-Path $startupScript) {
        $results.AutoHotkey = $true
        Debug "AutoHotkey startup script found"
    } else {
        $results.Issues += "AutoHotkey script not found in startup folder"
    }
    
    # Check espanso service
    $espansoCmd = Get-Command espanso -ErrorAction SilentlyContinue
    if ($espansoCmd) {
        try {
            # First check if espanso is running
            $espansoStatus = & espanso status 2>&1
            Debug "espanso status check: $espansoStatus"
            
            if ($espansoStatus -match "espanso is running") {
                # If it's running, check if it's set up as a service
                $serviceStatus = & espanso service status 2>&1
                Debug "espanso service status check: '$serviceStatus'"
                
                if ($serviceStatus -match "registered" -or $serviceStatus -match "running") {
                    $results.Espanso = $true
                    Debug "espanso service is registered for startup"
                } elseif ([string]::IsNullOrWhiteSpace($serviceStatus)) {
                    # Empty response means no service configured, but espanso is running manually
                    Debug "espanso is running but not as a service - this is acceptable"
                    # Don't mark as an issue since espanso is working
                } else {
                    $results.Issues += "espanso service not registered for startup"
                    Debug "espanso service status indicates not registered: '$serviceStatus'"
                }
            } else {
                $results.Issues += "espanso is installed but not running"
                Debug "espanso is not running: $espansoStatus"
            }
        } catch {
            $results.Issues += "Could not check espanso service status"
            Debug "Error checking espanso service: $_"
        }
    } else {
        Debug "espanso not installed, skipping startup check"
    }
    
    return $results
}
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
            Write-Host "Operation cancelled by user." -ForegroundColor Red
            exit 1
        }
    }
    return $true
}
function Refresh-PathEnvironment {
    Debug "Refreshing PATH environment variables..."
    try {
        $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
        $userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
        $newPath = "$machinePath;$userPath"
        
        # Remove duplicate paths and empty entries
        $pathEntries = $newPath -split ';' | Where-Object { $_ -and $_.Trim() } | Sort-Object -Unique
        $env:Path = $pathEntries -join ';'
        
        Debug "PATH refreshed successfully"
        Debug "Current PATH length: $($env:Path.Length) characters"
        
        # Also refresh other important environment variables that might affect Python/pipx
        try {
            $env:PATHEXT = [System.Environment]::GetEnvironmentVariable("PATHEXT", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATHEXT", "User")
        } catch {
            Debug "Could not refresh PATHEXT: $_"
        }
        
    } catch {
        Debug "Error refreshing PATH: $_"
        Write-Warning "Could not refresh PATH environment. Some commands may not be found."
        Write-Warning "You may need to restart your terminal for PATH changes to take effect."
    }
}

function Find-PythonInstallation {
    <#
    .SYNOPSIS
    Searches for Python installations and adds them to the current session PATH if found.
    .DESCRIPTION
    This function searches common Python installation locations and attempts to add
    the Python directory and Scripts directory to the current session PATH.
    Returns $true if Python is found and made available, $false otherwise.
    #>
    Debug "Searching for Python installation..."
    
    # First, try to find python command that might already be available but not detected
    $pythonCommands = @('python', 'python3', 'py')
    foreach ($cmd in $pythonCommands) {
        try {
            $result = Get-Command $cmd -ErrorAction SilentlyContinue
            if ($result) {
                $version = & $cmd --version 2>&1
                if ($version -match "Python \d+\.\d+") {
                    Info "[OK] Found working Python command '$cmd': $version"
                    Info "Location: $($result.Source)"
                    # Make sure 'python' alias is available
                    if ($cmd -ne 'python') {
                        Set-Alias -Name python -Value $result.Source -Scope Global -Force
                        Debug "Created 'python' alias for '$cmd'"
                    }
                    return $true
                }
            }
        } catch {
            Debug "Could not test command '$cmd': $_"
        }
    }
    
    # Check Windows Store Python location
    $storeApps = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps"
    if (Test-Path $storeApps) {
        $storePythons = @('python.exe', 'python3.exe')
        foreach ($pythonExe in $storePythons) {
            $storePython = Join-Path $storeApps $pythonExe
            if (Test-Path $storePython) {
                try {
                    $version = & "$storePython" --version 2>&1
                    if ($version -match "Python \d+\.\d+") {
                        Info "[OK] Found Windows Store Python: $storePython ($version)"
                        if ($env:PATH -notlike "*$storeApps*") {
                            $env:PATH = "$storeApps;$env:PATH"
                            Debug "Added Windows Store apps to PATH: $storeApps"
                        }
                        Set-Alias -Name python -Value $storePython -Scope Global -Force
                        return $true
                    }
                } catch {
                    Debug "Windows Store Python at $storePython not working: $_"
                }
            }
        }
    }
    
    # Comprehensive search for Python installations
    $searchRoots = @(
        $env:LOCALAPPDATA,
        $env:ProgramFiles,
        $env:APPDATA
    )
    if ($env:ProgramFiles -ne "${env:ProgramFiles(x86)}") {
        $searchRoots += "${env:ProgramFiles(x86)}"
    }
    
    $foundPythons = @()
    
    # Search for Python installations
    foreach ($root in $searchRoots) {
        if (Test-Path $root) {
            try {
                Debug "Searching for Python in: $root"
                
                # Look for Python directories (various patterns)
                $pythonPatterns = @("Python*", "python*")
                foreach ($pattern in $pythonPatterns) {
                    try {
                        $pythonDirs = Get-ChildItem -Path $root -Directory -Name $pattern -ErrorAction SilentlyContinue
                        foreach ($dir in $pythonDirs) {
                            $pythonPath = Join-Path (Join-Path $root $dir) "python.exe"
                            if (Test-Path $pythonPath) {
                                $foundPythons += $pythonPath
                                Debug "Found potential Python at: $pythonPath"
                            }
                        }
                    } catch {
                        Debug "Error searching pattern $pattern in $root`: $($_.Exception.Message)"
                    }
                }
                
                # Also look in Programs\Python subdirectory (common for user installs)
                $programsPython = Join-Path $root "Programs\Python"
                if (Test-Path $programsPython) {
                    try {
                        $pythonVersionDirs = Get-ChildItem -Path $programsPython -Directory -Name "Python*" -ErrorAction SilentlyContinue
                        foreach ($versionDir in $pythonVersionDirs) {
                            $pythonPath = Join-Path (Join-Path $programsPython $versionDir) "python.exe"
                            if (Test-Path $pythonPath) {
                                $foundPythons += $pythonPath
                                Debug "Found potential Python at: $pythonPath"
                            }
                        }
                    } catch {
                        Debug "Error searching Programs\Python in $root`: $($_.Exception.Message)"
                    }
                }
                
                # Check for Anaconda/Miniconda installations
                $condaPaths = @("Anaconda3", "Miniconda3", "anaconda3", "miniconda3")
                foreach ($condaPath in $condaPaths) {
                    $fullCondaPath = Join-Path $root $condaPath
                    if (Test-Path $fullCondaPath) {
                        $condaPython = Join-Path $fullCondaPath "python.exe"
                        if (Test-Path $condaPython) {
                            $foundPythons += $condaPython
                            Debug "Found Conda Python at: $condaPython"
                        }
                    }
                }
                
            } catch {
                Debug "Error searching in ${root}: $_"
            }
        }
    }
    
    # Also check common direct paths
    $commonPaths = @(
        "C:\Python312\python.exe",
        "C:\Python311\python.exe",
        "C:\Python310\python.exe",
        "C:\Python39\python.exe",
        "C:\Python38\python.exe"
    )
    foreach ($path in $commonPaths) {
        if (Test-Path $path) {
            $foundPythons += $path
            Debug "Found Python at common path: $path"
        }
    }
    
    # Remove duplicates and sort by version (newest first)
    $foundPythons = $foundPythons | Sort-Object -Unique
    
    # Test each Python installation and use the first working one
    $workingPythons = @()
    foreach ($pythonPath in $foundPythons) {
        try {
            Debug "Testing Python at: $pythonPath"
            $version = & "$pythonPath" --version 2>&1
            
            if ($version -and ($version -match "Python (\d+)\.(\d+)\.?(\d*)")) {
                $major = [int]$matches[1]
                $minor = [int]$matches[2]
                $patch = if ($matches[3]) { [int]$matches[3] } else { 0 }
                
                Debug "Working Python found: $pythonPath ($version)"
                $workingPythons += @{
                    Path = $pythonPath
                    Version = $version
                    Major = $major
                    Minor = $minor
                    Patch = $patch
                    SortKey = ($major * 10000) + ($minor * 100) + $patch
                }
            }
        } catch {
            Debug "Could not test Python at $pythonPath : $_"
        }
    }
    
    if ($workingPythons.Count -eq 0) {
        Debug "No working Python installations found"
        Info "Searched the following locations:"
        foreach ($root in $searchRoots) {
            Info "  - $root"
        }
        if ($foundPythons.Count -gt 0) {
            Info "Found Python executables but none are working:"
            foreach ($path in ($foundPythons | Select-Object -First 5)) {
                Info "  - $path"
            }
        }
        return $false
    }
    
    # Sort by version (newest first) and use the best one
    $bestPython = $workingPythons | Sort-Object -Property SortKey -Descending | Select-Object -First 1
    $pythonPath = $bestPython.Path
    $pythonVersion = $bestPython.Version
    
    Info "[OK] Using Python installation: $pythonPath"
    Info "Version: $pythonVersion"
    
    # Add Python directory to PATH for current session
    $pythonDir = Split-Path $pythonPath -Parent
    $pythonScripts = Join-Path $pythonDir "Scripts"
    
    $pathUpdated = $false
    if ($env:PATH -notlike "*$pythonDir*") {
        $env:PATH = "$pythonDir;$env:PATH"
        Debug "Added Python directory to PATH: $pythonDir"
        $pathUpdated = $true
    }
    if ((Test-Path $pythonScripts) -and ($env:PATH -notlike "*$pythonScripts*")) {
        $env:PATH = "$pythonScripts;$env:PATH"
        Debug "Added Python Scripts directory to PATH: $pythonScripts"
        $pathUpdated = $true
    }
    
    if ($pathUpdated) {
        Info "Added Python to current session PATH"
    }
    
    # Create python alias
    Set-Alias -Name python -Value $pythonPath -Scope Global -Force
    Debug "Created 'python' alias pointing to: $pythonPath"
    
    # Test if python command works now
    try {
        $testVersion = & python --version 2>&1
        if ($testVersion -match "Python \d+\.\d+") {
            Info "[OK] Python command is now available: $testVersion"
            return $true
        }
    } catch {
        Debug "Python alias test failed: $_"
    }
    
    # If we got here, we found Python but the command might not work perfectly
    # Still return true since we have a working Python installation
    Info "[OK] Python installation configured (may need terminal restart for full functionality)"
    return $true
}
function Install-WingetPackage {
    param(
        [string]$PackageId,
        [string]$PackageName,
        [int]$MaxRetries = 2
    )
    Info "Installing $PackageName..."
    for ($i = 1; $i -le $MaxRetries; $i++) {
        if ($MaxRetries -gt 1) { Debug "Attempting to install $PackageName (attempt $i/$MaxRetries)..." }
        Debug "Executing: winget install -e --id $PackageId --accept-source-agreements --accept-package-agreements"
        try {
            winget install -e --id $PackageId --accept-source-agreements --accept-package-agreements
            if ($LASTEXITCODE -eq 0) {
                Info "[OK] $PackageName installed successfully"
                Debug "$PackageName installation completed successfully"
                return $true
            } else {
                Debug "winget $PackageName exit code: $LASTEXITCODE"
                
                # Handle specific error codes for Python
                if ($PackageName -eq "Python" -and $LASTEXITCODE -ne 0) {
                    if ($LASTEXITCODE -eq -1978335212) {
                        Write-Warning "Python installation returned exit code $LASTEXITCODE"
                        Write-Warning "This may indicate the package is already installed, needs elevated permissions, or there's a version conflict."
                        
                        # Check if Python was actually installed despite the error
                        Start-Sleep -Seconds 3  # Give system more time to register the installation
                        
                        # Force refresh PATH and check again
                        try {
                            $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
                            $userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
                            $env:Path = "$machinePath;$userPath"
                            Debug "PATH refreshed after Python installation"
                        } catch {
                            Debug "Could not refresh PATH: $_"
                        }
                        
                        # Check if python command is now available
                        $pythonCheck = Get-Command python -ErrorAction SilentlyContinue
                        if ($pythonCheck) {
                            try {
                                $version = & python --version 2>&1
                                Info "[OK] Python is actually available despite error code: $version"
                                return $true
                            } catch {
                                Debug "Python command found but not working: $_"
                            }
                        }
                        
                        # Do a comprehensive search for Python installations
                        $searchRoots = @($env:LOCALAPPDATA, $env:ProgramFiles)
                        if ($env:ProgramFiles -ne "${env:ProgramFiles(x86)}") {
                            $searchRoots += "${env:ProgramFiles(x86)}"
                        }
                        
                        foreach ($root in $searchRoots) {
                            if (Test-Path $root) {
                                try {
                                    # Look for recent Python installations
                                    $pythonDirs = Get-ChildItem -Path $root -Directory -Name "Python*" -ErrorAction SilentlyContinue
                                    foreach ($dir in $pythonDirs) {
                                        $pythonPath = Join-Path (Join-Path $root $dir) "python.exe"
                                        if (Test-Path $pythonPath) {
                                            try {
                                                $version = & "$pythonPath" --version 2>&1
                                                if ($version -match "Python \d+\.\d+") {
                                                    Info "[OK] Found working Python installation despite error: $pythonPath ($version)"
                                                    return $true
                                                }
                                            } catch {
                                                Debug "Found Python at $pythonPath but couldn't get version: $_"
                                            }
                                        }
                                    }
                                    
                                    # Also check Programs\Python subdirectory
                                    $programsPython = Join-Path $root "Programs\Python"
                                    if (Test-Path $programsPython) {
                                        $pythonVersionDirs = Get-ChildItem -Path $programsPython -Directory -Name "Python*" -ErrorAction SilentlyContinue
                                        foreach ($versionDir in $pythonVersionDirs) {
                                            $pythonPath = Join-Path (Join-Path $programsPython $versionDir) "python.exe"
                                            if (Test-Path $pythonPath) {
                                                try {
                                                    $version = & "$pythonPath" --version 2>&1
                                                    if ($version -match "Python \d+\.\d+") {
                                                        Info "[OK] Found working Python installation despite error: $pythonPath ($version)"
                                                        return $true
                                                    }
                                                } catch {
                                                    Debug "Found Python at $pythonPath but couldn't get version: $_"
                                                }
                                            }
                                        }
                                    }
                                } catch {
                                    Debug "Error searching for Python in ${root}: $_"
                                }
                            }
                        }
                    } else {
                        Write-Warning "Python installation returned exit code $LASTEXITCODE"
                    }
                }
                
                # Handle AutoHotkey specific errors
                if ($PackageName -eq "AutoHotkey" -and $LASTEXITCODE -ne 0) {
                    # Check for specific AutoHotkey error codes
                    if ($LASTEXITCODE -eq -1978335189) {
                        Write-Warning "AutoHotkey installation returned exit code $LASTEXITCODE (0x8A15010B)"
                        Write-Warning "This typically means the package is already installed or requires elevated permissions."
                        
                        # Give system time to register any installation
                        Start-Sleep -Seconds 3
                        
                        # Check if AutoHotkey is actually installed despite the error
                        $ahkPaths = @(
                            "${env:ProgramFiles}\AutoHotkey\AutoHotkey.exe",
                            "${env:ProgramFiles(x86)}\AutoHotkey\AutoHotkey.exe",
                            "${env:LOCALAPPDATA}\Programs\AutoHotkey\AutoHotkey.exe",
                            "${env:ProgramFiles}\AutoHotkey\v2\AutoHotkey64.exe",
                            "${env:ProgramFiles}\AutoHotkey\v2\AutoHotkey32.exe",
                            "${env:ProgramFiles(x86)}\AutoHotkey\v2\AutoHotkey64.exe",
                            "${env:ProgramFiles(x86)}\AutoHotkey\v2\AutoHotkey32.exe"
                        )
                        
                        foreach ($path in $ahkPaths) {
                            if (Test-Path $path) {
                                Info "[OK] AutoHotkey is actually installed at $path despite error code"
                                return $true
                            }
                        }
                        
                        # Also check Windows Registry for AutoHotkey installation
                        try {
                            $regPaths = @(
                                "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
                                "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
                                "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*"
                            )
                            
                            foreach ($regPath in $regPaths) {
                                $apps = Get-ItemProperty $regPath -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -like "*AutoHotkey*" }
                                if ($apps) {
                                    foreach ($app in $apps) {
                                        $installLocation = $app.InstallLocation
                                        if ($installLocation -and (Test-Path $installLocation)) {
                                            $ahkExe = Get-ChildItem -Path $installLocation -Name "AutoHotkey*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
                                            if ($ahkExe) {
                                                $fullPath = Join-Path $installLocation $ahkExe
                                                Info "[OK] AutoHotkey found via registry at $fullPath"
                                                return $true
                                            }
                                        }
                                    }
                                }
                            }
                        } catch {
                            Debug "Could not check registry for AutoHotkey: $_"
                        }
                    } else {
                        Write-Warning "AutoHotkey installation returned exit code $LASTEXITCODE"
                    }
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
        Write-Warning "- Cancelled UAC permission dialogs"
        Write-Warning "- Insufficient administrator privileges"
        Write-Warning "- Installation conflicts with existing AutoHotkey versions"
    } elseif ($PackageName -eq "Python") {
        Write-Warning "For Python, this may be caused by:"
        Write-Warning "- Cancelled UAC permission dialogs"
        Write-Warning "- Existing Python installation conflicts"
        Write-Warning "- Microsoft Store Python installation interference"
        Write-Warning "You may need to install Python manually from https://python.org"
    }
    return $false
}

function Test-PythonAvailability {
    <#
    .SYNOPSIS
    Tests if Python is available through various methods
    .DESCRIPTION
    This function tests multiple ways to access Python and returns detailed information
    about what's available on the system.
    #>
    Debug "Testing Python availability..."
    
    $results = @{
        PythonCommand = $false
        Python3Command = $false
        PyCommand = $false
        WindowsStorePython = $false
        PythonAlias = $false
        FoundInstallations = @()
        WorkingPython = $null
        ErrorDetails = @()
    }
    
    # Test python command
    try {
        $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
        if ($pythonCmd) {
            $version = & python --version 2>&1
            if ($version -match "Python \d+\.\d+") {
                $results.PythonCommand = $true
                $results.WorkingPython = @{
                    Command = "python"
                    Path = $pythonCmd.Source
                    Version = $version
                }
                Debug "python command works: $version at $($pythonCmd.Source)"
            }
        }
    } catch {
        $results.ErrorDetails += "python command failed: $_"
        Debug "python command failed: $_"
    }
    
    # Test python3 command
    try {
        $python3Cmd = Get-Command python3 -ErrorAction SilentlyContinue
        if ($python3Cmd) {
            $version = & python3 --version 2>&1
            if ($version -match "Python \d+\.\d+") {
                $results.Python3Command = $true
                if (-not $results.WorkingPython) {
                    $results.WorkingPython = @{
                        Command = "python3"
                        Path = $python3Cmd.Source
                        Version = $version
                    }
                }
                Debug "python3 command works: $version at $($python3Cmd.Source)"
            }
        }
    } catch {
        $results.ErrorDetails += "python3 command failed: $_"
        Debug "python3 command failed: $_"
    }
    
    # Test py command (Python Launcher)
    try {
        $pyCmd = Get-Command py -ErrorAction SilentlyContinue
        if ($pyCmd) {
            $version = & py --version 2>&1
            if ($version -match "Python \d+\.\d+") {
                $results.PyCommand = $true
                if (-not $results.WorkingPython) {
                    $results.WorkingPython = @{
                        Command = "py"
                        Path = $pyCmd.Source
                        Version = $version
                    }
                }
                Debug "py command works: $version at $($pyCmd.Source)"
            }
        }
    } catch {
        $results.ErrorDetails += "py command failed: $_"
        Debug "py command failed: $_"
    }
    
    # Test Windows Store Python
    $storeApps = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps"
    $storePython = Join-Path $storeApps "python.exe"
    if (Test-Path $storePython) {
        try {
            $version = & "$storePython" --version 2>&1
            if ($version -match "Python \d+\.\d+") {
                $results.WindowsStorePython = $true
                $results.FoundInstallations += @{
                    Path = $storePython
                    Version = $version
                    Type = "Windows Store"
                }
                Debug "Windows Store Python works: $version at $storePython"
            }
        } catch {
            $results.ErrorDetails += "Windows Store Python failed: $_"
            Debug "Windows Store Python failed: $_"
        }
    }
    
    return $results
}

function Show-PythonDiagnostics {
    <#
    .SYNOPSIS
    Shows detailed diagnostics for Python installation issues
    #>
    Info "=== Python Installation Diagnostics ==="
    
    $results = Test-PythonAvailability
    
    Info "Command availability:"
    Info "  - python command: $(if ($results.PythonCommand) { '[OK]' } else { '[NOT FOUND]' })"
    Info "  - python3 command: $(if ($results.Python3Command) { '[OK]' } else { '[NOT FOUND]' })"
    Info "  - py command: $(if ($results.PyCommand) { '[OK]' } else { '[NOT FOUND]' })"
    Info "  - Windows Store Python: $(if ($results.WindowsStorePython) { '[OK]' } else { '[NOT FOUND]' })"
    
    if ($results.WorkingPython) {
        Info ""
        Info "Working Python found:"
        Info "  Command: $($results.WorkingPython.Command)"
        Info "  Version: $($results.WorkingPython.Version)"
        Info "  Path: $($results.WorkingPython.Path)"
    }
    
    if ($results.FoundInstallations.Count -gt 0) {
        Info ""
        Info "Found Python installations:"
        foreach ($install in $results.FoundInstallations) {
            Info "  - $($install.Type): $($install.Version) at $($install.Path)"
        }
    }
    
    if ($results.ErrorDetails.Count -gt 0) {
        Info ""
        Info "Error details:"
        foreach ($error in $results.ErrorDetails) {
            Info "  - $error"
        }
    }
    
    # Show PATH information
    Info ""
    Info "Current PATH contains:"
    $pathEntries = $env:PATH -split ';' | Where-Object { $_ -like "*python*" -or $_ -like "*Python*" }
    if ($pathEntries) {
        foreach ($entry in $pathEntries) {
            Info "  - $entry"
        }
    } else {
        Info "  - No Python-related paths found in PATH"
    }
    
    # Check for common Python installation directories
    Info ""
    Info "Checking common installation directories:"
    $commonDirs = @(
        "${env:LOCALAPPDATA}\Programs\Python",
        "${env:ProgramFiles}\Python312",
        "${env:ProgramFiles}\Python311", 
        "${env:ProgramFiles(x86)}\Python312",
        "${env:ProgramFiles(x86)}\Python311",
        "${env:APPDATA}\Python",
        "C:\Python312",
        "C:\Python311"
    )
    
    foreach ($dir in $commonDirs) {
        if (Test-Path $dir) {
            $pythonExe = Join-Path $dir "python.exe"
            if (Test-Path $pythonExe) {
                try {
                    $version = & "$pythonExe" --version 2>&1
                    Info "  [FOUND] $dir - $version"
                } catch {
                    Info "  [FOUND] $dir - (version check failed)"
                }
            } else {
                Info "  [DIR EXISTS] $dir - (no python.exe)"
            }
        }
    }
    
    Info ""
    Info "=== End Diagnostics ==="
    
    return $results.WorkingPython -ne $null
}
