#NoEnv
#SingleInstance Force
#InstallKeybdHook
#InstallMouseHook
#MaxHotkeysPerInterval 99000000
#HotkeyInterval 99000000
#KeyHistory 0

; Ctrl+Shift+J launches the prompt-automation with GUI fallback to CLI
^+j::
{
    ; Try GUI mode first
    Run, prompt-automation --gui,, Hide
    if ErrorLevel
    {
        Run, prompt-automation.exe --gui,, Hide
        if ErrorLevel
        {
            Run, python -m prompt_automation --gui,, Hide
            if ErrorLevel
            {
                ; If GUI fails, fall back to terminal mode
                Run, prompt-automation --terminal
                if ErrorLevel
                {
                    Run, prompt-automation.exe --terminal
                    if ErrorLevel
                    {
                        Run, python -m prompt_automation --terminal
                        if ErrorLevel
                        {
                            ; Final fallback - show error
                            MsgBox, 16, Error, prompt-automation failed to start. Please check installation.
                        }
                    }
                }
            }
        }
    }
    return
}
