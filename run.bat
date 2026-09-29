@echo off
REM OSINT Finder — Windows launcher.
REM Usage: run.bat
REM Automatically runs install.bat first if the virtual environment is missing.

setlocal

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

set VENV_DIR=.venv

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo Virtual environment not found. Running install.bat first...
    call install.bat
    if %ERRORLEVEL% NEQ 0 (
        echo Installation failed. See errors above.
        exit /b 1
    )
)

echo Launching OSINT Finder...
"%VENV_DIR%\Scripts\python.exe" main.py

endlocal
