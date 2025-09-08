# Espanso Package (Snippets)

This repository ships an Espanso package so all text expansion rules are versioned, shared, and easy to update.

## Install (from this repo)

- Requirement: Espanso v2 installed and running.
- Install the package directly from GitHub:

```bash
espanso package install prompt-automation --git https://github.com/josiahH-cf/prompt-automation
```

- Update when a new version is released:

```bash
espanso package update prompt-automation
```

- Uninstall if needed (does not affect Prompt-Automation itself):

```bash
espanso package uninstall prompt-automation
```

## Package Layout (Source of Truth)

```
espanso-package/
  _manifest.yml      # name, version, description, author (SemVer)
  package.yml        # minimal package descriptor (optional)
  match/             # split snippets across multiple files
    prompt_automation_basics.yml
    prompt_automation_tools.yml
```

Snippets can be split across any number of `match/*.yml` files. These are mirrored to the external distribution layout.

## Authoring & Conventions

- Place all snippets in `espanso-package/match/*.yml` with the structure:

```yaml
matches:
  - trigger: ":pa.hello"
    replace: "Hello from Prompt-Automation"
```

- Security: never include secrets or private data. Keep examples generic.
- Triggers: use a consistent namespace like `:pa.*` to avoid collisions.
- Tests: YAML is validated in CI for syntax and duplicate triggers across all files.

## Versioning & Releases

- Version lives in `espanso-package/_manifest.yml` and follows SemVer.
- CI workflow validates YAML on every PR and push.
- Manual release: Actions → "Espanso Package CI" → "Run workflow" → provide `new_version`.
  - The workflow bumps `_manifest.yml`, commits, tags `espanso-vX.Y.Z`, and pushes.

## Distribution Layout (for espanso install)

This repo also contains a mirror under `packages/<name>/<version>/` to support installing via `espanso package install <name> --git <repo>`.

- Mirror the source to the distribution layout and optionally bump the version:

```bash
# WSL/Linux
bash scripts/espanso-package-runbook.sh            # set BUMP_VERSION=true to auto-bump patch
# The runbook seeds ALL Windows %APPDATA%\espanso\match\*.yml into espanso-package/match/ before mirroring
```

- After mirroring, install/update on Windows:

```powershell
espanso package update prompt-automation
espanso restart
```

## Local Development & Validation

- Run tests for just the espanso package checks:

```bash
pytest -q tests/espanso
```

- If you want to try the package locally before pushing, you can point Espanso at your repo clone as above. After editing snippets, restart Espanso if needed:

```bash
espanso restart
```

## Helper Scripts

- Lint YAML and duplicates: `scripts/espanso.sh lint`
- Mirror (and optional bump): `BUMP_VERSION=true scripts/espanso.sh mirror`
- Update and restart local espanso: `scripts/espanso.sh update`
- Add a quick snippet:

```bash
scripts/espanso.sh add-snippet --file base.yml --trigger :pa.hello --replace "Hello from Prompt-Automation"
```

- Disable local `%APPDATA%\espanso\match\base.yml` on Windows to avoid duplicates:

```powershell
powershell -File scripts/espanso-windows.ps1 -DisableLocalBase
```

## Backward Compatibility

This package is additive and does not change Prompt-Automation behavior. If you uninstall or disable the Espanso package, Prompt-Automation continues to work normally.

## Troubleshooting

- If install fails, ensure Espanso v2 is installed and running.
- If triggers don’t expand, check `espanso status` and verify no duplicates exist with other packages.
- Reinstall/update the package to refresh local state.

---

Maintainers: keep snippets modular, avoid secrets, and rely on CI tests to catch YAML mistakes and trigger collisions.

## One-Command Sync (Colon Command)

- Trigger `:pa.sync` from any text field to run the full, non-interactive pipeline:
  - Validate YAML and reject duplicates with a clear error.
  - Mirror `espanso-package/` to `packages/<name>/<version>/`.
  - Install/update the package locally and restart Espanso.

How it works:

- The match `espanso-package/match/prompt_automation_sync.yml` invokes the CLI:
  - `prompt-automation --espanso-sync`
  - The orchestrator discovers the repo via `PROMPT_AUTOMATION_REPO` (set by installers) or by walking up from the current directory.

Flags and env:

- `PA_AUTO_BUMP=patch|off` (default off) controls auto patch-bump.
- `PA_SKIP_INSTALL=1` skips install/update (useful for dry-runs).
- `PA_DRY_RUN=1` validates and mirrors only.

Installer integration:

- Installers write `~/.prompt-automation/environment` including `PROMPT_AUTOMATION_REPO=<project_root>` so the colon command can find your repo clone.

## Template-Driven Generation

- On sync, the orchestrator generates/updates snippets from templates, then validates and mirrors.
- Templates are discovered at:
  - `espanso-package/templates/*.yml`, and
  - `espanso-package/match/*.yml.example` (written to a sibling `*.yml`).
- Multi-line `replace` values are written using YAML block scalars (|) for readability.
- Duplicate triggers across generated templates are deduplicated; validation still rejects any remaining duplicates across all files.

## Branch-Aware Install/Update

- By default, git-based install/update targets the current branch (`git rev-parse --abbrev-ref HEAD`).
- Override via `PA_GIT_BRANCH=<branch>` or CLI `--git-branch <branch>`.
- The orchestrator tries `espanso package install ... --ref <branch>`, then falls back to `--branch <branch>` if needed.

## Windows-First + WSL Fallback

- On Windows, the install/update attempts PowerShell first.
- If it fails (non-zero exit or timeout), it retries via WSL (`wsl.exe bash -lc 'espanso ...'`).
- Non-Windows runs espanso directly.

## GUI Button: “Sync Espanso?”

- In the app’s Options menu, click “Sync Espanso?” to run the same pipeline as `:pa.sync` and the CLI.
- Shows success/failure; see logs at `~/.prompt-automation/logs/` for step-by-step JSON lines.

### Repo discovery for the GUI

- Optionally set a repo root in your prompts settings file to make the GUI button work outside the repo:

```
src/prompt_automation/prompts/styles/Settings/settings.json
{
  "espanso_repo_root": "C:/Users/<you>/github-cf/prompt-automation"
}
```

The sync orchestrator will prefer installing from the local mirrored path to avoid depending on `git` when not necessary.

### Convergence to One Source

- Sync force‑converges your machine to use the package from your repo path first (`--external`), falling back to `--path`, and only then to `--git` if needed.
- If the package is already installed from a different source, sync attempts a safe uninstall + reinstall to converge without affecting other packages.
- Windows tip: if `%APPDATA%\espanso\match\base.yml` exists you may get duplicate triggers. Disable it with:

```
powershell -File scripts/espanso-windows.ps1 -DisableLocalBase
```
