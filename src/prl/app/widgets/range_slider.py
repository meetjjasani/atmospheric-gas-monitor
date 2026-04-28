from __future__ import annotations

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget


class RangeSlider(QWidget):
    """Simple dual-handle slider for selecting an inclusive integer range."""

    values_changed = Signal(int, int)

    def __init__(
        self,
        minimum: int = 0,
        maximum: int = 23,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._minimum = minimum
        self._maximum = maximum
        self._lower = minimum
        self._upper = maximum
        self._active_handle: str | None = None
        self._handle_radius = 8
        self.setObjectName("fitRangeSlider")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(28)
        self.setMinimumWidth(180)

    def values(self) -> tuple[int, int]:
        return self._lower, self._upper

    def set_values(self, lower: int, upper: int) -> None:
        lower = max(self._minimum, min(lower, self._maximum))
        upper = max(self._minimum, min(upper, self._maximum))
        if lower > upper:
            lower, upper = upper, lower
        if (lower, upper) == (self._lower, self._upper):
            return
        self._lower = lower
        self._upper = upper
        self.update()
        self.values_changed.emit(self._lower, self._upper)

    def paintEvent(self, _event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        track_y = self.height() / 2
        left_x = self._track_left()
        right_x = self._track_right()
        groove_pen = QPen(self._groove_color(), 4)
        groove_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(groove_pen)
        painter.drawLine(QPointF(left_x, track_y), QPointF(right_x, track_y))

        lower_x = self._value_to_pos(self._lower)
        upper_x = self._value_to_pos(self._upper)
        active_pen = QPen(self._active_color(), 4)
        active_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(active_pen)
        painter.drawLine(QPointF(lower_x, track_y), QPointF(upper_x, track_y))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._handle_fill_color())
        painter.drawEllipse(QPointF(lower_x, track_y), self._handle_radius, self._handle_radius)
        painter.drawEllipse(QPointF(upper_x, track_y), self._handle_radius, self._handle_radius)

        border_pen = QPen(self._handle_border_color(), 1)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(lower_x, track_y), self._handle_radius, self._handle_radius)
        painter.drawEllipse(QPointF(upper_x, track_y), self._handle_radius, self._handle_radius)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        position = event.position().x()
        lower_dist = abs(position - self._value_to_pos(self._lower))
        upper_dist = abs(position - self._value_to_pos(self._upper))
        self._active_handle = "lower" if lower_dist <= upper_dist else "upper"
        self._update_active_handle(position)
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._active_handle is None:
            return
        self._update_active_handle(event.position().x())
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._active_handle = None
        event.accept()

    def _update_active_handle(self, position: float) -> None:
        value = self._pos_to_value(position)
        if self._active_handle == "lower":
            self.set_values(value, self._upper)
        elif self._active_handle == "upper":
            self.set_values(self._lower, value)

    def _track_left(self) -> float:
        return float(self._handle_radius)

    def _track_right(self) -> float:
        return float(max(self._handle_radius, self.width() - self._handle_radius))

    def _value_to_pos(self, value: int) -> float:
        span = max(1, self._maximum - self._minimum)
        ratio = (value - self._minimum) / span
        return self._track_left() + ratio * (self._track_right() - self._track_left())

    def _pos_to_value(self, position: float) -> int:
        span = max(1.0, self._track_right() - self._track_left())
        ratio = (position - self._track_left()) / span
        ratio = max(0.0, min(1.0, ratio))
        return int(round(self._minimum + ratio * (self._maximum - self._minimum)))

    def _groove_color(self) -> QColor:
        color = self.palette().mid().color()
        return color.lighter(120) if color.lightness() < 128 else color

    def _active_color(self) -> QColor:
        return self.palette().highlight().color()

    def _handle_fill_color(self) -> QColor:
        return self.palette().base().color()

    def _handle_border_color(self) -> QColor:
        return self.palette().mid().color()
