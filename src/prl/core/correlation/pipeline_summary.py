from __future__ import annotations

import numpy as np
import pandas as pd


def _pair_stats(df: pd.DataFrame, x_col: str, y_col: str) -> dict:
    pair = df[[x_col, y_col]].dropna()
    n = len(pair)
    if n < 2:
        return {
            "x": x_col,
            "y": y_col,
            "n": n,
            "pearson_r": np.nan,
            "slope": np.nan,
            "intercept": np.nan,
            "r2": np.nan,
        }

    x = pair[x_col].to_numpy(dtype=float)
    y = pair[y_col].to_numpy(dtype=float)

    pearson_r = float(np.corrcoef(x, y)[0, 1])
    slope, intercept = np.polyfit(x, y, 1)
    y_hat = slope * x + intercept
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = float(1 - ss_res / ss_tot) if ss_tot else np.nan

    return {
        "x": x_col,
        "y": y_col,
        "n": n,
        "pearson_r": pearson_r,
        "slope": float(slope),
        "intercept": float(intercept),
        "r2": r2,
    }


def build_correlation_summary(df: pd.DataFrame) -> pd.DataFrame:
    stats = [
        _pair_stats(df, x_col="co2_sync", y_col="co_sync"),
        _pair_stats(df, x_col="co2_sync", y_col="ch4_sync"),
    ]
    return pd.DataFrame(stats)


def build_monthly_correlation_summary(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for month, mdf in df.groupby("month_ist"):
        s1 = _pair_stats(mdf, x_col="co2_sync", y_col="co_sync")
        s2 = _pair_stats(mdf, x_col="co2_sync", y_col="ch4_sync")
        s1["month_ist"] = month
        s2["month_ist"] = month
        records.extend([s1, s2])
    cols = ["month_ist", "x", "y", "n", "pearson_r", "slope", "intercept", "r2"]
    return pd.DataFrame(records)[cols]
