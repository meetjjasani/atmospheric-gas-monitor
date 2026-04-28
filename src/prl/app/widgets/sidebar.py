from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget


class Sidebar(QWidget):
    """Navigation rail for switching between dashboard sections."""

    section_changed = Signal(str)
    import_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.title_label = QLabel("PRL Dashboard")
        self.title_label.setObjectName("sidebarTitle")

        self.subtitle_label = QLabel("CRDS desktop viewer")
        self.subtitle_label.setObjectName("sidebarSubtitle")

        self.nav_list = QListWidget()
        self.nav_list.setObjectName("sidebarNav")
        self.nav_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self.nav_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.nav_list.setFrameShape(QFrame.Shape.NoFrame)
        self.nav_list.setSpacing(4)
        self.nav_list.currentItemChanged.connect(self._emit_current_section)

        self.summary_title = QLabel("Available Data")
        self.summary_title.setObjectName("sidebarSectionTitle")

        self.summary_label = QLabel("No dataset loaded")
        self.summary_label.setObjectName("sidebarSummary")
        self.summary_label.setWordWrap(True)
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.import_btn = QPushButton("Import Raw Month")
        self.import_btn.setObjectName("dateRangeButton")
        self.import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.import_btn.clicked.connect(self.import_requested.emit)


        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addSpacing(12)
        layout.addWidget(self.nav_list, 1)
        layout.addWidget(self.summary_title)
        layout.addWidget(self.summary_label)
        layout.addSpacing(8)
        layout.addWidget(self.import_btn)

    def set_sections(self, sections: Sequence[tuple[str, str]]) -> None:
        self.nav_list.blockSignals(True)
        self.nav_list.clear()
        for section_id, label in sections:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, section_id)
            self.nav_list.addItem(item)
        if self.nav_list.count():
            self.nav_list.setCurrentRow(0)
        self.nav_list.blockSignals(False)
        self._emit_current_section(self.nav_list.currentItem(), None)

    def set_current_section(self, section_id: str) -> None:
        for row in range(self.nav_list.count()):
            item = self.nav_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == section_id:
                self.nav_list.setCurrentRow(row)
                return

    def set_summary(self, text: str) -> None:
        self.summary_label.setText(text)

    def current_section(self) -> str:
        item = self.nav_list.currentItem()
        if item is None:
            return ""
        return str(item.data(Qt.ItemDataRole.UserRole) or "")

    def _emit_current_section(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        if current is None:
            return
        section_id = current.data(Qt.ItemDataRole.UserRole)
        if section_id:
            self.section_changed.emit(str(section_id))
