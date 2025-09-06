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
