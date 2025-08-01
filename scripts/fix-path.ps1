<#
.SYNOPSIS
Fixes PATH issues for prompt-automation command
.DESCRIPTION
This script helps diagnose and fix PATH issues that prevent the prompt-automation command from being found.
#>

. "$PSScriptRoot/utils.ps1"

Info "Diagnosing prompt-automation PATH issues..."

# Check if command is available
$cmd = Get-Command prompt-automation -ErrorAction SilentlyContinue
if ($cmd) {
    Info "[OK] prompt-automation is already available in PATH"
    Info "Location: $($cmd.Source)"
    try {
        # Try --version first, then --help if that fails
        $version = & prompt-automation --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            # --version not supported, try --help or just basic execution
            $helpOutput = & prompt-automation --help 2>&1
            if ($LASTEXITCODE -eq 0) {
                Info "Command is working (--version not supported, but --help works)"
                # Extract version from help output if available
                $versionMatch = $helpOutput | Select-String -Pattern "version|v\d+\.\d+" | Select-Object -First 1
                if ($versionMatch) {
                    Info "Version info: $($versionMatch.Line.Trim())"
                }
            } else {
                # Try just running the command without arguments
                $basicOutput = & prompt-automation 2>&1
                if ($basicOutput -match "usage:" -or $basicOutput -match "error:") {
                    Info "Command is working (shows usage/error message as expected)"
                } else {
                    Write-Warning "Command found but may have execution issues"
                }
            }
        } else {
            Info "Version: $version"
        }
    } catch {
        Write-Warning "Command found but failed to execute: $_"
    }
    exit 0
}

Info "prompt-automation not found in PATH. Searching for it..."

# Search for the executable
$searchPaths = @(
    "${env:APPDATA}\Python\Python312\Scripts",
    "${env:LOCALAPPDATA}\Programs\Python\Python312\Scripts", 
    "${env:USERPROFILE}\.local\bin",
    "${env:USERPROFILE}\.local\Scripts"
)

# Also get pipx bin directory
try {
    $pipxBinDir = & pipx environment --value PIPX_BIN_DIR 2>$null
    if ($pipxBinDir) {
        $searchPaths += $pipxBinDir
    }
} catch {
    # Fallback to default pipx location
    $searchPaths += "${env:USERPROFILE}\.local\bin"
}

$foundPath = $null
$executablePath = $null

foreach ($path in $searchPaths) {
    $promptCmd = Join-Path $path 'prompt-automation.exe'
    if (Test-Path $promptCmd) {
        Info "Found prompt-automation at: $promptCmd"
        $foundPath = $path
        $executablePath = $promptCmd
        
        # Test if it works
        try {
            # Try --version first, then --help if that fails
            $testVersion = & "$promptCmd" --version 2>&1
            if ($LASTEXITCODE -ne 0) {
                # --version not supported, try --help
                $testHelp = & "$promptCmd" --help 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Info "Executable works (--help successful)"
                } else {
                    # Try basic execution
                    $testBasic = & "$promptCmd" 2>&1
                    if ($testBasic -match "usage:" -or $testBasic -match "error:") {
                        Info "Executable works (shows usage as expected)"
                    } else {
                        Write-Warning "Found executable but it may have issues: $testBasic"
                    }
                }
            } else {
                Info "Executable works: $testVersion"
            }
        } catch {
            Write-Warning "Found executable but it failed to run: $_"
        }
        break
    }
}

if (-not $foundPath) {
    Write-Warning "Could not find prompt-automation.exe in common locations"
    Write-Warning "Searching entire user profile..."
    
    $found = Get-ChildItem -Path $env:USERPROFILE -Recurse -Name 'prompt-automation.exe' -ErrorAction SilentlyContinue | Select-Object -First 5
    if ($found) {
        foreach ($file in $found) {
            $fullPath = Join-Path $env:USERPROFILE $file
            Info "Found: $fullPath"
        }
    } else {
        Fail "prompt-automation.exe not found anywhere. Try reinstalling with: pipx install ."
    }
    exit 1
}

# If we found it, offer to fix the PATH
Info ""
Info "Found prompt-automation at: $executablePath"
Info "The directory $foundPath needs to be in your PATH"

# Check if it's already in PATH
if ($env:PATH -like "*$foundPath*") {
    Info "The directory is already in your PATH, but Windows might need to be refreshed"
    Info "Try restarting your terminal or running: refreshenv"
} else {
    Info "The directory is NOT in your PATH"
    
    $response = Read-Host "Would you like to add $foundPath to your user PATH permanently? (y/n)"
    if ($response -eq 'y' -or $response -eq 'Y' -or $response -eq 'yes') {
        try {
            # Get current user PATH
            $currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
            if ($currentPath -notlike "*$foundPath*") {
                $newPath = "$currentPath;$foundPath"
                [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
                Info "[OK] Added $foundPath to your user PATH"
                Info "You may need to restart your terminal for this to take effect"
                
                # Also update current session
                $env:PATH += ";$foundPath"
                Info "Also updated PATH for current session"
                
                # Test again
                $testCmd = Get-Command prompt-automation -ErrorAction SilentlyContinue
                if ($testCmd) {
                    Info "[OK] prompt-automation is now available!"
                    # Test with --help instead of --version since --version isn't supported
                    $helpTest = & prompt-automation --help 2>&1
                    if ($LASTEXITCODE -eq 0) {
                        Info "Command test successful!"
                    } else {
                        Info "Command is available but --help test failed (this may be normal)"
                    }
                } else {
                    Write-Warning "Added to PATH but command still not found. Try restarting your terminal."
                }
            } else {
                Info "Directory was already in user PATH"
            }
        } catch {
            Write-Warning "Failed to update PATH: $_"
            Info "You can manually add $foundPath to your PATH through Windows settings"
        }
    } else {
        Info "To temporarily add to PATH for this session, run:"
        Info "`$env:PATH += ';$foundPath'"
        Info ""
        Info "To permanently add through Windows UI:"
        Info "1. Open Settings > System > About > Advanced system settings"
        Info "2. Click Environment Variables"
        Info "3. Under User variables, select PATH and click Edit"
        Info "4. Click New and add: $foundPath"
    }
}
