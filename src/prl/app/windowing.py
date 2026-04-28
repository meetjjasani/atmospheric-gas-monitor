from __future__ import annotations

from PySide6.QtCore import QRect
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget


def screen_for(widget: QWidget | None):
    """Return the best screen associated with a widget."""
    if widget is not None:
        handle = widget.windowHandle()
        if handle is not None and handle.screen() is not None:
            return handle.screen()
        screen = widget.screen()
        if screen is not None:
            return screen
    return QGuiApplication.primaryScreen()


def fit_window_to_available_screen(
    window: QWidget,
    *,
    preferred_size: tuple[int, int],
    fill_ratio: tuple[float, float],
    min_size: tuple[int, int],
) -> tuple[int, int]:
    """Size and center a window inside the usable screen area."""
    screen = screen_for(window)
    if screen is None:
        return window.width(), window.height()

    margin = 8
    available = screen.availableGeometry().adjusted(margin, margin, -margin, -margin)

    target_width = min(preferred_size[0], int(available.width() * fill_ratio[0]))
    target_height = min(preferred_size[1], int(available.height() * fill_ratio[1]))
    target_width = max(target_width, min(min_size[0], available.width()))
    target_height = max(target_height, min(min_size[1], available.height()))
    target_width = min(target_width, available.width())
    target_height = min(target_height, available.height())

    x = available.x() + max(0, (available.width() - target_width) // 2)
    y = available.y() + max(0, (available.height() - target_height) // 2)
    window.setGeometry(x, y, target_width, target_height)
    return target_width, target_height


def apply_window_geometry_within_screen(window: QWidget, geometry: QRect) -> tuple[int, int]:
    """Clamp a saved geometry back inside the visible screen area."""
    screen = screen_for(window)
    if screen is None:
        window.setGeometry(geometry)
        return geometry.width(), geometry.height()

    margin = 8
    available = screen.availableGeometry().adjusted(margin, margin, -margin, -margin)
    target_width = min(geometry.width(), available.width())
    target_height = min(geometry.height(), available.height())
    max_x = available.x() + max(0, available.width() - target_width)
    max_y = available.y() + max(0, available.height() - target_height)
    x = min(max(geometry.x(), available.x()), max_x)
    y = min(max(geometry.y(), available.y()), max_y)
    window.setGeometry(x, y, target_width, target_height)
    return target_width, target_height
