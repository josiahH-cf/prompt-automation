# Install Python 3.11, pipx, fzf, espanso and prompt-automation
Write-Host "Step 1/6: Checking Python 3.11 ..."
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    winget install -e --id Python.Python.3.11
}
Write-Host "Step 2/6: Installing pipx ..."
if (-not (Get-Command pipx -ErrorAction SilentlyContinue)) {
    python -m pip install --user pipx
    pipx ensurepath
}
Write-Host "Step 3/6: Installing fzf ..."
if (-not (Get-Command fzf -ErrorAction SilentlyContinue)) {
    winget install -e --id Git.Fzf
}
Write-Host "Step 4/6: Installing espanso ..."
if (-not (Get-Command espanso -ErrorAction SilentlyContinue)) {
    winget install -e --id Espanso.Espanso
}
Write-Host "Step 5/6: Installing prompt-automation ..."
pipx install --force prompt-automation
Write-Host "Step 6/6: Opening README ..."
Start-Process README.md
