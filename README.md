# prompt-automation

**prompt-automation** is a keyboard driven prompt launcher designed for absolute beginners. With a single hotkey you can choose a template, fill in any placeholders and copy the result to your clipboard for manual pasting.


For a detailed codebase overview, see [CODEBASE_REFERENCE.md](CODEBASE_REFERENCE.md). AI coding partners should consult it before making changes.
---

## Getting Started with this Code

1. **Clone the repository**
   ```bash
   git clone https://github.com/<user>/prompt-automation.git
   cd prompt-automation
   ```
2. **Run the installer** for your platform. The script installs all dependencies (Python, pipx, fzf and espanso) and registers the global hotkey.
   - **Windows**
     ```powershell
     scripts\install.ps1
     ```
   - **macOS / Linux / WSL2**
     ```bash
     bash scripts/install.sh
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

Press **Ctrl+Shift+J** to launch the GUI. Select the basic template and fill in any required values. The rendered text is copied to your clipboard but not pasted automatically.

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

Templates live under `prompts/styles/`. Only `basic/01_basic.json` is bundled for now, but you can add your own templates in the same directory structure.

## Managing Templates

Template files are plain JSON documents in `prompts/styles/<Style>/`. You can organize them in nested subfolders (e.g. `prompts/styles/Code/Advanced/`) and they will still be discovered.
This repository currently includes a single example: `basic/01_basic.json`.
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
   .\scripts\install.ps1
   ```

**Alternative**: Run the installation directly from your WSL environment but
ensure Windows integration:

```bash
# In WSL, but installs to Windows
powershell.exe -Command "cd 'C:\\temp\\prompt-automation'; Copy-Item -Path '\\wsl.localhost\\Ubuntu\\home\\$(whoami)\\path\\to\\prompt-automation\\*' -Destination . -Recurse -Force; .\\scripts\\install.ps1"
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
