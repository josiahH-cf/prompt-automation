<#
.SYNOPSIS
Installs the prompt-automation application using pipx.
.DESCRIPTION
This script installs prompt-automation from the local project and verifies that
all components are available.
#>

. "$PSScriptRoot/utils.ps1"

if (-not (Test-ExecutionPolicy)) { Fail "Cannot proceed due to execution policy restrictions." }

$LogDir = Join-Path $env:USERPROFILE '.prompt-automation\logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir 'install-app.log'
Start-Transcript -Path $LogFile -Append | Out-Null
trap { Write-Warning "Error on line $($_.InvocationInfo.ScriptLineNumber). See $LogFile" }

Info "Installing prompt-automation..."

if (-not [System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::Windows)) {
    Fail "This installer must be run on Windows."
}

# Ensure pipx command
$global:pipxCommand = $null
$pipxCmd = Get-Command pipx -ErrorAction SilentlyContinue
if ($pipxCmd) { $global:pipxCommand = 'pipx' } else { $global:pipxCommand = 'python -m pipx' }

# Get project root
$scriptDir = $PSScriptRoot
$projectRoot = Split-Path -Parent $scriptDir

# Handle WSL path issues
if ($projectRoot -like "\\wsl.localhost\*") {
    Write-Warning "Detected installation from WSL path in Windows environment"
    Info "Copying project to Windows temp directory for installation..."
    
    $tempProjectDir = Join-Path $env:TEMP "prompt-automation-install"
    if (Test-Path $tempProjectDir) {
        Remove-Item $tempProjectDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $tempProjectDir -Force | Out-Null
    
    # Copy essential files
    $filesToCopy = @('pyproject.toml', 'README.md', 'LICENSE', 'src', 'prompts', 'MANIFEST.in')
    foreach ($file in $filesToCopy) {
        $sourcePath = Join-Path $projectRoot $file
        $destPath = Join-Path $tempProjectDir $file
        if (Test-Path $sourcePath) {
            if ((Get-Item $sourcePath).PSIsContainer) {
                Copy-Item -Path $sourcePath -Destination $destPath -Recurse -Force
            } else {
                Copy-Item -Path $sourcePath -Destination $destPath -Force
            }
        }
    }
    $projectRoot = $tempProjectDir
}

$pyprojectPath = Join-Path $projectRoot 'pyproject.toml'
if (-not (Test-Path $pyprojectPath)) { Fail "pyproject.toml not found at $pyprojectPath" }

if ($global:pipxCommand -eq 'python -m pipx') {
    python -m pipx install --force "$projectRoot"
} else {
    & $global:pipxCommand install --force "$projectRoot"
}
if ($LASTEXITCODE -ne 0) { Fail 'Failed to install prompt-automation from local source.' }

# Clean up temp directory if used
if ($projectRoot -like "*temp*prompt-automation-install*") {
    try {
        Remove-Item $projectRoot -Recurse -Force -ErrorAction SilentlyContinue
        Debug "Cleaned up temporary installation directory"
    } catch {
        Debug "Could not clean up temp directory: $_"
    }
}

# Verify command
$promptAutomationCmd = Get-Command prompt-automation -ErrorAction SilentlyContinue
if ($promptAutomationCmd) {
    Info "[OK] prompt-automation command is available"
    try { 
        # Test with help instead of version since --version isn't supported
        $help = & prompt-automation --help 2>&1 | Select-Object -First 1
        if ($help) { Info "   Command working: Help available" }
        # Reset exit code after help command
        $global:LASTEXITCODE = 0
    } catch { 
        Debug "Could not get help: $($_.Exception.Message)"
        # Reset exit code after failed help command
        $global:LASTEXITCODE = 0
    }
} else {
    Write-Warning 'prompt-automation command not found in PATH. You may need to restart your terminal.'
}

# Display summary
Info "`n=== Installation Summary ==="
Show-ComponentStatus -ComponentName 'Python'
Show-ComponentStatus -ComponentName 'pipx'
Show-ComponentStatus -ComponentName 'fzf'
Show-ComponentStatus -ComponentName 'espanso'
Show-ComponentStatus -ComponentName 'AutoHotkey'
Show-ComponentStatus -ComponentName 'prompt-automation'

Stop-Transcript | Out-Null
Info "Installation complete. Log saved to $LogFile"

# Explicitly set success exit code
exit 0
