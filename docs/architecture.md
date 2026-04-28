# Architecture — Developer Reference

## Overview

```
Raw .dat Files
    ↓
[prl.core.ingest]      — file discovery + fast CSV parsing
    ↓
[prl.core.preprocess]  — UTC→IST conversion + QC (hard bounds, spike detection)
    ↓
[prl.core.storage]     — Hive-partitioned Parquet + DuckDB virtual table
    ↓
[prl.core.metrics]     — aggregations (diurnal, hourly, daily)
[prl.core.correlation] — gas pair regression
    ↓
[prl.core.services]    — orchestration layer used by both UI and CLI
    ↓
[prl.app]              — PySide6 desktop application (5 dashboards)
[prl.pipeline.cli]     — headless batch processing
```

## Package Layout

```
src/prl/
├── core/               # Pure business logic — no PySide6, no UI
│   ├── ingest/         # service.py: discover_dat_files(), load_all()
│   ├── preprocess/     # service.py: standardize_and_convert_utc_to_ist(), apply_quality_control()
│   ├── storage/        # database.py: Database class (DuckDB + Parquet)
│   │                   # catalog.py: FileCatalog (incremental ingestion tracking)
│   ├── metrics/        # dashboard_metrics.py, pipeline_metrics.py
│   ├── correlation/    # service.py: build_correlation_frame(), regression_stats()
│   ├── plotting/       # chart_builder.py (Plotly), static_export.py (Matplotlib)
│   ├── services/
│   │   ├── dashboard_service.py   # view builders used by prl.app
│   │   └── pipeline_service.py    # full pipeline orchestration used by CLI
│   └── validation/     # service.py: build_quality_report()
│
├── app/                # PySide6 Desktop Application
│   ├── main.py         # Entry point: QApplication + MainWindow
│   ├── main_window.py  # MainWindow: layout, section switching, filter events
│   ├── dashboard_controller.py   # Coordinates filtered queries + view model building
│   ├── data_access.py  # DashboardDataRepository (wraps Database)
│   ├── view_models.py  # FilterState, DashboardSnapshot, section state dataclasses
│   ├── styles.py       # QSS theme loader
│   ├── windowing.py    # Screen-fit helpers
│   ├── widgets/        # Reusable PySide6 widgets
│   │   ├── sidebar.py, top_bar.py, filters_panel.py
│   │   ├── metrics_table.py, plot_section.py
│   │   ├── import_dialog.py, date_range_picker.py, range_slider.py
│   │   ├── dark.qss, light.qss
│   └── workers/
│       ├── dashboard_worker.py   # Background thread: builds DashboardSnapshot
│       └── import_worker.py      # Background thread: runs pipeline on import
│
├── pipeline/
│   └── cli.py          # argparse entry point → calls pipeline_service.run_pipeline()
│
└── infrastructure/
    └── runtime_paths.py  # Cross-platform path resolution (bundle, user data, exports)
```

## Data Flow — Desktop App

```
User adjusts filters
    ↓
FilterState updated in MainWindow
    ↓
User clicks Apply → _refresh_dashboard()
    ↓
DashboardWorker (background QThread)
    → DashboardController.build_snapshot(filter_state)
        → DashboardDataRepository.load_range(start, end, columns)  [DuckDB query]
        → dashboard_service.build_*_view(filtered_df, ...)
        → returns DashboardSnapshot
    ↓
snapshot_ready signal → main thread
    ↓
_render_active_section() → PlotSection + MetricsTable update
```

## Key Design Decisions

| Decision | Rationale |
|---|---|
| `src/` layout | Proper installable package; no PYTHONPATH hacks |
| Hive-partitioned Parquet | DuckDB prunes partitions → fast date queries |
| FileCatalog (mtime+size) | Re-running pipeline never re-ingests the same files |
| Raw + cleaned columns both stored | Full audit trail for QC review |
| Background QThread in desktop | UI never freezes during DuckDB queries |
| Services layer shared | `dashboard_service` functions used identically by CLI and desktop |
| `pyproject.toml` | Single source of truth for dependencies, scripts, tool config |

## Adding a New Dashboard Section

1. Add a new view builder in `src/prl/core/services/dashboard_service.py`
2. Add a new section state dataclass in `src/prl/app/view_models.py`
3. Add the render method in `src/prl/app/main_window.py`
4. Add the sidebar label in `SECTION_LABELS` dict
5. Add a test in `tests/unit/test_dashboard_service.py`
