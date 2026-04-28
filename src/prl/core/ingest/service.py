from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterable, Iterator

import pandas as pd

from prl.core.storage.catalog import FileCatalog




REQUIRED_COLUMNS = ["DATE", "TIME", "CO_sync", "CO2_sync", "CH4_sync"]


def discover_dat_files(data_root: Path, month_dirs: Iterable[str] | None = None) -> list[Path]:
    dirs: list[Path]
    if month_dirs:
        dirs = [data_root / m for m in month_dirs]
    else:
        dirs = [p for p in data_root.iterdir() if p.is_dir() and p.name.isdigit()]

    files: list[Path] = []
    for month_dir in sorted(dirs):
        if not month_dir.exists():
            continue
        files.extend(sorted(month_dir.rglob("*DataLog_User_Sync.dat")))
    return files


def read_dat_file(path: Path) -> pd.DataFrame:
    """Read a single CRDS .dat file with a high-speed 'Fast-First' approach."""
    # Explicit types to avoid guessing overhead and memory pressure
    dtypes = {
        "DATE": "string",
        "TIME": "string",
        "CO_sync": "float64",
        "CO2_sync": "float64",
        "CH4_sync": "float64"
    }

    # -- Tier 1: Fast Path (99% of real data) --
    # Directly use the super-fast C engine with whitespace delimiter
    try:
        # We try the standard CRDS format first (Header on line 0, multiple spaces)
        df = pd.read_csv(
            path, 
            sep=r"\s+", 
            engine="c", 
            usecols=REQUIRED_COLUMNS,
            dtype=dtypes,
            low_memory=False
        )
        # Note: If this succeeded, df only has the 5 columns we need.
        df["source_file"] = str(path)
        return df
    except Exception:
        # -- Tier 2: Safe Path (Synthetic or Malformed) --
        # If Tier 1 fails, use the robust Header Detection scanner
        return _read_dat_file_safe(path)

def _read_dat_file_safe(path: Path) -> pd.DataFrame:
    """Robust fallback: Scans for the header line before reading."""
    header_idx = 0
    with open(path, "r", errors="ignore") as f:
        for i, line in enumerate(f):
            upper_line = line.upper()
            if "DATE" in upper_line and "TIME" in upper_line:
                header_idx = i
                break
            if i > 100: break

    # Extract column names (Case Insensitive)
    try:
        header_df = pd.read_csv(path, sep=r"\s+", engine="python", skiprows=header_idx, nrows=0)
    except Exception:
        header_df = pd.read_csv(path, sep=None, engine="python", skiprows=header_idx, nrows=0)

    col_map = {}
    for target in REQUIRED_COLUMNS:
        match = next((c for c in header_df.columns if c.strip().upper() == target.upper()), None)
        if match: col_map[match] = target

    if len(col_map) < len(REQUIRED_COLUMNS):
        missing = [t for t in REQUIRED_COLUMNS if t not in col_map.values()]
        raise ValueError(f"Missing required columns {missing} in {path}")

    # Read data with the found header index
    try:
        df = pd.read_csv(path, sep=r"\s+", engine="python", skiprows=header_idx, usecols=list(col_map.keys()))
    except Exception:
        df = pd.read_csv(path, sep=None, engine="python", skiprows=header_idx, usecols=list(col_map.keys()))

    df = df.rename(columns=col_map)
    df["source_file"] = str(path)
    return df






def load_all(data_root: Path, month_dirs: Iterable[str] | None = None) -> pd.DataFrame:
    files = discover_dat_files(data_root, month_dirs=month_dirs)
    if not files:
        raise FileNotFoundError("No CRDS .dat files found.")

    frames = [read_dat_file(path) for path in files]
    return pd.concat(frames, ignore_index=True)


def stream_folders(
    folder_paths: Iterable[Path], 
    catalog_path: Path | None = None,
    batch_size: int = 50,
    force_reimport: bool = False
) -> Iterator[tuple[pd.DataFrame, list[Path], int]]:
    """Discover and stream .dat files in processed batches.
    
    Yields (DataFrame Batch, List of file paths, Total count of skipped files in the entire session).
    """
    # 1. Discovery
    files: list[Path] = []
    def _find_files(folder: Path) -> list[Path]:
        if folder.exists() and folder.is_dir():
            return sorted(list(folder.rglob("*.dat")))
        return []

    with ThreadPoolExecutor(max_workers=8) as discovery_executor:
        discovery_results = list(discovery_executor.map(_find_files, folder_paths))
    
    for result_list in discovery_results:
        files.extend(result_list)

    if not files:
        return

    # 2. Incremental Filter
    num_skipped = 0
    catalog = FileCatalog(catalog_path) if catalog_path else None
    
    if catalog and not force_reimport:
        new_files = [f for f in files if not catalog.is_processed(f)]
        num_skipped = len(files) - len(new_files)
        if not new_files:
            return
    else:
        new_files = files

    # 3. Batch Streaming
    for i in range(0, len(new_files), batch_size):
        chunk = new_files[i : i + batch_size]
        
        def _safe_read(path: Path) -> pd.DataFrame | None:
            try:
                return read_dat_file(path)
            except (ValueError, pd.errors.EmptyDataError):
                return None

        with ThreadPoolExecutor(max_workers=min(24, len(chunk))) as load_executor:
            results = list(load_executor.map(_safe_read, chunk))

        frames = [f for f in results if f is not None]
        processed_paths = [chunk[idx] for idx, f in enumerate(results) if f is not None]

        if frames:
            yield pd.concat(frames, ignore_index=True), processed_paths, num_skipped


def load_folders(
    folder_paths: Iterable[Path], 
    catalog_path: Path | None = None,
    force_reimport: bool = False
) -> tuple[pd.DataFrame, list[Path], int]:
    """Legacy compatibility: Consumes the full stream into a single DataFrame."""
    all_frames = []
    all_paths = []
    total_skipped = 0
    for df, paths, skipped in stream_folders(folder_paths, catalog_path, force_reimport=force_reimport):
        all_frames.append(df)
        all_paths.extend(paths)
        total_skipped = skipped
        
    if not all_frames:
        return pd.DataFrame(), [], total_skipped
        
    return pd.concat(all_frames, ignore_index=True), all_paths, total_skipped
