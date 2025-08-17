# Installation Troubleshooting Guide

(Relocated from project root)

This guide addresses common installation issues, particularly with Python installation and PATH configuration.

## Recent Improvements (Latest Update)

The installation scripts have been significantly improved to handle several common issues:

### Key Fixes Applied

1. **Force Python Detection**: Even when winget reports failure (exit code -1978335212), the installer now:
   - Searches comprehensively for Python installations
   - Automatically configures PATH for found installations
   - Uses Python aliases when PATH updates don't work immediately

2. **Enhanced Python Search**: Comprehensive search across:
   - `%LOCALAPPDATA%\Programs\Python\Python31X\`
   - `%ProgramFiles%\Python31X\`
   - `%ProgramFiles(x86)%\Python31X\`
   - Windows Store Python locations
   - Dynamic directory discovery

3. **Robust pipx Installation**: 
   - Handles cases where Python is available but not in PATH
   - Falls back to `python -m pipx` when pipx command isn't available
   - More resilient PATH configuration for Python Scripts directories

4. **AutoHotkey Detection**: Fixed issue where AutoHotkey was installed successfully but reported as failed

5. **Graceful Degradation**: Installation continues when Python is available, even if pipx has issues

### What The New Installation Flow Does

1. **Python Installation**:
   - Attempts winget installation
   - **Regardless of winget result**: Searches for Python installations
   - Configures PATH automatically for found installations  
   - Creates aliases when PATH updates don't work immediately
   - Only fails if absolutely no Python is found

2. **pipx Installation**:
   - Skips gracefully if Python isn't available
   - Uses multiple path detection methods
   - Falls back to `python -m pipx` when needed
   - Continues installation even if pipx isn't perfectly configured

3. **Dependency Checking**:
   - Accepts `python -m pipx` as equivalent to `pipx` command
   - Allows installation to continue with Python-only when pipx has issues
   - Provides better error messages and guidance

## Common Error Messages and Solutions

### "Python installation returned exit code -1978335212"
**Status**: This is now handled automatically
- The installer will search for Python installations despite this error
- If Python is found, installation continues normally
- This error often means Python was actually installed successfully

### "pipx still not available after installation"
**Status**: This is now handled automatically
- The installer will use `python -m pipx` as a fallback
- Installation continues with Python available
- You can manually run `python -m pipx ensurepath` after installation

### "AutoHotkey installation may have failed"
**Status**: This warning should no longer appear
- The installer now properly detects AutoHotkey installations
- Checks both PATH and common installation directories
- Provides accurate status reporting

### "Critical dependencies are missing"
### "Unable to parse package spec: C:\\Users\\<User>\\AppData\\Local\\Temp\\prompt-automation-install"

**Cause**: The original install used a temporary directory path (e.g. `%TEMP%\prompt-automation-install`) which was removed after installation. `pipx` stores that exact path as the package spec. When upgrading later it attempts to re‑interpret the path and fails.

**Current versions (>= 0.2.1+)**: The internal auto-updater now catches this message and force-reinstalls from PyPI (`pipx install --force prompt-automation`) to normalize the spec. Nothing extra needed unless you disabled the fallback.

**Fix (manual)**:
```powershell
pipx uninstall prompt-automation
pipx install prompt-automation
```
or if uninstall is blocked:
```powershell
pipx install --force prompt-automation
```

**Alternative (dev workflow)**: Install from a *stable* local folder (not `%TEMP%`) you keep around, or build a wheel:
```powershell
python -m build
pipx install dist\prompt_automation-<version>-py3-none-any.whl
```

**Disable automatic fallback** (diagnostics / reproducibility):
```powershell
$env:PROMPT_AUTOMATION_DISABLE_PIPX_FALLBACK = '1'
```
Re-run the app, then reproduce the upgrade error intentionally.

**Last resort (not recommended)**: Edit `%USERPROFILE%\pipx\venvs\prompt-automation\pipx_metadata.json` changing `package_or_url` to `"prompt-automation"`, then run `pipx upgrade prompt-automation`. Make a backup first.

**Status**: Much more lenient now
- Only fails if Python is completely unavailable
- Allows continuation with Python-only setup
- Provides clear guidance for manual fixes

## Manual Troubleshooting Steps

### If Installation Still Completely Fails

1. **Run as Administrator**: Some installations require elevated permissions
   ```powershell
   # Right-click PowerShell and "Run as Administrator"
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
   .\install.ps1
   ```

2. **Check for Microsoft Store Python Conflicts**:
   ```powershell
   # Remove Windows Store Python if causing issues
   Get-AppxPackage *python* | Remove-AppxPackage
   ```

3. **Manual Python Installation**:
   - Download from [python.org](https://python.org/downloads/)
   - **Critical**: Check "Add Python to PATH" during installation
   - Choose "Add Python to environment variables"

4. **Verify Installation**:
   ```powershell
   python --version
   python -m pip --version
   python -m pipx --version
   ```

### If PATH Issues Persist

1. **Restart Terminal**: Always try this first after installation

2. **Manual PATH Update**:
   ```powershell
   # Find your Python installation
   where.exe python
   
   # If not found, search manually
   Get-ChildItem -Path $env:LOCALAPPDATA -Recurse -Name "python.exe" -ErrorAction SilentlyContinue
   
   # Add to current session (replace path with your actual Python path)
   $env:PATH = "C:\Users\YourName\AppData\Local\Programs\Python\Python312;$env:PATH"
   $env:PATH = "C:\Users\YourName\AppData\Local\Programs\Python\Python312\Scripts;$env:PATH"
   ```

3. **Permanent PATH Fix**:
   - Windows Settings → System → About → Advanced system settings
   - Environment Variables → Edit User PATH
   - Add Python and Scripts directories

## Testing Your Installation

```powershell
# Test core components
python --version
python -m pip --version

# Test pipx (try both methods)
pipx --version
python -m pipx --version

# Test other tools
fzf --version
espanso --version

# Test the main application (after successful installation)
prompt-automation --version
```

## Advanced Troubleshooting

### Enable Debug Mode
Add debug output to see exactly what's happening:
```powershell
$DebugPreference = 'Continue'
.\install.ps1
```

### Check Installation Logs
Detailed logs are saved to:
- `%USERPROFILE%\.prompt-automation\logs\install.log`
- `%USERPROFILE%\.prompt-automation\logs\install-deps.log`

### Force Specific Python Version
If you have multiple Python versions:
```powershell
# Set specific Python for this session
Set-Alias python "C:\Users\YourName\AppData\Local\Programs\Python\Python312\python.exe"
.\install.ps1
```

## What's Different Now

- ✅ **Forced Installation**: Aggressively attempts to make installations work
- ✅ **Better Error Recovery**: Continues with partial success rather than complete failure  
- ✅ **Smarter Detection**: Finds installations even when they're not in PATH
- ✅ **Alternative Methods**: Falls back to module execution (`python -m pipx`)
- ✅ **Comprehensive Search**: Looks in all common installation locations
- ✅ **Automatic Configuration**: Sets up PATH and aliases automatically
- ✅ **Graceful Degradation**: Works with Python-only when pipx has issues

The installer should now work in many more scenarios and provide much better guidance when manual intervention is needed.

## Tkinter Missing

If you receive an error about Tkinter or the GUI not launching:

- **Debian/Ubuntu**: Install with `sudo apt install python3-tk` and rerun the installer.
- **Windows/macOS**: Reinstall Python using the official installer from [python.org](https://python.org/downloads/) to ensure Tkinter is included.
