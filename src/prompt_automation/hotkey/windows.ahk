#NoEnv
#SingleInstance Force
#InstallKeybdHook
#InstallMouseHook
#MaxHotkeysPerInterval 99000000
#HotkeyInterval 99000000
#KeyHistory 0

; Ctrl+Shift+J to launch prompt-automation natively on Windows
^+j::
{
    ; Show a tooltip to confirm hotkey is working
    ToolTip, Launching prompt-automation...
    SetTimer, RemoveToolTip, 1000
    
    ; Check if prompt-automation is already running to prevent multiple instances
    Process, Exist, prompt-automation.exe
    if (ErrorLevel > 0) {
        ToolTip, prompt-automation is already running
        SetTimer, RemoveToolTip, 2000
        return
    }
    
    ; Try Windows Terminal with PowerShell first (most reliable)
    try {
        Run, wt.exe powershell -NoExit -Command "if (Get-Command prompt-automation -ErrorAction SilentlyContinue) { prompt-automation } else { Write-Host 'ERROR: prompt-automation not found. Run scripts\install-prompt-automation.ps1 first.' -ForegroundColor Red; pause }", , UseErrorLevel
        if (ErrorLevel = 0) {
            return
        }
    }
    
    ; Fallback: Try Windows Terminal with Command Prompt
    try {
        Run, wt.exe cmd /k "prompt-automation || (echo ERROR: prompt-automation not found. Run scripts\install-prompt-automation.ps1 first. && pause)", , UseErrorLevel
        if (ErrorLevel = 0) {
            return
        }
    }
    
    ; Final fallback: Direct command prompt
    try {
        Run, cmd /k "prompt-automation || (echo ERROR: prompt-automation not found. Run scripts\install-prompt-automation.ps1 first. && pause)", , UseErrorLevel
    } catch {
        ToolTip, Failed to launch prompt-automation. Make sure it's installed with pipx.
        SetTimer, RemoveToolTip, 5000
    }
    return
}

RemoveToolTip:
    ToolTip
    SetTimer, RemoveToolTip, Off
return
