# Changelog

## Unreleased
- Bug fix: stabilize CLI fallback for file placeholders with invalid pre‑supplied paths and no template binding; initialize labels early to prevent crashes and allow deterministic skip (None) without repeated prompts.
- Added: Placeholder-empty fast-path in single-window GUI. When a template has no effective input placeholders (placeholders missing/`null`/`[]` or only reminder/link/invalid specs), the app bypasses the variable collection stage and opens the final output view directly. Outputs render with the same pipeline as the normal review stage and auto-copy behavior remains unchanged. Observability: one debug log line (`fastpath.placeholder_empty`) emitted on activation (no template content logged). Kill-switch: set `PROMPT_AUTOMATION_DISABLE_PLACEHOLDER_FASTPATH=1` or add `"disable_placeholder_fastpath": true` to `Settings/settings.json` to disable. Backward compatible: templates with placeholders are unaffected.
- Added: Recent history for executed templates (last 5, persisted in `~/.prompt-automation/recent-history.json`). New Options → Recent history panel lists newest→oldest with preview and Copy action. Feature flag `PROMPT_AUTOMATION_HISTORY` (and `Settings/settings.json: recent_history_enabled`) controls enablement; default enabled. Redaction hook via `PROMPT_AUTOMATION_HISTORY_REDACTION_PATTERNS` or `recent_history_redaction_patterns` in settings. Purge behavior when disabled via `PROMPT_AUTOMATION_HISTORY_PURGE_ON_DISABLE` or `recent_history_purge_on_disable`. Defensive parsing, atomic writes, and corruption quarantine. No changes to existing flows besides post-success appends.
- Added: Optional hierarchical template browsing behind a feature flag. A new scanner (`TemplateHierarchyScanner`) renders physical on‑disk folders as a tree with caching and safe defaults. CRUD operations (`TemplateFSService`) provide create/rename/move/delete for folders and templates with path sandboxing and name validation. CLI gains `--tree` (and `--flat`) modifiers for `--list`. Observability: structured INFO logs for scan and CRUD events. Backward‑compatible: flat listing and public APIs unchanged by default.
 - Added: Read‑only “reminders” support at template root and placeholder level. Inline reminder text renders beneath inputs in the single‑window GUI, with a collapsible panel presenting template/global reminders. CLI prints template/global reminders once before the first prompt and placeholder reminders before each query. Feature flag `PROMPT_AUTOMATION_REMINDERS` (and `Settings/settings.json: reminders_enabled`) controls enablement; default is enabled. Observability: single `reminders.summary` log per template summarizing counts.
- Single-window GUI: restored bullet/checklist auto-formatting for multiline placeholders via lightweight key bindings.
- Reference file picker now renders only when a `reference_file` placeholder exists and appears inline beneath it (no global toolbar clutter).
- Improved accessibility: focus changes auto-scroll to reveal the focused input; added debug logs for bullet insertion, inline ref picker instantiation, and scroll adjustments.
- Added feature flag `PA_DISABLE_SINGLE_WINDOW_FORMATTING_FIX=1` to temporarily disable the new formatting/scroll and revert to legacy global picker layout.
- Added Dark Mode & theming infrastructure:
  - New `dark` theme with accessible palette (AA contrast).
  - Runtime toggle `Ctrl+Alt+D` with persistence.
  - CLI override `--theme=<light|dark|system>` and `--persist-theme`.
  - Safe defaults: light remains unchanged; disable via `enable_theming=false`.
  - Minimal Tk-based applier (no heavy deps) + ANSI formatter for CLI headings.
  - Extension guide for registering additional themes.
- Unified single-window UI now matches legacy feature set and is the default
  experience. Set `PROMPT_AUTOMATION_FORCE_LEGACY=1` to restore the old
  multi-window dialogs.
- Removed experimental `PROMPT_AUTOMATION_SINGLE_WINDOW` toggle.
- Documented modular service layer (`template_search`, `multi_select`,
  `variable_form`, `overrides`, `exclusions`).

## 0.4.4 - 2025-08-18
Comprehensive GUI refactor + quality-of-life enhancements, consolidating prior selector modernization and adding new safety / clarity features.

### Highlights
- Unified single-window workflow (`gui/single_window.py`): persistent root window orchestrating selection → (optional combined multi-select preview) → variable collection → inline review with geometry persistence.
- Centralized Options menu (`gui/options_menu.py`) shared between embedded selector and single-window, eliminating duplicated menu construction logic.
- Inline reference file viewer for `reference_file` placeholder (markdown-ish rendering, truncation for large files, copy/reset/refresh controls & rich keybindings).
- Multi-select synthetic template preview stage: after Finish Multi, users see a read-only combined template before placeholder prompts begin (increases safety & orientation for large batch operations).
- Append targets preview: Review stage toolbar button opens read-only inspectors for each `append_file` / `*_append_file` target before commit.
- Conditional Copy Paths button: Appears in review only when any `*_path` tokens are present in the variable map (avoids UI noise).
- New recursion toggle hotkey (Ctrl+L) for fast recursive / non-recursive search switching without leaving the keyboard.
- Geometry persistence (`~/.prompt-automation/gui-settings.json`) ensures window position/size consistency across runs.

### Hotkey & Selector Improvements (carried forward into 0.4.x)
- Enhanced global hotkey system: GUI-first launch with terminal fallback across Windows (AutoHotkey), Linux (espanso / .desktop fallback), and macOS (AppleScript) with dependency validation.
- Interactive `--assign-hotkey` command + per-user hotkey mapping file.
- Added `--update` command to refresh hotkey configuration / verify dependencies.
- Numeric shortcut management & renumber dialog; digits 0–9 open mapped templates instantly.
- Preview toggle (Ctrl+P) reuses an existing preview window rather than spawning multiples.

### Selector & Navigation
- Modular selector (`gui/selector/`) replaces monolith; legacy wrapper retained for backward import stability.
- Hierarchical folder navigation with breadcrumb and Backspace up-navigation.
- Recursive full-content AND-token search (path, title, placeholder names, body) with live incremental filtering; non-recursive mode toggle + keyboard focus retention.
- Quick keyboard accelerators: `s` focus search, Enter open/select, arrow key navigation, Ctrl+P preview, Ctrl+L recursion toggle.
- Multi-select synthesis produces an id = -1 ephemeral template (original sources untouched).

### Placeholders & Overrides
- Multi-file placeholder system: independent persistence (`path` + `skip`) per (template, placeholder name) mirrored to `prompts/styles/Settings/settings.json`.
- Manage Overrides dialog for inspecting/removing persisted file paths & simple value overrides.
- Inline `reference_file` viewer supersedes legacy modal; other file placeholders still use modal flow (future extensibility path).
- Optional `append_file` / `*_append_file` targets append rendered output post-confirmation; preview added this release for transparency.
- Conditional injection of `*_path` tokens only when referenced in template body to keep variable map lean.

### Review & Output
- Single-window inline review frame: edit rendered text directly; Ctrl+Enter to finish & paste; Ctrl+Shift+C copy without closing; Esc cancel.
- Append targets preview & Copy Paths buttons enhance auditability before finalizing.
- Automatic clipboard copy & paste keystroke emission (with fallback to copy-only on failure).

### Documentation Updates
- HOTKEYS.md: Added Ctrl+L toggle, multi-select preview stage, append targets preview, conditional Copy Paths description.
- CODEBASE_REFERENCE.md: Added `options_menu.py`, expanded single-window architecture, updated feature matrix, toolbar notes.
- VARIABLES_REFERENCE.md: Documented append targets preview & conditional Copy Paths; clarified inline `reference_file` behavior.
- CHANGELOG now reflects 0.4.4 unified release (previous “Unreleased” content incorporated here).

### Internal / Architecture
- Introduced `options_menu.configure_options_menu()` for DRY menu creation & accelerator binding mapping.
- Added multi-stage orchestration within `SingleWindowApp` with explicit stage swapping helper `_swap_stage()`.
- Title wrap-length auto-adjust bound to `<Configure>` events for responsive UX.
- Centralized geometry save/load helpers with defensive IO handling.
- Guarded fallbacks to legacy multi-window path if single-window initialization fails.

### Migration / Upgrade Notes
- No breaking template schema changes. Existing templates & overrides remain compatible.
- Legacy modal `reference_file` viewer still available for non-single-window flows; inline path is automatic in single-window mode.
- If you previously scripted selector menu modifications, update integrations to use `configure_options_menu` rather than manual `tk.Menu` mutation.
- Duplicate 0.2.1 entries in historical section left untouched (will be rationalized in a future housekeeping release).

### Testing & Stability
- Existing 22 test cases pass (no regressions introduced by refactor).
- GUI code paths wrapped in defensive try/except blocks; failures fall back to legacy flows where practical.

### Future Considerations (Not Yet Implemented)
- Optional inline mode for additional file placeholders.
- Filter / transform pipeline (e.g. length, case, diff) for future placeholder post-processing.
- Lightweight plugin hook for augmenting Options menu via `extra_items` callback.

## 0.2.1 - 2025-08-01
- Enhanced cross-platform compatibility for WSL2/Windows environments
- Fixed Unicode character encoding issues in PowerShell scripts  
- Improved WSL path detection and temporary file handling
- Enhanced prompts directory resolution with multiple fallback locations
- Updated all installation scripts for better cross-platform support
- Fixed package distribution to include prompts directory in all installations
- Added comprehensive error handling for missing prompts directory
- Made Windows keyboard library optional to prevent system hook errors
- Improved error handling for keyboard library failures with PowerShell fallback

## 0.2.1 - 2024-05-01
- Documentation overhaul with install instructions, template management guide and advanced configuration.
- `PROMPT_AUTOMATION_PROMPTS` and `PROMPT_AUTOMATION_DB` environment variables allow custom locations for templates and usage log.
