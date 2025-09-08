# prompt-automation

**prompt-automation** is a keyboard driven prompt launcher designed for absolute beginners. With a single hotkey you can choose a template, fill in any placeholders and copy the result to your clipboard for manual pasting. The selector, collector and review now run in a unified single window. Set `PROMPT_AUTOMATION_FORCE_LEGACY=1` before launching to force the older multi-window flow.

Recent feature highlights:
- Default value helper: input dialogs show a truncated hint of each placeholder's default (with a [view] popup for long defaults) and empty submissions now fall back to that default at render time.
- Global reminders: define `global_placeholders.reminders` (string or list) in `globals.json` and they'll be appended as a markdown blockquote to every template that doesn't override them.
- New Template Wizard: GUI tool (Options -> New template wizard) to create styles/subfolders and scaffold a template with suggested structured sections.
- Numeric shortcuts & renumbering: Assign single‑digit keys to favorite templates (Options -> Manage shortcuts / renumber) and optionally renumber files/IDs to match those digits. Press the digit in the selector for instant open.
 - Multi-file reference placeholders with per‑placeholder persistence via `override: true`, plus lazy `{{name_path}}` tokens for any file variable.
 - Opt‑in value persistence using `"persist": true` (replaces legacy always‑persist behavior) with clear override management UI & CLI.
- Conditional phrase removal (`remove_if_empty`) to auto‑strip headings / prefixes when optional values omitted.
- Expanded, example‑rich Variables & Globals reference (see docs) covering formatting (`format` / `as`), path tokens, snapshotting, exclusions, and troubleshooting.
- Espanso integration: one‑click “Sync Espanso?” under Options (or use `:pa.sync` / `prompt-automation --espanso-sync`) updates snippets, validates, mirrors, installs/updates the package, and restarts Espanso. Supports branch override via `PA_GIT_BRANCH` and Windows PowerShell‑first with automatic WSL fallback.
 - Cleanup/reset commands: `prompt-automation --espanso-clean[-deep|-list]` safely backs up and removes local match files and uninstalls legacy/conflicting packages (cross‑platform). See the First‑Run checklist.
 
## Espanso: Create and Sync Workflow

Single source of truth lives under `espanso-package/`. Use templates to generate snippets, then sync.

- Add a template (preferred):
  - Create `espanso-package/templates/my_snippets.yml` with entries like:
    
        matches:
          - trigger: ":pa.kudos"
            replace: "Nice work!"
          - trigger: ":pa.mline"
            replace: "Line 1\nLine 2"
    
  - Or add a template stub in `espanso-package/match/*.yml.example` (will be written to `*.yml`).
- Generate + validate + mirror + install/update:
  - GUI: Options → "Sync Espanso?" (Windows-first PowerShell with WSL fallback).
  - Colon command: type `:pa.sync` anywhere.
  - CLI: `prompt-automation --espanso-sync`
  - Script: `scripts/espanso.sh sync`
- Branch override (git sources):
  - `PA_GIT_BRANCH=feature-x scripts/espanso.sh sync`
  - or `prompt-automation --espanso-sync --git-branch feature-x`
- Dry-run (generate + validate + mirror only):
  - `PA_SKIP_INSTALL=1 scripts/espanso.sh sync`
- After sync:
  - `espanso package list` shows `prompt-automation`.
  - `espanso restart` (run automatically by sync) ensures expansions are live.

Notes
- Multi-line replacements are written as YAML block scalars for readability.
- Duplicate triggers are deduplicated across generated templates, and validation rejects remaining duplicates across all files.
- Logs are JSON-line structured at `~/.prompt-automation/logs/`.

### Troubleshooting Espanso Sync

- Error: `No module named 'yaml'` (PyYAML missing)
  - If installed via pipx: `pipx inject prompt-automation pyyaml`
  - If using a venv: `pip install pyyaml`
  - Re-run: `prompt-automation --espanso-sync`

- Espanso not found
  - Ensure espanso v2 is installed and on PATH. Then re-run sync.

- Windows: PowerShell call fails
  - Sync automatically falls back to WSL if available. You can also run `scripts/espanso.sh sync` from WSL.

Fast-path (placeholder-empty templates):
- If a template defines no effective input placeholders (placeholders field is missing, null, `[]`, or only contains reminder/link/invalid entries), the app skips the variable collection step and navigates straight to the final review/output view. Output is rendered and available immediately; auto-copy behavior follows your existing setting. Disable via `PROMPT_AUTOMATION_DISABLE_PLACEHOLDER_FASTPATH=1` or `Settings/settings.json: { "disable_placeholder_fastpath": true }`.

### Reminders (Template & Placeholder)

Lightweight, read‑only instructional text you can declare in JSON which shows during variable collection to reduce cognitive load.

- Where to declare:
  - Template root: `"reminders": ["Keep code examples minimal", "Prefer POSIX shell"]`
  - Placeholder-level: in any placeholder object: `"reminders": ["Write in bullets", "Max 5 sentences"]`
  - Global file: `globals.json -> global_placeholders.reminders` provides defaults merged into template reminders.
- GUI behavior:
  - Inline: placeholder reminders render beneath the associated input field with muted styling.
  - Collapsible panel: a top “Reminders” panel groups template/global reminders; expanded on first open per session; toggle remembered for the session.
- CLI behavior:
  - Template/global reminders print once before the first prompt.
  - Placeholder reminders print just before that placeholder’s query.
- Read‑only: reminders are not editable at runtime and are never persisted; they are sourced from JSON only.
- Feature flag: enable/disable via `PROMPT_AUTOMATION_REMINDERS=1|0` or `Settings/settings.json: { "reminders_enabled": true|false }`.
- Dev timing (optional): set `PROMPT_AUTOMATION_REMINDERS_TIMING=1` to log `reminders.timing_ms` for the parsing step.

JSON examples:

```jsonc
{
  "id": 123,
  "title": "My Template",
  "reminders": [
    "Keep answers concise",
    "Cite any external data"
  ],
  "placeholders": [
    { "name": "summary", "label": "Summary", "multiline": true, "reminders": ["Bullet points", "<= 5 lines"] },
    { "name": "severity", "type": "options", "options": ["low","medium","high"], "reminders": ["Default is medium"] }
  ]
}
```

Note: Existing behavior that appends global reminders to the rendered output (as a markdown block) remains available for templates that rely on it.

### Hierarchical Templates (Opt‑In)

Browse and manage templates using the on‑disk folder structure. This is disabled by default to preserve existing behavior.

- Enable via env: set `PROMPT_AUTOMATION_HIERARCHICAL_TEMPLATES=1` (or add `"hierarchical_templates": true` to `Settings/settings.json`).
- CLI tree listing: `prompt-automation --list --tree` (use `--flat` to force legacy flat listing).
- Safe operations (for GUI adapters / future CLI): create, rename, move, duplicate, and delete templates/folders are sandboxed under `PROMPTS_DIR` with name validation and path traversal protection.
- Observability: scan and CRUD actions emit structured INFO logs (no template content).
 - GUI toggle: Options → "Toggle Hierarchical Templates" shows current state and persists your choice.

Rollback: unset the env var or set the settings flag to `false` to return to the flat view. No data migration is required—the filesystem is canonical.

---

### Developer Install (One-Step)

For local development where edits should take effect immediately and without re‑installing:

- Windows (recommended): run `install/install-dev.ps1` in PowerShell.
  - Installs in editable mode via pipx (or falls back to pip `--user -e`).
  - Sets `PROMPT_AUTOMATION_DEV=1` and `PROMPT_AUTOMATION_AUTO_UPDATE=0` for your user.
  - Assigns the standard hotkey (Ctrl+Shift+J) and writes the AHK script.
- Linux/macOS: install in editable mode and assign hotkey
  - `pipx install --editable .` or `python -m pip install --user -e .`
  - `prompt-automation --assign-hotkey`

Launch commands (any): `prompt-automation`, `prompt_automation`, `pa`, or `python -m prompt_automation`.

Hotkey repair/verification: `prompt-automation --hotkey-repair` (re-writes AHK/Espanso config; safe to run anytime). Status: `prompt-automation --hotkey-status`.

Run tests as a baseline: `pytest -q`.

### Espanso Package (Snippets)

Install the versioned Espanso package from this repo to get team-wide text expansions:

```bash
espanso package install prompt-automation --git https://github.com/josiahH-cf/prompt-automation
```

Update when a new version is released:

```bash
espanso package update prompt-automation
```

Uninstall (does not affect Prompt-Automation itself):

```bash
espanso package uninstall prompt-automation
```

See `docs/ESPANSO_PACKAGE.md` for authoring, versioning, and CI details.

#### Quick Add → Validate → Sync (Espanso)

- Create safely (prevents duplicates):
   - python3 scripts/add_espanso_snippet.py --file my_tools.yml --trigger :pa.kudos --replace "Great job — thanks for the help!"
- Validate fast:
   - pytest -q tests/espanso
   - scripts/espanso.sh lint
- Sync locally (mirror + install/update + restart):
   - scripts/espanso.sh sync
   - Optional: PA_SKIP_INSTALL=1 (dry-run), PA_AUTO_BUMP=patch (auto bump)
- Smoke check:
   - espanso package list; espanso status; try your trigger in any text field
- Commit & push:
   - git add espanso-package packages && git commit -m "feat(espanso): add :pa.kudos snippet" && git push

Tip: Use the template "Espanso Snippet – Meta‑Prompt (Simple)" to generate a compact meta‑prompt you can paste into your LLM assistant to perform the exact edits and commands above.

### Dark Mode & Theming

- Default is light (unchanged visuals). Toggle at runtime with `Ctrl+Alt+D`.
- Persist your choice automatically; disable theming entirely by setting `enable_theming` to `false` in `Settings/settings.json`.
- One-off override from CLI: `prompt-automation --theme=dark` (does not persist). To persist: add `--persist-theme`.
- Theming is implemented via Tk’s option database (no heavy dependencies). Additional themes can be registered via JSON—see `docs/THEME_EXTENSION_GUIDE.md`.

### Default Value Hints & Fallback (Feature A)

Placeholder dialogs now display a grey "Default:" box showing the (possibly truncated) default value. Long defaults provide a `[view]` button to inspect the full text. If you submit an empty value (or for list placeholders, only blank lines) the default is injected automatically at render time.

### Global Reminders (Feature B)

Add a `reminders` entry (string or list of strings) under `global_placeholders` inside your top-level `globals.json`. These will appear in the GUI’s collapsible panel and CLI preface during collection. If your template uses the legacy post‑render append, they will also be appended to the final markdown unless the template excludes them.

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

### Placeholder & Global Variable Reference

This section explains every variable type you will encounter, how values are collected (or auto‑injected), how persistence works, and how to fully control **global** variables (define once, reuse forever, or exclude per template).

#### 1. Placeholder Basics

Each template has a `placeholders` array. Every entry minimally declares `{ "name": "variable_name" }` and can include:

| Key | Meaning | Common Values |
|-----|---------|---------------|
| `name` | Identifier referenced as `{{name}}` in the template body. | e.g. `objective` |
| `type` | Input mode override. One of `file`, `list`, `number`, or omitted (text). | `file` |
| `multiline` | If true, opens a large text area (multi‑paragraph). | `true` / `false` |
| `default` | Fallback text/list used only when user input is blank. | Any string |
| `options` | Fixed choices (GUI combobox / CLI menu). | `["A","B"]` |
| `label` | Friendly prompt label; if omitted we derive one from global notes. | `"Context (high-level)"` |

Rules:
* Empty submission (blank text, or list with zero non‑blank lines) → default substituted at render time (raw stored value remains empty for audit).
* A placeholder that resolves to an empty string or `None` removes the *entire line* containing its token.

#### 2. Supported Placeholder Types

| Type / Flag | Input UI | Stored Form | Render Behavior |
|-------------|----------|-------------|-----------------|
| (omitted) / text | Single line | `str` | Direct substitution (default fill if empty) |
| `multiline: true` | Multi-line text box | `str` | Preserves newlines |
| `type: "list"` | Multi-line (one item per line) | `list[str]` | Joined with `\n`; empty ⇒ default |
| `type: "file"` | File chooser dialog | path (string) | File read at render; for `reference_file` its content auto-injected / previewed |
| `type: "number"` | Single line | stringified number | Validated; invalid → `0` |
| `options: [...]` | Dropdown / selection | selected string | Value used verbatim (mapped for some special names) |

#### 3. Special Placeholder Names

| Name | Purpose | Notes |
|------|---------|-------|
| `context` | Free-form or file‑loaded context block. | File load copies contents into the text area. Path tracked separately for re‑read. |
| `reference_file` | Capture path to a key document. | Skip once → never reprompt until reset. |
| `reference_file_content` | (Legacy) Synthetic content of `reference_file` (still populated for backward compatibility). |
| `hallucinate` | Creativity / inference policy line. | Dropdown auto-generated if no `options`; canonical tokens: `critical`, `normal`, `high`, `low`, or omitted. `(omit)` removes the line. |
| `think_deeply` | Reflective reasoning directive. | Usually supplied globally; auto-appends if token absent. |
| `reminders` | Safety/quality reminders list. | Appended as blockquote list at end. |

#### 4. Persistence (Per Template)

Stored in `~/.prompt-automation/placeholder-overrides.json`:
* `template_values` – last non-empty simple/list values for each template ID → auto pre-fill → GUI skips re-prompt unless you clear them.
* `templates` – file placeholder paths + skip flags.
* `template_globals` – snapshot of global values (see below) at the *first* run of a template.

Manage via GUI: Options → Manage overrides (edit or remove), or CLI flags.

#### 5. Global Variables (Define Once, Reuse Everywhere)

Create / edit `globals.json` at your prompts root (`prompts/styles/globals.json`):

```jsonc
{
   "schema": 1,
   "type": "globals",
   "global_placeholders": {
      "hallucinate": "Absolutely no hallucination (critical)",
      "think_deeply": "Reflect step-by-step; verify factual claims.",
      "reminders": [
         "Cite sources when possible",
         "Flag uncertainties",
         "Prefer concise, actionable structure"
      ],
      "company_name": "Acme Corp"
   },
   "notes": {
      "hallucinate": "hallucinate – Creativity policy (omit / critical / normal / high / low).",
      "think_deeply": "think_deeply – Appended reflective directive if token absent.",
      "reminders": "reminders – Safety / quality bullet list appended at end.",
      "company_name": "company_name – Injected brand identifier."
   }
}
```

How it works:
1. On each render we merge `global_placeholders` into the template’s own `global_placeholders` (template wins on conflicts).
2. The first time a given template ID renders we take a **snapshot** (stored under `template_globals`). Future runs reuse the snapshot even if `globals.json` changes (stable reproducibility).
3. Auto-injection: If a global key’s token (e.g. `{{company_name}}`) appears in the template body and you did not explicitly prompt for it, its global value fills the slot without prompting.
4. Special behaviors:
    * `reminders`: appended as a blockquote section if present and not excluded.
    * `think_deeply`: appended at end (if present globally), only if token not already placed and directive text not already present.
    * `hallucinate`: treat like any normal token; if omitted or set to `(omit)` the line is removed when empty.

Update a global for all templates:
* Edit `globals.json`.
* Delete snapshot entries (remove the template ID under `template_globals` in overrides) to force re-snapshot on next run.

#### 6. Excluding Specific Globals per Template

Add to template metadata:

```json
"metadata": {
   "exclude_globals": ["reminders", "think_deeply"]
}
```
* Excluded keys are removed **before** snapshot & auto-injection.
* They stay suppressed until you edit the metadata.
* You can edit this list via GUI: Options → Edit global exclusions.

#### 7. “Prompt Once Then Make Global” Workflow

1. Leave a variable (e.g. `hallucinate`) as a normal placeholder → collect your preferred policy.
2. Copy chosen value into `globals.json.global_placeholders.hallucinate`.
3. Remove the placeholder from templates (leave the token in body if you still want the line) or add `(omit)` semantics.
4. Run template again → snapshot includes new policy; you will not be prompted for it anymore.

#### 8. Reset / Maintenance Cheat Sheet

| Task | Action |
|------|--------|
| Clear one file override | Options → Manage overrides → remove row (kind=file) |
| Clear one simple value | Same dialog (kind=value) |
| Reset all file overrides | Options → Reset reference files (now asks to confirm; undo available) |
| Refresh global values for one template | Delete its entry under `template_globals` in overrides file |
| Suppress a global for one template | Add it to `metadata.exclude_globals` |
| Re-enable a suppressed global | Remove from `exclude_globals` & delete snapshot if you want latest root value |

#### 9. Hallucination Policy Levels

| Canonical | Friendly Label (GUI) | Intent |
|-----------|----------------------|--------|
| (omit) | (omit) | No explicit policy line (token removed) |
| critical | Absolutely no hallucination (critical) | Strict factual fidelity | 
| normal | Balanced correctness & breadth (normal) | Balanced creativity |
| high | Some creative inference allowed (high) | Moderate exploration |
| low | Maximum creative exploration (low) | Max creativity; correctness secondary |

To change default policy globally: edit `globals.json`, remove snapshots (optional), rerun templates.

---

### New Template Wizard

From the selector choose Options -> New template wizard to interactively:
1. Pick or create a style & nested subfolders.
2. Enter a title.
3. Accept or edit a suggested placeholder list (role, objective, context, etc.).
4. Choose to auto-generate a structured body (section headings with placeholder insertions) or provide a custom body.
5. Mark the template private (stored under `prompts/local/`) or shared.

The wizard allocates the next free ID (01–98) in that style and writes a JSON skeleton with defaults (role defaults to `assistant`).


For a detailed codebase overview, see [docs/CODEBASE_REFERENCE.md](docs/CODEBASE_REFERENCE.md). For comprehensive, example‑rich placeholder & global variable semantics (multi‑file, persistence, path tokens, formatting, exclusions, troubleshooting) read [docs/VARIABLES_REFERENCE.md](docs/VARIABLES_REFERENCE.md). AI coding partners should consult these before making changes.
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
- Press * (asterisk) or click the "Star / Unstar (*)" button to toggle a template in your starred list (max 10). When at the shared root with no active search, a ---Starred--- section will appear at the top listing your favorites. Use arrow keys as usual to navigate.
- Assign numeric quick command keys (0-9) via Options -> Manage Shortcuts. When assigned, a --- Quick Commands--- section appears (shared root, no search) showing entries like `1: Title`. Hitting the digit key instantly opens that template.

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

### Reference / Context File Placeholders (Multi-File)

You can declare **multiple** file placeholders. Each one captures a path and injects its file contents.

Example snippet:

```jsonc
"placeholders": [
   { "name": "reference_file", "type": "file" },
   { "name": "architecture_notes_file", "type": "file" },
   { "name": "reference_file_2", "type": "file" }
]
```

Tokens you can use inside the template body:
* `{{reference_file}}` → content of the main reference file
* `{{reference_file_content}}` → legacy alias for the same content (still supported)
* `{{architecture_notes_file}}` → content of that secondary file
* `{{architecture_notes_file_path}}` → the filesystem path (path tokens are only created when referenced)
* `{{reference_file_path}}`, `{{reference_file_2_path}}`, etc. follow the same pattern

Global fallback rules:
* Only the canonical name `reference_file` can fall back to a globally configured file if the template either omits the placeholder or leaves it blank but references `{{reference_file}}` or `{{reference_file_content}}`.
* Other file placeholders never use the global fallback—they remain empty if not selected.

Skipping / persistence:
* Each (template id, placeholder name) pair stores its own selected path or skip flag in `~/.prompt-automation/placeholder-overrides.json` (mirrored to `prompts/styles/Settings/settings.json`).
* Remove the entry (GUI or CLI) to re-enable prompting.

Refreshing / updates:
* Content is always read fresh at render time and on viewer refresh (no caching). Editing a referenced file and re-rendering immediately shows the updated content.

Manage or clear stored paths / skips via:
* GUI: Options -> Manage overrides
* CLI: `prompt-automation --list-overrides`, `--reset-one-override <TID> <NAME>`, or `--reset-file-overrides`

The legacy global "reference_file_skip" behavior is removed—skipping is explicit per template & placeholder now.

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

## Services

The GUI now delegates work to a small service layer useful for extensions and automation:

- `template_search` – walk the prompts tree and resolve numeric shortcuts.
- `multi_select` – build synthetic combined templates from marked items.
- `variable_form` – construct placeholder widgets for variable collection.
- `overrides` – manage persisted placeholder values and file paths.
- `exclusions` – parse `exclude_globals` metadata.

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

### Windows auto-update safety

On Windows, automatic background upgrades via `pipx` are disabled by default to
avoid breaking the `pipx` shim in certain edge cases (e.g., installing from a
temporary or WSL-backed path). You can opt in explicitly by setting:

```powershell
$env:PROMPT_AUTOMATION_WINDOWS_ALLOW_PIPX_UPDATE = '1'
```

Manual updates continue to work and are recommended on Windows:

```powershell
pipx upgrade prompt-automation
# or
prompt-automation --update
```

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

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup. For a summary of the selector, collector, and review window features, see the [GUI parity spec](docs/PARITY_SPEC.md).
### Mapping Digit Shortcuts (Guided)

- Open Options → Manage shortcuts / renumber.
- Double‑click a row to edit a digit. A structured picker lists all templates with ID, title, and relative path; you can double‑click to select instead of typing a free path.
- If you overwrite an existing mapping for a digit, the UI asks for confirmation.
- The “Renumber” action updates template IDs and file prefixes to match any numeric digit shortcuts.

### Reset Overrides with Undo

- Options → Reset reference files now shows a confirmation dialog and creates a one‑level undo snapshot.
- To restore, use Options → Undo last reset.
- Scope: includes file path/skip overrides and template value overrides stored in `placeholder-overrides.json`. The undo snapshot is single‑level and is cleared after restore.
### Espanso First‑Run / Reset

Use these commands any time to converge to a clean, single‑source setup:

- Inspect local state (no changes): `prompt-automation --espanso-clean-list`
- Minimal cleanup: `prompt-automation --espanso-clean` (backs up + removes local base.yml; uninstalls legacy package names; restarts Espanso)
- Deep cleanup: `prompt-automation --espanso-clean-deep` (backs up + removes all local match/*.yml)

Then sync:

- GUI: Options → "Sync Espanso?"
- CLI: `prompt-automation --espanso-sync`

See `docs/ESPANSO_FIRST_RUN.md` for the full checklist.
