#NoEnv
#SingleInstance Force
#InstallKeybdHook
#InstallMouseHook
#MaxHotkeysPerInterval 99000000
#HotkeyInterval 99000000
#KeyHistory 0

; Ctrl+Shift+J to launch prompt-automation
^+j::
{
    ; Check if prompt-automation is already running to prevent multiple instances
    Process, Exist, prompt-automation.exe
    if (ErrorLevel > 0) {
        ; If running, just return without launching another instance
        return
    }
    
    ; Launch prompt-automation with error handling
    try {
        Run, prompt-automation,, UseErrorLevel
        if (ErrorLevel) {
            ; If launch failed, show a brief message
            ToolTip, Failed to launch prompt-automation
            SetTimer, RemoveToolTip, 2000
        }
    } catch e {
        ; Catch any errors and show tooltip
        ToolTip, Error launching prompt-automation: %e.message%
        SetTimer, RemoveToolTip, 3000
    }
    return
}

RemoveToolTip:
    ToolTip
    SetTimer, RemoveToolTip, Off
return
