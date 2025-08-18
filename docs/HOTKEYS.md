# Global Hotkey Setup

This project provides platform-specific scripts for launching `prompt-automation` with a keyboard shortcut.
The default key combination is **Ctrl+Shift+J**. Run `prompt-automation --assign-hotkey` to change it at any time.

## Windows
1. Run `install/install.ps1` from PowerShell. The script installs dependencies, checks for AutoHotkey v2, and copies `windows.ahk` to your Startup folder.
2. Verify registration with:
   ```powershell
   Get-ChildItem "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup" | Where-Object Name -eq 'prompt-automation.ahk'
   ```
3. To change the hotkey run `prompt-automation --assign-hotkey` or edit `prompt-automation.ahk` in that folder and log out.

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
2. Copy `src/prompt_automation/hotkey/linux.yaml` to `$HOME/.config/espanso/match/prompt-automation.yml` and run `espanso restart` (or use `prompt-automation --assign-hotkey`).
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
application, install from Windows using `install\install.ps1` and copy the
repository with `\wsl.localhost` paths as described in the README.

After installation, press **Ctrl+Shift+J** to activate the launcher. If the hotkey fails, rerun the installer or consult your platform's hotkey settings.

## GUI Selector Keyboard Cheat Sheet (Hotkey Flow)

When launched via the global hotkey the GUI opens focused on the search box:

| Key / Action | Result |
|--------------|--------|
| `s` | Focus search box & select text |
| Type text | Live recursive search (path/title/placeholders/body) |
| Toggle Non-recursive | Restrict search/filter to current folder |
| Up / Down | Move selection |
| Enter / Double-click | Open folder or select template |
| Backspace | Go up one level |
| Ctrl+P | Toggle preview window for highlighted template |
| Ctrl+L | Toggle recursive search on/off (focus preserved) |
| Multi-select checkbox | Enable marking multiple templates |
| Enter (in multi mode) | Toggle mark (adds/removes `*` prefix) |
| Finish Multi | Build synthetic combined template (id -1) |
| (After Finish Multi) | Combined preview stage appears before variable prompts |
| Esc | Cancel/close selector |

After template selection the single-window workflow swaps to variable collection (auto-focused inputs, inline reference file viewer) and then to an embedded review (Ctrl+Enter confirm, Ctrl+Shift+C copy without close). Legacy modal windows still appear for non-inline file placeholders.

### Variable Collection (Single Window) Keys

| Placeholder Type | Keys |
|------------------|------|
| Single-line text | Enter = Next, Ctrl+S = Skip, Esc = Cancel |
| Multiline / list | Ctrl+Enter = Next, Enter = newline, Ctrl+S = Skip, Esc = Cancel |
| Dropdown/options | Enter = Next, Up/Down navigate, Ctrl+S = Skip |
| reference_file (inline) | Ctrl+Enter = Next, Ctrl+R = Reset, Ctrl+U = Refresh, Ctrl+S = Skip, Esc = Cancel |
| Other file (modal) | Ctrl+Enter accept (viewer), Ctrl+R reset, Esc cancel |
| Context | Ctrl+Enter save & next | Remembers last context |
| Review stage | Ctrl+Enter confirm, Ctrl+Shift+C copy only, Esc cancel |
| Review toolbar buttons | Copy Paths (shown only if any *_path tokens referenced), Preview Append Targets (lists each pending append file + current contents) |
