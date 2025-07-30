# PromptPilot

PromptPilot is a keyboard-only smart prompt launcher for Windows, macOS, and Linux. It lets you pick prompt templates via a quick menu and automatically pastes the rendered prompt at your cursor location.

## Quick start

```powershell
# Windows
iwr https://example.com/install.ps1 | iex
```

```bash
# macOS/Linux
bash <(curl -fsSL https://example.com/install.sh)
```

## Prerequisites
- Python 3.11+
- pipx
- fzf
- espanso

## Usage
The installer registers an Espanso snippet `;pp` which launches the menu. Choose a style, then a prompt, fill in any variables, and the text is pasted for you.

### Adding a new prompt (Option 99)
Selecting option 99 lets you create a new template interactively. The JSON file is saved under `prompts/styles/<Style>/` and becomes available immediately.

### Logging
Every run stores a timestamp, prompt ID, and estimated token count in `~/.promptpilot/usage.db`.

## Uninstall
Remove the espanso snippet and delete the pipx package `promptpilot`.

