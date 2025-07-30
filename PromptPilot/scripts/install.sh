#!/bin/sh
set -e
OS=$(uname)
if [ "$OS" = "Darwin" ]; then
    brew install python@3.11 pipx fzf espanso || true
else
    sudo apt-get update && sudo apt-get install -y python3-pip pipx fzf espanso || true
fi
pipx install --force --pip-args "--upgrade pip" "$(dirname "$0")/.."
mkdir -p ~/.config/espanso/match
cat > ~/.config/espanso/match/promptpilot.yml <<'YML'
matches:
  - trigger: ';pp'
    run: promptpilot
YML
printf 'Installed PromptPilot. Trigger with ;pp\n'
