from __future__ import annotations

import pandas as pd

GASES = ["co_sync", "co2_sync", "ch4_sync"]


def hourly_mean_timeseries(df: pd.DataFrame) -> pd.DataFrame:
    hourly = (
        df.set_index("datetime_ist")[GASES]
        .resample("1h")
        .mean()
        .reset_index()
        .rename(columns={"datetime_ist": "hour_start_ist"})
    )
    return hourly


def daily_diurnal_matrix(df: pd.DataFrame, gas: str = "co2_sync") -> pd.DataFrame:
    grouped = (
        df.groupby(["date_ist", "hour_ist"], as_index=False)[gas]
        .mean()
        .pivot(index="hour_ist", columns="date_ist", values=gas)
        .sort_index()
    )
    grouped.index.name = "hour_ist"
    return grouped.reset_index()


def monthly_diurnal_24point(df: pd.DataFrame, gas: str) -> pd.DataFrame:
    out = (
        df.groupby(["month_ist", "hour_ist"], as_index=False)[gas]
        .mean()
        .sort_values(["month_ist", "hour_ist"])
    )
    return out


def monthly_hour_day_matrix(df: pd.DataFrame, gas: str) -> pd.DataFrame:
    base = (
        df.groupby(["month_ist", "day_ist", "hour_ist"], as_index=False)[gas]
        .mean()
        .sort_values(["month_ist", "day_ist", "hour_ist"])
    )
    pivoted = base.pivot_table(
        index=["month_ist", "hour_ist"],
        columns="day_ist",
        values=gas,
        aggfunc="mean",
    )
    return pivoted.reset_index()
