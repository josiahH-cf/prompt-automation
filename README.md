# prompt-automation

**prompt-automation** is a keyboard-driven launcher for your favorite AI prompt templates.

## 1. Install prerequisites

### Windows 11
1. Install [Git](https://git-scm.com/download/win).
2. Open PowerShell as Administrator and run:
   ```powershell
   winget install -e --id Python.Python.3.11
   winget install -e --id Microsoft.VisualStudioCode
   winget install -e --id Git.Git
   ```

### macOS 14
1. Install [Homebrew](https://brew.sh) if missing.
2. Run:
   ```bash
   brew install git python@3.11 --cask visual-studio-code
   ```

## 2. Clone this repository

```bash
git clone https://github.com/<user>/prompt-automation.git
cd prompt-automation
```

## 3. Run the installer

### macOS/Linux
```bash
curl -sSL https://example.com/install.sh | bash
```

### Windows PowerShell
```powershell
iwr -useb https://example.com/install.ps1 | iex
```

After installation, restart your terminal or log out/in if prompted.
Detailed hotkey setup instructions for each platform are available in
[docs/HOTKEYS.md](docs/HOTKEYS.md).

## 4. Try the hotkey

Press **Ctrl+Shift+J** and a style picker will appear. Choose a template and the text is pasted automatically.

```
[Ctrl+Shift+J] -> [Style Picker] -> [Fill Placeholders] -> [Pasted Output]
```

## 5. Add a new prompt

Run the launcher and select **Option 99**. Provide style, ID, title, role, template lines and placeholders when prompted. The new JSON template is saved under `prompts/styles/<Style>/` and is available immediately.

## Troubleshooting

- **Behind a firewall?** Download the repo and run the installer scripts locally.
- **Hotkey not working?** Re-run `prompt-automation` from the terminal to reset the hotkey integration.
- **Need more help?** Run `prompt-automation --troubleshoot` and check `~/.prompt-automation/logs` for details.

## Uninstall

```bash
pipx uninstall prompt-automation
rm -rf ~/.prompt-automation
```

Enjoy!
