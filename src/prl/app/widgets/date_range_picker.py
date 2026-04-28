from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import QDate, QEvent, QObject, QPoint, Qt, Signal
from PySide6.QtGui import QColor, QTextCharFormat
from PySide6.QtWidgets import (
    QCalendarWidget,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)


def _to_qdate(value: date) -> QDate:
    return QDate(value.year, value.month, value.day)


def _to_pydate(value: QDate) -> date:
    return date(value.year(), value.month(), value.day())


def _cell_to_date(
    calendar: QCalendarWidget,
    row: int,  # 1-based data row (row 0 = day-name header)
    col: int,  # 0-based data column (0 to 6) — because we use NoVerticalHeader
) -> date | None:
    """Convert a (row, col) model index into the date shown in that calendar cell.

    Verified correct against live QCalendarWidget grid for March 2026.
    Because we configured 'NoVerticalHeader' on the calendar, the week-number
    column is entirely removed, so the 7 visible day columns are at indices 0 to 6.
    """
    if row < 1 or col < 0 or col > 6:
        return None

    year = calendar.yearShown()
    month = calendar.monthShown()
    first_of_month = QDate(year, month, 1)
    first_dow = first_of_month.dayOfWeek()          # 1=Mon … 7=Sun
    fdow = calendar.firstDayOfWeek()
    # PySide6 returns a DayOfWeek enum; .value gives the int
    first_day_int = fdow.value if hasattr(fdow, "value") else int(fdow)

    days_back = (first_dow - first_day_int) % 7
    if days_back == 0:
        # First of month lands exactly on the start-of-week day; Qt still
        # shows the preceding full week in row 1.
        days_back = 7

    grid_start = first_of_month.addDays(-days_back)
    py_start = date(grid_start.year(), grid_start.month(), grid_start.day())
    # offset uses col exactly since columns are 0-indexed (0 to 6)
    return py_start + timedelta(days=(row - 1) * 7 + col)



class _ViewportHoverFilter(QObject):
    """Event filter on the QCalendarWidget viewport that emits the hovered date.

    Mouse events arrive at the VIEWPORT (QScrollArea child), not the QTableView.
    We convert the viewport-relative mouse position to a (row, col) via
    indexAt(), then compute the exact calendar date from the grid geometry.
    """

    date_hovered = Signal(date)

    def __init__(
        self,
        calendar: QCalendarWidget,
        table_view: QTableView,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._calendar = calendar
        self._tv = table_view

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseMove:
            pos: QPoint = event.pos()  # type: ignore[attr-defined]
            index = self._tv.indexAt(pos)
            if index.isValid():
                row, col = index.row(), index.column()
                d = _cell_to_date(self._calendar, row, col)
                if d is not None:
                    self.date_hovered.emit(d)
        return super().eventFilter(watched, event)


class DateRangePickerDialog(QDialog):
    """Compact frameless calendar popup with live hover-range preview.

    Step 1: Click start date  → turns solid blue (anchor locked).
    Step 2: Move mouse        → range from anchor to cursor highlights instantly.
    Step 3: Click end date    → range committed, dialog closes.
    """

    range_selected = Signal(date, date)

    def __init__(
        self,
        start_date: date,
        end_date: date,
        minimum_date: date,
        maximum_date: date,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        # We don't use setModal(True) because it can interfere with focus-based 
        # auto-close behavior in some window managers (especially on Mac).
        # The WindowType.Popup flag will already handle clicks outside.
        self.setObjectName("dateRangeDialog")
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)

        self._minimum_date = minimum_date
        self._maximum_date = maximum_date
        self._anchor_date: date | None = None
        self._selected_start = start_date
        self._selected_end = end_date
        self._highlighted_dates: list[date] = []

        # ── Helper label ──────────────────────────────────────────────
        self.helper_label = QLabel("Click a start date to begin your selection.")
        self.helper_label.setObjectName("plotStatus")
        self.helper_label.setWordWrap(True)

        # ── Calendar ──────────────────────────────────────────────────
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(False)
        self.calendar.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader
        )
        self.calendar.setMinimumDate(_to_qdate(minimum_date))
        self.calendar.setMaximumDate(_to_qdate(maximum_date))
        self.calendar.setSelectedDate(_to_qdate(start_date))
        self.calendar.clicked.connect(self._handle_click)

        # ── Install hover filter on the VIEWPORT ──────────────────────
        table_views = self.calendar.findChildren(QTableView)
        if table_views:
            tv = table_views[0]
            vp = tv.viewport()
            vp.setMouseTracking(True)
            filt = _ViewportHoverFilter(self.calendar, tv, self)
            filt.date_hovered.connect(self._handle_hover)
            vp.installEventFilter(filt)

        # ── Cancel button ─────────────────────────────────────────────
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        buttons.rejected.connect(self.reject)

        # ── Layout ────────────────────────────────────────────────────
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        layout.addWidget(self.helper_label)
        layout.addWidget(self.calendar)
        layout.addWidget(buttons)
        self.setFixedWidth(280)

        # Show previous selection
        self._paint_range(start_date, end_date)

    def event(self, event: QEvent) -> bool:
        """Close the popup if it loses focus (e.g. clicking outside)."""
        if event.type() == QEvent.Type.WindowDeactivate:
            # We delay the rejection slightly to ensure we don't interfere 
            # with internal mouse handling if a click actually hit the dialog.
            self.reject()
        return super().event(event)
    # ─────────────────────────────────────────────────────────────────
    # Click handler
    # ─────────────────────────────────────────────────────────────────

    def _handle_click(self, qdate: QDate) -> None:
        chosen = _to_pydate(qdate)
        if self._anchor_date is None:
            self._anchor_date = chosen
            self.helper_label.setText(
                f"Start: {chosen.strftime('%d %b %Y')} — move to end date and click."
            )
            self._paint_range(chosen, chosen)
        else:
            start = min(self._anchor_date, chosen)
            end = max(self._anchor_date, chosen)
            self._paint_range(start, end)
            self.range_selected.emit(start, end)
            self.accept()

    # ─────────────────────────────────────────────────────────────────
    # Hover handler — LIVE range preview
    # ─────────────────────────────────────────────────────────────────

    def _handle_hover(self, hovered: date) -> None:
        """Fires on every mouse move. Updates the highlighted range instantly."""
        if self._anchor_date is None:
            return
        start = min(self._anchor_date, hovered)
        end = max(self._anchor_date, hovered)
        days = (end - start).days + 1
        self.helper_label.setText(
            f"{start.strftime('%d %b %Y')} → {end.strftime('%d %b %Y')}"
            f"  ({days} day{'s' if days != 1 else ''})"
        )
        self._paint_range(start, end, is_preview=True)

    # ─────────────────────────────────────────────────────────────────
    # Range painter
    # ─────────────────────────────────────────────────────────────────

    def _paint_range(
        self,
        start: date,
        end: date,
        *,
        is_preview: bool = False,
    ) -> None:
        # Clear old highlights
        clear = QTextCharFormat()
        for d in self._highlighted_dates:
            self.calendar.setDateTextFormat(_to_qdate(d), clear)

        is_dark = self.palette().color(self.backgroundRole()).lightness() < 128

        if is_dark:
            anchor_bg = QColor("#3b82f6")
            anchor_fg = QColor("#ffffff")
            end_bg    = QColor("#1d4ed8")
            end_fg    = QColor("#bfdbfe")
            mid_bg    = QColor("#1a2a4a") if is_preview else QColor("#1e3a8a")
            mid_fg    = QColor("#93c5fd")
        else:
            anchor_bg = QColor("#2563eb")
            anchor_fg = QColor("#ffffff")
            end_bg    = QColor("#1d4ed8")
            end_fg    = QColor("#ffffff")
            mid_bg    = QColor("#dbeafe") if is_preview else QColor("#bfdbfe")
            mid_fg    = QColor("#2563eb")

        dates: list[date] = []
        cur = start
        while cur <= end:
            dates.append(cur)
            cur += timedelta(days=1)

        for d in dates:
            fmt = QTextCharFormat()
            if d == self._anchor_date or (d == start and self._anchor_date is None):
                fmt.setBackground(anchor_bg)
                fmt.setForeground(anchor_fg)
                fmt.setFontWeight(700)
            elif d == end and end != start:
                fmt.setBackground(end_bg)
                fmt.setForeground(end_fg)
                fmt.setFontWeight(600)
            else:
                fmt.setBackground(mid_bg)
                fmt.setForeground(mid_fg)
            self.calendar.setDateTextFormat(_to_qdate(d), fmt)

        self._highlighted_dates = dates
        
        # FATAL BUG FIX: If we call setSelectedDate during a live hover preview,
        # moving the mouse over a greyed-out date from the next/prev month causes
        # the calendar to instantly switch months. This pulls the grid out from
        # under the mouse, causing severe visual misalignment and jumping.
        # We only set the actual focus date when the range is committed.
        if not is_preview:
            self.calendar.setSelectedDate(_to_qdate(end))


class DateRangePickerButton(QPushButton):
    """Single-button that opens the compact range-select calendar popup."""

    range_changed = Signal(date, date)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dateRangeButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._minimum_date = date.today()
        self._maximum_date = date.today()
        self._start_date = date.today()
        self._end_date = date.today()
        self._active_dialog: DateRangePickerDialog | None = None
        self.clicked.connect(self._open_dialog)
        self._refresh_text()

    def set_bounds(self, minimum_date: date, maximum_date: date) -> None:
        self._minimum_date = minimum_date
        self._maximum_date = maximum_date
        self.set_range(
            max(minimum_date, min(self._start_date, maximum_date)),
            max(minimum_date, min(self._end_date, maximum_date)),
            emit_signal=False,
        )

    def set_range(self, start_date: date, end_date: date, *, emit_signal: bool = False) -> None:
        self._start_date = min(start_date, end_date)
        self._end_date = max(start_date, end_date)
        self._refresh_text()
        if emit_signal:
            self.range_changed.emit(self._start_date, self._end_date)

    def date_range(self) -> tuple[date, date]:
        return self._start_date, self._end_date

    def _open_dialog(self) -> None:
        if self._active_dialog:
            self._active_dialog.close()

        self._active_dialog = DateRangePickerDialog(
            start_date=self._start_date,
            end_date=self._end_date,
            minimum_date=self._minimum_date,
            maximum_date=self._maximum_date,
            parent=self,
        )
        self._active_dialog.range_selected.connect(lambda s, e: self.set_range(s, e, emit_signal=True))
        self._active_dialog.move(self.mapToGlobal(QPoint(0, self.height() + 6)))
        self._active_dialog.show()

    def _refresh_text(self) -> None:
        if self._start_date == self._end_date:
            self.setText(self._start_date.strftime("%d %b %Y"))
        else:
            self.setText(
                f"{self._start_date.strftime('%d %b %Y')} – "
                f"{self._end_date.strftime('%d %b %Y')}"
            )
