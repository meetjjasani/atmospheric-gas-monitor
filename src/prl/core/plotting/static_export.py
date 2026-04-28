from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Force non-interactive backend for background threads
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot_hourly_mean(hourly_df: pd.DataFrame, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(12, 5))
    for col in ["co_sync", "co2_sync", "ch4_sync"]:
        ax.plot(hourly_df["hour_start_ist"], hourly_df[col], label=col, linewidth=1)
    ax.set_title("Hourly Mean (IST)")
    ax.set_xlabel("IST Time")
    ax.set_ylabel("Concentration")
    ax.legend()
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_monthly_diurnal(monthly_24_df: pd.DataFrame, gas: str, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    for month, mdf in monthly_24_df.groupby("month_ist"):
        ax.plot(mdf["hour_ist"], mdf[gas], marker="o", markersize=3, label=month)
    ax.set_title(f"Monthly Diurnal 24-Point ({gas}, IST)")
    ax.set_xlabel("Hour IST")
    ax.set_ylabel(gas)
    ax.set_xticks(range(24))
    ax.legend(title="Month")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_scatter_with_fit(df: pd.DataFrame, x_col: str, y_col: str, out_path: Path) -> None:
    pair = df[[x_col, y_col]].dropna()
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(pair[x_col], pair[y_col], s=5, alpha=0.4)

    if len(pair) >= 2:
        coeff = float(pair[y_col].corr(pair[x_col]))
        slope, intercept = np.polyfit(pair[x_col], pair[y_col], 1)
        xline = np.array([pair[x_col].min(), pair[x_col].max()])
        yline = slope * xline + intercept
        ax.plot(xline, yline, color="red", linewidth=2, label=f"r={coeff:.3f}")
        ax.legend()

    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title(f"{y_col} vs {x_col}")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
