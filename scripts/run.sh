#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

if ! command -v poetry >/dev/null 2>&1; then
    echo "Poetry is not installed or not in PATH."
    echo "Install it using: curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

echo "Configuring Poetry to use in-project virtual environments..."
poetry config virtualenvs.in-project true

echo "Starting PostgreSQL container..."
"$ROOT_DIR/scripts/start_db.sh"

cd "$BACKEND_DIR"

VENV_PATH=$(poetry env info --path 2>/dev/null || true)
if [[ -z "$VENV_PATH" ]]; then
    echo "No Poetry environment found. Creating one..."
    poetry install
    VENV_PATH=$(poetry env info --path)
fi

OS_NAME="$(uname -s)"
if [[ "$OS_NAME" == MINGW* || "$OS_NAME" == MSYS* || "$OS_NAME" == CYGWIN* ]]; then
    if ! command -v cygpath >/dev/null 2>&1; then
        echo "cygpath was not found; cannot activate Windows Poetry environment from this shell."
        exit 1
    fi

    VENV_PATH_UNIX=$(cygpath -u "$VENV_PATH")
    ACTIVATE_PATH="$VENV_PATH_UNIX/Scripts/activate"
else
    ACTIVATE_PATH="$VENV_PATH/bin/activate"
fi

if [[ ! -f "$ACTIVATE_PATH" ]]; then
    echo "Activation script not found at: $ACTIVATE_PATH"
    exit 1
fi

echo "Poetry environment found at $VENV_PATH"
echo "Entering virtual environment shell..."
exec bash --rcfile <(printf 'source "%s"\n' "$ACTIVATE_PATH")
