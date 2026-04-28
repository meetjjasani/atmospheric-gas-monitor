# PRL Dashboard

Desktop application for CRDS gas (CO, CO₂, CH₄) analysis and visualization at the Physical Research Laboratory.

## Features

- **5 interactive dashboards** — Correlations, Daily Diurnal, Daily Mean & Median, Hourly Mean, Heatmap
- **UTC → IST conversion** with multi-level quality control (hard bounds, spike detection, sustained shift detection)
- **DuckDB + Parquet** storage for fast queries across large multi-year datasets
- **Distributable as `.exe`** for Windows — no Python required on scientist machines

## Quick Start (Development)

```bash
# 1. Install in editable mode (replaces all requirements*.txt files)
pip install -e ".[dev]"

# 2. Run the desktop app
prl-app
# or
python -m prl.app.main

# 3. Run the data pipeline (processes new .dat files)
prl-pipeline --config config/config.json
```

## Building the Windows .exe

```bash
pip install -e ".[build]"
python installer/build.py
# Output: dist/PRL-Setup.exe
```

## Project Structure

```
src/prl/              # Main Python package
  core/               # Pure business logic (no UI)
    ingest/           # .dat file discovery and parsing
    preprocess/       # UTC→IST + QC flags
    storage/          # DuckDB + Parquet read/write
    metrics/          # Aggregations (diurnal, hourly, daily)
    correlation/      # Regression and ratio math
    plotting/         # Chart builders (Plotly + Matplotlib)
    services/         # Orchestration layer (pipeline + dashboard)
    validation/       # QC report builder
  app/                # Desktop application (PySide6)
    widgets/          # Reusable UI components + themes
    workers/          # Background threads
  pipeline/           # CLI data pipeline
  infrastructure/     # Runtime paths (cross-platform)

tests/                # Unit and integration tests
docs/                 # Full documentation
installer/            # PyInstaller packaging
config/               # Pipeline configuration
data/                 # Raw and processed data (gitignored)
```

## Documentation

| Doc | Description |
|-----|-------------|
| [docs/user_guide.md](docs/user_guide.md) | How scientists use the app |
| [docs/installation.md](docs/installation.md) | Installing the .exe on Windows |
| [docs/data_format.md](docs/data_format.md) | .dat file format specification |
| [docs/architecture.md](docs/architecture.md) | System design for developers |

## Configuration

Edit `config/config.json` to set raw data paths, month folders to ingest, and QC thresholds:

```json
{
  "data_root": "data/raw/2025",
  "month_dirs": ["11", "12"],
  "qc": {
    "point_spike_z": 8.0,
    "hourly_spike_z": 6.0,
    "hourly_reference_window_hours": 168
  }
}
```

## Running Tests

```bash
pytest
```
