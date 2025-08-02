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

    # Use smart AutoHotkey detection
    $ahkAvailable = Test-ComponentAvailability -ComponentName 'AutoHotkey'
    if ($ahkAvailable) {
        # Try to find the actual path for version info
        $ahkCmd = Get-Command AutoHotkey -ErrorAction SilentlyContinue
        if ($ahkCmd) {
            Info "[OK] AutoHotkey is installed at: $($ahkCmd.Source)"
            try { 
                $ahkVersion = (Get-ItemProperty -Path $ahkCmd.Source).VersionInfo.FileVersion
                if ($ahkVersion) { Debug "  Version: $ahkVersion" }
            } catch { }
        } else {
            # Check standard paths for version info
            $standardPaths = @(
                "${env:ProgramFiles}\AutoHotkey\AutoHotkey.exe",
                "${env:ProgramFiles(x86)}\AutoHotkey\AutoHotkey.exe",
                "${env:LOCALAPPDATA}\Programs\AutoHotkey\AutoHotkey.exe"
            )
            foreach ($path in $standardPaths) {
                if (Test-Path $path) {
                    Info "[OK] AutoHotkey is installed at: $path"
                    try { 
                        $ahkVersion = (Get-ItemProperty -Path $path).VersionInfo.FileVersion
                        if ($ahkVersion) { Debug "  Version: $ahkVersion" }
                    } catch { }
                    break
                }
            }
        }
        
        # If Fix mode is enabled, try to add AutoHotkey to PATH
        if ($Fix -and -not $ahkAvailable) {
            Info "Attempting to add AutoHotkey to PATH..."
            if (Add-AutoHotkeyToPath) {
                Info "[OK] AutoHotkey added to PATH successfully"
                $ahkAvailable = Test-ComponentAvailability -ComponentName 'AutoHotkey'
            }
        }
    } else {
        Error "[FAIL] AutoHotkey is not installed or not in PATH"
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
                    Info "[OK] AutoHotkey installation attempted successfully"
                } else {
                    Error "[FAIL] AutoHotkey installation failed with exit code: $LASTEXITCODE"
                    Warn "This often indicates UAC dialogs were cancelled or permission issues"
                }
            } catch { 
                Error "AutoHotkey installation failed with exception: $($_.Exception.Message)" 
            }
        }
        return
    }

    $startupScript = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup\prompt-automation.ahk'
    if (Test-Path $startupScript) {
        Info "[OK] AutoHotkey script found in startup folder"
        Debug "  Location: $startupScript"
    } else {
        Error "[FAIL] AutoHotkey script not found in startup folder"
        Debug "  Expected location: $startupScript"
        if ($Fix) {
            Info "Attempting to fix by copying the script..."
            if (Setup-AutoHotkeyStartup -Force) {
                Info "[OK] AutoHotkey startup configuration fixed"
            } else {
                Error "[FAIL] Could not fix AutoHotkey startup configuration"
            }
        }
    }

    $ahkProcess = Get-Process -Name "AutoHotkey*" -ErrorAction SilentlyContinue
    if ($ahkProcess) {
        Info "[OK] AutoHotkey process is running:"
        foreach ($proc in $ahkProcess) { Debug "  PID: $($proc.Id), Name: $($proc.ProcessName)" }
    } else {
        Warn "[WARN] No AutoHotkey processes found running"
        if ($Fix -or $Restart) {
            Info "Starting AutoHotkey script manually..."
            if (Test-Path $startupScript) {
                try {
                    # Find AutoHotkey executable
                    $ahkExe = $null
                    $ahkCmd = Get-Command AutoHotkey -ErrorAction SilentlyContinue
                    if ($ahkCmd) {
                        $ahkExe = $ahkCmd.Source
                    } else {
                        # Check standard paths
                        $standardPaths = @(
                            "${env:ProgramFiles}\AutoHotkey\AutoHotkey.exe",
                            "${env:ProgramFiles(x86)}\AutoHotkey\AutoHotkey.exe",
                            "${env:LOCALAPPDATA}\Programs\AutoHotkey\AutoHotkey.exe"
                        )
                        foreach ($path in $standardPaths) {
                            if (Test-Path $path) {
                                $ahkExe = $path
                                break
                            }
                        }
                    }
                    
                    if ($ahkExe) {
                        Start-Process -FilePath $ahkExe -ArgumentList "`"$startupScript`"" -NoNewWindow
                        Start-Sleep -Seconds 2
                        $ahkProcess = Get-Process -Name "AutoHotkey*" -ErrorAction SilentlyContinue
                        if ($ahkProcess) { 
                            Info "[OK] AutoHotkey script started successfully" 
                        } else { 
                            Error "[FAIL] Failed to start AutoHotkey script" 
                        }
                    } else {
                        Error "[FAIL] AutoHotkey executable not found"
                    }
                } catch { 
                    Error "Error starting AutoHotkey: $($_.Exception.Message)" 
                }
            }
        }
    }

    $paCmd = Get-Command prompt-automation -ErrorAction SilentlyContinue
    if ($paCmd) {
        Info "prompt-automation command is available"
        try { 
            # Try to get help instead of version since --version isn't supported
            $help = & prompt-automation --help 2>&1 | Select-Object -First 5
            Debug "  Help output available: $($help -ne $null)" 
        } catch { 
            Debug "Could not get help: $($_.Exception.Message)"
        }
    } else {
        Error "[FAIL] prompt-automation command not found"
        Info "  Install with: pipx install prompt-automation"
        Info "  Or from local source: pipx install --force ."
    }

    Info ""
    Info "=== Checking espanso Configuration ==="
    $espansoCmd = Get-Command espanso -ErrorAction SilentlyContinue
    if ($espansoCmd) {
        try { 
            $espansoStatus = & espanso status 2>&1
            Debug "espanso status output: $espansoStatus"
            
            if ($espansoStatus -match 'espanso is running') { 
                Info "[OK] espanso is running and active"
                
                # Check if service is registered for startup
                $serviceStatus = & espanso service status 2>&1
                Debug "espanso service status: '$serviceStatus'"
                
                if ($serviceStatus -match 'registered') {
                    Info "[OK] espanso service is configured for automatic startup"
                } elseif ([string]::IsNullOrWhiteSpace($serviceStatus)) {
                    Info "[INFO] espanso is running manually (not as a service)"
                    Info "This is fine - espanso will work, but won't auto-start after reboot"
                    if ($Fix) {
                        Info "Configuring espanso for automatic startup..."
                        if (Setup-EspansoStartup -Force) {
                            Info "[OK] espanso startup configuration added"
                        } else {
                            Warn "Could not configure espanso for automatic startup"
                        }
                    }
                } else {
                    Warn "espanso is running but service status unclear: $serviceStatus"
                    if ($Fix) {
                        Info "Attempting to configure espanso for automatic startup..."
                        if (Setup-EspansoStartup -Force) {
                            Info "[OK] espanso startup configuration fixed"
                        } else {
                            Warn "Could not configure espanso for automatic startup"
                        }
                    }
                }
            } else { 
                Warn "espanso is installed but not running"
                Debug "espanso status was: $espansoStatus"
                if ($Fix) {
                    Info "Starting espanso and configuring for startup..."
                    if (Setup-EspansoStartup -Force) {
                        Info "[OK] espanso configured and started"
                    } else {
                        Warn "Could not start and configure espanso"
                    }
                }
            } 
        } catch { 
            Debug "Could not check espanso status: $($_.Exception.Message)"
        }
    } else {
        Debug "espanso not installed"
    }
    $startupDir = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
    $ahkFiles = Get-ChildItem -Path $startupDir -Filter '*.ahk' -ErrorAction SilentlyContinue
    if ($ahkFiles.Count -gt 1) { Warn "[WARN] Multiple AutoHotkey scripts found in startup" }

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
