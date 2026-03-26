#!/bin/bash
# Explanation in Docs.

# Check if Poetry is installed.
if ! command -v poetry &> /dev/null
then
    echo "Poetry is not installed!"
    echo "Install it using: curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# Configure Poetry to create the virtual environment inside the project directory (.venv).
echo "Configuring Poetry to use in-project virtual environments..."
poetry config virtualenvs.in-project true

echo "Starting PostgreSQL container..." # Database will run upon entering the venv.
./scripts/start_db.sh

cd backend || exit 1 # Poetry (pyproject.toml) resides.

# The virtual environment path for Poetry. This is absolutely The virtual environment associated with the current project not the Poetry's own .venv managing the Poetry tool itself.
VENV_PATH=$(poetry env info --path 2>/dev/null)

# If no venv exists yet, create one and get its path again.
if [ -z "$VENV_PATH" ]; then
    echo "No Poetry environment found! Creating one..."
    poetry install
    VENV_PATH=$(poetry env info --path)
fi

VENV_PATH_UNIX=$(cygpath -u "$VENV_PATH") # Convert Windows path to Git Bash path

# Activate the virtual environment by replacing the current shell with one inside the venv.
if [ -d "$VENV_PATH" ]; then
    echo "Poetry environment found at $VENV_PATH"
    echo "Entering virtual environment shell..."
    # exec bash --init-file <(echo ". ~/.bashrc; source \"$VENV_PATH/bin/activate\"")  # bash to start with a custom RC file (Load local .bashrc first (which includes aliases like ll)), which in this case is the venv's activate script. Reason we need custom bash rc shell is to source everything in a new clean shell (loaded with local .bashrc but we can make also a blank one). (Linux/Mac)
    exec bash --rcfile <(echo "source \"$VENV_PATH_UNIX/Scripts/activate\"") # Windows
else
    echo "Failed to find or create a virtual environment."
    exit 1
fi

