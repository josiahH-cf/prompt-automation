# Global Hotkey Setup

This project provides platform-specific scripts for launching `prompt-automation` with a keyboard shortcut.
The default key combination is **Ctrl+Shift+J**.

## Windows
1. Run `scripts/install.ps1` from PowerShell. The script installs dependencies, checks for AutoHotkey v2, and copies `windows.ahk` to your Startup folder.
2. Verify registration with:
   ```powershell
   Get-ChildItem "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup" | Where-Object Name -eq 'prompt-automation.ahk'
   ```
3. To unregister or change the hotkey, remove or edit `prompt-automation.ahk` from that folder and log out.

## macOS
1. Open `src/prompt_automation/hotkey/macos.applescript` with Automator and save it as an **Application**.
2. Assign a keyboard shortcut under **System Preferences › Keyboard › Shortcuts › App Shortcuts**.
3. Add the generated `.app` bundle to login items:
   ```bash
   osascript -e 'tell application "System Events" to make login item at end with properties {path:"/path/to/prompt-automation.app", hidden:false}'
   ```
4. Remove the login item with:
   ```bash
   osascript -e 'tell application "System Events" to delete login item "prompt-automation"'
   ```

## Linux / WSL2
1. Ensure [Espanso](https://espanso.org) is installed.
2. Copy `src/prompt_automation/hotkey/linux.yaml` to `$HOME/.config/espanso/match/prompt-automation.yml` and run `espanso restart`.
3. If Espanso is unavailable, create `$HOME/.config/autostart/prompt-automation.desktop`:
   ```ini
   [Desktop Entry]
   Type=Application
   Exec=prompt-automation
   Hidden=false
   NoDisplay=false
   X-GNOME-Autostart-enabled=true
   Name=prompt-automation
   ```
4. Remove or edit that file to unregister or change the hotkey.

### WSL Notes

When using WSL, the hotkey runs inside Linux only. To trigger the Windows
application, install from Windows using `scripts\install.ps1` and copy the
repository with `\wsl.localhost` paths as described in the README.

After installation, press **Ctrl+Shift+J** to activate the launcher. If the hotkey fails, rerun the installer or consult your platform's hotkey settings.
