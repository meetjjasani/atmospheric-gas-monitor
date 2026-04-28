from __future__ import annotations

import pandas as pd

from prl.core.metrics.pipeline_metrics import (
    daily_diurnal_matrix,
    hourly_mean_timeseries,
    monthly_diurnal_24point,
)
from prl.core.preprocess.service import apply_quality_control


def _sample_frame() -> pd.DataFrame:
    timestamps = pd.to_datetime(
        [
            "2025-11-01 05:30:00+05:30",
            "2025-11-01 05:45:00+05:30",
            "2025-11-01 06:15:00+05:30",
            "2025-11-02 05:30:00+05:30",
        ]
    )
    return pd.DataFrame(
        {
            "datetime_utc": timestamps.tz_convert("UTC"),
            "datetime_ist": timestamps,
            "hour_start_ist": timestamps.floor("h"),
            "date_ist": timestamps.date,
            "hour_ist": timestamps.hour,
            "day_ist": timestamps.day,
            "month_ist": timestamps.strftime("%Y-%m"),
            "source_file": ["a.dat"] * 4,
            "co_sync_raw": [1.0, 1.2, 1.4, 1.6],
            "co2_sync_raw": [400.0, 402.0, 404.0, 406.0],
            "ch4_sync_raw": [1.8, 1.9, 2.0, 2.1],
            "co_sync": [1.0, 1.2, 1.4, 1.6],
            "co2_sync": [400.0, 402.0, 404.0, 406.0],
            "ch4_sync": [1.8, 1.9, 2.0, 2.1],
        }
    )


def test_apply_quality_control_preserves_valid_values() -> None:
    qc = apply_quality_control(_sample_frame())
    assert "qc_any_excluded" in qc.columns
    assert qc["co_sync"].notna().all()
    assert qc["co2_sync"].notna().all()
    assert qc["ch4_sync"].notna().all()


def test_pipeline_metrics_generate_expected_shapes() -> None:
    df = _sample_frame()

    hourly = hourly_mean_timeseries(df)
    assert {"hour_start_ist", "co_sync", "co2_sync", "ch4_sync"} == set(hourly.columns)
    assert len(hourly) >= 2

    diurnal = daily_diurnal_matrix(df, gas="co2_sync")
    assert "hour_ist" in diurnal.columns
    assert len(diurnal) >= 1

    monthly = monthly_diurnal_24point(df, gas="co_sync")
    assert {"month_ist", "hour_ist", "co_sync"} == set(monthly.columns)
