from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget


class MetricsTable(QWidget):
    """Compact metrics panel rendered as responsive horizontal metric cards."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("metricsTable")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(60)
        self.setMaximumHeight(90)

        self.title_label = QLabel("Metrics")
        self.title_label.setObjectName("sectionTitle")

        self.cards_container = QWidget()
        self.cards_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.cards_layout = QHBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(12)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)
        layout.addWidget(self.title_label)
        layout.addWidget(self.cards_container, 0)

    def update_rows(self, rows: Sequence[tuple[str, str]], title: str = "Metrics") -> None:
        self.title_label.setText(title)
        self._clear_cards()

        for metric, value in rows:
            self.cards_layout.addWidget(self._create_metric_card(metric, value))

        self.cards_layout.addStretch(1)

    def clear_rows(self, title: str = "Metrics") -> None:
        self.update_rows([], title=title)

    def _create_metric_card(self, metric: str, value: str) -> QWidget:
        card = QWidget()
        card.setObjectName("metricCard")
        card.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        label = QLabel(metric)
        label.setObjectName("metricLabel")
        label.setWordWrap(False)

        value_label = QLabel(value)
        value_label.setObjectName("metricValue")
        value_label.setWordWrap(False)
        value_label.setMaximumWidth(250)
        value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(label)
        layout.addStretch(1)
        layout.addWidget(value_label)
        return card

    def _clear_cards(self) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
