# Install Python 3.11, pipx, fzf, espanso and PromptPilot
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { Write-Host "Python 3.11 required"; exit }
if (-not (Get-Command pipx -ErrorAction SilentlyContinue)) { python -m pip install --user pipx; pipx ensurepath }
if (-not (Get-Command fzf -ErrorAction SilentlyContinue)) { Write-Host "Install fzf from GitHub" }
if (-not (Get-Command espanso -ErrorAction SilentlyContinue)) { Write-Host "Install espanso from GitHub" }
pipx install --force promptpilot
