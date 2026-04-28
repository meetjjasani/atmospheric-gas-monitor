from __future__ import annotations

import json
import urllib.request
import webbrowser
from urllib.error import URLError

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QMessageBox, QWidget

from prl import __version__

GITHUB_API_LATEST = (
    "https://api.github.com/repos/meetjjasani/atmospheric-gas-monitor/releases/latest"
)
RELEASES_PAGE = "https://github.com/meetjjasani/atmospheric-gas-monitor/releases/latest"
REQUEST_TIMEOUT_SECONDS = 5


def _parse_version(tag: str) -> tuple[int, ...]:
    """Convert 'v2.0.1' or '2.0.1' into (2, 0, 1) for safe numeric comparison."""
    cleaned = tag.lstrip("vV").strip()
    parts = []
    for piece in cleaned.split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


class _UpdateCheckWorker(QObject):
    """Background worker that asks GitHub for the latest release tag."""

    finished = Signal(bool, str)  # (update_available, latest_version_tag)

    def run(self) -> None:
        try:
            req = urllib.request.Request(
                GITHUB_API_LATEST,
                headers={"Accept": "application/vnd.github+json"},
            )
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            latest_tag = payload.get("tag_name", "")
            if not latest_tag:
                self.finished.emit(False, "")
                return
            update_available = _parse_version(latest_tag) > _parse_version(__version__)
            self.finished.emit(update_available, latest_tag)
        except (URLError, TimeoutError, json.JSONDecodeError, OSError):
            # No internet, GitHub down, or rate-limited — silently skip.
            self.finished.emit(False, "")


class UpdateChecker(QObject):
    """Checks GitHub for a newer release and shows a popup if found."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._parent_widget = parent
        self._thread: QThread | None = None
        self._worker: _UpdateCheckWorker | None = None

    def check_async(self) -> None:
        """Start the background check. Safe to call once at app startup."""
        self._thread = QThread()
        self._worker = _UpdateCheckWorker()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_finished(self, update_available: bool, latest_tag: str) -> None:
        if not update_available:
            return
        reply = QMessageBox.question(
            self._parent_widget,
            "Update Available",
            f"A new version ({latest_tag}) of PRL Dashboard is available.\n\n"
            f"You are currently using v{__version__}.\n\n"
            f"Would you like to download it now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            webbrowser.open(RELEASES_PAGE)
