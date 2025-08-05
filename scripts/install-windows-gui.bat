@echo off
REM Windows GUI Installation for prompt-automation
REM This batch file handles the PowerShell execution policy and runs the installation

echo Starting prompt-automation Windows GUI installation...
echo.

REM Check if we're running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running as Administrator - good!
) else (
    echo Warning: Not running as Administrator. Some operations may fail.
    echo If you encounter permission errors, please run as Administrator.
    echo.
)

REM Set execution policy for current session
echo Setting PowerShell execution policy...
powershell -Command "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force"

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"

REM Run the PowerShell installation script
echo Running installation script...
powershell -ExecutionPolicy RemoteSigned -File "%SCRIPT_DIR%install-windows-gui.ps1"

REM Check the exit code
if %errorLevel% == 0 (
    echo.
    echo ===================================
    echo Installation completed successfully!
    echo ===================================
    echo.
    echo You can now use:
    echo   prompt-automation --gui
    echo   prompt-automation --terminal
    echo   prompt-automation --assign-hotkey
    echo.
) else (
    echo.
    echo =============================
    echo Installation failed!
    echo =============================
    echo Check the log files in %USERPROFILE%\.prompt-automation\logs\
    echo.
)

pause
