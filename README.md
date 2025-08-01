# prompt-automation

**prompt-automation** is a keyboard driven prompt launcher designed for absolute beginners. With a single hotkey you can choose a template, fill in any placeholders and instantly paste the result into the active application.

---

## Getting Started

1. **Clone the repository**
   ```bash
   git clone https://github.com/<user>/prompt-automation.git
   cd prompt-automation
   ```
2. **Run the installer** for your platform. The script installs all dependencies (Python, pipx, fzf and espanso) and registers the global hotkey.
   - **Windows**
     ```powershell
     scripts\install.ps1
     ```
   - **macOS / Linux / WSL2**
     ```bash
     bash scripts/install.sh
     ```

After installation restart your terminal so `pipx` is on your `PATH`.

## Usage

Press **Ctrl+Shift+J** to open the style picker. Select a style, choose a template and fill in any required values. The rendered text is copied to your clipboard and pasted automatically.

```
[Hotkey] -> [Style] -> [Template] -> [Fill] -> [Paste]
```

Templates live under `prompts/styles/`. Choosing option `99` in the style picker lets you create a new template interactively.

## Managing Templates

Template files are plain JSON documents in `prompts/styles/<Style>/`.
A minimal example:

```json
{
  "id": 1,
  "title": "My Template",
  "style": "Utility",
  "role": "assistant",
  "template": ["Hello {{name}}"],
  "placeholders": [{"name": "name", "label": "Name"}]
}
```

## Troubleshooting

- Run `prompt-automation --troubleshoot` to print log and database locations.
- Use `prompt-automation --list` to list available templates.
- If the hotkey does not work see [docs/HOTKEYS.md](docs/HOTKEYS.md) for manual setup instructions.

## FAQ

**Where is usage stored?** In `$HOME/.prompt-automation/usage.db`. Clear it with `--reset-log`.

**How do I use my own templates?** Set the `PROMPT_AUTOMATION_PROMPTS` environment variable or pass `--prompt-dir` when launching.

## Troubleshooting

**Windows Error `0x80070002` when launching:** This error typically occurs due to Windows keyboard library permissions. The application will automatically fallback to PowerShell-based key sending. To resolve:
- Run PowerShell as Administrator when first installing
- Or install with `pipx install prompt-automation[windows]` for optional keyboard support
- The application works fine without the keyboard library using PowerShell fallback

**WSL/Windows Path Issues:** If running from WSL but accessing Windows, ensure:
- Use the provided PowerShell installation scripts from Windows
- Prompts directory is accessible from both environments
- Use `--troubleshoot` flag to see path resolution details

## WSL (Windows Subsystem for Linux) Troubleshooting

If you're running into issues with prompt-automation in WSL, it's likely
because the tool is trying to run from the WSL environment instead of native
Windows.

**Solution**: Install prompt-automation in your native Windows environment:

1. **Open PowerShell as Administrator in Windows** (not in WSL)
2. **Navigate to a temporary directory**:
   ```powershell
   cd C:\temp
   mkdir prompt-automation
   cd prompt-automation
   Copy-Item -Path "\\wsl.localhost\Ubuntu\home\$env:USERNAME\path\to\prompt-automation\*" -Destination . -Recurse -Force
   .\scripts\install.ps1
   ```

**Alternative**: Run the installation directly from your WSL environment but
ensure Windows integration:

```bash
# In WSL, but installs to Windows
powershell.exe -Command "cd 'C:\\temp\\prompt-automation'; Copy-Item -Path '\\wsl.localhost\\Ubuntu\\home\\$(whoami)\\path\\to\\prompt-automation\\*' -Destination . -Recurse -Force; .\\scripts\\install.ps1"
```

**Missing Prompts Directory:** If you see "prompts directory not found":
- Reinstall with `pipx install --force dist/prompt_automation-0.2.1-py3-none-any.whl`
- Or set `PROMPT_AUTOMATION_PROMPTS` environment variable to your prompts location
- Use `--troubleshoot` to see all attempted locations

## Directory Overview

```
project/
├── docs/               # Additional documentation
├── prompts/
│   └── styles/         # Prompt JSON files
├── scripts/            # Install helpers
├── src/
│   └── prompt_automation/
│       ├── hotkey/     # Platform hotkey scripts
│       └── ...         # Application modules
└── tests/              # Test suite
```

Enjoy!
