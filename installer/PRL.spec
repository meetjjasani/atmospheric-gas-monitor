# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for PRL Dashboard Desktop App.

Build:
    pip install -e ".[build]"
    python installer/build.py
    # or directly:
    pyinstaller installer/PRL.spec
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent
SRC  = ROOT / "src"

block_cipher = None

a = Analysis(
    [str(SRC / "prl" / "app" / "main.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=[
        # Bundle QSS theme files
        (str(SRC / "prl" / "app" / "widgets" / "dark.qss"),  "prl/app/widgets"),
        (str(SRC / "prl" / "app" / "widgets" / "light.qss"), "prl/app/widgets"),
        # Bundle any widget assets (icons, images)
        (str(SRC / "prl" / "app" / "widgets" / "assets"),    "prl/app/widgets/assets"),
        # Bundle default config
        (str(ROOT / "config" / "config.json"), "config"),
    ],
    hiddenimports=[
        "duckdb",
        "pyarrow",
        "pyarrow.vendored.version",
        "plotly",
        "pyqtgraph",
        "pandas",
        "numpy",
        "PySide6.QtSvg",
        "PySide6.QtPrintSupport",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "streamlit",
        "streamlit_app",
        "tkinter",
        "IPython",
        "jupyter",
        "notebook",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PRL Dashboard",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                       # No terminal window for end users
    icon=str(ROOT / "installer" / "assets" / "icon.ico") if (ROOT / "installer" / "assets" / "icon.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PRL Dashboard",
)
