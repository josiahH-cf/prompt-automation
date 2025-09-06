# Espanso Package

This repository hosts an Espanso external package under `espanso-package/` and mirrored in `packages/<name>/<version>/` for installation via `espanso package install --git ... --external`.

Edit snippets in `espanso-package/match/*.yml`, bump `_manifest.yml` version, commit, push, then update on Windows with:

    espanso package update your-pa
    espanso restart
# Espanso Package (Snippets)

This repository ships an Espanso package so all text expansion rules are versioned, shared, and easy to update.

## Install (from this repo)

- Requirement: Espanso v2 installed and running.
- Install the package directly from GitHub:

```bash
espanso package install your-pa --git https://github.com/ORG/REPO
```

- Update when a new version is released:

```bash
espanso package update your-pa
```

- Uninstall if needed (does not affect Prompt-Automation itself):

```bash
espanso package uninstall your-pa
```

## Package Layout

```
espanso-package/
  _manifest.yml      # name, version, description, author
  package.yml        # minimal package descriptor
  match/             # split snippets across multiple files
    prompt_automation_basics.yml
    prompt_automation_tools.yml
```

Snippets can be split across any number of `match/*.yml` files; Espanso loads them all.

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
- To release a new espanso package version, run the GitHub Action manually:
  - Actions → "Espanso Package CI" → "Run workflow" → provide `new_version`.
  - The workflow bumps `_manifest.yml`, commits, tags `espanso-vX.Y.Z`, and pushes.

## Local Development & Validation

- Run tests for just the espanso package checks:

```bash
pytest -q tests/espanso
```

- If you want to try the package locally before pushing, you can point Espanso at your repo clone as above. After editing snippets, restart Espanso if needed:

```bash
espanso restart
```

## Backward Compatibility

This package is additive and does not change Prompt-Automation behavior. If you uninstall or disable the Espanso package, Prompt-Automation continues to work normally.

## Troubleshooting

- If install fails, ensure Espanso v2 is installed and running.
- If triggers don’t expand, check `espanso status` and verify no duplicates exist with other packages.
- Reinstall/update the package to refresh local state.

---

Maintainers: keep snippets modular, avoid secrets, and rely on CI tests to catch YAML mistakes and trigger collisions.
