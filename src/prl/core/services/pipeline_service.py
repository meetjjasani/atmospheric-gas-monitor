from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


from prl.core.correlation.pipeline_summary import (
    build_correlation_summary,
    build_monthly_correlation_summary,
)
from prl.core.ingest.service import load_all
from prl.core.io_utils import ensure_dirs, write_table
from prl.core.storage.database import Database

from prl.core.metrics.pipeline_metrics import (
    daily_diurnal_matrix,
    hourly_mean_timeseries,
    monthly_diurnal_24point,
    monthly_hour_day_matrix,
)
from prl.core.plotting.static_export import (
    plot_hourly_mean,
    plot_monthly_diurnal,
    plot_scatter_with_fit,
)
from prl.core.preprocess.service import apply_quality_control, standardize_and_convert_utc_to_ist
from prl.core.validation.service import build_quality_report


def load_pipeline_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def run_pipeline(config_path: Path) -> Path:
    cfg = load_pipeline_config(config_path)

    project_root = Path(cfg["project_root"]).resolve()
    data_root = project_root / cfg.get("data_root", ".")
    out_data = project_root / cfg["output"]["processed_dir"]
    out_plots = project_root / cfg["output"]["plots_dir"]
    out_logs = project_root / cfg["output"]["logs_dir"]
    ensure_dirs([out_data, out_plots, out_logs])

    raw = load_all(data_root=data_root, month_dirs=cfg.get("month_dirs"))
    return process_and_save_dataset(
        raw,
        out_data=out_data,
        out_plots=out_plots,
        out_logs=out_logs,
        qc_cfg=cfg.get("qc"),
    )


def process_batch(
    df: pd.DataFrame,
    db_root: Path,
    qc_cfg: dict | None = None,
    db: Database | None = None,
) -> None:
    """Process a single data batch and append to the partitioned database.

    Pass ``db`` from the caller to reuse an existing DuckDB connection across
    multiple batches — avoids the ~200 ms overhead of opening a new connection
    and rebuilding views on every call.
    """
    # 1. Standardize and QC
    standardized = standardize_and_convert_utc_to_ist(df)
    clean = apply_quality_control(standardized, qc_cfg)

    # 2. Add partitioning columns
    clean["year"] = clean["datetime_ist"].dt.year
    clean["month"] = clean["datetime_ist"].dt.month

    # 3. Additive Append via Database Interface
    if db is None:
        db = Database(db_root)
    db.save_batch(clean)


def process_and_save_dataset(
    df: pd.DataFrame,
    out_data: Path,
    out_plots: Path,
    out_logs: Path,
    qc_cfg: dict | None = None,
) -> Path:
    """Legacy entry point: Processes a full dataset in one go."""
    db_root = out_data / "db"
    process_batch(df, db_root=db_root, qc_cfg=qc_cfg)
    
    # Standard metrics generation for the full dataset (Optional: can be optimized later)
    # We load the full processed set once to generate the static files
    db = Database(db_root)
    clean = db.query("SELECT * FROM prl_data") # Load back into Pandas for metrics
    
    qa = build_quality_report(clean)
    write_table(qa, out_logs / "qa_report.csv")

    hourly = hourly_mean_timeseries(clean)
    write_table(hourly, out_data / "hourly_mean_ist.csv")
    
    # ... rest of the metrics logic (Plotting etc.) ...
    for gas in ["co_sync", "co2_sync", "ch4_sync"]:
        monthly_24 = monthly_diurnal_24point(clean, gas=gas)
        write_table(monthly_24, out_data / f"monthly_diurnal_24point_{gas}.csv")
        plot_monthly_diurnal(monthly_24, gas, out_plots / f"monthly_diurnal_{gas}.png")

    # Rebuild the hourly store so the dashboard can load instantly.
    db.rebuild_hourly_aggregates()

    return db_root


