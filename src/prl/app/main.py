from __future__ import annotations

import os
import sys

# Critical fix for macOS: matplotlib GUI backends are not thread-safe and 
# cause a system abort(134) when used in a background QThread. 
# Forcing 'Agg' (headless) must happen before ANY other module imports plt.
import matplotlib
matplotlib.use("Agg")

from prl.infrastructure.runtime_paths import mpl_config_dir



os.environ.setdefault("MPLCONFIGDIR", str(mpl_config_dir()))

from PySide6.QtWidgets import QApplication

from prl.app.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("PRL Desktop")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
