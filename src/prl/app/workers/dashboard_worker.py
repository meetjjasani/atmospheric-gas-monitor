from __future__ import annotations

import traceback
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from prl.app.dashboard_controller import DashboardController

if TYPE_CHECKING:
    from prl.app.view_models import FilterState, DashboardSnapshot


class DashboardWorker(QObject):
    """Execution logic for heavy dashboard data operations.
    
    This worker runs in a separate thread to prevent blocking the UI.
    """
    init_finished = Signal(object)      # (DashboardController)
    snapshot_ready = Signal(object) # (DashboardSnapshot)
    error_occurred = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._controller: DashboardController | None = None

    def initialize_controller(self) -> None:
        """Heavily-lifting initialization of the data repository."""
        try:
            self._controller = DashboardController()
            self.init_finished.emit(self._controller)
        except Exception as e:
            self.error_occurred.emit(f"Initialization Error: {str(e)}")

    def build_snapshot(self, state: FilterState, theme_name: str = "light") -> None:
        """Execute DuckDB queries and build view models asynchronously."""
        if not self._controller:
            self.error_occurred.emit("Controller not initialized.")
            return

        try:
            snapshot = self._controller.build_snapshot(state, theme_name=theme_name)
            self.snapshot_ready.emit(snapshot)
        except Exception as e:
            traceback.print_exc()
            self.error_occurred.emit(f"Data Refresh Error: {str(e)}")

    def reload_data(self) -> None:
        """Trigger a full reload of the underlying data repository."""
        if not self._controller:
            return
            
        try:
            self._controller.reload_data()
            self.init_finished.emit(self._controller)
        except Exception as e:
            self.error_occurred.emit(f"Reload Error: {str(e)}")
