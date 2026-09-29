@echo off
REM OSINT Finder — Windows installer.
REM Usage: install.bat

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

set VENV_DIR=.venv
set REQUIREMENTS_FILE=requirements.txt

echo OSINT Finder - Windows setup
echo -----------------------------

REM Detect Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Python was not found. Install Python 3.10+ from https://www.python.org/downloads/
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VERSION=%%v
echo Python %PY_VERSION% detected

REM Create virtual environment if missing
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv "%VENV_DIR%"
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to create virtual environment.
        exit /b 1
    )
) else (
    echo Virtual environment already exists
)

set VENV_PYTHON=%VENV_DIR%\Scripts\python.exe
set VENV_PIP=%VENV_DIR%\Scripts\pip.exe

echo Upgrading pip...
"%VENV_PYTHON%" -m pip install --upgrade pip --quiet
if %ERRORLEVEL% NEQ 0 (
    echo Failed to upgrade pip. Check your internet connection.
    exit /b 1
)

echo Installing dependencies...
"%VENV_PIP%" install -r "%REQUIREMENTS_FILE%" --quiet
if %ERRORLEVEL% NEQ 0 (
    echo Failed to install dependencies. Check your internet connection.
    exit /b 1
)

echo Verifying installation...
"%VENV_PYTHON%" -c "import PySide6, maigret, httpx, PIL"
if %ERRORLEVEL% NEQ 0 (
    echo Dependency verification failed. Try deleting the .venv folder and re-running install.bat.
    exit /b 1
)

echo Running diagnostics...
"%VENV_PYTHON%" scripts\bootstrap.py --diagnose

echo.
echo Setup complete. Run the app with: run.bat
endlocal
