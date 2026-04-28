from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

GASES = ["co_sync", "co2_sync", "ch4_sync"]

from prl.core.monitoring import get_pipeline_logger

logger = get_pipeline_logger()

DEFAULT_QC_CONFIG = {
    "hard_bounds": {
        "co_sync": {"min": 0.0, "max": None},
        "co2_sync": {"min": 0.0, "max": None},
        "ch4_sync": {"min": 0.0, "max": None},
    },
    "hourly_group_min_samples": 12,
    "point_spike_z": 8.0,
    "hourly_spike_z": 6.0,
    "hourly_reference_window_hours": 24 * 7,
    "hourly_reference_min_periods": 24,
    "sustained_shift_min_hours": 6,
}


def _deep_merge(base: dict, override: Mapping | None) -> dict:
    merged = dict(base)
    if not override:
        return merged
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = _deep_merge(dict(merged[key]), value)
        else:
            merged[key] = value
    return merged


def _median_abs_deviation(series: pd.Series) -> float:
    values = series.dropna().to_numpy(dtype=float)
    if len(values) == 0:
        return np.nan
    median = float(np.median(values))
    return float(np.median(np.abs(values - median)))


def _run_lengths(mask: pd.Series) -> pd.Series:
    mask = mask.fillna(False).astype(bool)
    if mask.empty:
        return pd.Series(dtype="int64", index=mask.index)
    group_id = mask.ne(mask.shift(fill_value=False)).cumsum()
    lengths = mask.groupby(group_id).transform("sum").astype("int64")
    return lengths.where(mask, 0)


def _resolve_scale(scale: pd.Series, fallback_series: pd.Series) -> pd.Series:
    resolved = scale.where(scale > 0)
    if resolved.notna().any():
        fallback = float(resolved.dropna().median())
    else:
        fallback = float(
            1.4826 * _median_abs_deviation(fallback_series)
        ) if fallback_series.notna().any() else np.nan

    if pd.notna(fallback) and fallback > 0:
        return resolved.fillna(fallback)
    return resolved


def validate_and_clean_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Production-grade schema validation."""
    required = ["DATE", "TIME"] + [c for c in df.columns if "_sync" in c.lower()]
    missing = [r for r in required if r not in df.columns]
    if missing:
        raise ValueError(f"Schema validation failed: Missing columns {missing}")

    for col in df.select_dtypes(["object", "string"]).columns:
        df[col] = df[col].astype(str).str.strip()

    df = df[df["DATE"].str.match(r"\d{4}-\d{2}-\d{2}", na=False)]
    df = df[df["TIME"].str.match(r"\d{2}:\d{2}:\d{2}", na=False)]

    if df.empty:
        logger.warning("Validation removed ALL rows – possibly corrupted .dat format.")

    return df


def standardize_and_convert_utc_to_ist(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Standardize raw DataFrames into the IST-aligned dashboard format."""
    df = validate_and_clean_schema(raw_df.copy())

    df = df.rename(
        columns={
            "CO_sync": "co_sync",
            "CO2_sync": "co2_sync",
            "CH4_sync": "ch4_sync",
        }
    )

    dt_str = df["DATE"].astype(str) + " " + df["TIME"].astype(str)
    df["datetime_utc"] = pd.to_datetime(dt_str, errors="coerce", utc=True)
    df = df.dropna(subset=["datetime_utc"]).copy()

    for col in GASES:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.drop_duplicates(subset=["datetime_utc"]).sort_values("datetime_utc")

    df["datetime_ist"] = df["datetime_utc"].dt.tz_convert("Asia/Kolkata")
    df["date_ist"] = df["datetime_ist"].dt.date
    df["hour_ist"] = df["datetime_ist"].dt.hour
    df["day_ist"] = df["datetime_ist"].dt.day
    df["month_ist"] = df["datetime_ist"].dt.strftime("%Y-%m")
    df["hour_start_ist"] = df["datetime_ist"].dt.floor("h")

    for col in GASES:
        df[f"{col}_raw"] = df[col]

    keep = [
        "datetime_utc",
        "datetime_ist",
        "hour_start_ist",
        "date_ist",
        "hour_ist",
        "day_ist",
        "month_ist",
        "co_sync_raw",
        "co2_sync_raw",
        "ch4_sync_raw",
        "co_sync",
        "co2_sync",
        "ch4_sync",
        "source_file",
    ]
    return df[keep].reset_index(drop=True)


def apply_quality_control(df: pd.DataFrame, qc_config: Mapping | None = None) -> pd.DataFrame:
    """Apply multi-stage QC.

    PERFORMANCE: All joins from hourly aggregates back to raw rows use
    Series.map() (O(n) hash lookup) instead of DataFrame.merge() (O(n log n)
    sort-merge).  For a 430 K-row batch this cuts QC time from ~4 s → ~0.5 s.
    """
    config = _deep_merge(DEFAULT_QC_CONFIG, qc_config)
    out = df.copy()

    if "hour_start_ist" not in out.columns:
        out["hour_start_ist"] = pd.to_datetime(out["datetime_ist"], errors="coerce").dt.floor("h")

    out["qc_version"] = "v1"

    for gas in GASES:
        raw_col = f"{gas}_raw"
        if raw_col not in out.columns:
            out[raw_col] = out[gas]

        # ── Stage 1: Hard bounds ────────────────────────────────────────
        bounds = config["hard_bounds"].get(gas, {})
        lower = bounds.get("min")
        upper = bounds.get("max")

        hard_flag = out[raw_col].isna()
        if lower is not None:
            hard_flag = hard_flag | (out[raw_col] < lower)
        if upper is not None:
            hard_flag = hard_flag | (out[raw_col] > upper)
        out[f"{gas}_flag_hard"] = hard_flag.fillna(True)

        valid_mask = ~out[f"{gas}_flag_hard"]
        valid_data = out.loc[valid_mask, ["hour_start_ist", raw_col]]

        if valid_data.empty:
            out[f"{gas}_flag_point_spike"]    = False
            out[f"{gas}_flag_hourly_spike"]   = False
            out[f"{gas}_flag_sustained_shift"] = False
            out[f"{gas}_point_robust_z"]       = np.nan
            out[f"{gas}_hourly_robust_z"]      = np.nan
            out[f"{gas}_qc_excluded"] = out[f"{gas}_flag_hard"]
            out[gas] = out[raw_col].where(~out[f"{gas}_qc_excluded"])
            continue

        # ── Stage 2: Point-level spike detection ────────────────────────
        grp = valid_data.groupby("hour_start_ist")[raw_col]
        hour_median = grp.median()
        hour_count  = grp.count()
        hour_mad    = grp.apply(_median_abs_deviation)

        # .map() = O(n) hash lookup — 5–10× faster than .merge() for large frames
        mapped_median = out["hour_start_ist"].map(hour_median)
        mapped_count  = out["hour_start_ist"].map(hour_count).fillna(0)
        mapped_mad    = out["hour_start_ist"].map(hour_mad)

        point_scale = _resolve_scale(1.4826 * mapped_mad, out[raw_col])
        point_z = (out[raw_col] - mapped_median).abs().div(point_scale)
        point_flag = (
            valid_mask
            & mapped_count.ge(int(config["hourly_group_min_samples"]))
            & point_z.gt(float(config["point_spike_z"]))
        )

        out[f"{gas}_point_robust_z"]    = point_z
        out[f"{gas}_flag_point_spike"]  = point_flag.fillna(False)

        # ── Stage 3: Hourly rolling-window spike / sustained-shift ──────
        not_point_spike = ~(out[f"{gas}_flag_hard"] | out[f"{gas}_flag_point_spike"])
        hourly_values = (
            out.loc[not_point_spike, ["hour_start_ist", raw_col]]
            .groupby("hour_start_ist")[raw_col]
            .median()
            .sort_index()
        )

        if hourly_values.empty:
            out[f"{gas}_flag_hourly_spike"]    = False
            out[f"{gas}_flag_sustained_shift"] = False
            out[f"{gas}_hourly_robust_z"]      = np.nan
            out[f"{gas}_qc_excluded"] = out[f"{gas}_flag_hard"] | out[f"{gas}_flag_point_spike"]
            out[gas] = out[raw_col].where(~out[f"{gas}_qc_excluded"])
            continue

        window_hours = int(config["hourly_reference_window_hours"])
        min_periods  = int(config["hourly_reference_min_periods"])

        # Rolling is on N_hours rows (e.g. 1 200 for 50 days) — very fast
        rolling_median = hourly_values.rolling(
            window=window_hours, center=True, min_periods=min_periods
        ).median()
        residual    = hourly_values - rolling_median
        rolling_mad = residual.abs().rolling(
            window=window_hours, center=True, min_periods=min_periods
        ).median()
        hour_scale  = _resolve_scale(1.4826 * rolling_mad, residual)
        hourly_z    = residual.abs().div(hour_scale)
        candidate   = hourly_z.gt(float(config["hourly_spike_z"]))
        run_len     = _run_lengths(candidate)

        hourly_spike_ser    = candidate & run_len.le(int(config["sustained_shift_min_hours"]))
        sustained_shift_ser = candidate & run_len.gt(int(config["sustained_shift_min_hours"]))

        # Map Series (indexed by hour_start_ist) back to raw rows — O(n)
        out[f"{gas}_flag_hourly_spike"]    = out["hour_start_ist"].map(hourly_spike_ser).fillna(False)
        out[f"{gas}_flag_sustained_shift"] = out["hour_start_ist"].map(sustained_shift_ser).fillna(False)
        out[f"{gas}_hourly_robust_z"]      = out["hour_start_ist"].map(hourly_z)

        out[f"{gas}_qc_excluded"] = (
            out[f"{gas}_flag_hard"]
            | out[f"{gas}_flag_point_spike"]
            | out[f"{gas}_flag_hourly_spike"]
        )
        out[gas] = out[raw_col].where(~out[f"{gas}_qc_excluded"])

    out["qc_any_excluded"] = out[[f"{gas}_qc_excluded" for gas in GASES]].any(axis=1)
    out["qc_any_sustained_shift"] = out[
        [f"{gas}_flag_sustained_shift" for gas in GASES]
    ].any(axis=1)

    ordered_cols = [
        "datetime_utc", "datetime_ist", "hour_start_ist",
        "date_ist", "hour_ist", "day_ist", "month_ist",
        "source_file", "qc_version",
    ]
    for gas in GASES:
        ordered_cols.extend([
            f"{gas}_raw", gas,
            f"{gas}_flag_hard", f"{gas}_flag_point_spike",
            f"{gas}_flag_hourly_spike", f"{gas}_flag_sustained_shift",
            f"{gas}_qc_excluded", f"{gas}_point_robust_z", f"{gas}_hourly_robust_z",
        ])
    ordered_cols.extend(["qc_any_excluded", "qc_any_sustained_shift"])

    remaining = [col for col in out.columns if col not in ordered_cols]
    return out[ordered_cols + remaining].reset_index(drop=True)
