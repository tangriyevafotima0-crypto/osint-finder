#!/usr/bin/env bash
# OSINT Finder — macOS launcher.
#
# Usage:
#   chmod +x run.sh
#   ./run.sh
#
# Idempotent: safe to run repeatedly. Only does the work that's actually
# needed (won't recreate an existing venv, won't reinstall everything if
# dependencies are already present).

set -u  # (intentionally not `set -e` — we want to report failures ourselves)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR=".venv"
REQUIREMENTS_FILE="requirements.txt"

fail() {
    local what="$1"
    local cmd="$2"
    local reason="$3"
    local fix="$4"
    echo ""
    echo "❌ Setup failed: ${what}"
    echo "   Command:  ${cmd}"
    echo "   Reason:   ${reason}"
    echo "   Try:      ${fix}"
    echo ""
    exit 1
}

echo "OSINT Finder — environment setup"
echo "---------------------------------"

# 1. Detect macOS ------------------------------------------------------
OS_NAME="$(uname -s)"
if [ "$OS_NAME" != "Darwin" ]; then
    echo "⚠️  This script targets macOS. Detected: ${OS_NAME}."
    echo "   Continuing anyway, but some features may not work as expected."
fi

# 2. Detect Python -------------------------------------------------------
PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
fi

if [ -z "$PYTHON_BIN" ]; then
    echo "❌ Python was not found on this system."
    if command -v brew >/dev/null 2>&1; then
        echo "   Homebrew is available. You can install Python with:"
        echo "     brew install python@3.12"
    else
        echo "   Homebrew was not found either."
        echo "   Install Python from https://www.python.org/downloads/macos/"
        echo "   or install Homebrew first from https://brew.sh"
    fi
    exit 1
fi

# 3. Verify Python version (>= 3.10) -------------------------------------
PYTHON_VERSION="$("$PYTHON_BIN" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
PYTHON_MAJOR="$("$PYTHON_BIN" -c 'import sys; print(sys.version_info[0])')"
PYTHON_MINOR="$("$PYTHON_BIN" -c 'import sys; print(sys.version_info[1])')"

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
    echo "❌ Python ${PYTHON_VERSION} found, but OSINT Finder requires Python >= 3.10."
    if command -v brew >/dev/null 2>&1; then
        echo "   Install a newer version with: brew install python@3.12"
    else
        echo "   Install a newer version from https://www.python.org/downloads/macos/"
    fi
    exit 1
fi
echo "✓ Python ${PYTHON_VERSION} detected"

# 4. Detect architecture --------------------------------------------------
ARCH="$(uname -m)"
echo "✓ Architecture: ${ARCH}"

# 5. Create virtual environment (only if missing) -------------------------
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    "$PYTHON_BIN" -m venv "$VENV_DIR" || fail \
        "virtual environment creation" \
        "$PYTHON_BIN -m venv $VENV_DIR" \
        "venv module unavailable or disk/permission issue" \
        "ensure the 'venv' module is available (it ships with Python) and that you have write access to this directory"
else
    echo "✓ Virtual environment already exists"
fi

VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

if [ ! -x "$VENV_PYTHON" ]; then
    fail "virtual environment" "$VENV_PYTHON" "venv appears corrupted (missing python binary)" \
        "delete the .venv directory and re-run ./run.sh"
fi

# 6. Upgrade pip ------------------------------------------------------------
"$VENV_PYTHON" -m pip install --upgrade pip --quiet || fail \
    "pip upgrade" "$VENV_PYTHON -m pip install --upgrade pip" \
    "network unavailable or PyPI unreachable" \
    "check your internet connection and try again"

# 7. Install dependencies (only what's missing) ------------------------------
echo "Checking dependencies..."
MISSING_DEPS=0
for module in PySide6 maigret httpx PIL; do
    if ! "$VENV_PYTHON" -c "import ${module}" >/dev/null 2>&1; then
        MISSING_DEPS=1
        break
    fi
done

if [ "$MISSING_DEPS" -eq 1 ]; then
    echo "Installing dependencies from ${REQUIREMENTS_FILE}..."
    "$VENV_PIP" install -r "$REQUIREMENTS_FILE" --quiet || fail \
        "dependency installation" \
        "$VENV_PIP install -r $REQUIREMENTS_FILE" \
        "network unavailable, PyPI unreachable, or a package failed to build" \
        "check your internet connection; re-run ./run.sh; if it persists, run '$VENV_PIP install -r $REQUIREMENTS_FILE' manually to see the full error"
else
    echo "✓ Dependencies already installed"
fi

# 8. Verify critical imports --------------------------------------------------
echo "Verifying installation..."
"$VENV_PYTHON" -c "import PySide6, maigret, httpx, PIL" || fail \
    "dependency verification" \
    "$VENV_PYTHON -c 'import PySide6, maigret, httpx, PIL'" \
    "one or more packages failed to install correctly" \
    "delete .venv and re-run ./run.sh for a clean install"
echo "✓ All dependencies verified"

# 9. Create application directories + run diagnostics ---------------------
echo ""
echo "Running diagnostics..."
"$VENV_PYTHON" scripts/bootstrap.py --diagnose
DIAG_STATUS=$?

if [ "$DIAG_STATUS" -ne 0 ]; then
    fail "diagnostics" "$VENV_PYTHON scripts/bootstrap.py --diagnose" \
        "environment is not fully ready (see output above)" \
        "resolve the [FAIL] items above and re-run ./run.sh"
fi

# 10. Launch the application -----------------------------------------------
echo ""
echo "Launching OSINT Finder..."
exec "$VENV_PYTHON" main.py
