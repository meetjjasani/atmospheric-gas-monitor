from __future__ import annotations

from pathlib import Path


THEMES_DIR = Path(__file__).resolve().parent / "widgets"
THEME_FILES = {
    "light": THEMES_DIR / "light.qss",
    "dark": THEMES_DIR / "dark.qss",
}


def load_theme_stylesheet(theme_name: str) -> str:
    """Load a theme stylesheet from the desktop UI package."""
    theme_key = theme_name if theme_name in THEME_FILES else "light"
    return THEME_FILES[theme_key].read_text(encoding="utf-8")
