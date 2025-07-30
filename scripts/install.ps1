# PowerShell install script for prompt-automation
param()

function Info($msg) { Write-Host $msg -ForegroundColor Green }
function Fail($msg) { Write-Host $msg -ForegroundColor Red; exit 1 }

if (-not [System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::Windows)) {
    Fail "This installer must be run on Windows."
}

# Ensure Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Info "Installing Python3 via winget..."
    winget install -e --id Python.Python.3 || Fail "Failed to install Python"
}

# Ensure pipx
if (-not (Get-Command pipx -ErrorAction SilentlyContinue)) {
    Info "Installing pipx..."
    python -m pip install --user pipx || Fail "pip install pipx failed"
    python -m pipx ensurepath
    $env:Path += ";$([Python]::CreateEngine().GetSysModule().GetAttr('prefix').ToString())\Scripts"
}

# Install fzf
if (-not (Get-Command fzf -ErrorAction SilentlyContinue)) {
    Info "Installing fzf..."
    winget install -e --id Git.Fzf || Fail "Failed to install fzf"
}

# Install espanso
if (-not (Get-Command espanso -ErrorAction SilentlyContinue)) {
    Info "Installing espanso..."
    winget install -e --id Espanso.Espanso || Fail "Failed to install espanso"
}

# Install AutoHotkey v2
if (-not (Get-Command AutoHotkey -ErrorAction SilentlyContinue)) {
    Info "Installing AutoHotkey..."
    winget install -e --id AutoHotkey.AutoHotkey || Fail "Failed to install AutoHotkey"
}

# Copy AHK script to Startup
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ahkSource = Join-Path $scriptDir '..\src\prompt_automation\hotkey\windows.ahk'
$ahkSource = Resolve-Path $ahkSource
$startup = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup\prompt-automation.ahk'
try {
    Copy-Item -Path $ahkSource -Destination $startup -Force
    Info "Registered prompt-automation hotkey script."
} catch {
    Write-Warning "Failed to register AutoHotkey script: $_"
}

# Install prompt-automation
Info "Installing prompt-automation via pipx..."
pipx install --force prompt-automation || Fail "Failed to install prompt-automation"

Info "Installation complete. You may need to log out and back in for hotkeys to activate."
