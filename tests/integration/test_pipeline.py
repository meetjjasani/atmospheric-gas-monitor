from __future__ import annotations

from pathlib import Path

import pandas as pd

from prl.core.ingest.service import discover_dat_files, load_all, read_dat_file
from prl.core.preprocess.service import standardize_and_convert_utc_to_ist


def test_ingest_discovers_and_reads_sync_files(tmp_path: Path) -> None:
    month_dir = tmp_path / "11" / "01"
    month_dir.mkdir(parents=True)
    dat_file = month_dir / "CFKADS-20251101-000014Z-DataLog_User_Sync.dat"
    dat_file.write_text(
        "DATE TIME CO_sync CO2_sync CH4_sync\n"
        "2025-11-01 00:00:00 1.0 400.0 1.8\n"
        "2025-11-01 00:00:05 1.1 401.0 1.9\n",
        encoding="utf-8",
    )

    discovered = discover_dat_files(tmp_path, month_dirs=["11"])
    assert discovered == [dat_file]

    frame = read_dat_file(dat_file)
    assert list(frame.columns) == ["DATE", "TIME", "CO_sync", "CO2_sync", "CH4_sync", "source_file"]
    assert len(frame) == 2

    loaded = load_all(tmp_path, month_dirs=["11"])
    assert len(loaded) == 2


def test_preprocess_standardizes_and_converts_to_ist() -> None:
    raw = pd.DataFrame(
        {
            "DATE": ["2025-11-01", "2025-11-01"],
            "TIME": ["00:00:00", "01:00:00"],
            "CO_sync": ["1.0", "1.5"],
            "CO2_sync": ["400.0", "405.0"],
            "CH4_sync": ["1.8", "1.9"],
            "source_file": ["a.dat", "a.dat"],
        }
    )

    standardized = standardize_and_convert_utc_to_ist(raw)

    assert {"datetime_utc", "datetime_ist", "co_sync", "co2_sync", "ch4_sync"}.issubset(
        standardized.columns
    )
    assert len(standardized) == 2
    assert standardized["datetime_ist"].dt.tz is not None
    assert standardized["hour_start_ist"].notna().all()
