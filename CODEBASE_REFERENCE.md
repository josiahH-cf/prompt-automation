# Codebase Reference Guide

This document provides a machine-readable and human-readable overview of the `prompt-automation` project. AI coding partners (e.g. GitHub Copilot, Cursor, Codex) and human contributors should consult this file before editing the codebase. Keep it up-to-date whenever new modules or directories are added.

## Project Summary

`prompt-automation` is a cross-platform prompt launcher. A global hotkey triggers a style picker, renders a chosen template with user-provided values, copies the result to the clipboard and optionally pastes it into the active application.

## Directory Structure

```
.
├── docs/                     # Additional documentation such as hotkey setup
├── prompts/                  # Prompt template JSON files grouped by style
├── scripts/                  # Installation and troubleshooting scripts (PowerShell/bash)
├── src/
│   └── prompt_automation/
│       ├── cli.py            # Command-line entry point and dependency checks
│       ├── errorlog.py       # Shared logger that writes to ~/.prompt-automation/logs/error.log
│       ├── gui.py            # Optional PySimpleGUI interface for choosing templates
│       ├── hotkey/           # Platform-specific hotkey definitions
│       ├── hotkeys.py        # Interactive hotkey assignment and system integration
│       ├── logger.py         # Usage logging with SQLite rotation
│       ├── menus.py          # Fzf-based style/template picker and template creation
│       ├── paste.py          # Clipboard interaction and keystroke simulation
│       ├── prompts/          # Packaged prompt templates
│       ├── renderer.py       # Template loading, validation, and placeholder substitution
│       ├── resources/        # Static assets like banner.txt
│       ├── utils.py          # Safe subprocess execution helpers
│       └── variables.py      # Collect values for placeholders via GUI/editor/CLI
├── tests/                    # Pytest suite
├── tasks.py                  # Invoke tasks: lint, test, build
└── ...                       # Root configuration files (pyproject.toml, README.md, etc.)
```

## Component Interaction

1. **Entry Points**
   - `cli.main()` runs when the command-line tool is invoked. It performs dependency checks and launches either the terminal picker or the GUI.
   - `gui.run()` provides a graphical front-end when `--gui` is supplied.
2. **Template Selection**
   - `menus.list_styles()` and `menus.list_prompts()` locate available JSON templates under `prompts/styles/`.
   - `menus.pick_style()` and `menus.pick_prompt()` present fzf or text-based menus.
3. **Rendering**
   - Selected templates are loaded with `renderer.load_template()` and placeholders are filled via `variables.get_variables()`.
   - The final text is produced by `renderer.fill_placeholders()`.
4. **Output**
   - `paste.paste_text()` copies the rendered text to the clipboard and attempts to send the paste keystroke.
   - `logger.log_usage()` records prompt usage to `~/.prompt-automation/usage.db` and rotates the database when it grows too large.
5. **Error Handling**
   - All modules use `errorlog.get_logger()` to write diagnostic information to a shared log file.

## Scripts and Utilities

- `scripts/install.sh`, `scripts/install.ps1`, and related scripts automate installation on Linux/macOS/Windows.
- `tasks.py` defines Invoke tasks for linting (`invoke lint`), running tests (`invoke test`), and building distributable packages (`invoke build`).

## Prompt Templates

Prompt JSON files live under `prompts/styles/<Style>/`. Each template includes an integer `id`, a `title`, a `style`, a list of `template` lines, and optional `placeholders`. The application enforces unique IDs via `menus.ensure_unique_ids()`.

## Working With This File

- When adding or modifying modules, scripts, or directories, update the relevant section here.
- Refer AI coding partners to this guide in initial instructions so they can quickly locate the appropriate components.


