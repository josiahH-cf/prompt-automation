#!/bin/bash
set -e
# Install Python 3.11, pipx, fzf and espanso, then PromptPilot
if ! command -v python3.11 >/dev/null; then
  echo "Python 3.11 required"
  exit 1
fi
if ! command -v pipx >/dev/null; then
  python3.11 -m pip install --user pipx
  python3.11 -m pipx ensurepath
fi
if ! command -v fzf >/dev/null; then
  echo "Install fzf from https://github.com/junegunn/fzf/releases"
fi
if ! command -v espanso >/dev/null; then
  echo "Install espanso from https://github.com/espanso/espanso/releases"
fi
pipx install --force promptpilot
