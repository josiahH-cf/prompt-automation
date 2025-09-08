#!/usr/bin/env bash

set -euo pipefail

info(){ echo -e "\033[1;32m$1\033[0m"; }
err(){ echo -e "\033[1;31m$1\033[0m" >&2; }
retry(){
    local cmd="$1"; local attempts=0; local max=2
    until eval "$cmd"; do
        attempts=$((attempts+1))
        if [ $attempts -ge $max ]; then
            return 1
        fi
        sleep 2
        info "Retrying: $cmd"
    done
}

LOG_DIR="$HOME/.prompt-automation/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/install.log"
exec > >(tee -a "$LOG_FILE") 2>&1
trap 'err "Error on line $LINENO. See $LOG_FILE"' ERR

# Detect platform
PLATFORM="$(uname -s)"
if grep -qi microsoft /proc/version 2>/dev/null; then
    PLATFORM="WSL2"
elif [ "$PLATFORM" = "Darwin" ]; then
    PLATFORM="macOS"
else
    PLATFORM="Linux"
fi
info "Detected platform: $PLATFORM"

# Determine package manager commands
if [ "$PLATFORM" = "macOS" ]; then
    if ! command -v brew >/dev/null; then
        err "Homebrew not found. Install from https://brew.sh and rerun."; exit 1
    fi
    PM_INSTALL="brew install"
else
    if command -v apt-get >/dev/null; then
        sudo apt-get update -y
        PM_INSTALL="sudo apt-get install -y"
    elif command -v dnf >/dev/null; then
        PM_INSTALL="sudo dnf install -y"
    elif command -v yum >/dev/null; then
        PM_INSTALL="sudo yum install -y"
    elif command -v pacman >/dev/null; then
        PM_INSTALL="sudo pacman -Sy --noconfirm"
    else
        err "Supported package manager not found. Install dependencies manually."; exit 1
    fi
fi

# Ensure python3
if ! command -v python3 >/dev/null; then
    info "Installing Python3..."
    retry "$PM_INSTALL python3" || { err "Failed to install Python3"; exit 1; }
fi

if ! python3 -m pip --version >/dev/null 2>&1; then
    err "pip is required but could not be found"; exit 1
fi

# Ensure Tkinter
if ! python3 - <<'PY' >/dev/null 2>&1; then
import tkinter
PY
    info "Tkinter not found. Attempting installation..."
    if command -v apt-get >/dev/null; then
        retry "$PM_INSTALL python3-tk" || info "Please install python3-tk manually."
    else
        err "Tkinter is missing. Install Python with Tk support (e.g., via python.org)."
    fi
fi

# Ensure pipx
if ! command -v pipx >/dev/null; then
    info "Installing pipx..."
    retry "python3 -m pip install --user pipx" || { err "pip install pipx failed"; exit 1; }
    retry "python3 -m pipx ensurepath" || { err "pipx ensurepath failed"; exit 1; }
    export PATH="$PATH:$(python3 -m site --user-base)/bin"
fi

# Install fzf
if ! command -v fzf >/dev/null; then
    info "Installing fzf..."
    retry "$PM_INSTALL fzf" || { err "Failed to install fzf"; exit 1; }
else
    info "fzf already installed"
fi

# Install espanso
if ! command -v espanso >/dev/null; then
    info "Installing espanso..."
    retry "$PM_INSTALL espanso" || { err "Failed to install espanso"; exit 1; }
else
    info "espanso already installed"
fi

# Register global hotkey
HOTKEY_SRC="$(cd "$(dirname "$0")/.." && pwd)/src/prompt_automation/hotkey"
if [ "$PLATFORM" = "Linux" ] || [ "$PLATFORM" = "WSL2" ]; then
    ESPANSO_MATCH_DIR="$HOME/.config/espanso/match"
    mkdir -p "$ESPANSO_MATCH_DIR"
    cp "$HOTKEY_SRC/linux.yaml" "$ESPANSO_MATCH_DIR/prompt-automation.yml"
    info "Espanso hotkey added. Restarting espanso..."
    espanso restart || true
elif [ "$PLATFORM" = "macOS" ]; then
    WORKFLOW_DIR="$HOME/Library/Application Scripts/prompt-automation"
    mkdir -p "$WORKFLOW_DIR"
    cp "$HOTKEY_SRC/macos.applescript" "$WORKFLOW_DIR/"
    osascript -e 'tell application "System Events" to make login item at end with properties {path:"'$WORKFLOW_DIR'/macos.applescript", hidden:false}' || true
fi

# Determine project root early (used by environment file below)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
info "Project root directory: $PROJECT_ROOT"

# record default hotkey mapping and enable GUI + auto updates
HOTKEY_CFG_DIR="$HOME/.prompt-automation"
mkdir -p "$HOTKEY_CFG_DIR"
echo '{"hotkey": "ctrl+shift+j"}' > "$HOTKEY_CFG_DIR/hotkey.json"
ENV_FILE="$HOTKEY_CFG_DIR/environment"
{
    echo 'PROMPT_AUTOMATION_GUI=1'
    echo 'PROMPT_AUTOMATION_AUTO_UPDATE=1'
    echo 'PROMPT_AUTOMATION_MANIFEST_AUTO=1'
    # Enable espanso sync orchestration to find this repo root
    echo "PROMPT_AUTOMATION_REPO=$PROJECT_ROOT"
} > "$ENV_FILE"
info "Wrote environment defaults to $ENV_FILE"

# Install prompt-automation via pipx
info "Installing prompt-automation..."

if [ ! -f "$PROJECT_ROOT/pyproject.toml" ]; then
    err "pyproject.toml not found at $PROJECT_ROOT/pyproject.toml. Make sure you're running this script from the correct location."; exit 1
fi
info "Found pyproject.toml at: $PROJECT_ROOT/pyproject.toml"

retry "pipx install --force \"$PROJECT_ROOT\"" || { err "Failed to install prompt-automation from local source"; exit 1; }

# Ensure PyYAML is available for espanso sync (belt-and-suspenders)
if command -v pipx >/dev/null 2>&1; then
    (pipx inject prompt-automation PyYAML >/dev/null 2>&1 || true) &
fi

# Perform immediate background upgrade + manifest update (idempotent) so future runs are current
(pipx upgrade prompt-automation >/dev/null 2>&1 || true) &
UPGRADE_PID=$!
(
    # Trigger manifest auto-update (if PROMPT_AUTOMATION_UPDATE_URL configured by user beforehand)
    prompt-automation --update >/dev/null 2>&1 || true
) &
UPDATE_PID=$!

# Set up global hotkey with GUI mode
info "Setting up global hotkey..."
PYTHONPATH="$PROJECT_ROOT/src" python3 -m prompt_automation.install.hotkey --hotkey "ctrl+shift+j" || {
    err "Failed to configure global hotkey. You can set it up manually later with: prompt-automation --assign-hotkey"
}

# Register espanso colon command and ensure package is mirrored + installed
info "Configuring espanso package and :pa.sync command..."
PROMPT_AUTOMATION_REPO="$PROJECT_ROOT" prompt-automation --espanso-sync || info "espanso sync orchestration completed with warnings"

# Seed Settings/settings.json with espanso_repo_root so GUI sync can find repo
python3 - <<PY || true
import json, os
from pathlib import Path
try:
    from prompt_automation.config import PROMPTS_DIR
    repo = os.environ.get('PROMPT_AUTOMATION_REPO', '')
    settings_dir = PROMPTS_DIR / 'Settings'
    settings_dir.mkdir(parents=True, exist_ok=True)
    sf = settings_dir / 'settings.json'
    try:
        data = json.loads(sf.read_text(encoding='utf-8')) if sf.exists() else {}
    except Exception:
        data = {}
    if repo:
        data['espanso_repo_root'] = repo
        sf.write_text(json.dumps(data, indent=2), encoding='utf-8')
        print(f"[install] Seeded espanso_repo_root in {sf}")
except Exception as e:
    print('[install] Could not seed espanso_repo_root:', e)
PY

# Summary verification
wait $UPGRADE_PID 2>/dev/null || true
wait $UPDATE_PID 2>/dev/null || true

info "\n=== Installation Summary ==="
for cmd in python3 pipx fzf espanso prompt-automation; do
    if command -v "$cmd" >/dev/null; then
        info "- $cmd: installed"
    else
        err "- $cmd: missing"
    fi
done

# Health check
info "\n=== Health Check ==="
PYTHONPATH="$PROJECT_ROOT/src" python3 - <<'PY' || { err "Health check failed"; exit 1; }
try:
    import prompt_automation.cli, prompt_automation.gui
    print("OK")
except Exception as e:
    print(f"ERROR: {e}")
    raise SystemExit(1)
PY

if [ "$PLATFORM" = "WSL2" ]; then
    info "WSL2 detected. For Windows hotkey integration run: powershell.exe -Command \"(Get-Location).Path; .\\install\\install.ps1\""
fi

info "Installation complete. You may need to restart your shell for PATH changes to take effect."
info "Installation log saved to $LOG_FILE"
