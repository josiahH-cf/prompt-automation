# PromptPilot

Keyboard-only launcher for your favorite LLM prompts. Invoke with **Ctrl+Shift+J** and paste the rendered text anywhere.

## Quick start

```bash
# Linux/macOS
curl -sSL https://example.com/install.sh | bash
# Windows (PowerShell)
iwr -useb https://example.com/install.ps1 | iex
```

## Prerequisites

Python 3.11, pipx, fzf and espanso are installed by the one-liner above. See `scripts/install.*` if you prefer manual steps.

## Usage

Run `promptpilot` once to configure the hotkey. Use **Ctrl+Shift+J** in any application to open the style picker. Fill in placeholder values and the text will be pasted automatically.

## Creating a new prompt

Choose option 99 from the style picker. Supply a style name, two digit ID, title, role and body. The new template is saved under `prompts/styles/<Style>` and immediately available.

## Logging

Usage is recorded to `~/.promptpilot/usage.db`. When the file grows beyond 5MB it is archived and vacuumed.

## Firewall / offline install

If the one-liners fail, download release assets from this repository and run `install.sh` or `install.ps1` locally.

## Uninstall

Remove the `promptpilot` package with `pipx uninstall promptpilot` and delete the `~/.promptpilot` directory.

## Contributing

Pull requests are welcome. See the MIT License for terms.
