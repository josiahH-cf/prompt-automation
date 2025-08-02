#NoEnv
#SingleInstance Force
#InstallKeybdHook
#InstallMouseHook
#MaxHotkeysPerInterval 99000000
#HotkeyInterval 99000000
#KeyHistory 0

; Ctrl+Shift+J launches the prompt-automation GUI without opening a console
^+j::
{
    Run, prompt-automation.exe --gui,, Hide
    return
}
