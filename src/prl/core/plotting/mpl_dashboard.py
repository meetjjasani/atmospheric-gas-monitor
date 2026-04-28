from __future__ import annotations

from datetime import date

import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from matplotlib.axes import Axes

from prl.core.correlation.service import regression_stats


GAS_LABELS = {
    "co_sync": "CO (ppm)",
    "co2_sync": "CO2 (ppm)",
    "ch4_sync": "CH4 (ppm)",
    "co2_over_co_plus_co2": "CO2 / (CO + CO2)",
}

GAS_NAMES = {
    "co_sync": "CO",
    "co2_sync": "CO2",
    "ch4_sync": "CH4",
    "co2_over_co_plus_co2": "CO2 / (CO + CO2)",
}


def _style_axes(ax: Axes) -> None:
    ax.set_facecolor("#fbfcfe")
    ax.grid(True, alpha=0.18, linewidth=0.8)
    for spine in ax.spines.values():
        spine.set_color("#d7dce5")


def _title_date_range(start_date: date, end_date: date) -> str:
    start_text = pd.to_datetime(start_date).strftime("%d/%m/%Y")
    end_text = pd.to_datetime(end_date).strftime("%d/%m/%Y")
    return start_text if start_text == end_text else f"{start_text} to {end_text}"


def _sample_tick_labels(labels: list[str]) -> tuple[list[int], list[str]]:
    if not labels:
        return [], []
    if len(labels) <= 10:
        step = 1
    elif len(labels) <= 20:
        step = 2
    elif len(labels) <= 45:
        step = 5
    else:
        step = 7
    indices = list(range(0, len(labels), step))
    if indices[-1] != len(labels) - 1:
        indices.append(len(labels) - 1)
    return indices, [labels[i] for i in indices]


def render_correlation(
    ax: Axes,
    corr_df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    fit_start: int,
    fit_end: int,
) -> dict:
    ax.clear()
    _style_axes(ax)

    pair = corr_df[[x_col, y_col, "datetime_ist"]].dropna()
    if pair.empty:
        ax.set_title(f"{title}\nNo data available")
        return {
            "n": 0,
            "pearson_r": np.nan,
            "r2": np.nan,
            "slope": np.nan,
            "intercept": np.nan,
            "x": np.array([]),
            "y": np.array([]),
        }

    hours = pd.to_datetime(pair["datetime_ist"], errors="coerce").dt.hour.to_numpy(dtype=float)
    scatter = ax.scatter(
        pair[x_col].to_numpy(dtype=float),
        pair[y_col].to_numpy(dtype=float),
        c=hours,
        cmap="jet",
        s=20,
        alpha=0.85,
        edgecolors="black",
        linewidths=0.25,
    )
    colorbar = ax.figure.colorbar(scatter, ax=ax, pad=0.02)
    colorbar.set_label("IST Hour")

    fit_source = corr_df.loc[
        pd.to_datetime(corr_df["datetime_ist"], errors="coerce").dt.hour.between(fit_start, fit_end)
    ]
    stats = regression_stats(fit_source, x_col, y_col)
    if stats["n"] >= 2:
        xline = np.array([np.nanmin(stats["x"]), np.nanmax(stats["x"])])
        yline = stats["slope"] * xline + stats["intercept"]
        fit_text = f"Fit {fit_start:02d}-{fit_end:02d} IST, r={stats['pearson_r']:.3f}"
        ax.plot(xline, yline, color="black", linewidth=1.8, label=fit_text)
        ax.legend(frameon=False, loc="best")

    ax.set_title(title)
    ax.set_xlabel(GAS_LABELS.get(x_col, x_col))
    ax.set_ylabel(GAS_LABELS.get(y_col, y_col))
    return stats


def render_diurnal(ax: Axes, stats_df: pd.DataFrame, gas: str, start_date: date, end_date: date) -> None:
    ax.clear()
    _style_axes(ax)

    ax.plot(stats_df["hour_ist"], stats_df["mean"], color="#1664c0", linewidth=2.2, label="Mean")
    ax.plot(
        stats_df["hour_ist"],
        stats_df["median"],
        color="#ef7d1a",
        linewidth=1.9,
        linestyle="--",
        label="Median",
    )
    ax.fill_between(
        stats_df["hour_ist"],
        stats_df["lower"],
        stats_df["upper"],
        color="#1664c0",
        alpha=0.12,
        label="Mean ± SD",
    )

    ax.set_xlim(0, 23)
    ax.set_xticks(range(24))
    ax.set_title(f"24-point diurnal average ({GAS_NAMES.get(gas, gas)}) | {_title_date_range(start_date, end_date)}")
    ax.set_xlabel("Hour IST")
    ax.set_ylabel(GAS_LABELS.get(gas, gas))
    ax.legend(frameon=False, loc="best")


def render_daily_mean_median(
    ax: Axes, daily_stats: pd.DataFrame, gas: str, start_date: date, end_date: date
) -> None:
    ax.clear()
    _style_axes(ax)

    labels = [pd.to_datetime(value).strftime("%d/%m") for value in daily_stats["date_ist"]]
    x = np.arange(len(labels))
    width = 0.42
    ax.bar(x - width / 2, daily_stats["mean"], width=width, color="#1664c0", label="Mean")
    ax.bar(x + width / 2, daily_stats["median"], width=width, color="#ef7d1a", label="Median")

    tick_idx, tick_labels = _sample_tick_labels(labels)
    ax.set_xticks(tick_idx, tick_labels)
    ax.set_title(
        f"Daily mean & median ({GAS_NAMES.get(gas, gas)}) | {_title_date_range(start_date, end_date)}"
    )
    ax.set_xlabel("Date (IST)")
    ax.set_ylabel(GAS_LABELS.get(gas, gas))
    ax.legend(frameon=False, loc="best")


def render_hourly_mean(ax: Axes, hourly: pd.DataFrame, gas: str, start_date: date, end_date: date) -> None:
    ax.clear()
    _style_axes(ax)

    x = pd.to_datetime(hourly["datetime_ist"], errors="coerce")
    ax.plot(x, hourly[gas], color="#1664c0", linewidth=1.7)
    ax.set_title(
        f"Hourly mean ({GAS_NAMES.get(gas, gas)}) | {_title_date_range(start_date, end_date)}"
    )
    ax.set_xlabel("Datetime IST")
    ax.set_ylabel(GAS_LABELS.get(gas, gas))
    locator = mdates.AutoDateLocator(minticks=4, maxticks=10)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))


def render_heatmap(ax: Axes, matrix: pd.DataFrame, gas: str, start_date: date, end_date: date) -> None:
    ax.clear()
    _style_axes(ax)

    display = matrix.transpose().sort_index()
    image = ax.imshow(display.to_numpy(dtype=float), aspect="auto", cmap="viridis", origin="upper")
    colorbar = ax.figure.colorbar(image, ax=ax, pad=0.02)
    colorbar.set_label(GAS_LABELS.get(gas, gas))

    ax.set_title(
        f"Heatmap ({GAS_NAMES.get(gas, gas)}) | {_title_date_range(start_date, end_date)}"
    )
    ax.set_xlabel("Hour IST")
    ax.set_ylabel("Date")
    ax.set_xticks(range(24))

    y_labels = [pd.to_datetime(value).strftime("%d/%m") for value in display.index]
    tick_idx, tick_labels = _sample_tick_labels(y_labels)
    ax.set_yticks(tick_idx, tick_labels)
