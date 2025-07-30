# prompt-automation

**prompt-automation** is a keyboard driven launcher for your favorite AI prompts. Press a hotkey, pick a template and the text is pasted wherever your cursor lives.

---

## Getting the Code

Clone the repository and change into the project directory:

```bash
git clone https://github.com/<user>/prompt-automation.git
cd prompt-automation
```

## OS Specific Installation

### Windows 11
Run the PowerShell installer:
```powershell
scripts\install.ps1
```
The script installs Python, pipx, fzf, espanso and registers the **Ctrl+Shift+J** hotkey using AutoHotkey.

### macOS 14
Run the shell installer:
```bash
bash scripts/install.sh
```
Homebrew is used to fetch dependencies. A small AppleScript registers the hotkey on login.

### Linux
Run the shell installer as above. It expects `apt` or `brew` and uses Espanso for the hotkey.

### WSL2
Run the Linux installer inside your distribution. Clipboard integration requires `clip.exe` in your Windows path.

After installation restart your terminal session so `pipx` is on your `PATH`.

## Launching and Hotkeys

Press **Ctrl+Shift+J** to open the style picker. Hotkey troubleshooting and manual setup steps for each platform are documented in [docs/HOTKEYS.md](docs/HOTKEYS.md).

## Using prompt-automation

1. **Pick Style** – Choose a style category.
2. **Pick Template** – Select the prompt template.
3. **Fill Placeholders** – Enter any required values.
4. **Paste** – The rendered text is copied to the clipboard and pasted for you.

```
[Hotkey] -> [Style] -> [Template] -> [Fill] -> [Paste]
```

Templates live under `prompts/styles/`. Selecting option `99` inside the style picker lets you create a new template interactively.

## Managing Prompt Templates

Template files are JSON documents stored in subfolders of `prompts/styles/`.
Each file must contain:

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

The filename should start with a two digit ID: `01_my_template.json`.
To edit an existing template simply modify the JSON file and rerun the launcher.

## Usage Log

Every time text is pasted an entry is recorded in `~/.prompt-automation/usage.db`.
Delete this file to reset statistics.

## Advanced Configuration

Several environment variables allow custom paths:

- `PROMPT_AUTOMATION_PROMPTS` – directory containing the `styles/` folders.
- `PROMPT_AUTOMATION_DB` – path to the usage database.

You can also modify the installed hotkey by editing the platform specific file in `src/prompt_automation/hotkey/` and rerunning the installer.

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
