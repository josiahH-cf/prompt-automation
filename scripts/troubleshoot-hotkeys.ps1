<#
.SYNOPSIS
Troubleshoots prompt-automation hotkey issues.
.DESCRIPTION
Provides diagnostics and optional fixes for the AutoHotkey integration.
#>

param(
    [switch]$Fix,
    [switch]$Status,
    [switch]$Restart
)

. "$PSScriptRoot/utils.ps1"

$LogDir = Join-Path $env:USERPROFILE '.prompt-automation\logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir 'troubleshoot-hotkeys.log'
Start-Transcript -Path $LogFile -Append | Out-Null
trap { Write-Warning "Error on line $($_.InvocationInfo.ScriptLineNumber). See $LogFile" }

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

    $ahkCmd = Get-Command AutoHotkey -ErrorAction SilentlyContinue
    if ($ahkCmd) {
        Info "✓ AutoHotkey is installed at: $($ahkCmd.Source)"
        try { $ahkVersion = & $ahkCmd.Source --version 2>&1; Debug "  Version: $ahkVersion" } catch { }
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
                } else {
                    Error "✗ AutoHotkey installation failed with exit code: $LASTEXITCODE"
                    Warn "This often indicates UAC dialogs were cancelled or permission issues"
                }
            } catch { Error "✗ AutoHotkey installation failed with exception: $_" }
        }
        return
    }

    $startupScript = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup\prompt-automation.ahk'
    if (Test-Path $startupScript) {
        Info "✓ AutoHotkey script found in startup folder"
        Debug "  Location: $startupScript"
    } else {
        Error "✗ AutoHotkey script not found in startup folder"
        Debug "  Expected location: $startupScript"
        if ($Fix) {
            Info "Attempting to fix by copying the script..."
            $scriptDir = $PSScriptRoot
            $sourceScript = Join-Path $scriptDir '..\src\prompt_automation\hotkey\windows.ahk'
            
            # Handle WSL path issues
            if ($sourceScript -like "\\wsl.localhost\*") {
                $tempScript = Join-Path $env:TEMP 'prompt-automation-hotkey-temp.ahk'
                try {
                    Copy-Item -Path $sourceScript -Destination $tempScript -Force
                    $sourceScript = $tempScript
                } catch {
                    Error "✗ Failed to copy script from WSL: $_"
                    return
                }
            }
            
            if (Test-Path $sourceScript) { 
                Copy-Item -Path $sourceScript -Destination $startupScript -Force
                Info "✓ Script copied to startup folder"
                
                # Clean up temp file if used
                if ($sourceScript -like "*temp*") {
                    Remove-Item $sourceScript -Force -ErrorAction SilentlyContinue
                }
            } else { 
                Error "✗ Source script not found at: $sourceScript" 
            }
        }
    }

    $ahkProcess = Get-Process -Name "AutoHotkey*" -ErrorAction SilentlyContinue
    if ($ahkProcess) {
        Info "✓ AutoHotkey process is running:"
        foreach ($proc in $ahkProcess) { Debug "  PID: $($proc.Id), Name: $($proc.ProcessName)" }
    } else {
        Warn "⚠ No AutoHotkey processes found running"
        if ($Fix -or $Restart) {
            Info "Starting AutoHotkey script manually..."
            if (Test-Path $startupScript) {
                try {
                    Start-Process -FilePath $ahkCmd.Source -ArgumentList "`"$startupScript`"" -NoNewWindow
                    Start-Sleep -Seconds 2
                    $ahkProcess = Get-Process -Name "AutoHotkey*" -ErrorAction SilentlyContinue
                    if ($ahkProcess) { Info "✓ AutoHotkey script started successfully" } else { Error "✗ Failed to start AutoHotkey script" }
                } catch { Error "✗ Error starting AutoHotkey: $_" }
            }
        }
    }

    $paCmd = Get-Command prompt-automation -ErrorAction SilentlyContinue
    if ($paCmd) {
        Info "✓ prompt-automation command is available"
        try { $version = & prompt-automation --version 2>&1; Debug "  Version: $version" } catch { }
    } else {
        Error "✗ prompt-automation command not found"
        Info "  Install with: pipx install prompt-automation"
        Info "  Or from local source: pipx install --force ."
    }

    Info ""
    Info "=== Checking for potential conflicts ==="
    $espansoCmd = Get-Command espanso -ErrorAction SilentlyContinue
    if ($espansoCmd) {
        try { $espansoStatus = & espanso status 2>&1; if ($espansoStatus -match 'espanso is running') { Warn "⚠ espanso is running - this may conflict with AutoHotkey" } else { Info "✓ espanso is installed but not running" } } catch { }
    }
    $startupDir = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
    $ahkFiles = Get-ChildItem -Path $startupDir -Filter '*.ahk' -ErrorAction SilentlyContinue
    if ($ahkFiles.Count -gt 1) { Warn "⚠ Multiple AutoHotkey scripts found in startup" }

    Info ""
    if ($Status) {
        Info "Status check complete."
    } elseif ($Fix) {
        Info "Fix attempt complete. Try the hotkey now: Ctrl+Shift+J"
    } elseif ($Restart) {
        Info "Restart attempt complete. Try the hotkey now: Ctrl+Shift+J"
    } else {
        Info "Diagnosis complete. Use the following flags for actions:"
        Info "  --Fix     : Attempt to fix common issues"
        Info "  --Restart : Restart the AutoHotkey script"
        Info "  --Status  : Just show status information"
    }

    Info ""
    Info "Manual troubleshooting steps:"
    Info "1. Log out and log back in to ensure startup scripts run"
    Info "2. Manually run the AutoHotkey script: AutoHotkey `"$startupScript`""
    Info "3. Check if other applications are using Ctrl+Shift+J"
    Info "4. Try running 'prompt-automation' directly from command prompt"
}

Invoke-TroubleshootHotkeys -Fix:$Fix -Status:$Status -Restart:$Restart

Stop-Transcript | Out-Null
Info "Troubleshooting log saved to $LogFile"
