#!/bin/bash
set -e
# Install Python 3.11, pipx, fzf and espanso, then prompt-automation
echo "Step 1/6: Checking Python 3.11 ..."
if ! command -v python3.11 >/dev/null; then
  if command -v brew >/dev/null; then
    brew install python@3.11
  else
    echo "Please install Homebrew from https://brew.sh and retry."; exit 1
  fi
fi
echo "Step 2/6: Installing pipx ..."
if ! command -v pipx >/dev/null; then
  python3.11 -m pip install --user pipx
  python3.11 -m pipx ensurepath
fi
echo "Step 3/6: Installing fzf ..."
if ! command -v fzf >/dev/null; then
  brew install fzf
fi
echo "Step 4/6: Installing espanso ..."
if ! command -v espanso >/dev/null; then
  brew install espanso
fi
echo "Step 5/6: Installing prompt-automation ..."
pipx install --force prompt-automation
echo "Step 6/6: Opening README ..."
if command -v open >/dev/null; then
  open README.md
elif command -v xdg-open >/dev/null; then
  xdg-open README.md
fi
