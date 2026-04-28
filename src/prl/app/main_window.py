from __future__ import annotations

import matplotlib
matplotlib.use("Agg")

import os

import sys
from collections import OrderedDict
from dataclasses import replace
from datetime import date

from prl.infrastructure.runtime_paths import mpl_config_dir
import numpy as np
from PySide6.QtCore import QTimer, Qt, QThread
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from prl.app.dashboard_controller import DashboardController
from prl.app.styles import load_theme_stylesheet
from prl.app.widgets import (
    FiltersPanel,
    FiltersPanelState,
    ImportDataDialog,
    MetricsTable,
    PlotSection,
    Sidebar,
    TopBar,
)
from prl.app.view_models import (
    CorrelationSectionState,
    DailyStatsSectionState,
    DashboardSnapshot,
    DiurnalSectionState,
    HeatmapSectionState,
    HourlyMeanSectionState,
)
from prl.app.windowing import fit_window_to_available_screen
from prl.app.workers.dashboard_worker import DashboardWorker
from prl.core.services import dashboard_service


SECTION_LABELS = OrderedDict(
    [
        ("correlation", "Correlations"),
        ("diurnal", "Daily Diurnal"),
        ("daily_stats", "Daily Mean & Median"),
        ("hourly_mean", "Hourly Mean"),
        ("heatmap", "Heatmap"),
    ]
)

GAS_LABELS = {
    "co_sync": "CO",
    "co2_sync": "CO₂",
    "ch4_sync": "CH₄",
}


class MainWindow(QMainWindow):
    """Modular PRL desktop dashboard composed from reusable QWidget sections."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PRL Desktop")
        self.setMinimumSize(1280, 760)

        self._launch_geometry_synced = False
        self._theme_name = "light"
        self._current_section = "correlation"
        self._snapshot: DashboardSnapshot | None = None
        self._is_fresh_session = True # Radical Clean Start: Don't load anything!
        
        self.controller: DashboardController | None = None
        self._is_refreshing = False # Task lock/debounce flag
        
        # 1. Setup the Async Dashboard worker
        self._dashboard_thread = QThread()
        self.worker = DashboardWorker()
        self.worker.moveToThread(self._dashboard_thread)
        
        self._dashboard_thread.start()
        self._connect_worker_signals()

        self._start_app_flow()

    def _connect_worker_signals(self) -> None:
        """Centralized wiring for the background data thread."""
        self.worker.init_finished.connect(self._on_init_finished)
        self.worker.snapshot_ready.connect(self._on_snapshot_ready)
        self.worker.error_occurred.connect(self._on_worker_error)

    def _on_init_finished(self, controller: DashboardController) -> None:
        """Slot for background initialization success."""
        self.controller = controller
        self._filter_state = self.controller.default_filter_state()
        self._applied_filter_state = self._filter_state
        
        self._configure_components()
        self._render_active_section()
        self.statusBar().showMessage("Database initialized successfully.", 4000)

    def _on_snapshot_ready(self, snapshot: DashboardSnapshot) -> None:
        """Slot for successful background query completion."""
        self._is_refreshing = False
        self._snapshot = snapshot
        
        self._update_shell()
        self._render_active_section()
        
        self.plot_section.set_loading(False)
        self.filters_panel.set_applying(False)
        self._update_apply_state()
        
        self.statusBar().showMessage(snapshot.summary.status_text, 4000)

    def _on_worker_error(self, message: str) -> None:
        """Slot for any background failures."""
        self._is_refreshing = False
        self.plot_section.set_loading(False)
        self.filters_panel.set_applying(False)
        self.statusBar().showMessage("Operation failed.")
        QMessageBox.critical(self, "Data Error", message)

    def _ensure_controller(self) -> bool:
        """Asynchronously triggers controller initialization if needed."""
        if self.controller is not None:
            return True
            
        self.statusBar().showMessage("Starting database engine...")
        # Fire and forget; _on_init_finished will handle the result
        QTimer.singleShot(0, self.worker.initialize_controller)
        return False

    def _start_app_flow(self) -> None:
        """Kicks off UI setup and final launch sequence."""
        self._build_ui()
        self._configure_components()
        self._connect_signals()
        self._apply_theme(self._theme_name)
        
        # We explicitly SKIP _refresh_dashboard here to satisfy 'Start Empty'
        self.statusBar().showMessage("Ready. Use Sidebar to Import Data.")
        self._show_welcome_state()

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("mainWindowRoot")
        self.setCentralWidget(central)

        self.sidebar = Sidebar()
        self.sidebar.setFixedWidth(220)

        self.top_bar = TopBar()
        self.top_bar.setFixedHeight(64)

        self.filters_panel = FiltersPanel()
        self.plot_section = PlotSection()
        self.metrics_table = MetricsTable()

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)
        content_layout.addWidget(self.top_bar)
        content_layout.addWidget(self.filters_panel)
        content_layout.addWidget(self.plot_section, 1)
        content_layout.addWidget(self.metrics_table, 0)
        content_layout.setStretchFactor(self.plot_section, 1)
        content_layout.setStretchFactor(self.metrics_table, 0)

        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(16)
        root_layout.addWidget(self.sidebar)
        root_layout.addWidget(content, 1)

        self.statusBar().showMessage("Ready")

    def _configure_components(self) -> None:
        self.sidebar.set_sections(list(SECTION_LABELS.items()))
        self.top_bar.set_title("PRL Sync Gases Dashboard")
        self.top_bar.set_subtitle("Interactive desktop analysis")

        if self.controller is None:
            self.sidebar.set_summary(
                "No data loaded.\n\n"
                "Please use the button below to import raw files."
            )
            self.filters_panel.set_date_bounds(date.today(), date.today())
        else:
            data_summary = self.controller.data_summary
            if data_summary.is_empty:
                self.sidebar.set_summary(
                    "No data loaded.\n\n"
                    "Please use the button below to import raw files."
                )
            else:
                self.sidebar.set_summary(
                    "Available range\n"
                    f"{self._format_date(data_summary.min_date)} to {self._format_date(data_summary.max_date)}\n\n"
                    f"Rows available\n{data_summary.row_count:,}"
                )
            
            self.filters_panel.set_available_pairs(list(self.controller.PAIR_MAP))
            self.filters_panel.set_available_gases({GAS_LABELS.get(gas, gas): gas for gas in dashboard_service.GASES})
            self.filters_panel.set_available_months(
                [(label, month_range.start, month_range.end) for label, month_range in self.controller.available_months]
            )
            self.filters_panel.set_date_bounds(data_summary.min_date, data_summary.max_date)

        self.filters_panel.set_section(self._current_section)
        self.plot_section.set_heading("PRL Dashboard", "Welcome! Select a section or import data to begin.")
        self.metrics_table.update_rows([], title="Metrics Summary")



    def _connect_signals(self) -> None:
        self.sidebar.section_changed.connect(self._on_section_changed)
        self.top_bar.save_html_requested.connect(self._save_current_html)
        self.top_bar.theme_changed.connect(self._apply_theme)
        self.filters_panel.state_changed.connect(self._on_filters_edited)
        self.filters_panel.apply_requested.connect(self._refresh_dashboard)
        self.sidebar.import_requested.connect(self._on_import_requested)


    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._launch_geometry_synced:
            return
        self._launch_geometry_synced = True
        QTimer.singleShot(0, self._apply_launch_geometry)

    def _apply_launch_geometry(self) -> None:
        from prl.app.windowing import fit_window_to_available_screen
        fit_window_to_available_screen(
            self,
            preferred_size=(1400, 860),
            fill_ratio=(0.9, 0.88),
            min_size=(1280, 760),
        )

    def closeEvent(self, event) -> None:
        """Gracefully shut down background threads on exit."""
        self._dashboard_thread.quit()
        self._dashboard_thread.wait()
        super().closeEvent(event)

    def _refresh_dashboard(self) -> None:

        """Non-blocking refresh of dashboard charts."""
        if not self._ensure_controller():
            return
            
        if self._is_refreshing:
            return # Prevent duplicate clicks from spawning multiple threads

        self._is_refreshing = True
        self.statusBar().showMessage("Fetching data from DuckDB...")

        self.filters_panel.set_applying(True)
        self.plot_section.set_loading(True)
        
        # 1. Update intended state (for apply-button enablement check later)
        self._update_filter_state_from_panel()
        self._applied_filter_state = self._filter_state
        
        # 2. Kick off background task
        QTimer.singleShot(0, lambda: self.worker.build_snapshot(self._filter_state, theme_name=self._theme_name))

    def _on_import_requested(self) -> None:
        dialog = ImportDataDialog(self)
        if dialog.exec():
            if not self._ensure_controller():
                return

            # Session is no longer fresh once data is imported
            self._is_fresh_session = False
            self.statusBar().showMessage("Reloading database...")
            
            # Use the worker for reloading
            QTimer.singleShot(0, self.worker.reload_data)

            
            QMessageBox.information(
                self, 
                "Data Updated", 
                "The dashboard has been refreshed with the newly imported data."
            )

    def _show_welcome_state(self) -> None:
        """Display a placeholder state when no data is loaded."""
        self.plot_section.set_heading("PRL Dashboard", "Ready to analyze CRDS data.")
        # We could also show a specific welcome HTML page in the web view here if desired


    def _update_shell(self) -> None:
        if self._snapshot is None:
            return

        rows = self._snapshot.summary.row_count
        range_label = self._snapshot.summary.range_label
        section_label = SECTION_LABELS[self._current_section]
        self.top_bar.set_subtitle(f"{section_label} | {rows:,} rows | {range_label}")
        self.top_bar.set_save_enabled(self._snapshot.has_data)
        data_summary = self.controller.data_summary
        self.sidebar.set_summary(
            "Available range\n"
            f"{self._format_date(data_summary.min_date)} to {self._format_date(data_summary.max_date)}\n\n"
            "Selected range\n"
            f"{range_label}\n\n"
            f"Rows shown\n{rows:,}"
        )

    def _render_active_section(self) -> None:
        if self._snapshot is None:
            return

        renderers = {
            "correlation": lambda: self._render_correlation(self._snapshot.correlation),
            "diurnal": lambda: self._render_diurnal(self._snapshot.diurnal),
            "daily_stats": lambda: self._render_daily_stats(self._snapshot.daily_stats),
            "hourly_mean": lambda: self._render_hourly_mean(self._snapshot.hourly_mean),
            "heatmap": lambda: self._render_heatmap(self._snapshot.heatmap),
        }
        renderers[self._current_section]()

    def _update_plot_metadata(self, section_name: str, element_label: str) -> None:
        if self._snapshot is None:
            return
            
        start_date = self._snapshot.selected_range.start
        end_date = self._snapshot.selected_range.end
        
        # 1. Format for window title (Human readable)
        date_str = self._format_date(start_date)
        if start_date != end_date:
            date_str = f"{date_str} to {self._format_date(end_date)}"
        
        self.plot_section.full_title = f"{section_name} - {element_label} - {date_str}"
        
        # 2. Format for smart filename (Filesystem safe)
        start_fs = start_date.strftime("%d-%b-%Y")
        end_fs = end_date.strftime("%d-%b-%Y")
        range_fs = start_fs if start_fs == end_fs else f"{start_fs}_to_{end_fs}"
        
        element_fs = element_label.replace(" ", "_").replace("₂", "2").replace("₄", "4")
        plot_fs = section_name.replace(" ", "_")
        
        self.plot_section.smart_filename = f"{range_fs}_{element_fs}_{plot_fs}"


    def _render_correlation(self, state: CorrelationSectionState) -> None:
        self._update_plot_metadata("Correlation", state.title)
        self.plot_section.set_heading(
            "Correlations",
            f"{state.title} | Fit hours {state.fit_start_hour:02d}-{state.fit_end_hour:02d} IST",
        )
        if state.data.empty:
            self.plot_section.show_message("No correlation data is available for the selected range.")
        else:
            figure, _stats = dashboard_service.create_correlation_figure(
                state.data,
                x_col=state.x_col,
                y_col=state.y_col,
                title=state.title,
                point_label="Hourly mean data",
                fit_df=state.fit_data,
                fit_label=f"hours {state.fit_start_hour:02d}-{state.fit_end_hour:02d} IST",
            )
            self.plot_section.set_figure(figure)

        self.metrics_table.update_rows(
            [(row.label, row.value) for row in state.table_rows],
            title="Correlation Metrics",
        )

    def _render_diurnal(self, state: DiurnalSectionState) -> None:
        gas_label = GAS_LABELS.get(state.gas, state.gas)
        self._update_plot_metadata("Daily_Diurnal", gas_label)
        self.plot_section.set_heading("Daily Diurnal", f"{gas_label} 24-point profile")
        if state.stats.empty:
            self.plot_section.show_message("No diurnal profile is available for the selected range.")
        else:
            figure = dashboard_service.create_diurnal_figure(
                state.stats,
                state.gas,
                self._snapshot.selected_range.start,
                self._snapshot.selected_range.end,
            )
            self.plot_section.set_figure(figure)

        self.metrics_table.update_rows(self._diurnal_rows(state), title="Diurnal Metrics")

    def _render_daily_stats(self, state: DailyStatsSectionState) -> None:
        gas_label = GAS_LABELS.get(state.gas, state.gas)
        self._update_plot_metadata("Mean_Median", gas_label)
        self.plot_section.set_heading("Daily Mean & Median", f"{gas_label} daily aggregates")
        if state.stats.empty:
            self.plot_section.show_message("No daily statistics are available for the selected range.")
        else:
            figure = dashboard_service.create_daily_mean_median_figure(
                state.stats,
                state.gas,
                self._snapshot.selected_range.start,
                self._snapshot.selected_range.end,
            )
            self.plot_section.set_figure(figure)

        self.metrics_table.update_rows(self._daily_stats_rows(state), title="Daily Metrics")

    def _render_hourly_mean(self, state: HourlyMeanSectionState) -> None:
        gas_label = GAS_LABELS.get(state.gas, state.gas)
        self._update_plot_metadata("Hourly_Mean", gas_label)
        self.plot_section.set_heading("Hourly Mean", f"{gas_label} hourly time series")
        if state.values.empty:
            self.plot_section.show_message("No hourly mean values are available for the selected range.")
        else:
            figure = dashboard_service.create_hourly_mean_figure(
                state.values,
                state.gas,
                self._snapshot.selected_range.start,
                self._snapshot.selected_range.end,
            )
            self.plot_section.set_figure(figure)

        self.metrics_table.update_rows(self._hourly_rows(state), title="Hourly Metrics")

    def _render_heatmap(self, state: HeatmapSectionState) -> None:
        gas_label = GAS_LABELS.get(state.gas, state.gas)
        self._update_plot_metadata("Heatmap", gas_label)
        self.plot_section.set_heading("Heatmap", f"{gas_label} by date and hour")
        if state.matrix.empty:
            self.plot_section.show_message("No heatmap values are available for the selected range.")
        else:
            figure = dashboard_service.create_heatmap_figure(
                state.matrix,
                state.gas,
                self._snapshot.selected_range.start,
                self._snapshot.selected_range.end,
            )
            self.plot_section.set_figure(figure)

        self.metrics_table.update_rows(self._heatmap_rows(state), title="Heatmap Metrics")

    def _on_section_changed(self, section_id: str) -> None:
        self._current_section = section_id
        if self.controller is not None:
            self._render_active_section()
        self.filters_panel.set_section(section_id)
        
    def _on_filters_edited(self, panel_state: FiltersPanelState) -> None:
        if self.controller is None:
            return
        self._update_filter_state_from_panel()

        self._update_apply_state()
        self.statusBar().showMessage("Filters changed. Click Apply to refresh.", 3000)

    def _save_current_html(self) -> None:
        if not self.plot_section.save_html():
            self.statusBar().showMessage("No interactive chart is available to export.", 3000)

    def _apply_theme(self, theme_name: str) -> None:
        self._theme_name = theme_name
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(load_theme_stylesheet(theme_name))
        self.top_bar.set_theme(theme_name)
        self.plot_section.set_theme(theme_name)

    def _sync_filters_from_state(self) -> None:
        self.filters_panel.set_state(
            FiltersPanelState(
                date_range=self._filter_state.date_range,
                correlation_pair=self._filter_state.correlation_pair,
                gas=self._section_gas(self._current_section),
                fit_start_hour=self._filter_state.fit_start_hour,
                fit_end_hour=self._filter_state.fit_end_hour,
            )
        )
        self._update_apply_state()

    def _update_filter_state_from_panel(self) -> None:
        state = self.filters_panel.current_state()
        updated = replace(
            self._filter_state,
            date_range=state.date_range,
            correlation_pair=state.correlation_pair,
            fit_start_hour=state.fit_start_hour,
            fit_end_hour=state.fit_end_hour,
        )

        if self._current_section == "diurnal":
            updated = replace(updated, diurnal_gas=state.gas)
        elif self._current_section == "daily_stats":
            updated = replace(updated, daily_stats_gas=state.gas)
        elif self._current_section == "hourly_mean":
            updated = replace(updated, hourly_mean_gas=state.gas)
        elif self._current_section == "heatmap":
            updated = replace(updated, heatmap_gas=state.gas)

        self._filter_state = updated

    def _update_apply_state(self) -> None:
        self.filters_panel.set_apply_enabled(self._filter_state != self._applied_filter_state)

    def _section_gas(self, section_id: str) -> str:
        if section_id == "diurnal":
            return self._filter_state.diurnal_gas
        if section_id == "daily_stats":
            return self._filter_state.daily_stats_gas
        if section_id == "hourly_mean":
            return self._filter_state.hourly_mean_gas
        if section_id == "heatmap":
            return self._filter_state.heatmap_gas
        return self._filter_state.diurnal_gas

    @staticmethod
    def _format_date(value: date) -> str:
        return value.strftime("%d/%m/%Y")

    def _diurnal_rows(self, state: DiurnalSectionState) -> list[tuple[str, str]]:
        if state.stats.empty:
            return [("Status", "No data")]
        return [
            ("Gas", GAS_LABELS.get(state.gas, state.gas)),
            ("Hours", f"{len(state.stats):,}"),
            ("Average", f"{float(state.stats['mean'].mean()):.4f}"),
            ("Median", f"{float(state.stats['median'].median()):.4f}"),
            ("Std. Dev.", f"{float(state.stats['std'].mean()):.4f}"),
        ]

    def _daily_stats_rows(self, state: DailyStatsSectionState) -> list[tuple[str, str]]:
        if state.stats.empty:
            return [("Status", "No data")]
        return [
            ("Gas", GAS_LABELS.get(state.gas, state.gas)),
            ("Days", f"{len(state.stats):,}"),
            ("Mean avg", f"{float(state.stats['mean'].mean()):.4f}"),
            ("Median avg", f"{float(state.stats['median'].mean()):.4f}"),
            ("Min mean", f"{float(state.stats['mean'].min()):.4f}"),
            ("Max mean", f"{float(state.stats['mean'].max()):.4f}"),
        ]

    def _hourly_rows(self, state: HourlyMeanSectionState) -> list[tuple[str, str]]:
        if state.values.empty:
            return [("Status", "No data")]
        series = state.values[state.gas]
        return [
            ("Gas", GAS_LABELS.get(state.gas, state.gas)),
            ("Points", f"{len(state.values):,}"),
            ("Mean", f"{float(series.mean()):.4f}"),
            ("Min", f"{float(series.min()):.4f}"),
            ("Max", f"{float(series.max()):.4f}"),
        ]

    def _heatmap_rows(self, state: HeatmapSectionState) -> list[tuple[str, str]]:
        if state.matrix.empty:
            return [("Status", "No data")]

        values = state.matrix.to_numpy(dtype=float).ravel()
        finite_values = values[np.isfinite(values)]
        if len(finite_values) == 0:
            return [("Status", "No finite values")]

        return [
            ("Gas", GAS_LABELS.get(state.gas, state.gas)),
            ("Cells", f"{len(finite_values):,}"),
            ("Mean", f"{float(finite_values.mean()):.4f}"),
            ("Min", f"{float(finite_values.min()):.4f}"),
            ("Max", f"{float(finite_values.max()):.4f}"),
        ]
