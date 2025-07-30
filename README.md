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

**Where is usage stored?** In `~/.prompt-automation/usage.db`. Clear it with `--reset-log`.

**How do I use my own templates?** Set the `PROMPT_AUTOMATION_PROMPTS` environment variable or pass `--prompt-dir` when launching.

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
