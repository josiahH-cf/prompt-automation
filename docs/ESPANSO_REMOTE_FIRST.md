# Espanso Remote‑First Guide (Windows, WSL, macOS/Linux)

This guide documents the remote‑first Espanso setup used by Prompt‑Automation.
Your GitHub repository (the `espanso-package/` folder) is the single source of truth.
Local user config files are treated as ephemeral and removed during sync to
avoid duplicates like the “Hi there!” sample.

If you only read one section, read “Quick Start”.

---

## Quick Start (Recommended)

1) Set the default repo URL once
   - App menu: `Options → Espanso → Set Default Repo URL…`
   - Enter your HTTPS URL, for example:
     - `https://github.com/josiahH-cf/prompt-automation.git`

2) Clean & Sync
   - App menu: `Options → Espanso → Deep Clean + Sync (Windows)`
   - This removes all user `match/*.yml` files, writes a sentinel `disabled.yml`
     to stop defaults being recreated, installs the package from your Git URL,
     and restarts Espanso.

3) Verify (Windows PowerShell)
   - `espanso package list` → should show `prompt-automation` with
     `git: https://github.com/...` as the source
   - `Test-Path "$env:APPDATA\espanso\match\base.yml"` → `False`
   - `Test-Path "$env:APPDATA\espanso\match\disabled.yml"` → `True`

That’s it. Future edits go into `espanso-package/`. Other machines only need
to set the Default Repo URL once, then run Clean & Sync.

---

## What the tooling does

- Remote‑first install/update:
  - When a Git remote (or the “Default Repo URL”) is available, installs from
    GitHub (HTTPS on Windows) instead of using local `--path`.
  - Removes conflicting path installs and repo aliases before and after install
    so only one canonical package remains.

- Local default pruning:
  - Deletes all user `match/*.yml` and `*.yaml` files at
    - Windows: `%APPDATA%\espanso\match\` and `%LOCALAPPDATA%\espanso\match\`
    - Linux: `~/.config/espanso/match/`
    - macOS: `~/Library/Application Support/espanso/match/`
  - Writes `disabled.yml` with `matches: []` to prevent Espanso from recreating
    the sample files.

- Git robustness:
  - On “dubious ownership” errors, adds `safe.directory` and retries push/tag.
  - Uses HTTPS remotes on Windows to avoid SSH key prompts from GUI contexts.

---

## Routine workflow

- On your main machine
  - Edit triggers in `espanso-package/match/*.yml`
  - App menu: `Options → Espanso → Sync Espanso?`
    - Generates from any templates, validates, mirrors to `packages/`,
      commits/tries to push, then installs/updates from Git and restarts.

- On another machine
  - Set default repo URL (once), then run `Deep Clean + Sync (Windows)`.

### About tags/releases

Some Espanso builds resolve “latest” from GitHub Releases. If you prefer that
flow, publish tags like `espanso-vX.Y.Z` where `_manifest.yml` contains
`version: X.Y.Z`. Otherwise, install from a branch or explicit tag using the
Espanso submenu actions (they accept branch/tag names).

---

## Troubleshooting

### “Hi there!” still appears in suggestions
- Cause: local user match files exist or were recreated by Espanso.
- Fix quickly (Windows):
  - App menu: `Options → Espanso → Deep Clean + Sync (Windows)`
  - Or PowerShell (removes user files and leaves a sentinel):
    ```powershell
    $ErrorActionPreference='SilentlyContinue'
    Remove-Item -Force "$env:APPDATA\espanso\match\*.yml","$env:APPDATA\espanso\match\*.yaml"
    Remove-Item -Force "$env:LOCALAPPDATA\espanso\match\*.yml","$env:LOCALAPPDATA\espanso\match\*.yaml"
    New-Item -ItemType Directory -Force "$env:APPDATA\espanso\match" | Out-Null
    Set-Content -Encoding UTF8 "$env:APPDATA\espanso\match\disabled.yml" "matches: []"
    espanso restart
    ```

### Package stuck at an older version (e.g., 0.1.20)
- Often the GitHub provider installs the latest Release it recognizes.
  - Publish a new tag `espanso-vX.Y.Z` where `_manifest.yml` has `version: X.Y.Z`.
  - Or use `Install from Branch/Tag/URL` in the Espanso submenu to bypass
    Releases and install exactly what you want.

### “Permission denied (publickey)” or pushes/tags not updating
- Switch your repo’s remote to HTTPS on Windows and use the credential manager:
  ```powershell
  git remote set-url origin https://github.com/<owner>/<repo>.git
  git config --global credential.helper manager-core
  git fetch --prune origin
  git push -u origin HEAD
  ```

### “Dubious ownership” when pushing from UNC/WSL paths
```powershell
git config --global --add safe.directory <full repo path>
```
The sync tool does this automatically on push/tag failures, but you can pre‑set it.

### WSL vs Windows Espanso
- Espanso running inside WSL can’t drive Windows apps and may cause confusion.
  Remove it if you don’t need it:
  ```bash
  # In WSL
  set -euxo pipefail
  if command -v espanso >/dev/null 2>&1; then
    espanso stop || true
    espanso service unregister || true
    espanso package uninstall prompt-automation || true
  fi
  rm -rf ~/.config/espanso ~/.cache/espanso
  (command -v apt >/dev/null 2>&1 && sudo apt -y remove --purge espanso) || true
  (command -v snap >/dev/null 2>&1 && sudo snap remove espanso) || true
  ```

---

## Verification commands

### Windows (PowerShell)
- Paths and packages
  ```powershell
  espanso path
  espanso package list
  Test-Path "$env:APPDATA\espanso\match\base.yml"
  Test-Path "$env:APPDATA\espanso\match\disabled.yml"
  Select-String -Path "$env:APPDATA\espanso\**\*.yml","$env:LOCALAPPDATA\espanso\**\*.yml" -Pattern '(^|\s)trigger:\s*":espanso"' -List -ErrorAction SilentlyContinue
  ```

- One‑shot Clean & Sync (script form)
  ```powershell
  $ErrorActionPreference='SilentlyContinue'; espanso stop; Start-Sleep -Seconds 1;
  $dirs = @("$env:APPDATA\espanso\match", "$env:LOCALAPPDATA\espanso\match");
  foreach ($d in $dirs) {
    if (Test-Path $d) {
      Remove-Item -Force "$d\*.yml","$d\*.yaml"; Set-Content -Encoding UTF8 "$d\disabled.yml" "matches: []"
    }
  }
  espanso package uninstall prompt-automation | Out-Null
  # Use your Default Repo URL (set in the app) or paste the HTTPS URL + desired branch/tag
  espanso package install prompt-automation --git https://github.com/<owner>/<repo>.git --git-branch espanso-vX.Y.Z --external
  espanso restart
  espanso package list
  ```

### macOS (Terminal)
- Paths and basic cleanup
  ```bash
  espanso path
  ls -1 "$HOME/Library/Application Support/espanso/match" || true
  rm -f "$HOME/Library/Application Support/espanso/match"/*.yml "$HOME/Library/Application Support/espanso/match"/*.yaml
  printf 'matches: []\n' > "$HOME/Library/Application Support/espanso/match/disabled.yml"
  espanso package list
  ```

### Linux/WSL (Shell)
- Paths and basic cleanup
  ```bash
  espanso path || true
  ls -1 ~/.config/espanso/match || true
  rm -f ~/.config/espanso/match/*.yml ~/.config/espanso/match/*.yaml
  printf 'matches: []\n' > ~/.config/espanso/match/disabled.yml
  espanso package list || true
  ```

---

## Best practices

- Keep `espanso-package/` as the only editable source of truth.
- Always set the “Default Repo URL” in the app once per machine.
- Prefer HTTPS remotes on Windows; avoid running Git/Espanso from `\\wsl.localhost` paths.
- Tag releases as `espanso-vX.Y.Z` and keep `_manifest.yml`’s version in sync.
- When in doubt, run `Deep Clean + Sync (Windows)`; it converges state reliably.

---

## FAQ

- Q: Do I need Espanso inside WSL?
  - A: No. Uninstall it unless you specifically need headless automation inside WSL.

- Q: I still see duplicates after Clean & Sync.
  - A: Verify no extra `*.yml` are present under user match paths; ensure only one
       `prompt-automation` entry appears in `espanso package list`; restart Espanso.

- Q: Updates don’t reflect on another machine.
  - A: If you rely on Releases, publish a new `espanso-vX.Y.Z` tag; otherwise install
       from a branch/tag using the Espanso submenu.

