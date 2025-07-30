# Install PromptPilot - Windows
$ErrorActionPreference = 'Stop'
if (-not (Get-Command pipx -ErrorAction SilentlyContinue)) {
    winget install --id Python.Python.3.11 -e
    python -m pip install --user pipx
    $env:PATH += ';$env:USERPROFILE\\.local\\bin'
}
if (-not (Get-Command fzf.exe -ErrorAction SilentlyContinue)) {
    winget install --id junegunn.fzf -e
}
if (-not (Get-Command espanso -ErrorAction SilentlyContinue)) {
    winget install --id espanso.espanso -e
}
pipx install "$PSScriptRoot\.." --force
$snippetDir = "$env:APPDATA\espanso\match"; mkdir $snippetDir -ea 0
"matches:\n  - trigger: ';pp'\n    run: promptpilot" | Out-File -Encoding utf8 "$snippetDir\promptpilot.yml"
Write-Host 'Installed PromptPilot. Use ;pp to launch.'
