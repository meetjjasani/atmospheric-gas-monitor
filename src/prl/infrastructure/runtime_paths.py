from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


APP_DIR_NAME = "PRL"


def bundle_root() -> Path:
    """Return the directory that contains bundled app assets."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def user_data_root() -> Path:
    """Return a writable per-user directory for exports and caches."""
    override = os.environ.get("PRL_APP_HOME")
    if override:
        root = Path(override).expanduser()
    elif sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / APP_DIR_NAME
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_DIR_NAME

    try:
        root.mkdir(parents=True, exist_ok=True)
        return root
    except OSError:
        fallback = Path(tempfile.gettempdir()) / APP_DIR_NAME
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def app_config_path() -> Path:
    """Resolve config.json for both frozen .exe and dev mode."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "config" / "config.json"
    return Path(__file__).resolve().parents[3] / "config" / "config.json"


def processed_data_dir() -> Path:
    """Writable directory for the processed database and ingest catalog."""
    if getattr(sys, "frozen", False):
        path = user_data_root() / "data" / "processed"
    else:
        path = Path(__file__).resolve().parents[3] / "data" / "processed"
    path.mkdir(parents=True, exist_ok=True)
    return path


def app_logs_dir() -> Path:
    """Writable directory for pipeline logs."""
    if getattr(sys, "frozen", False):
        path = user_data_root() / "logs"
    else:
        path = Path(__file__).resolve().parents[3] / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def bundled_processed_dir() -> Path:
    return bundle_root() / "data" / "processed"


def export_dir() -> Path:
    path = user_data_root() / "exports" / "plots"
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_dir() -> Path:
    path = user_data_root() / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def mpl_config_dir() -> Path:
    path = user_data_root() / "mplconfig"
    path.mkdir(parents=True, exist_ok=True)
    return path
