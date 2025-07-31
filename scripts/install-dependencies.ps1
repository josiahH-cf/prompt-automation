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

if (-not [System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::Windows)) {
    Fail "This installer must be run on Windows."
}

# Ensure Python
Info "Checking for Python installation..."
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCmd) {
    $pythonVersion = & python --version 2>&1
    Info "✓ Python is already installed: $pythonVersion"
    Debug "Found Python: $pythonVersion at $($pythonCmd.Source)"
} else {
    Info "Python not found. Installing Python3 via winget..."
    if (-not (Install-WingetPackage -PackageId 'Python.Python.3' -PackageName 'Python')) {
        Fail "Failed to install Python. Check winget is available and try again."
    }
    Info "✓ Python installation completed successfully"
    Refresh-PathEnvironment
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) { Fail 'Python still not found in PATH after installation.' }
}

# Ensure pipx
Info "Checking for pipx..."
$pipxCmd = Get-Command pipx -ErrorAction SilentlyContinue
if ($pipxCmd) {
    Info "✓ pipx is already installed"
    Debug "Found pipx at $($pipxCmd.Source)"
} else {
    Info "pipx not found. Installing pipx..."
    python -m pip install --user pipx
    if ($LASTEXITCODE -ne 0) { Fail 'pip install pipx failed.' }
    python -m pipx ensurepath
    try {
        $userScripts = python -c "import sysconfig; print(sysconfig.get_path('scripts', scheme='nt_user'))" 2>$null
        if ($userScripts -and (Test-Path $userScripts) -and ($env:Path -notlike "*$userScripts*")) { $env:Path += ";$userScripts" }
        $pythonUserBase = python -c "import site; print(site.USER_BASE)" 2>$null
        if ($pythonUserBase) {
            $alternateScripts = Join-Path $pythonUserBase 'Scripts'
            if ((Test-Path $alternateScripts) -and ($env:Path -notlike "*$alternateScripts*")) { $env:Path += ";$alternateScripts" }
        }
        $pythonVersion = python -c "import sys; print(f'Python{sys.version_info.major}{sys.version_info.minor}')" 2>$null
        if ($pythonVersion) {
            $standardUserScripts = Join-Path $env:APPDATA "$pythonVersion\Scripts"
            if ((Test-Path $standardUserScripts) -and ($env:Path -notlike "*$standardUserScripts*")) { $env:Path += ";$standardUserScripts" }
        }
        $standardUserScripts312 = Join-Path $env:APPDATA 'Python\Python312\Scripts'
        if ((Test-Path $standardUserScripts312) -and ($env:Path -notlike "*$standardUserScripts312*")) { $env:Path += ";$standardUserScripts312" }
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
    if ($fzfInstalled) { Info '✓ fzf installed successfully' }
    Refresh-PathEnvironment
} else {
    Info '✓ fzf is already installed'
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
            if ($espansoStatus -match 'espanso is running') { Info '✓ espanso service started successfully' }
        } catch { Write-Warning 'Could not start espanso automatically.' }
    }
} else {
    Info '✓ espanso is already installed'
}

# Install AutoHotkey
Info 'Checking for AutoHotkey...'
$ahk = Get-Command AutoHotkey -ErrorAction SilentlyContinue
if (-not $ahk) {
    Info 'AutoHotkey not found. Installing AutoHotkey...'
    $ahkInstalled = Install-WingetPackage -PackageId 'AutoHotkey.AutoHotkey' -PackageName 'AutoHotkey'
    Refresh-PathEnvironment
    $ahk = Get-Command AutoHotkey -ErrorAction SilentlyContinue
    if (-not $ahkInstalled -and -not $ahk) {
        Write-Warning 'AutoHotkey installation may have failed.'
    }
} else {
    Info '✓ AutoHotkey is already installed'
}

# Copy AHK script to startup
$ahkAvailable = (Get-Command AutoHotkey -ErrorAction SilentlyContinue) -ne $null
if ($ahkAvailable) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
    $ahkSource = Join-Path $scriptDir '..\src\prompt_automation\hotkey\windows.ahk'
    if (Test-Path $ahkSource) {
        $ahkSource = Resolve-Path $ahkSource
        $startup = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup\prompt-automation.ahk'
        try { Copy-Item -Path $ahkSource -Destination $startup -Force } catch { Write-Warning "Failed to copy hotkey script: $_" }
    } else {
        Write-Warning "AutoHotkey source script not found at $ahkSource."
    }
} else {
    Write-Warning 'AutoHotkey is not available - skipping hotkey script setup.'
}

Stop-Transcript | Out-Null
Info "Dependency installation complete. Log saved to $LogFile"
