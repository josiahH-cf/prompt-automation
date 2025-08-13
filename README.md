# prompt-automation

**prompt-automation** is a keyboard driven prompt launcher designed for absolute beginners. With a single hotkey you can choose a template, fill in any placeholders and copy the result to your clipboard for manual pasting.

Recent feature highlights:
- Default value helper: input dialogs show a truncated hint of each placeholder's default (with a [view] popup for long defaults) and empty submissions now fall back to that default at render time.
- Global reminders: define `global_placeholders.reminders` (string or list) in `globals.json` and they'll be appended as a markdown blockquote to every template that doesn't override them.
- New Template Wizard: GUI tool (Options -> New template wizard) to create styles/subfolders and scaffold a template with suggested structured sections.
- Numeric shortcuts & renumbering: Assign single‑digit keys to favorite templates (Options -> Manage shortcuts / renumber) and optionally renumber files/IDs to match those digits. Press the digit in the selector for instant open.

### Default Value Hints & Fallback (Feature A)

Placeholder dialogs now display a grey "Default:" box showing the (possibly truncated) default value. Long defaults provide a `[view]` button to inspect the full text. If you submit an empty value (or for list placeholders, only blank lines) the default is injected automatically at render time.

### Global Reminders (Feature B)

Add a `reminders` entry (string or list of strings) under `global_placeholders` inside your top-level `globals.json` to have them appended as a markdown blockquote at the end of each rendered prompt. Individual templates can override by defining their own `global_placeholders.reminders`.

Example `globals.json` fragment:

```jsonc
{
   "global_placeholders": {
      "reminders": [
         "Verify numerical assumptions",
         "List uncertainties explicitly"
      ]
   }
}
```

Rendered tail (Markdown):

```
> Reminders:
> - Verify numerical assumptions
> - List uncertainties explicitly
```

### New Template Wizard

From the selector choose Options -> New template wizard to interactively:
1. Pick or create a style & nested subfolders.
2. Enter a title.
3. Accept or edit a suggested placeholder list (role, objective, context, etc.).
4. Choose to auto-generate a structured body (section headings with placeholder insertions) or provide a custom body.
5. Mark the template private (stored under `prompts/local/`) or shared.

The wizard allocates the next free ID (01–98) in that style and writes a JSON skeleton with defaults (role defaults to `assistant`).


For a detailed codebase overview, see [CODEBASE_REFERENCE.md](CODEBASE_REFERENCE.md). AI coding partners should consult it before making changes.
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
    install\install.ps1
     ```
   - **macOS / Linux / WSL2**
     ```bash
    bash install/install.sh
     ```

   Windows + WSL note: If you launch the Windows installer from a repository that lives inside WSL (\\wsl.localhost\...), the script stages a temporary copy for installation. As of version 0.2.1+ the installer now performs a post‑install "spec normalization" step (a forced pipx install from PyPI) so future `pipx upgrade prompt-automation` calls work. Earlier manual installs that deleted the temp directory could cause:

   ```text
   Unable to parse package spec: C:\Users\<User>\AppData\Local\Temp\prompt-automation-install
   ```

   If you still see this message, simply run:
   ```powershell
   pipx uninstall prompt-automation
   pipx install prompt-automation
   ```
   (Or upgrade to a newer version and run the app once so the internal fallback auto-fixes the spec.)

The GUI relies on the standard Tkinter module. Most Python distributions include it, but Debian/Ubuntu users may need `sudo apt install python3-tk`.

After installation restart your terminal so `pipx` is on your `PATH`.

## Usage

Press **Ctrl+Shift+J** to launch the GUI. A hierarchical template browser opens at `prompts/styles/`.

### GUI Selector Features (New)

Navigation & Selection:
- Arrow Up/Down: move selection
- Enter / Double‑Click: open folder or select template
- Backspace: go up one directory
- `s`: focus search box
- Ctrl+P: toggle preview window for highlighted template
- Multi-select checkbox: enable multi selection (prefix `*`) then Enter to mark/unmark items, Finish Multi to combine
- Finish Multi: builds a synthetic combined template (id -1) concatenating selected template bodies in order selected

Search:
- Recursive search is ON by default (searches all templates: path, title, placeholders, body)
- Toggle "Non-recursive" to restrict to current directory only
- Typing in the search box instantly filters results; Up/Down + Enter work while cursor remains in the box

Preview:
- Select a template and use the Preview button or Ctrl+P to open / close a read‑only preview window.

Breadcrumb & Focus:
- Breadcrumb line shows current path within styles
- Initial keyboard focus lands in search box so you can type immediately after pressing the global hotkey

After selecting a template and filling placeholders an editable review window appears.
Press **Ctrl+Enter** to finish (copies and closes) or **Ctrl+Shift+C** to copy
without closing. To skip a placeholder leave it blank and submit with
**Ctrl+Enter** – the entire line is removed from the final prompt. The rendered
text is copied to your clipboard (not auto‑pasted unless your platform hotkey script adds it).

The hotkey system automatically:
- Tries to launch the GUI first
- Falls back to terminal mode if GUI is unavailable
- Handles multiple installation methods (pip, pipx, executable)

To change the global hotkey, run:

```bash
prompt-automation --assign-hotkey
```
and press the desired key combination.

To update existing hotkeys after installation or system changes:

```bash
prompt-automation --update
```

```
[Hotkey] -> [Template] -> [Fill] -> [Copy]
```

Templates live under `prompts/styles/`. Nested subfolders are supported (e.g. `prompts/styles/Code/Troubleshoot/`). Only a small starter set is bundled; add your own freely.

### Reference / Context File Placeholders

Add a placeholder with `"type": "file"` (e.g. `reference_file`) followed by a plain placeholder named `reference_file_content` to trigger a popup viewer of the selected file. Include `{{reference_file_content}}` in your template lines if you want the file content injected; omit it to only view the popup.

Skipping a file: Press the `Skip` button in the file picker dialog. That choice is persisted per template (stored in `~/.prompt-automation/placeholder-overrides.json` and mirrored to `prompts/styles/Settings/settings.json`) and you will not be prompted again unless you reset it.

Manage or clear individual stored paths / skips via:
* GUI: Options -> Manage overrides
* CLI: `prompt-automation --list-overrides`, `--reset-one-override <TID> <NAME>`, or `--reset-file-overrides`

The legacy global "reference_file_skip" flag has been removed—skipping is now an explicit per-template action only.

## Managing Templates

Template files are plain JSON documents in `prompts/styles/<Style>/`. You can organize them in nested subfolders (e.g. `prompts/styles/Code/Advanced/`) and they will still be discovered recursively (GUI & CLI).
Examples included: `basic/01_basic.json`, and troubleshooting / code oriented samples.
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

Global defaults for common placeholders live in `prompts/styles/globals.json`.

## Sharing & Private Templates

By default every template JSON is considered shareable/open and can be exported or included in any list you might publish. A new explicit metadata flag now controls this behavior:

```
"metadata": {
   "share_this_file_openly": true
}
```

Rules (precedence order):
1. If `metadata.share_this_file_openly` is `false` the template is private/local-only.
2. Else if the file path lives under `prompts/local/` (case-insensitive) it is private (implicit).
3. Else it is shared.

Defaults & backward compatibility:
* Existing templates that lacked the flag are treated as shared (`true`). A migration script (see below) adds the explicit key so future tooling can rely on its presence.
* Missing `metadata` objects are created at load time. Malformed / non-boolean values are coerced (truthy -> `true`, falsy -> `false`) with a warning.

Local-only directory:
* Create `src/prompt_automation/prompts/local/` for templates you never want committed or shared. This path is `.gitignore`d. Any JSON here is automatically private even if it omits the flag or sets it `true` (path rule wins only when flag is absent or `true`; an explicit `false` already makes it private).

Why keep the explicit flag if directories can imply privacy?
* Future export / sync tooling can operate on paths outside `prompts/local/` and still distinguish deliberate private templates.
* Makes intent obvious when reading a file and enables one-off private files inside normal style folders.

FAQ:
* Q: What if I delete the flag?  A: Loader injects it as `true` (unless under `prompts/local/`).
* Q: Can I add comments?  A: JSON has no comments; you can use an `_comment` key or extend the `metadata` object (e.g. `"_comment": "internal draft"`).
* Q: How do I batch add the flag?  A: Use the provided migration script or the `jq` one-liner below.

Migration script (idempotent):
```
python scripts/add_share_flag.py
```

`jq` one-liner alternative (Linux/macOS):
```
find src/prompt_automation/prompts/styles -name '*.json' -print -exec \
   sh -c 'tmp="$(mktemp)" && jq \'(.metadata // {path:null}| .share_this_file_openly? // true | .) as $f | if (.metadata.share_this_file_openly? ) then . else (.metadata.share_this_file_openly=true) end' "$1" > "$tmp" && mv "$tmp" "$1"' _ {} \;
```
Adjust as needed; the Python migration script is simpler and safer.

Templates can omit these entries to use the defaults or override them by
defining placeholders with the same names.

### Appending output to a file

File placeholders named `append_file` (or ending with `_append_file`) cause the
final rendered text to be appended to the chosen path after you confirm the
prompt with **Ctrl+Enter**. The text is written in UTF-8 with a trailing
newline.

Example template:

```json
{
  "id": 45,
  "title": "Append log entry",
  "style": "Tool",
  "template": ["{{entry}}"],
  "placeholders": [
    {"name": "entry", "label": "Log entry", "multiline": true},
    {"name": "append_file", "label": "Log file", "type": "file"}
  ]
}
```

This will copy the prompt to your clipboard and also append it to the selected
log file when confirmed.

### Context files

Templates that include a `context` placeholder now open a popup that lets you
type the context manually or load it from a file. If a file is chosen its
contents populate the "Context" section before the prompt runs, and the final
response is appended to that same file with a timestamped separator when you
confirm with **Ctrl+Enter**.

### Override & Settings Sync

Per-template file selections and skip decisions are stored locally in `~/.prompt-automation/placeholder-overrides.json` and auto-synced to an editable settings file at `prompts/styles/Settings/settings.json` (key: `file_overrides.templates`). You can edit either location; changes propagate both ways on next run. This lets you version-control default overrides while still keeping user-specific runtime state local.

## Troubleshooting

- Run `prompt-automation --troubleshoot` to print log and database locations.
- Use `prompt-automation --list` to list available templates.
- Use `prompt-automation --update` to refresh hotkey configuration and ensure dependencies are properly installed.
- If the hotkey does not work see [docs/HOTKEYS.md](docs/HOTKEYS.md) for manual setup instructions.

### Tkinter Missing

If the GUI fails to launch due to a missing Tkinter module:

- **Debian/Ubuntu**: `sudo apt install python3-tk`
- **Windows/macOS**: Reinstall Python using the official installer from [python.org](https://python.org/downloads/), which bundles Tkinter by default.

### Hotkey Issues

If **Ctrl+Shift+J** is not working:

1. **Check dependencies**: Run `prompt-automation --update` to ensure all platform-specific hotkey dependencies are installed
   - **Windows**: Requires AutoHotkey (`winget install AutoHotkey.AutoHotkey`)
   - **Linux**: Requires espanso (see [espanso.org/install](https://espanso.org/install/))
   - **macOS**: Uses built-in AppleScript (manual setup required in System Preferences)

2. **Verify hotkey files**: The update command will check if hotkey scripts are in the correct locations:
   - **Windows**: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\prompt-automation.ahk`
   - **Linux**: `~/.config/espanso/match/prompt-automation.yml`
   - **macOS**: `~/Library/Application Scripts/prompt-automation/macos.applescript`

3. **Change hotkey**: Run `prompt-automation --assign-hotkey` to capture a new hotkey combination

## FAQ

**Where is usage stored?** In `$HOME/.prompt-automation/usage.db`. Clear it with `--reset-log`.

**How do I use my own templates?** Set the `PROMPT_AUTOMATION_PROMPTS` environment variable or pass `--prompt-dir` when launching.
**How do I multi‑select templates?** Check the Multi-select box, mark templates (they get `*` prefix), click Finish Multi. A synthetic template (id -1) concatenates the chosen bodies.
**How do I search across all templates?** Just type in search (recursive by default). To restrict scope, tick Non-recursive.
**Why do some templates show a preview but not others?** All valid JSON templates can be previewed; invalid templates are filtered out by validation.

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
   .\install\install.ps1
   ```

**Alternative**: Run the installation directly from your WSL environment but
ensure Windows integration:

```bash
# In WSL, but installs to Windows
powershell.exe -Command "cd 'C:\\temp\\prompt-automation'; Copy-Item -Path '\\wsl.localhost\\Ubuntu\\home\\$(whoami)\\path\\to\\prompt-automation\\*' -Destination . -Recurse -Force; .\\install\\install.ps1"
```

**Missing Prompts Directory:** If you see "prompts directory not found":
- Reinstall with `pipx install --force dist/prompt_automation-0.2.1-py3-none-any.whl`
- Or set `PROMPT_AUTOMATION_PROMPTS` environment variable to your prompts location
- Use `--troubleshoot` to see all attempted locations

## Directory Overview

```
project/
├── docs/               # Additional documentation
├── scripts/            # Install helpers
├── src/
│   └── prompt_automation/
│       ├── hotkey/     # Platform hotkey scripts
│       ├── prompts/    # Contains styles/basic/01_basic.json
│       └── ...         # Application modules
```

Enjoy!

## Quick Command Cheat Sheet (New)

Common one-liners:

```bash
# Run GUI directly
prompt-automation --gui

# Run terminal picker (fzf fallback)
prompt-automation --terminal

# List templates (CLI)
prompt-automation --list

# Rebuild / refresh hotkey scripts
prompt-automation --update

# Assign a new global hotkey
prompt-automation --assign-hotkey

# Show file override entries
prompt-automation --list-overrides

# Reset all file overrides (show those prompts again)
prompt-automation --reset-file-overrides

# Reset a single override (template id 12, placeholder reference_file)
prompt-automation --reset-one-override 12 reference_file

# Force manifest update (if PROMPT_AUTOMATION_UPDATE_URL is set)
prompt-automation --update --force

# Disable auto PyPI self-update
export PROMPT_AUTOMATION_AUTO_UPDATE=0
```

## Automatic Updates

When installed with `pipx install prompt-automation`, the tool will:

- On every start perform a fast, rate-limited (once per 24h) check
   against PyPI for a newer released version.
- If a newer version exists and `pipx` is on PATH it quietly executes:
   `pipx upgrade prompt-automation`.

You can opt out by setting an environment variable before launching:

```bash
export PROMPT_AUTOMATION_AUTO_UPDATE=0
```

Or permanently by adding the line above to `~/.prompt-automation/environment`.

Manual upgrade at any time:

```bash
pipx upgrade prompt-automation
```

This background updater is separate from the existing `--update` flow
which applies manifest-based template/hotkey updates.

### Handling Broken Local Path Specs (pipx)

If you installed from a *temporary* local path (e.g. a copy in `%TEMP%`) and that folder was deleted, `pipx upgrade` may fail with the "Unable to parse package spec" error. The updater now detects this and transparently re-runs:

```text
pipx install --force prompt-automation
```

falling back to a user `pip` install if pipx itself is unusable. You can disable this safety net with:

```bash
export PROMPT_AUTOMATION_DISABLE_PIPX_FALLBACK=1
```

To proactively fix a broken spec yourself:
```powershell
pipx uninstall prompt-automation
pipx install prompt-automation
```

Or (to keep a dev checkout) install from a *stable* non‑temp folder you do not delete, or build a wheel and install that.

## Releasing New Versions

Use the helper script to bump version, roll CHANGELOG, build artifacts, tag, and optionally publish:

```bash
# Patch bump (e.g. 0.2.1 -> 0.2.2), commit + tag, build
python scripts/release.py --level patch --tag

# Minor bump without tagging yet (dry run preview only)
python scripts/release.py --level minor --dry-run

# Set explicit version and publish to PyPI
python scripts/release.py --set 0.3.0 --tag --publish
```

Behavior:
1. Moves current "Unreleased" notes into a dated section for the new version.
2. Resets Unreleased placeholder.
3. Updates `pyproject.toml` version.
4. Builds wheel + sdist (installs build/twine if missing).
5. Commits and optionally tags `v<version>`.
6. Optionally uploads to PyPI via twine (`--publish`).

Require clean git tree unless `--allow-dirty` or `RELEASE_ALLOW_DIRTY=1`.

After tagging/publishing push:
```bash
git push && git push --tags
```

### Manual Build

To build the package without the release script, run:

```bash
python -m build
```

### Continuous Auto-Release (GitHub Actions)

An automated workflow (`.github/workflows/auto-release.yml`) bumps the patch version and publishes to PyPI on every push to `main` (excluding pure docs / workflow changes). To request a larger bump include a marker in any recent commit message:

- `[minor]` → increments minor, resets patch
- `[major]` → increments major, resets minor+patch

Flow executed by the Action:
1. Inspect last 20 commit subjects for bump marker (default patch).
2. Compute next version from current `pyproject.toml`.
3. Run `scripts/release.py --set <version> --tag` (updates CHANGELOG + tags).
4. Build artifacts.
5. Upload to PyPI with token `PYPI_API_TOKEN` (store in repo secrets).
6. Push commit + tag back to `main`.

Disable by removing or editing the workflow file. Manual releases remain possible via the script.

### Manifest (Template/Hotkey) Auto-Updates

If you provide a remote manifest via `PROMPT_AUTOMATION_UPDATE_URL`, the
tool now auto-applies those file updates on startup (backing up conflicts
as `*.bak`, moving renamed files). To restore interactive prompts set:

```bash
export PROMPT_AUTOMATION_MANIFEST_AUTO=0
```

Force a manual run (still respects interactive mode setting):

```bash
prompt-automation --update
```
