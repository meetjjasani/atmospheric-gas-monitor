from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListView,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from prl.app.widgets.date_range_picker import DateRangePickerButton
from prl.app.widgets.range_slider import RangeSlider
from prl.app.view_models import DateRange


@dataclass(frozen=True, slots=True)
class FiltersPanelState:
    """Common filter values exposed by the compact control strip."""

    date_range: DateRange
    correlation_pair: str
    gas: str
    fit_start_hour: int
    fit_end_hour: int


class FiltersPanel(QWidget):
    """Apply-driven filter strip with unified date selection and compact controls."""

    state_changed = Signal(FiltersPanelState)
    apply_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("filtersPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._month_ranges: list[tuple[str, date, date]] = []
        self._minimum_date: date | None = None
        self._maximum_date: date | None = None

        self.date_picker = DateRangePickerButton()
        self.date_picker.range_changed.connect(self._handle_date_range_changed)
        self.date_picker.setFixedWidth(210)
        self.date_picker.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.month_combo = self._make_combo(130)
        self.month_combo.currentIndexChanged.connect(self._handle_month_selected)

        self.all_data_button = QPushButton("All Data")
        self.all_data_button.setProperty("compact", True)
        self.all_data_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.all_data_button.setFixedWidth(80)
        self.all_data_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.all_data_button.clicked.connect(self._select_all_data)

        self.fit_range_slider = RangeSlider(0, 23)
        self.fit_range_slider.setFixedWidth(130)
        self.fit_range_slider.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.fit_range_slider.values_changed.connect(self._handle_fit_range_changed)
        
        self.fit_range_value = QLabel("00-23")
        self.fit_range_value.setObjectName("filterValue")
        self.fit_range_value.setFixedWidth(45)

        self.pair_combo = self._make_combo(160)
        self.pair_combo.currentIndexChanged.connect(lambda _index: self.apply_requested.emit())

        self.gas_combo = self._make_combo(100)
        self.gas_combo.currentIndexChanged.connect(lambda _index: self.apply_requested.emit())

        self.apply_button = QPushButton("Apply")
        self.apply_button.setProperty("accent", True)
        self.apply_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.apply_button.setFixedWidth(65)
        self.apply_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self.apply_requested.emit)

        self.reset_fit_button = QPushButton("Reset")
        self.reset_fit_button.setProperty("compact", True)
        self.reset_fit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_fit_button.setFixedWidth(65)
        self.reset_fit_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.reset_fit_button.clicked.connect(self._reset_fit_hours)

        self.date_field = self._create_field("Date", self.date_picker)
        self.range_field = self._create_month_field()
        self.fit_field = self._create_fit_field()
        self.pair_field = self._create_field("Pair", self.pair_combo)
        self.gas_field = self._create_field("Gas", self.gas_combo)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)
        layout.addWidget(self.date_field)
        layout.addWidget(self.range_field)
        layout.addWidget(self.fit_field)
        layout.addWidget(self.pair_field)
        layout.addWidget(self.gas_field)
        layout.addStretch()

        self.set_section("correlation")

    def set_available_pairs(self, pairs: list[str]) -> None:
        self.pair_combo.clear()
        self.pair_combo.addItems(pairs)

    def set_available_gases(self, gases: dict[str, str]) -> None:
        self.gas_combo.clear()
        for label, gas_id in gases.items():
            self.gas_combo.addItem(label, gas_id)

    def set_available_months(self, months: Sequence[tuple[str, date, date]]) -> None:
        self._month_ranges = list(months)
        blocker = QSignalBlocker(self.month_combo)
        _ = blocker
        self.month_combo.clear()
        self.month_combo.addItem("Month", None)
        for label, start_date, end_date in self._month_ranges:
            self.month_combo.addItem(label, (start_date, end_date))

    def set_date_bounds(self, min_date: date, max_date: date) -> None:
        self._minimum_date = min_date
        self._maximum_date = max_date
        self.date_picker.set_bounds(min_date, max_date)

    def set_section(self, section_id: str) -> None:
        is_correlation = section_id == "correlation"
        self.fit_field.setVisible(is_correlation)
        self.pair_field.setVisible(is_correlation)
        self.gas_field.setVisible(not is_correlation)

    def set_state(self, state: FiltersPanelState) -> None:
        blockers = [
            QSignalBlocker(self.month_combo),
            QSignalBlocker(self.pair_combo),
            QSignalBlocker(self.gas_combo),
            QSignalBlocker(self.fit_range_slider),
        ]
        _ = blockers

        self.date_picker.set_range(state.date_range.start, state.date_range.end)
        self.pair_combo.setCurrentText(state.correlation_pair)
        idx = self.gas_combo.findData(state.gas)
        if idx >= 0:
            self.gas_combo.setCurrentIndex(idx)
        else:
            self.gas_combo.setCurrentText(state.gas)
        self.fit_range_slider.set_values(state.fit_start_hour, state.fit_end_hour)
        self._update_fit_range_label(state.fit_start_hour, state.fit_end_hour)
        self._sync_month_selection(state.date_range)

    def current_state(self) -> FiltersPanelState:
        start, end = self.date_picker.date_range()
        fit_start, fit_end = self.fit_range_slider.values()
        return FiltersPanelState(
            date_range=DateRange(start=start, end=end),
            correlation_pair=self.pair_combo.currentText(),
            gas=self.gas_combo.currentData(),
            fit_start_hour=fit_start,
            fit_end_hour=fit_end,
        )

    def set_apply_enabled(self, enabled: bool) -> None:
        self.apply_button.setEnabled(enabled)

    def set_applying(self, applying: bool) -> None:
        self.apply_button.setEnabled(not applying and self.apply_button.isEnabled())
        self.apply_button.setText("Applying..." if applying else "Apply")

    def _handle_date_range_changed(self, _start: date, _end: date) -> None:
        self._sync_month_selection(self.current_state().date_range)
        self.apply_requested.emit()

    def _handle_month_selected(self, index: int) -> None:
        if index <= 0:
            return
        month_range = self.month_combo.itemData(index)
        if not month_range:
            return
        start_date, end_date = month_range
        self.date_picker.set_range(start_date, end_date, emit_signal=False)
        self.apply_requested.emit()

    def _select_all_data(self) -> None:
        if self._minimum_date is None or self._maximum_date is None:
            return
        self.date_picker.set_range(self._minimum_date, self._maximum_date, emit_signal=False)
        self._sync_month_selection(DateRange(start=self._minimum_date, end=self._maximum_date))
        self.apply_requested.emit()

    def _handle_fit_range_changed(self, lower: int, upper: int) -> None:
        self._update_fit_range_label(lower, upper)
        self.state_changed.emit(self.current_state())

    def _update_fit_range_label(self, lower: int, upper: int) -> None:
        self.fit_range_value.setText(f"{lower:02d}-{upper:02d}")

    def _reset_fit_hours(self) -> None:
        self.fit_range_slider.set_values(0, 23)
        self.apply_requested.emit()

    def _sync_month_selection(self, date_range: DateRange) -> None:
        target_index = 0
        for index, (_label, start_date, end_date) in enumerate(self._month_ranges, start=1):
            if start_date == date_range.start and end_date == date_range.end:
                target_index = index
                break
        blocker = QSignalBlocker(self.month_combo)
        _ = blocker
        self.month_combo.setCurrentIndex(target_index)

    @staticmethod
    def _make_combo(width: int) -> QComboBox:
        """QComboBox with a clean, bar-free popup.

        Three things are required on macOS:
        1. setFrameShape(NoFrame) on the view — removes the system-drawn
           border that renders as black lines around the list.
        2. setMouseTracking(True) on the view — without this macOS never
           fires hover events so QSS ::item:hover has no effect.
        3. Inline stylesheet on the vertical scrollbar — the cascade from
           the app QSS sheet does not reach popup windows on macOS, so the
           scrollbar arrow buttons (add-line / sub-line) stay visible as
           black rectangles at the bottom of the popup unless explicitly
           zeroed out here.
        """
        combo = QComboBox()
        view = QListView(combo)
        view.setFrameShape(QFrame.Shape.NoFrame)
        view.setFrameShadow(QFrame.Shadow.Plain)
        view.setMouseTracking(True)
        # Belt-and-suspenders: zero out the scrollbar arrow buttons directly
        # on the widget — the only method that reliably works on macOS.
        view.verticalScrollBar().setStyleSheet(
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {"
            "  height: 0px; border: none; background: transparent; }"
            "QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {"
            "  height: 0px; width: 0px; image: none; }"
        )
        combo.setView(view)
        combo.setFixedWidth(width)
        combo.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        return combo

    def _create_field(self, label_text: str, control: QWidget) -> QWidget:
        label = QLabel(label_text)
        label.setObjectName("filterLabel")
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(label)
        layout.addWidget(control)
        return container

    def _create_month_field(self) -> QWidget:
        label = QLabel("Range")
        label.setObjectName("filterLabel")

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)
        row_layout.addWidget(self.month_combo)
        row_layout.addWidget(self.all_data_button)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(label)
        layout.addWidget(row)
        return container

    def _create_fit_field(self) -> QWidget:
        label = QLabel("Fit hours")
        label.setObjectName("filterLabel")

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)
        row_layout.addWidget(self.fit_range_slider)
        row_layout.addWidget(self.fit_range_value)
        row_layout.addWidget(self.reset_fit_button)
        row_layout.addWidget(self.apply_button)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(label)
        layout.addWidget(row)
        return container
