from __future__ import annotations

import pandas as pd

GASES = ["co_sync", "co2_sync", "ch4_sync"]

def build_quality_report(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in GASES:
        series = df[col]
        raw_col = f"{col}_raw"
        raw_series = df[raw_col] if raw_col in df.columns else series
        rows.append(
            {
                "column": col,
                "rows": int(len(df)),
                "raw_missing": int(raw_series.isna().sum()),
                "raw_missing_pct": float(raw_series.isna().mean() * 100),
                "clean_missing": int(series.isna().sum()),
                "clean_missing_pct": float(series.isna().mean() * 100),
                "hard_flags": int(df.get(f"{col}_flag_hard", pd.Series(False, index=df.index)).sum()),
                "point_spikes": int(
                    df.get(f"{col}_flag_point_spike", pd.Series(False, index=df.index)).sum()
                ),
                "hourly_spikes": int(
                    df.get(f"{col}_flag_hourly_spike", pd.Series(False, index=df.index)).sum()
                ),
                "sustained_shifts": int(
                    df.get(f"{col}_flag_sustained_shift", pd.Series(False, index=df.index)).sum()
                ),
                "excluded_points": int(
                    df.get(f"{col}_qc_excluded", pd.Series(False, index=df.index)).sum()
                ),
                "raw_min": float(raw_series.min(skipna=True)) if raw_series.notna().any() else None,
                "raw_max": float(raw_series.max(skipna=True)) if raw_series.notna().any() else None,
                "clean_min": float(series.min(skipna=True)) if series.notna().any() else None,
                "clean_max": float(series.max(skipna=True)) if series.notna().any() else None,
                "clean_mean": float(series.mean(skipna=True)) if series.notna().any() else None,
            }
        )

    duplicate_utc = int(df["datetime_utc"].duplicated().sum())
    rows.append(
        {
            "column": "datetime_utc",
            "rows": int(len(df)),
            "raw_missing": None,
            "raw_missing_pct": None,
            "clean_missing": int(df["datetime_utc"].isna().sum()),
            "clean_missing_pct": float(df["datetime_utc"].isna().mean() * 100),
            "hard_flags": None,
            "point_spikes": None,
            "hourly_spikes": None,
            "sustained_shifts": None,
            "excluded_points": None,
            "raw_min": None,
            "raw_max": None,
            "clean_min": None,
            "clean_max": None,
            "clean_mean": None,
            "duplicate_rows": duplicate_utc,
        }
    )

    return pd.DataFrame(rows)
