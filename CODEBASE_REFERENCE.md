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
│       │   ├── controller.py       # High-level GUI workflow (uses selector)
│       │   ├── selector/           # Modular template selector (model + controller)
│       │   │   ├── model.py        # BrowserState, recursive index & search
│       │   │   └── controller.py   # Hierarchical UI, multi-select, preview, search
│       │   ├── template_selector.py # Backwards-compat thin wrapper
│       │   ├── collector/          # Variable input collection helpers
│       │   │   ├── __init__.py
│       │   │   ├── prompts.py     # GUI prompt construction
│       │   │   ├── overrides.py   # File override logic
│       │   │   └── persistence.py # Session state & persistence
│       │   ├── review_window.py
│       │   ├── file_append.py      # Shared append-to-file logic
│       │   └── gui.py              # Entry point launching PromptGUI
│       ├── hotkey/           # Platform-specific hotkey definitions
│       ├── hotkeys/         # Interactive hotkey assignment, dependency checking, and system integration
│       ├── logger.py         # Usage logging with SQLite rotation
│       ├── menus.py          # Fzf-based style/template picker and template creation
│       ├── shortcuts.py      # Numeric shortcut mapping & renumbering utilities
│       ├── updater.py        # Lightweight PyPI version check + pipx upgrade (rate-limited, silent)
│       ├── paste.py          # Clipboard interaction and keystroke simulation
│       ├── prompts/          # Packaged prompt templates (styles/basic/01_basic.json)
│       │   └── Settings/     # settings.json (mirrors per-template file overrides; editable)
│       ├── renderer.py       # Template loading, validation, and placeholder substitution
│       ├── resources/        # Static assets like banner.txt
│       ├── utils.py          # Safe subprocess execution helpers
│       └── variables.py      # Collect values for placeholders via GUI/editor/CLI; manages per-template file path/skip overrides
└── ...                       # Root configuration files (pyproject.toml, README.md, etc.)
```

## Component Interaction

1. **Entry Points**
   - `cli.main()` runs when the command-line tool starts. It performs dependency checks and launches either the terminal picker or the GUI.
   - `gui.gui.run()` provides a graphical front-end when `--gui` is supplied.
2. **Hotkey System**
   - `hotkeys.assign_hotkey()` captures user input and configures platform-specific global hotkeys
   - `hotkeys.update_hotkeys()` refreshes existing hotkey configuration and verifies dependencies
   - `hotkeys.ensure_hotkey_dependencies()` checks for required platform dependencies (AutoHotkey, espanso)
   - Platform-specific functions generate scripts with GUI-first, terminal fallback execution chains
3. **Template Selection**
   - GUI: `gui/selector/model.py` builds a hierarchical listing and a one-time recursive content index (path, title, placeholders, body lines) for fast AND-token search.
   - GUI: `gui/selector/controller.py` provides: recursive search (default), optional non-recursive filter, multi-select with synthetic combined template, preview window (Ctrl+P), quick search focus (`s`), numeric shortcut activation (0-9), backspace up-navigation, initial focus on search entry, shortcut manager & template wizard access.
   - CLI: `menus.list_styles()` and `menus.list_prompts()` (recursive) then `menus.pick_style()` / `menus.pick_prompt()` (fzf or text fallback).
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
 - Build distributions with `python -m build`.

## Prompt Templates

Prompt JSON files live under `prompts/styles/<Style>/`. The repository bundles only `basic/01_basic.json` as a minimal example. Each template includes an integer `id`, a `title`, a `style`, a list of `template` lines, and optional `placeholders`. The application enforces unique IDs via `menus.ensure_unique_ids()`.

### File / Reference Placeholder Pattern
To attach (and optionally inject) an external file:
1. Add `{ "name": "reference_file", "type": "file" }` once. First run prompts for a file and persists globally (not per template). Content is auto-loaded each run and available via `{{reference_file_content}}` for backward compatibility.

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

## GUI Selector Feature Matrix (Quick Reference)

| Feature | Implementation | Shortcut |
|---------|----------------|----------|
| Recursive search (default) | BrowserState.search index | (on by default) |
| Non-recursive filter | In-memory filter of current dir | Toggle checkbox |
| Focus search | Tk bindings | `s` |
| Numeric shortcut open | shortcuts.load_shortcuts + key bind | Digits 0-9 |
| Navigate | Listbox + search entry bindings | Arrow keys |
| Select/Open | open_or_select | Enter / Double-click |
| Up one directory | BrowserState.enter(up) | Backspace |
| Preview window | Toplevel (read-only) | Button / Ctrl+P |
| Multi-select toggle | UI checkbox | (mouse/space) |
| Mark template | Prefix `*` | Enter in multi-select |
| Finish multi | Synthetic merged template | Finish Multi button |
| Manage shortcuts / renumber | _manage_shortcuts dialog | Menu / Ctrl+Shift+S |
| New template wizard | open_new_template_wizard | Menu |

## Working With This File

- When adding or modifying modules, scripts, or directories, update the relevant section here.
- Refer AI coding partners to this guide in initial instructions so they can quickly locate the appropriate components.

## Numeric Shortcuts & Renumbering

Module: `shortcuts.py`

Responsibilities:
- Maintain `prompts/styles/Settings/template-shortcuts.json` mapping digit -> relative template path.
- Provide `renumber_templates()` to sync on-disk template `id` + filename prefix with chosen shortcut digits (1-98 range used; digit 0 allowed for mapping but not forced renumber if out of range logic is retained).

Renumber Process:
1. Build map of desired digit -> template path from mapping file.
2. For each desired numeric key, if current holder differs and digit occupied, the occupant is reassigned to the next free ID.
3. Update template JSON `id` and rename file to `NN_slug.json` (preserving rest of filename).
4. Update shortcut mapping paths if filenames changed.
5. Persist mapping atomically.

Collision Safety: Reassignment searches sequentially for the next unused ID (1-98). Exhaustion raises `ValueError`.

GUI Integration: Options -> Manage shortcuts / renumber dialog lists templates, allows double-click key assignment, clearing keys, and triggering the renumber routine. Selector binds digits 0-9 for instant opening.

Test: `tests/test_shortcuts.py` validates core renumber logic.

## Default Value Hint & Global Reminders

Default Hint (Feature A):
- `gui.collector.collect_single_variable()` displays a grey panel summarizing the placeholder's default (truncates >160 chars, `[view]` opens a modal to inspect full text). Input pre-filled with default; if cleared by user the raw value is empty.
- `menus.render_template()` substitutes defaults for placeholders whose collected values are effectively empty (None, blank string, empty list) without mutating the raw captured values.

Global Reminders (Feature B):
- At render time `menus.render_template()` merges a `reminders` value (string or list) from root `globals.json` into the template's `global_placeholders` when not already defined.
- Appends a markdown blockquote list `> Reminders:` with each reminder truncated to 500 chars.

Tests: `tests/test_defaults_and_reminders.py` covers fallback substitution and reminder block rendering.


