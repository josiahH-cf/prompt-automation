# Python Installation Issues - Quick Fix Guide

(Relocated from project root)

## Before Running the Installer Again

**First, run the diagnostic tool to identify your Python installations:**

```powershell
cd scripts
.\diagnose-python.ps1
```

This will show you:
- All Python installations found on your system
- Which ones are working
- PATH issues
- Recommendations for fixes

## Common Fixes Based on Your Error

### Issue 1: AutoHotkey Installation Error (-1978335189)

This error usually means:
- UAC permission dialog was cancelled
- AutoHotkey is already installed but not detected
- Needs elevated permissions

**Quick Fix:**
```powershell
# Run PowerShell as Administrator
# Right-click PowerShell and select "Run as Administrator"
.\install.ps1
```

### Issue 2: Python Not Detected Despite Being Installed

This happens when:
- Multiple Python versions are installed
- Windows Store Python is interfering with regular Python
- Python is installed but not in PATH

**Quick Fixes:**

1. **Find and set your Python manually:**
   ```powershell
   # Run the diagnostic first
   .\diagnose-python.ps1
   
   # If it shows a working Python, set an alias:
   Set-Alias python "C:\path\to\your\python.exe"
   
   # Then run the installer
   .\install.ps1
   ```

2. **Check for Windows Store Python conflict:**
   ```powershell
   # Remove Windows Store Python if causing issues
   Get-AppxPackage *python* | Remove-AppxPackage
   ```

3. **Use Python Launcher if available:**
   ```powershell
   # Test if Python Launcher works
   py --version
   
   # If it works, you can use 'py' instead of 'python'
   # The installer will detect this automatically
   ```

## Updated Installation Features

The installer now:
- ✅ **Tests multiple Python commands** (`python`, `python3`, `py`)
- ✅ **Searches comprehensively** for Python installations
- ✅ **Handles Windows Store Python** properly
- ✅ **Forces AutoHotkey detection** even with permission errors
- ✅ **Provides detailed diagnostics** when things fail
- ✅ **Creates aliases automatically** when PATH issues exist

## Step-by-Step Troubleshooting

1. **Run diagnostics:**
   ```powershell
   .\diagnose-python.ps1
   ```

2. **If Python is found but not working:**
   - Note the path shown in diagnostics
   - Set a manual alias: `Set-Alias python "C:\full\path\to\python.exe"`
   - Run installer: `.\install.ps1`

3. **If no Python is found:**
   - Install from [python.org](https://python.org/downloads/)
   - **Check "Add Python to PATH" during installation**
   - Or install from Microsoft Store: "Python 3.12"

4. **If AutoHotkey fails:**
   - Run PowerShell as Administrator
   - Or install AutoHotkey manually from [autohotkey.com](https://autohotkey.com)

5. **Run the installer:**
   ```powershell
   .\install.ps1
   ```

## Still Having Issues?

Check the installation logs:
- `%USERPROFILE%\.prompt-automation\logs\install.log`
- `%USERPROFILE%\.prompt-automation\logs\install-deps.log`

The logs will contain detailed debug information about what the installer found and tried.
