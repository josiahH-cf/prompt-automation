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
│       ├── config.py         # Central configuration paths
│       ├── gui/             # Optional Tkinter interface for choosing templates
│       │   ├── controller.py       # High-level GUI workflow (prefers single-window orchestration)
│       │   ├── selector/           # Modular template selector (model + controller)
│       │   │   ├── model.py        # BrowserState, recursive index & search
│       │   │   └── controller.py   # Hierarchical UI, multi-select, preview, search
│       │   ├── template_selector.py # Backwards-compat thin wrapper
│       │   ├── collector/          # Variable input collection helpers
│       │   │   ├── __init__.py
│       │   │   ├── prompts.py     # GUI prompt construction
│       │   │   ├── overrides.py   # File override logic
│       │   │   └── persistence.py # Session state & persistence
│       │   ├── review_window.py    # Legacy review (still used for fallback / modular reuse)
│       │   ├── single_window.py    # Unified selector → (optional multi-select combined preview) → variables → review (geometry + inline viewers + append targets preview)
│       │   ├── options_menu.py     # Centralized Options menu builder reused by selector & single-window
│       │   ├── file_append.py      # Shared append-to-file logic
│       │   └── gui.py              # Entry point launching PromptGUI
│       ├── hotkey/           # Platform-specific hotkey definitions
│       ├── hotkeys/         # Interactive hotkey assignment, dependency checking, and system integration
│       ├── hotkeys.py       # Compatibility wrapper for hotkeys package
│       ├── install/         # Installation helpers (e.g., configure hotkey)
│       ├── logger.py         # Usage logging with SQLite rotation
│       ├── menus.py          # Fzf-based style/template picker and template creation
│       ├── shortcuts.py      # Numeric shortcut mapping & renumbering utilities
│       ├── starred.py       # Starred template persistence helpers
│       ├── switch_mode.py   # Toggle default GUI/terminal mode
│       ├── types.py         # TypedDict definitions for templates
│       ├── updater.py        # Lightweight PyPI version check + pipx upgrade (rate-limited, silent)
│       ├── update.py         # Self-update utilities applying manifest files
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
3. **Template Selection & Single Window**
   - Single Window: `gui/single_window.py` embeds the selector in a persistent root, then swaps frames for variable collection and in-place review (no new root windows). Geometry is persisted to `~/.prompt-automation/gui-settings.json`.
   - Selector Model: `gui/selector/model.py` builds hierarchical listing and recursive index (path, title, placeholders, body lines) for fast AND-token search.
   - Selector Controller: `gui/selector/controller.py` provides recursive / non-recursive search toggle (runtime toggle via Ctrl+L), multi-select synthetic template, preview window (Ctrl+P), quick search focus (`s`), numeric shortcut activation (0-9), backspace up-navigation, shortcut manager & template wizard access. In single-window mode its widgets are mounted inside a parent frame instead of their own root.
   - CLI: `menus.list_styles()` / `menus.list_prompts()` (recursive) then `menus.pick_style()` / `menus.pick_prompt()` (fzf or plain fallback).
4. **Rendering**
   - Selected templates are loaded with `renderer.load_template()` and placeholders are filled via `variables.get_variables()`.
   - The final text is produced by `renderer.fill_placeholders()`.
5. **Output**
   - `paste.paste_text()` copies the rendered text to the clipboard and attempts to send the paste keystroke.
   - `logger.log_usage()` records prompt usage to `~/.prompt-automation/usage.db` and rotates the database when it grows too large.
   - Single-window review occurs inline (Ctrl+Enter confirm, Esc cancel, Ctrl+Shift+C copy without closing) preserving window geometry.
6. **Error Handling**
   - All modules use `errorlog.get_logger()` to write diagnostic information to a shared log file.

## Scripts and Utilities

 - `install/install.sh`, `install/install.ps1`, and related scripts automate installation on Linux/macOS/Windows.
 - Build distributions with `python -m build`.

## Prompt Templates

Prompt JSON files live under `prompts/styles/<Style>/`. The repository bundles only `basic/01_basic.json` as a minimal example. Each template includes an integer `id`, a `title`, a `style`, a list of `template` lines, and optional `placeholders`. The application enforces unique IDs via `menus.ensure_unique_ids()`.

### File / Reference Placeholder Pattern (Multi-File Support & Inline Viewer)
You can declare **any number** of file placeholders inside a template. Example:

```jsonc
"placeholders": [
   { "name": "reference_file", "type": "file" },
   { "name": "architecture_notes_file", "type": "file" },
   { "name": "reference_file_2", "type": "file" }
]
```

Behavior:
* Each placeholder's collected path is persisted **per template + placeholder name** under `templates.<id>.<name>.path` in `placeholder-overrides.json` (only when user actually selects a file). The GUI treats `reference_file` the same as any other file placeholder—each template can reference a different file.
* On render the **file content** is injected at `{{<name>}}`.
* If the template body references `{{<name>_path}}` that token receives the raw filesystem path (only created when referenced – lazy insertion keeps var map clean).
* The legacy alias `{{reference_file_content}}` is still populated with the content of the canonical `reference_file` placeholder for backward compatibility. Other file placeholders do **not** get a `_content` alias.
* **Render-time global fallback (reference_file only)**: If a template does NOT declare `reference_file` *or* its collected path is blank, yet the body contains `{{reference_file}}` or `{{reference_file_content}}`, the globally configured reference file (if any) is loaded and injected. No other placeholder name receives a global fallback.
* Skipping a file via the GUI persists a `skip` flag for that (template,id,name). Remove the entry to re-enable prompting.
* Contents are always read fresh at render time—no cached snapshots—so edits to referenced files are reflected immediately upon re-render.
* Single-window enhancement: `reference_file` now uses an inline integrated selector + markdown-capable preview (Ctrl+Enter accept, Ctrl+R reset, Ctrl+U refresh, Ctrl+S skip) instead of a separate viewer window; other file placeholders retain legacy modal flow (future extensibility: declare `"inline_view": true`).

Management:
* GUI: Options → Manage overrides (add/remove per-file entries or clear skips)
* CLI: `--list-overrides`, `--reset-one-override <TID> <NAME>`, `--reset-file-overrides`

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
| Recursive search (default) | BrowserState.search index | (on by default; toggle Ctrl+L) |
| Non-recursive filter | In-memory filter of current dir | Toggle checkbox |
| Focus search | Tk bindings | `s` |
| Numeric shortcut open | shortcuts.load_shortcuts + key bind | Digits 0-9 |
| Navigate | Listbox + search entry bindings | Arrow keys |
| Select/Open | open_or_select | Enter / Double-click |
| Up one directory | BrowserState.enter(up) | Backspace |
| Preview window | Toplevel (read-only) | Button / Ctrl+P |
| Multi-select toggle | UI checkbox | (mouse/space) |
| Mark template | Prefix `*` | Enter in multi-select |
| Finish multi | Synthetic merged template | Finish Multi button (combined preview stage appears before variable prompts) |
| Manage shortcuts / renumber | _manage_shortcuts dialog | Menu / Ctrl+Shift+S |
| New template wizard | open_new_template_wizard | Menu |

## Single Window Variable Collection & Review

| Feature | Keys / Actions | Notes |
|---------|----------------|-------|
| Auto focus next field | After Next / Skip | Eliminates extra clicks |
| Single-line text | Enter=Next, Ctrl+S=Skip, Esc=Cancel | Status hints below title |
| Multiline / list | Ctrl+Enter=Next, Enter=newline, Ctrl+S=Skip | Word wrap + scroll |
| Dropdown/options | Enter=Next, Up/Down navigate | First option preselected |
| reference_file (inline) | Ctrl+Enter=Next, Ctrl+R=Reset, Ctrl+U=Refresh, Ctrl+S=Skip | Markdown-ish rendering, truncates >200KB |
| Other file placeholders | Legacy modal chooser/viewer | Future: inline flag |
| Context placeholder | Ctrl+Enter save/advance | Remembers last context globally |
| Review stage | Ctrl+Enter confirm, Ctrl+Shift+C copy only, Esc cancel | Inline review frame (toolbar: conditional Copy Paths, Preview Append Targets) |

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
3. Assign / fix missing or duplicate numeric `id` values (positive integers). Filenames are no longer auto-renamed to match the title; new files are created as `ID.json` (zero‑padded to at least two digits for IDs < 100). Existing filenames are left unchanged when titles change.
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
