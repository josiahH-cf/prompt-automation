<#
.SYNOPSIS
Alternative installer for prompt-automation that bypasses pipx.
.DESCRIPTION
This script installs prompt-automation using pip directly when pipx has issues.
Use this if the main installer fails due to pipx permission problems.
#>

. "$PSScriptRoot/utils.ps1"

if (-not (Test-ExecutionPolicy)) { Fail "Cannot proceed due to execution policy restrictions." }

$LogDir = Join-Path $env:USERPROFILE '.prompt-automation\logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir 'install-alternative.log'
Start-Transcript -Path $LogFile -Append | Out-Null
trap { Write-Warning "Error on line $($_.InvocationInfo.ScriptLineNumber). See $LogFile" }

Info "Installing prompt-automation using alternative method (pip)..."

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Warning "Not running as administrator. If you encounter permission errors, try running as administrator."
}

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

# Uninstall any existing installation
Info "Removing any existing installation..."
try {
    & python -m pip uninstall prompt-automation -y 2>&1 | Out-Null
    Info "Existing installation removed"
} catch {
    Info "No existing installation found"
}

# Install with pip
Info "Installing prompt-automation with pip..."
try {
    & python -m pip install --user --force-reinstall "$projectRoot"
    if ($LASTEXITCODE -eq 0) {
        Info "Installation successful"
    } else {
        Fail "pip installation failed"
    }
} catch {
    Fail "pip installation failed: $($_.Exception.Message)"
}

# Clean up temp directory if used
if ($projectRoot -like "*temp*prompt-automation-install*") {
    try {
        Remove-Item $projectRoot -Recurse -Force -ErrorAction SilentlyContinue
        Debug "Cleaned up temporary installation directory"
    } catch {
        Debug "Could not clean up temp directory: $_"
    }
}

# Verify installation
Info "Verifying installation..."
try {
    & python -c "import prompt_automation; print('✓ Module import successful')"
    if ($LASTEXITCODE -eq 0) {
        Info "[OK] prompt-automation module is available"
        
        # Test help
        try {
            $help = & python -m prompt_automation --help 2>&1 | Select-Object -First 1
            if ($help) { Info "   Command working: Help available" }
            # Reset exit code after help command
            $global:LASTEXITCODE = 0
        } catch {
            Debug "Could not get help: $($_.Exception.Message)"
            # Reset exit code after failed help command
            $global:LASTEXITCODE = 0
        }
    } else {
        Fail "Module verification failed"
    }
} catch {
    Fail "Module verification failed: $($_.Exception.Message)"
}

# Create a simple launcher script
$launcherDir = Join-Path $env:USERPROFILE '.prompt-automation'
New-Item -ItemType Directory -Force -Path $launcherDir | Out-Null
$launcherScript = Join-Path $launcherDir 'launch.cmd'

$launcherContent = @"
@echo off
python -m prompt_automation %*
"@

Set-Content -Path $launcherScript -Value $launcherContent
Info "Created launcher script at: $launcherScript"

Info "`n=== Alternative Installation Complete ==="
Info "Since pipx was bypassed, use one of these methods to run prompt-automation:"
Info "1. python -m prompt_automation --gui"
Info "2. Use the launcher: $launcherScript --gui"
Info ""
Info "To add to PATH permanently, add this directory to your PATH:"
Info "   $launcherDir"

Stop-Transcript | Out-Null
Info "Installation log saved to $LogFile"

# Explicitly set success exit code
exit 0
