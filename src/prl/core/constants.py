from __future__ import annotations

from prl.infrastructure.runtime_paths import bundled_processed_dir


DATA_PROCESSED_DIR = bundled_processed_dir()
DATA_PARQUET = DATA_PROCESSED_DIR / "processed_master.parquet"
DATA_CSV = DATA_PROCESSED_DIR / "processed_master.csv"
GASES = ["co_sync", "co2_sync", "ch4_sync"]
