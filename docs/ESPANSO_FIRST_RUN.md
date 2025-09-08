# Espanso: First-Run Checklist

Use this quick checklist to converge to a single, repo‑backed Espanso setup and verify it works.

Applies to Windows, Linux/WSL, and macOS.

## 1) Clean local state (safe backup)

Use the CLI command from any terminal. It backs up anything it removes.

- Inspect (no changes):

  `prompt-automation --espanso-clean-list`

- Minimal cleanup (recommended): backs up and removes only `base.yml` in your local match directory and uninstalls legacy/conflicting packages (like `your-pa`).

  `prompt-automation --espanso-clean`

- Deep cleanup: backs up and removes all local match `*.yml` (use if you suspect stray local files).

  `prompt-automation --espanso-clean-deep`

## 2) Sync package from your repo (single source)

- GUI: Options → “Sync Espanso?”
- CLI: `prompt-automation --espanso-sync`

Behavior:
- Generates from templates (if any), validates YAML, mirrors to `packages/<name>/<version>/`.
- Installs via local external/path; uninstalls any legacy package names pointing at this repo; restarts Espanso.

## 3) Verify

- `espanso package list` → should show only `prompt-automation` (preferably referencing your local repo path).
- `espanso status` → “espanso is running”.
- Test any trigger (e.g., `:espanso`, `:ntsk`) once — only one entry should appear.

## Notes

- The GUI “Sync Espanso?” and CLI discover your repo via `Settings/settings.json` key `espanso_repo_root` (seeded by the installers) or `~/.prompt-automation/environment` (`PROMPT_AUTOMATION_REPO`). No manual edits are required after install.
- Windows: if `%APPDATA%\espanso\match\base.yml` exists, it might duplicate triggers. The cleanup steps above handle this automatically.
