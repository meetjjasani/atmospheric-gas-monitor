from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QWidget


class TopBar(QWidget):
    """Header row with title, summary text, and global actions."""

    save_html_requested = Signal()
    theme_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("topBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.title_label = QLabel("PRL Sync Gases Dashboard")
        self.title_label.setObjectName("appTitle")

        self.subtitle_label = QLabel("Desktop analysis view")
        self.subtitle_label.setObjectName("appSubtitle")

        self.theme_button = QPushButton("Dark Mode")
        self.theme_button.setObjectName("themeButton")
        self.theme_button.setCheckable(True)
        self.theme_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_button.toggled.connect(self._emit_theme_change)

        self.save_button = QPushButton("Save HTML")
        self.save_button.setObjectName("saveHtmlButton")
        self.save_button.setProperty("accent", True)
        self.save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_button.clicked.connect(self.save_html_requested.emit)

        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(4)
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.subtitle_label)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addLayout(title_layout)
        layout.addStretch(1)
        layout.addWidget(self.theme_button, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.save_button, alignment=Qt.AlignmentFlag.AlignVCenter)

    def set_title(self, title: str) -> None:
        self.title_label.setText(title)

    def set_subtitle(self, subtitle: str) -> None:
        self.subtitle_label.setText(subtitle)

    def set_theme(self, theme_name: str) -> None:
        is_dark = theme_name == "dark"
        self.theme_button.blockSignals(True)
        self.theme_button.setChecked(is_dark)
        self.theme_button.blockSignals(False)

    def set_save_enabled(self, enabled: bool) -> None:
        self.save_button.setEnabled(enabled)

    def _emit_theme_change(self, checked: bool) -> None:
        self.theme_changed.emit("dark" if checked else "light")
