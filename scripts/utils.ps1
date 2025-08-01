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
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
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
        $env:Path = "$machinePath;$userPath"
        Debug "PATH refreshed successfully"
    } catch {
        Debug "Error refreshing PATH: $_"
        Write-Warning "Could not refresh PATH environment. Some commands may not be found."
    }
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
                if ($PackageName -eq "AutoHotkey" -and $LASTEXITCODE -ne 0) {
                    # Check for specific AutoHotkey error codes
                    if ($LASTEXITCODE -eq -1978335189) {
                        Write-Warning "AutoHotkey installation returned exit code $LASTEXITCODE (0x8A15010B)"
                        Write-Warning "This typically means the package is already installed or requires elevated permissions."
                        # Check if AutoHotkey is actually installed
                        $ahkPaths = @(
                            "${env:ProgramFiles}\AutoHotkey\AutoHotkey.exe",
                            "${env:ProgramFiles(x86)}\AutoHotkey\AutoHotkey.exe",
                            "${env:LOCALAPPDATA}\Programs\AutoHotkey\AutoHotkey.exe"
                        )
                        foreach ($path in $ahkPaths) {
                            if (Test-Path $path) {
                                Info "[OK] AutoHotkey is actually installed at $path"
                                return $true
                            }
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
    }
    return $false
}
