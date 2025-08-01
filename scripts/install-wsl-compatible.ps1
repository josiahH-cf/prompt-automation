<#
.SYNOPSIS
Alternative installer that avoids WSL/Windows path issues
.DESCRIPTION
This script installs prompt-automation from PyPI or Git instead of local WSL files
#>

. "$PSScriptRoot/utils.ps1"

if (-not (Test-ExecutionPolicy)) { Fail "Cannot proceed due to execution policy restrictions." }

Info "Starting prompt-automation installation (WSL-compatible method)..."

# Install dependencies first (Python, pipx, etc.)
$depScript = Join-Path $PSScriptRoot 'install-dependencies.ps1'
if (Test-Path $depScript) {
    Info "Installing dependencies first..."
    & $depScript
    if ($LASTEXITCODE -ne 0) {
        Fail "Dependency installation failed"
    }
} else {
    Write-Warning "Dependencies script not found. Make sure Python and pipx are installed."
}

# Now install prompt-automation using a WSL-compatible method
Info "Installing prompt-automation using Git repository method..."

try {
    # First check if we have git
    $gitCmd = Get-Command git -ErrorAction SilentlyContinue
    if (-not $gitCmd) {
        Info "Git not found. Installing git..."
        if (-not (Install-WingetPackage -PackageId 'Git.Git' -PackageName 'Git')) {
            Write-Warning "Could not install Git. Trying alternative method..."
        } else {
            Refresh-PathEnvironment
        }
    }
    
    # Method 1: Try installing from current directory (if it works)
    $currentDir = Get-Location
    Info "Attempting installation from current directory: $currentDir"
    
    $installOutput = & pipx install --force . 2>&1
    Debug "pipx install output: $installOutput"
    
    if ($LASTEXITCODE -eq 0) {
        Info "[OK] prompt-automation installed successfully from current directory"
    } else {
        Info "Current directory installation failed. Trying alternative methods..."
        
        # Method 2: Install from a Git URL (if this is a git repo)
        try {
            $gitRemote = & git remote get-url origin 2>$null
            if ($gitRemote) {
                Info "Found git remote: $gitRemote"
                Info "Installing from Git repository..."
                $installOutput = & pipx install --force "git+$gitRemote" 2>&1
                Debug "Git install output: $installOutput"
                
                if ($LASTEXITCODE -eq 0) {
                    Info "[OK] prompt-automation installed from Git repository"
                } else {
                    throw "Git installation also failed"
                }
            } else {
                throw "No git remote found"
            }
        } catch {
            Info "Git method failed: $_"
            
            # Method 3: Create a setup.py installation in temp directory
            Info "Trying setup.py installation method..."
            
            $tempDir = Join-Path $env:TEMP "prompt-automation-setup"
            if (Test-Path $tempDir) {
                Remove-Item $tempDir -Recurse -Force
            }
            New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
            
            # Create a minimal setup.py
            $setupPy = @"
from setuptools import setup, find_packages

# Read requirements from pyproject.toml if available
try:
    import tomli
    with open('pyproject.toml', 'rb') as f:
        pyproject = tomli.load(f)
    dependencies = pyproject.get('project', {}).get('dependencies', [])
except:
    dependencies = [
        'click',
        'rich', 
        'pyyaml',
        'jinja2'
    ]

setup(
    name='prompt-automation',
    version='1.0.0',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=dependencies,
    entry_points={
        'console_scripts': [
            'prompt-automation=prompt_automation.cli:main'
        ]
    }
)
"@
            
            $setupPyPath = Join-Path $tempDir 'setup.py'
            Set-Content -Path $setupPyPath -Value $setupPy
            
            # Copy source files
            $sourceDir = Join-Path (Split-Path -Parent $PSCommandPath) '..\src'
            if (Test-Path $sourceDir) {
                Copy-Item -Path $sourceDir -Destination $tempDir -Recurse -Force
                Info "Copied source files to temp directory"
                
                Push-Location $tempDir
                try {
                    $installOutput = & pipx install --force . 2>&1 
                    Debug "Setup.py install output: $installOutput"
                    
                    if ($LASTEXITCODE -eq 0) {
                        Info "[OK] prompt-automation installed using setup.py method"
                    } else {
                        throw "Setup.py installation failed"
                    }
                } finally {
                    Pop-Location
                    Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue
                }
            } else {
                throw "Source directory not found"
            }
        }
    }
    
    # Test the installation
    Refresh-PathEnvironment
    Start-Sleep -Seconds 2
    
    $testCmd = Get-Command prompt-automation -ErrorAction SilentlyContinue
    if ($testCmd) {
        $version = & prompt-automation --version 2>&1
        Info "[OK] Installation successful! Version: $version"
        Info "Location: $($testCmd.Source)"
    } else {
        Write-Warning "Installation completed but command not found in PATH"
        Write-Warning "You may need to restart your terminal or run the fix-path.ps1 script"
    }
    
} catch {
    Write-Warning "Installation failed: $_"
    Write-Warning "You may need to install manually or check the installation logs"
}

Info "Installation process completed."
