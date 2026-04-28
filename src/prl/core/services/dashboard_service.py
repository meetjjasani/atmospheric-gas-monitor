from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from prl.app.data_access import load_dashboard_data
from prl.core.constants import DATA_CSV, DATA_PARQUET, GASES
from prl.core.correlation.service import build_correlation_frame, regression_stats
from prl.core.metrics.dashboard_metrics import (
    build_daily_diurnal_matrix,
    build_daily_mean_median_stats,
    build_hourly_diurnal_stats,
    build_hourly_mean_timeseries,
)
from prl.core.plotting.chart_builder import (
    plot_daily_mean_median_bars,
    plot_gas_heatmap,
    plot_single_gas_24_point,
    plot_single_gas_hourly_mean,
    scatter_with_fit,
)


PAIR_MAP = {
    "CO vs CO2": ("co2_sync", "co_sync"),
    "CH4 vs CO2": ("co2_sync", "ch4_sync"),
    "CH4 vs CO2/(CO+CO2)": ("co2_over_co_plus_co2", "ch4_sync"),
}


@dataclass(frozen=True, slots=True)
class RangeSummary:
    min_date: date
    max_date: date
    row_count: int


def processed_data_mtimes() -> tuple[int | None, int | None]:
    parquet_mtime = int(DATA_PARQUET.stat().st_mtime_ns) if DATA_PARQUET.exists() else None
    csv_mtime = int(DATA_CSV.stat().st_mtime_ns) if DATA_CSV.exists() else None
    return parquet_mtime, csv_mtime


def get_dashboard_data() -> pd.DataFrame:
    return load_dashboard_data()


def summarize_range(df: pd.DataFrame) -> RangeSummary:
    return RangeSummary(
        min_date=df["date_ist"].min(),
        max_date=df["date_ist"].max(),
        row_count=len(df),
    )


def filter_by_date_range(df: pd.DataFrame, start_date: date, end_date: date) -> pd.DataFrame:
    return df[(df["date_ist"] >= start_date) & (df["date_ist"] <= end_date)].copy()


def metric_triplet_from_values(values: pd.Series | np.ndarray) -> tuple[str, str, str]:
    flat = np.asarray(values, dtype=float)
    flat = flat[np.isfinite(flat)]
    if len(flat) == 0:
        return "", "", ""
    return (
        f"Min: {float(flat.min()):.4f}",
        f"Avg: {float(flat.mean()):.4f}",
        f"Max: {float(flat.max()):.4f}",
    )


def build_correlation_view(
    filtered: pd.DataFrame,
    pair_label: str,
    fit_start_hour: int,
    fit_end_hour: int,
    *,
    title: str | None = None,
    point_label: str = "Hourly mean data",
    fit_label: str | None = None,
):
    x_col, y_col = PAIR_MAP[pair_label]
    corr_df = build_correlation_frame(filtered)
    start_hour = min(fit_start_hour, fit_end_hour)
    end_hour = max(fit_start_hour, fit_end_hour)
    hours = pd.to_datetime(corr_df["datetime_ist"], errors="coerce").dt.hour
    fit_df = corr_df.loc[hours.between(start_hour, end_hour, inclusive="both")]
    resolved_fit_label = fit_label or (
        "all hours 00-23" if start_hour == 0 and end_hour == 23 else f"hours {start_hour:02d}-{end_hour:02d} IST"
    )
    figure, stats = scatter_with_fit(
        corr_df,
        x_col=x_col,
        y_col=y_col,
        title=title or pair_label,
        point_label=point_label,
        fit_df=fit_df,
        fit_label=resolved_fit_label,
    )
    return {
        "data": corr_df,
        "fit_data": fit_df,
        "stats": stats,
        "figure": figure,
        "x_col": x_col,
        "y_col": y_col,
        "fit_start_hour": start_hour,
        "fit_end_hour": end_hour,
        "fit_label": resolved_fit_label,
    }


def build_diurnal_view(filtered: pd.DataFrame, gas: str, start_date: date, end_date: date) -> dict:
    matrix = build_daily_diurnal_matrix(filtered, gas=gas)
    stats_df = build_hourly_diurnal_stats(matrix)
    figure = plot_single_gas_24_point(
        stats_df,
        gas,
        start_date.strftime("%d/%m/%Y"),
        end_date.strftime("%d/%m/%Y"),
    )
    metric_text = (
        "",
        "",
        "",
    )
    if not stats_df.empty:
        metric_text = (
            f"Avg: {float(stats_df['mean'].mean()):.4f}",
            f"Median: {float(stats_df['median'].median()):.4f}",
            f"SD: {float(stats_df['std'].mean()):.4f}",
        )
    return {"matrix": matrix, "stats": stats_df, "figure": figure, "metrics": metric_text}


def build_daily_mean_median_view(
    filtered: pd.DataFrame,
    gas: str,
    start_date: date,
    end_date: date,
) -> dict:
    matrix = build_daily_diurnal_matrix(filtered, gas=gas)
    daily_stats = build_daily_mean_median_stats(matrix)
    figure = None
    if not daily_stats.empty:
        figure = plot_daily_mean_median_bars(
            daily_stats,
            gas,
            start_date.strftime("%d/%m/%Y"),
            end_date.strftime("%d/%m/%Y"),
        )
    metric_text = ("", "", "")
    if not daily_stats.empty:
        metric_text = (
            f"Days: {len(daily_stats):,}",
            f"Mean avg: {float(daily_stats['mean'].mean()):.4f}",
            f"Median avg: {float(daily_stats['median'].mean()):.4f}",
        )
    return {"matrix": matrix, "stats": daily_stats, "figure": figure, "metrics": metric_text}


def build_hourly_mean_view(filtered: pd.DataFrame, gas: str, start_date: date, end_date: date) -> dict:
    hourly = build_hourly_mean_timeseries(filtered)
    figure = plot_single_gas_hourly_mean(
        hourly,
        gas,
        start_date.strftime("%d/%m/%Y"),
        end_date.strftime("%d/%m/%Y"),
    )
    metric_text = ("", "", "")
    if not hourly.empty:
        metric_text = (
            f"Points: {len(hourly):,}",
            f"Min: {float(hourly[gas].min()):.4f}",
            f"Max: {float(hourly[gas].max()):.4f}",
        )
    return {"values": hourly, "figure": figure, "metrics": metric_text}


def build_heatmap_view(filtered: pd.DataFrame, gas: str, start_date: date, end_date: date) -> dict:
    matrix = build_daily_diurnal_matrix(filtered, gas=gas)
    figure = plot_gas_heatmap(
        matrix,
        gas,
        start_date.strftime("%d/%m/%Y"),
        end_date.strftime("%d/%m/%Y"),
    )
    metric_text = metric_triplet_from_values(matrix.to_numpy(dtype=float))
    return {"matrix": matrix, "figure": figure, "metrics": metric_text}


def create_correlation_figure(
    df: pd.DataFrame,
    *,
    x_col: str,
    y_col: str,
    title: str,
    point_label: str = "Data points",
    show_hour_colorbar: bool = True,
    fit_df: pd.DataFrame | None = None,
    fit_label: str | None = None,
):
    """Compatibility wrapper for desktop and Streamlit callers."""
    return scatter_with_fit(
        df,
        x_col=x_col,
        y_col=y_col,
        title=title,
        point_label=point_label,
        show_hour_colorbar=show_hour_colorbar,
        fit_df=fit_df,
        fit_label=fit_label,
    )


def create_diurnal_figure(
    stats_df: pd.DataFrame,
    gas: str,
    start_date: date,
    end_date: date,
):
    return plot_single_gas_24_point(
        stats_df,
        gas,
        start_date.strftime("%d/%m/%Y"),
        end_date.strftime("%d/%m/%Y"),
    )


def create_daily_mean_median_figure(
    daily_stats: pd.DataFrame,
    gas: str,
    start_date: date,
    end_date: date,
):
    return plot_daily_mean_median_bars(
        daily_stats,
        gas,
        start_date.strftime("%d/%m/%Y"),
        end_date.strftime("%d/%m/%Y"),
    )


def create_hourly_mean_figure(
    hourly_df: pd.DataFrame,
    gas: str,
    start_date: date,
    end_date: date,
):
    return plot_single_gas_hourly_mean(
        hourly_df,
        gas,
        start_date.strftime("%d/%m/%Y"),
        end_date.strftime("%d/%m/%Y"),
    )


def create_heatmap_figure(
    matrix: pd.DataFrame,
    gas: str,
    start_date: date,
    end_date: date,
):
    return plot_gas_heatmap(
        matrix,
        gas,
        start_date.strftime("%d/%m/%Y"),
        end_date.strftime("%d/%m/%Y"),
    )
