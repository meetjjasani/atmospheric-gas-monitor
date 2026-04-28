from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


def ensure_dirs(paths: Iterable[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def write_table(df: pd.DataFrame, path: Path) -> Path:
    """Write parquet when possible; fallback to CSV if parquet engine is missing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".parquet":
        try:
            df.to_parquet(path, index=False)
            return path
        except Exception:
            fallback = path.with_suffix(".csv")
            df.to_csv(fallback, index=False)
            return fallback
    df.to_csv(path, index=False)
    return path
