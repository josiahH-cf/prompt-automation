#!/usr/bin/env bash

set -euo pipefail

LOG_DIR="$HOME/.prompt-automation/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/install.log"
exec > >(tee -a "$LOG_FILE") 2>&1
trap 'err "Error on line $LINENO. See $LOG_FILE"' ERR

info(){ echo -e "\033[1;32m$1\033[0m"; }
err(){ echo -e "\033[1;31m$1\033[0m" >&2; }

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
    else
        err "Supported package manager not found. Install dependencies manually."; exit 1
    fi
fi

# Ensure python3
if ! command -v python3 >/dev/null; then
    info "Installing Python3..."
    $PM_INSTALL python3 || { err "Failed to install Python3"; exit 1; }
fi

# Ensure pipx
if ! command -v pipx >/dev/null; then
    info "Installing pipx..."
    python3 -m pip install --user pipx || { err "pip install pipx failed"; exit 1; }
    python3 -m pipx ensurepath || { err "pipx ensurepath failed"; exit 1; }
    export PATH="$PATH:$(python3 -m site --user-base)/bin"
fi

# Install fzf
if ! command -v fzf >/dev/null; then
    info "Installing fzf..."
    $PM_INSTALL fzf || { err "Failed to install fzf"; exit 1; }
else
    info "fzf already installed"
fi

# Install espanso
if ! command -v espanso >/dev/null; then
    info "Installing espanso..."
    $PM_INSTALL espanso || { err "Failed to install espanso"; exit 1; }
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

# Install prompt-automation via pipx
info "Installing prompt-automation..."
pipx install --force prompt-automation || { err "Failed to install prompt-automation"; exit 1; }

info "Installation complete. You may need to restart your shell for PATH changes to take effect."
info "Installation log saved to $LOG_FILE"
