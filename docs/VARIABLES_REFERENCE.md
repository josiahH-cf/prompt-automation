# Variables & Globals Reference

Comprehensive guide to every kind of variable (placeholder) and global control point used by `prompt-automation`: how values are collected, transformed, persisted, excluded, and rendered. Split into focused sections for clarity.
# Variables & Globals Reference

Authoritative, example‑rich guide to every kind of variable (placeholder) and global control point used by `prompt-automation`: how values are collected, transformed, persisted, excluded, and rendered. Each section now includes practical JSON/body snippets plus rendered outputs for clarity.

Variable collection and review now occur in a single window. Set
`PROMPT_AUTOMATION_FORCE_LEGACY=1` before launching to restore the
multi-window dialogs.

---
## 1. High-Level Flow

1. Load template JSON (inject/share flag normalization).
2. Merge root globals → template globals (respect exclusions) & snapshot first run.
3. Collect placeholders (GUI / CLI / editor fallback).
4. Inject defaults for empty submissions.
5. Inject file contents + optional `*_path` tokens.
6. Apply formatting (`format` / `as`).
7. Fill placeholders (indent-aware multi-line expansion).
8. Remove empty lines & conditional phrases.
9. Append reminders & think_deeply (if applicable).
10. Trim blanks and output.
## 1. High-Level Flow

1. Load template JSON (normalize metadata / share flag).
2. Merge root `globals.json.global_placeholders` → template globals (respect `exclude_globals`), snapshot on first run.
3. Collect placeholders (GUI / CLI / editor fallback) + file chooser dialogs.
4. Apply default injection rules (only if user input empty).
5. Read file placeholder contents (supports multi-file) & lazily add `*_path` tokens if referenced.
6. Apply formatting transforms (`format` / `as`).
7. Perform indent‑aware substitution (multi-line content lines get indented to token column).
8. Remove lines that resolved empty + conditional phrase removals.
9. Append `reminders` & `think_deeply` (if defined & not excluded) when tokens missing.
10. Trim leading/trailing blank lines (if trimming enabled) and output.

Mini trace example:
```
Template line: 'Context:\n{{context}}'          (collect) -> user empties box
Default: '(none provided)'                       (default inject)
Line becomes: 'Context:\n(none provided)'
```

---
## 2. Placeholder Schema

| Key | Type | Purpose | Notes |
|-----|------|---------|-------|
| name | string | Token `{{name}}`. | Unique per template. |
| type | string | `file`, `list`, `number`; omit = text. | UI & processing. |
| label | string | UI label. | Auto from `globals.json.notes` if missing. |
| default | string/list | Fallback when empty. | Lists can be newline string. |
| multiline | bool | Force multi-line box. | Implicit for list. |
| options | list[str] | Dropdown choices. | Auto for `hallucinate` if missing. |
| format / as | string | `list`, `checklist`, `auto`. | Adds bullets / boxes. |
| remove_if_empty(_phrases) | str/list | Phrases to strip when value empty. | Case-insensitive. |
| persist | bool | Opt-in persistence (non-file). | File placeholders excluded. |
| override | bool | For file placeholders: persist path + skip. | Needed for multi-file memory. |

Example placeholder block with several attributes:
```jsonc
{
  "name": "acceptance_criteria",
  "type": "list",
  "default": ["All tests pass", "Meets performance budget"],
  "format": "checklist",
  "remove_if_empty": ["Acceptance Criteria:"]
}
```
Body usage:
```
Acceptance Criteria:\n{{acceptance_criteria}}
```
If the user enters nothing the rendered output becomes:
```
Acceptance Criteria:\n- [ ] All tests pass\n- [ ] Meets performance budget
```
If the user deletes all items, phrase removal strips the heading entirely.

---
## 3. Types & Behavior

| Type | Collected | Stored Raw | Substitution |
|------|-----------|------------|-------------|
| text | text box | string | direct (default if empty) |
| list | multiline lines | list[str] | joined with `\n` |
| file | chooser | path | content (plus optional path token) |
| number | numeric entry | string | direct (invalid→"0") |
| options | dropdown | string | direct |

Edge cases:
* Empty list placeholder lines (only whitespace) ⇒ treated as empty → default applied.
* Number: user inputs `abc` → coerced to `0` (you can still set a default like `1`).
* File: path persisted only when `override: true`; without it you are prompted each run.

Quick compare:
```
Input (list type, user types):
"Item A\n\nItem B  \n   "  -> Stored raw list: ["Item A", "", "Item B", "   "]
Render join -> 'Item A\n\nItem B\n'
Default injection? No (non-blank present)
```

---
## 4. File Placeholders (Multi-File + Inline Viewer)

Declare: `{ "name": "ref2", "type": "file", "override": true }`.

Rules:
* `override: true` persists `{path, skip}` per (template, name).
* Omit `override` → ephemeral (always prompt).
* Content at `{{name}}`; path at `{{name_path}}` (only if token appears).
* `reference_file` also provides legacy `{{reference_file_content}}` + global fallback. In single-window mode it renders inline with a markdown-ish preview (headings, bold, fenced code, simple bullets) and large file truncation (display only) instead of opening a separate modal viewer. Other file placeholders retain the legacy modal chooser unless future flags (e.g. `"inline_view": true`) are added.
* Global fallback triggers only if no/blank `reference_file` placeholder but body references it.
* Skipping: user can permanent skip (`skip:true`); one-time reminder emitted.
* Always fresh read (supports multiple encodings + `.docx`).

Multi-file example segment:
```jsonc
"placeholders": [
  {"name": "reference_file", "type": "file", "override": true},
  {"name": "design_notes", "type": "file", "override": true},
  {"name": "log_snippet", "type": "file"} // ephemeral, always re-prompt
]
```
Body:
```
Primary Doc Path: {{reference_file_path}}
Design Notes Length: {{design_notes | len}}
--- PRIMARY CONTENT ---
{{reference_file}}
--- DESIGN NOTES ---
{{design_notes}}
```
Result (assuming only `reference_file` selected, others skipped):
```
Primary Doc Path: /home/me/spec.md
Design Notes Length:      (line removed if token line empty)
--- PRIMARY CONTENT ---
<contents of spec.md>
--- DESIGN NOTES ---      (section header removed because placeholder line empty)
```
(`| len` is ignored today—future enhancement could enable filters; shown to illustrate safe no-op.)

---
## 5. Special Names

| Name | Purpose | Notes |
|------|---------|-------|
| reference_file | Primary file | Inline viewer (single-window) + legacy alias & fallback. |
| reference_file_content | Legacy alias | Not declared manually. |
| append_file / *_append_file | Append output file | Post-render write (review toolbar offers 'Preview Append Targets' to inspect existing file contents before confirmation). |
| context | Freeform context | May be replaced by file content manually pasted. |
| context_file / context_append_file | Internal path tracking | Not user-authored. |
| hallucinate | Creativity policy | Auto options & mapping. |
| think_deeply | Reflect directive | Appended if token absent. |
| reminders | Quality checklist | Appended blockquote; token optional (Copy Paths button appears in review only if any *_path tokens referenced). |

---
## 6. Formatting (`format` / `as`)

* list → prefix `- `.
* checklist → prefix `- [ ] `.
* auto → if every non-blank already bulleted, keep; else treat as list.
* Multi-line replacement keeps indentation if placeholder alone on line.

Formatting examples:
```jsonc
{"name": "risks", "type": "list", "format": "list"}
```
User input:
```
Latency regression
Security gap
```
Rendered:
```
- Latency regression
- Security gap
```

Checklist:
```jsonc
{"name": "qa_checks", "type": "list", "format": "checklist"}
```
Rendered:
```
- [ ] Unit tests passing
- [ ] Load tests green
```

Indent preservation:
```
Steps:\n    {{qa_checks}}
```
→ each line receives the four spaces indentation.

---
## 7. Hallucination Mapping

Substring mapping:
| Input Contains | Canonical |
|----------------|----------|
| omit / blank | (None) |
| critical | critical |
| normal | normal |
| high | high |
| low | low |

Canonical value inserted; None removes line if token alone.

---
## 8. Defaults

Inserted only if collected value is empty (None, blank string, or list with no non-blank items). Raw stored value remains empty.

Demonstration:
Placeholder:
```jsonc
{"name": "objective", "default": "(summarize key task succinctly)"}
```
User submission: blank → Render inserts default.
Later run (persist not set) still prompts; you can leave blank again for same effect.

---
## 9. Persistence

`~/.prompt-automation/placeholder-overrides.json` sections:
| Section | Description |
|---------|-------------|
| templates | File placeholder states `{path, skip}` |
| template_values | Persisted simple/list values (`persist: true`) |
| template_globals | First-run snapshot of globals per template |
| global_files.reference_file | Global fallback ref file path |
| session | Session data (`remembered_context`) |
| reminders | One-time skip notices |

Mirrored: `prompts/styles/Settings/settings.json` (only `templates`).

Example excerpt of `~/.prompt-automation/placeholder-overrides.json`:
```jsonc
{
  "templates": {
    "42": { "reference_file": {"path": "/home/me/spec.md", "skip": false},
             "design_notes": {"path": "/home/me/design.md", "skip": true} }
  },
  "template_values": {
    "42": { "objective": "Refactor parser for clarity" }
  },
  "template_globals": {
    "42": { "think_deeply": "Reflect step-by-step." }
  }
}
```
Setting `persist: true`:
```jsonc
{"name": "audience", "default": "Senior Engineers", "persist": true}
```
Once filled, value auto pre-fills next time (still editable).

---
## 10. Globals (`globals.json`)

Keys:
* `global_placeholders`: shared values.
* `notes`: auto-label hints (`name – description`).
* `render_settings.trim_blanks`: default trimming.

Snapshotting: first run saves copy under `template_globals.<id>`. Remove snapshot to re-sync.

Example: Change global `company_name` from "Acme" to "BetaCorp". Existing template still renders "Acme" until you delete that template's snapshot entry under `template_globals`. Then next render snapshots "BetaCorp".

---
## 11. Conditional Phrase Removal

If placeholder empty, phrases listed in `remove_if_empty` are stripped (case-insensitive) when followed by punctuation or whitespace boundaries.

Example:
Placeholder:
```jsonc
{"name": "risks", "type": "list", "remove_if_empty": ["Risks:"]}
```
Body:
```
Risks: {{risks}}
```
User leaves blank → Entire line removed (no orphan heading).
Case-insensitive: `RISKs:` would also be removed.

---
## 12. Excluding Globals

Template metadata: `"exclude_globals": ["reminders", "think_deeply"]` suppresses those keys before snapshot and injection.

Template snippet:
```jsonc
"metadata": { "exclude_globals": ["reminders", "think_deeply"] }
```
Effect: Even if globals define those entries they won't be appended; snapshot omits them so later global changes to those keys don't affect this template unless you remove the exclusion & delete snapshot.

---
## 13. Reminders Append

If global (or template) `reminders` present (string or list) and not excluded => appended:
```
Reminders:
> - Item 1
> - Item 2
```

---
### Quick Cheat Sheet

| Task | Action |
|------|--------|
| Persist simple value | Add `"persist": true` to placeholder |
| Remember file path | Add file placeholder with `"override": true` |
| Reset one snapshot | Remove template ID key under `template_globals` |
| Suppress global reminder | Add it to `metadata.exclude_globals` |
| Remove heading if empty | `"remove_if_empty": ["Heading:"]` |
| Add checklist | `"format": "checklist"` on list type |
| Path of file | Use `{{placeholder_name_path}}` |
| Legacy reference content | `{{reference_file_content}}` still works |
| Append reasoning directive | Provide global `think_deeply`; omit token |
| Show overrides | `prompt-automation --list-overrides` |

---

---
## 14. think_deeply Directive

If defined and not excluded:
* Token present → substituted.
* Token absent → directive appended at end (unless duplicate text already there).

Duplicate detection trims, normalizes whitespace & case so minor text casing differences still count as duplicates.

---
## 15. Path Tokens

For any file placeholder `X`, `{{X_path}}` injects the stored path (created lazily only if referenced). Legacy alias: `reference_file_content`.

Edge cases:
* If a path token is referenced but the user skipped the file, that line is removed (token resolves empty).
* Changing a file selection updates the path immediately on next render; no caching.

---
## 16. Environment Variables

| Variable | Effect | Default |
|----------|--------|---------|
| PROMPT_AUTOMATION_TRIM_BLANKS | Force enable/disable trimming (`0/false` disables) | Auto (true) |
| PROMPT_AUTOMATION_AUTO_UPDATE | Toggle background updater | Enabled |
| PROMPT_AUTOMATION_MANIFEST_AUTO | Toggle manifest auto-apply | Enabled |
| PROMPT_AUTOMATION_FORCE_LEGACY | Revert to legacy multi-window GUI | Disabled |

---
## 17. Metadata Keys

| Key | Type | Purpose |
|-----|------|---------|
| share_this_file_openly | bool | Privacy/export control (default true unless under `prompts/local`). |
| exclude_globals | list / string | Suppress selected globals. |
| trim_blanks | bool | Override trimming behavior. |

Example metadata block:
```jsonc
"metadata": {
  "share_this_file_openly": false,
  "exclude_globals": ["reminders"],
  "trim_blanks": false
}
```
Result: Template marked private, global reminders suppressed, trailing blank lines preserved.

---
## 18. Worked Example (Abbrev.)

Template:
```jsonc
{
  "id": 42,
  "template": ["# Review {{component}}", "{{reference_file_path}}", "{{think_deeply}}"],
  "placeholders": [
    {"name": "component", "default": "(unnamed)"},
    {"name": "reference_file", "type": "file", "override": true}
  ]
}
```
Flow: globals merge → snapshot → collect → file content injected → path token injected → think_deeply appended if missing.

## 19. Backward Compatibility

| Legacy | Current |
|--------|---------|
| reference_file_content | Still populated automatically. |
| Global fallback for arbitrary file placeholders | Limited to `reference_file` only. |
| Modal reference_file viewer | Inline viewer in single-window path (legacy modal remains for others). |
| Auto-persist all values | Replaced by `persist: true`. |

Migration tips:
* To convert always-persisted placeholders: add `"persist": true` explicitly to each you still want remembered.
* Remove obsolete fields from overrides by deleting their entries; they are regenerated as needed.

---
## 20. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| {{X_path}} blank | Skipped or path missing | Re-select / reset override. |
| Global change ignored | Snapshot present | Delete entry in `template_globals`. |
| Placeholder keeps prompting | Still defined though globalized | Remove from `placeholders`. |
| Empty line remains | Token not sole content | Put token alone or add phrase removal. |

Deep dive: If a token sits between other text `Intro {{objective}} details` and resolves empty, only the token disappears; surrounding spacing may leave a double space. Prefer placing tokens on their own line when optional.

---
## 21. Adding Features

1. Extend schema & docs.
2. Implement collection logic.
3. Add tests (render + edge cases).
4. Update README (summary) + this file.
5. Provide migration for legacy data.

Testing guidance:
* Add unit tests for: default injection, phrase removal, path token creation, multi-file skip + override persistence, think_deeply append logic, reminders exclusion, encoding fallback (.txt + .docx).
* Use parametrized tests for placeholder type formatting permutations.

---
## 22. Services

Internally, variable handling is powered by modular service helpers which can be
reused in custom tooling:

- `template_search`
- `multi_select`
- `variable_form`
- `overrides`
- `exclusions`

---
## 23. Related Docs

* Codebase overview: `docs/CODEBASE_REFERENCE.md`
* Installation issues: `docs/INSTALLATION_TROUBLESHOOTING.md`
* Python issues: `docs/PYTHON_TROUBLESHOOTING.md`

Keep this authoritative; open a PR for clarifications.
