from __future__ import annotations

import pandas as pd

from prl.core.constants import GASES


def build_daily_diurnal_matrix(df: pd.DataFrame, gas: str) -> pd.DataFrame:
    matrix = (
        df.groupby(["date_ist", "hour_ist"], as_index=False)[gas]
        .mean()
        .pivot(index="hour_ist", columns="date_ist", values=gas)
        .sort_index()
    )
    matrix.index.name = "hour_ist"
    return matrix


def build_range_24_point_for_gas(matrix: pd.DataFrame, gas: str) -> pd.DataFrame:
    return matrix.mean(axis=1).reset_index(name=f"avg_{gas}")


def build_hourly_diurnal_stats(matrix: pd.DataFrame) -> pd.DataFrame:
    values = matrix.copy()
    mean = values.mean(axis=1)
    median = values.median(axis=1)
    std = values.std(axis=1, ddof=1).fillna(0.0)

    out = pd.DataFrame(
        {
            "hour_ist": values.index.astype(int),
            "mean": mean.to_numpy(dtype=float),
            "median": median.to_numpy(dtype=float),
            "std": std.to_numpy(dtype=float),
        }
    )
    out["upper"] = out["mean"] + out["std"]
    out["lower"] = out["mean"] - out["std"]
    return out.sort_values("hour_ist").reset_index(drop=True)


def build_daily_mean_median_stats(matrix: pd.DataFrame) -> pd.DataFrame:
    if matrix.empty:
        return pd.DataFrame(columns=["date_ist", "mean", "median"])

    mean = matrix.mean(axis=0)
    median = matrix.median(axis=0)
    return (
        pd.DataFrame(
            {
                "date_ist": mean.index,
                "mean": mean.to_numpy(dtype=float),
                "median": median.to_numpy(dtype=float),
            }
        )
        .sort_values("date_ist")
        .reset_index(drop=True)
    )


def build_24_point_profile_all_gases(df: pd.DataFrame) -> pd.DataFrame:
    present_gases = [g for g in GASES if g in df.columns]
    return (
        df.groupby("hour_ist", as_index=False)[present_gases]
        .mean()
        .sort_values("hour_ist")
    )


def build_hourly_mean_timeseries(df: pd.DataFrame) -> pd.DataFrame:
    # Work on a copy so original 5-second data frame remains unchanged.
    values = df.copy()
    values = values.dropna(subset=["datetime_ist"]).sort_values("datetime_ist")
    present_gases = [g for g in GASES if g in values.columns]
    return (
        values.set_index("datetime_ist")[present_gases]
        .resample("1h")
        .mean()
        .reset_index()
    )
