from __future__ import annotations

import numpy as np
import pandas as pd

from prl.core.constants import GASES


def build_correlation_frame(filtered_df: pd.DataFrame) -> pd.DataFrame:
    # Dynamic filtering: only use gases that are actually present in the input DataFrame
    present_gases = [g for g in GASES if g in filtered_df.columns]
    
    corr = (
        filtered_df.set_index("datetime_ist")[present_gases]
        .resample("1h")
        .mean()
        .dropna(how="all")
        .reset_index()
    )
    
    # Ratios require specific columns
    if "co_sync" in corr.columns and "co2_sync" in corr.columns:
        denom = corr["co_sync"] + corr["co2_sync"]
        corr["co_over_co_plus_co2"] = np.where(denom > 0, corr["co_sync"] / denom, np.nan)
        corr["co2_over_co_plus_co2"] = np.where(denom > 0, corr["co2_sync"] / denom, np.nan)

    return corr


def regression_stats(df: pd.DataFrame, x_col: str, y_col: str) -> dict:
    pair = df[[x_col, y_col]].dropna()
    n = len(pair)
    if n < 2:
        return {
            "n": n,
            "pearson_r": np.nan,
            "r2": np.nan,
            "slope": np.nan,
            "intercept": np.nan,
            "x": np.array([]),
            "y": np.array([]),
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
        "n": n,
        "pearson_r": pearson_r,
        "r2": r2,
        "slope": float(slope),
        "intercept": float(intercept),
        "x": x,
        "y": y,
    }
