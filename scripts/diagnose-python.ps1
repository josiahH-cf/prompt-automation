<#
.SYNOPSIS
Diagnostic script to identify Python installations on Windows.
.DESCRIPTION
This script helps identify multiple Python installations, version conflicts,
and PATH issues that might be preventing the installer from finding Python.
#>

. "$PSScriptRoot/../install/utils.ps1"

Write-Host "Python Installation Diagnostic Tool" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green
Write-Host ""

# Show detailed Python diagnostics
Show-PythonDiagnostics

Write-Host ""
Write-Host "Additional System Information:" -ForegroundColor Yellow
Write-Host "Operating System: $((Get-CimInstance Win32_OperatingSystem).Caption)"
Write-Host "PowerShell Version: $($PSVersionTable.PSVersion)"
Write-Host "Execution Policy: $(Get-ExecutionPolicy)"
Write-Host ""

# Check for Python Launcher
Write-Host "Python Launcher Information:" -ForegroundColor Yellow
try {
    $pyList = & py -0 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Available Python versions via Python Launcher:"
        $pyList | ForEach-Object { Write-Host "  $_" }
    } else {
        Write-Host "Python Launcher not available or no versions found"
    }
} catch {
    Write-Host "Python Launcher test failed: $_"
}

Write-Host ""

# Show environment variables
Write-Host "Relevant Environment Variables:" -ForegroundColor Yellow
$envVars = @('PATH', 'PYTHONPATH', 'PYTHONHOME', 'PY_PYTHON', 'PY_PYTHON3')
foreach ($var in $envVars) {
    $value = [System.Environment]::GetEnvironmentVariable($var)
    if ($value) {
        Write-Host "$var = $value"
    } else {
        Write-Host "$var = (not set)"
    }
}

Write-Host ""

# Test manual installation paths
Write-Host "Manual Python Installation Test:" -ForegroundColor Yellow
Write-Host "You can try running Python directly from these paths if they exist:"

$testPaths = @(
    "${env:LOCALAPPDATA}\Programs\Python\Python312\python.exe",
    "${env:LOCALAPPDATA}\Programs\Python\Python311\python.exe", 
    "${env:ProgramFiles}\Python312\python.exe",
    "${env:ProgramFiles}\Python311\python.exe",
    "${env:APPDATA}\Python\Python312\Scripts\python.exe",
    "C:\Python312\python.exe",
    "C:\Python311\python.exe"
)

foreach ($path in $testPaths) {
    if (Test-Path $path) {
        try {
            $version = & "$path" --version 2>&1
            Write-Host "[WORKING] $path - $version" -ForegroundColor Green
            Write-Host "  To use this Python, run: Set-Alias python '$path'"
        } catch {
            Write-Host "[FOUND BUT NOT WORKING] $path - $_" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "Recommendations:" -ForegroundColor Green
Write-Host "1. If you see a [WORKING] Python above, you can manually set it:"
Write-Host "   Set-Alias python 'C:\path\to\your\python.exe'"
Write-Host "   Then run the installer again"
Write-Host ""
Write-Host "2. If no working Python is found, install from:"
Write-Host "   - https://python.org/downloads/ (check 'Add to PATH')"
Write-Host "   - Microsoft Store: 'Python 3.12'"
Write-Host ""
Write-Host "3. If Python is installed but not working, try:"
Write-Host "   - Restart your terminal as Administrator"
Write-Host "   - Reinstall Python with 'Add to PATH' checked"
Write-Host "   - Remove Microsoft Store Python if it conflicts"
