# Codebase Reference Guide

This document provides a machine-readable and human-readable overview of the `prompt-automation` project. AI coding partners (e.g. GitHub Copilot, Cursor, Codex) and human contributors should consult this file before editing the codebase. Keep it up-to-date whenever new modules or directories are added.

## Project Summary

`prompt-automation` is a cross-platform prompt launcher. A global hotkey triggers a template picker, renders the selection with user-provided values, copies the result to the clipboard and optionally pastes it into the active application.

## Directory Structure

```
.
├── docs/                     # Additional documentation such as hotkey setup
├── scripts/                  # Installation and troubleshooting scripts (PowerShell/bash)
├── src/
│   └── prompt_automation/
│       ├── cli.py            # Command-line entry point and dependency checks
│       ├── errorlog.py       # Shared logger that writes to ~/.prompt-automation/logs/error.log
│       ├── gui/             # Optional Tkinter interface for choosing templates
│       │   ├── controller.py       # Orchestrates workflow via PromptGUI
│       │   ├── template_selector.py
│       │   ├── variable_collector.py
│       │   ├── review_window.py
│       │   ├── file_append.py      # Shared append-to-file logic
│       │   └── gui.py              # Entry point launching PromptGUI
│       ├── hotkey/           # Platform-specific hotkey definitions
│       ├── hotkeys/         # Interactive hotkey assignment, dependency checking, and system integration
│       ├── logger.py         # Usage logging with SQLite rotation
│       ├── menus.py          # Fzf-based style/template picker and template creation
│       ├── updater.py        # Lightweight PyPI version check + pipx upgrade (rate-limited, silent)
│       ├── paste.py          # Clipboard interaction and keystroke simulation
│       ├── prompts/          # Packaged prompt templates (styles/basic/01_basic.json)
│       │   └── Settings/     # settings.json (mirrors per-template file overrides; editable)
│       ├── renderer.py       # Template loading, validation, and placeholder substitution
│       ├── resources/        # Static assets like banner.txt
│       ├── utils.py          # Safe subprocess execution helpers
│       └── variables.py      # Collect values for placeholders via GUI/editor/CLI; manages per-template file path/skip overrides
├── tasks.py                  # Invoke tasks for building distributions
└── ...                       # Root configuration files (pyproject.toml, README.md, etc.)
```

## Component Interaction

1. **Entry Points**
   - `cli.main()` runs when the command-line tool is invoked. It performs dependency checks and launches either the terminal picker or the GUI.
   - `gui.gui.run()` provides a graphical front-end when `--gui` is supplied.
2. **Hotkey System**
   - `hotkeys.assign_hotkey()` captures user input and configures platform-specific global hotkeys
   - `hotkeys.update_hotkeys()` refreshes existing hotkey configuration and verifies dependencies
   - `hotkeys.ensure_hotkey_dependencies()` checks for required platform dependencies (AutoHotkey, espanso)
   - Platform-specific functions generate scripts with GUI-first, terminal fallback execution chains
3. **Template Selection**
   - `menus.list_styles()` and `menus.list_prompts()` locate available JSON templates under `prompts/styles/` (now recursive – nested subfolders inside each style are supported and discovered automatically).
   - `menus.pick_style()` and `menus.pick_prompt()` present fzf or text-based menus.
4. **Rendering**
   - Selected templates are loaded with `renderer.load_template()` and placeholders are filled via `variables.get_variables()`.
   - The final text is produced by `renderer.fill_placeholders()`.
5. **Output**
   - `paste.paste_text()` copies the rendered text to the clipboard and attempts to send the paste keystroke.
   - `logger.log_usage()` records prompt usage to `~/.prompt-automation/usage.db` and rotates the database when it grows too large.
6. **Error Handling**
   - All modules use `errorlog.get_logger()` to write diagnostic information to a shared log file.

## Scripts and Utilities

 - `install/install.sh`, `install/install.ps1`, and related scripts automate installation on Linux/macOS/Windows.
 - `tasks.py` defines an Invoke task for building distributable packages (`invoke build`).

## Prompt Templates

Prompt JSON files live under `prompts/styles/<Style>/`. The repository bundles only `basic/01_basic.json` as a minimal example. Each template includes an integer `id`, a `title`, a `style`, a list of `template` lines, and optional `placeholders`. The application enforces unique IDs via `menus.ensure_unique_ids()`.

### File / Reference Placeholder Pattern
To attach (and optionally inject) an external file:
1. Add `{ "name": "reference_file", "type": "file" }` (collects path; persisted per template)
2. Add `{ "name": "reference_file_content" }` (triggers popup; auto-filled with contents)
3. Include `{{reference_file_content}}` in `template` lines to inline the file contents, or omit to just view it.

Skipping the file via the GUI "Skip" button persists a `skip` flag; future runs won't prompt unless you reset it. Management:
* GUI: Options → Manage overrides (remove an entry to re-enable prompting)
* CLI: `--list-overrides`, `--reset-one-override <TID> <NAME>`, `--reset-file-overrides`

Overrides are stored locally in `~/.prompt-automation/placeholder-overrides.json` and synced to `prompts/styles/Settings/settings.json` so a curated default set can be versioned. No global skip flag remains—behavior is explicit and per-template.

## Hotkey System Architecture

The hotkey system provides cross-platform global hotkey support with robust fallback mechanisms:

### Platform-Specific Implementation

- **Windows**: Uses AutoHotkey scripts placed in Startup folder
  - Script tries multiple execution paths: `prompt-automation`, `prompt-automation.exe`, `python -m prompt_automation`
  - Each path attempts GUI first (`--gui`), then terminal (`--terminal`) on failure
  - Final fallback shows error message box

- **Linux**: Uses espanso text expansion with shell commands
  - Configuration in `~/.config/espanso/match/prompt-automation.yml`
  - Uses shell OR operator (`||`) for GUI-to-terminal fallback
  - Automatically restarts espanso service after configuration

- **macOS**: Uses AppleScript for background execution
  - Script stored in `~/Library/Application Scripts/prompt-automation/`
  - Requires manual assignment in System Preferences > Keyboard > Shortcuts
  - Background execution with error dialogs for failures

### Configuration Management

- User hotkey preferences stored in `~/.prompt-automation/hotkey.json`
- Environment configuration in `~/.prompt-automation/environment`
- GUI mode enabled by default for hotkey usage
- Dependency checking with installation guidance

## Working With This File

- When adding or modifying modules, scripts, or directories, update the relevant section here.
- Refer AI coding partners to this guide in initial instructions so they can quickly locate the appropriate components.


