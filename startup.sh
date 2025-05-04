#!/usr/bin/env bash

set -e  # Exit immediately if a command exits with a non-zero status

# Check if pyenv is installed and use the Python version from .python-version if available
if command -v pyenv &> /dev/null && [ -f ".python-version" ]; then
    echo "Using Python version specified in .python-version"
    PYTHON_CMD="pyenv exec python"
    
    # Install Python version if not already installed
    PYTHON_VERSION=$(cat .python-version)
    if ! pyenv versions | grep -q "$PYTHON_VERSION"; then
        echo "Installing Python $PYTHON_VERSION..."
        pyenv install "$PYTHON_VERSION"
        pyenv local "$PYTHON_VERSION"
    fi
else
    echo "Using system Python"
    PYTHON_CMD="python3"
fi

# Create virtual environment
echo "Creating virtual environment..."
$PYTHON_CMD -m venv env

# Activate virtual environment
source env/bin/activate

# Upgrade pip and install setuptools first to handle distutils dependency
python3 -m pip install --upgrade pip
python3 -m pip install setuptools

# Now install other requirements
python3 -m pip install -r requirements.txt

# Run the application
python3 app.py