"""
Build script for PRL Dashboard .exe.

Usage:
    pip install -e ".[build]"
    python installer/build.py

Output:
    dist/PRL Dashboard/PRL Dashboard.exe
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "installer" / "PRL.spec"


def main() -> None:
    print(f"Building PRL Dashboard from: {SPEC}")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(SPEC), "--clean", "--noconfirm"],
        cwd=str(ROOT),
        check=False,
    )
    if result.returncode != 0:
        print("\nBuild FAILED. Check output above.")
        sys.exit(1)
    exe_path = ROOT / "dist" / "PRL Dashboard" / "PRL Dashboard.exe"
    print(f"\nBuild succeeded!")
    print(f"Executable: {exe_path}")


if __name__ == "__main__":
    main()
