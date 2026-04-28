# Installation Guide

## For Scientists (Windows .exe)

1. Download `PRL-Dashboard-vX.X.X-Setup.exe` from the Releases page
2. Double-click and follow the installer
3. Launch from Desktop shortcut or Start Menu → "PRL Dashboard"
4. No Python installation required

## For Developers (Source)

### Requirements
- Python 3.10+
- pip

### Setup

```bash
# Clone or copy the project
cd PRL/

# Install all dependencies (dev mode — editable install)
pip install -e ".[dev]"

# Run the app
prl-app

# Run the pipeline
prl-pipeline --config config/config.json
```

### Building the .exe

```bash
pip install -e ".[build]"
python installer/build.py
# Output: dist/PRL Dashboard.exe
```
