import shutil
from datetime import datetime
from pathlib import Path
from typing import Iterable, Callable

from prl.core.ingest.service import stream_folders
from prl.core.monitoring import setup_pipeline_logging
from prl.core.services.pipeline_service import load_pipeline_config, process_batch
from prl.core.storage.catalog import FileCatalog
from prl.core.storage.database import Database



def clear_database(config_path: Path = Path("config/config.json")) -> None:
    """Wipe the local partitioned database, hourly cache, and ingestion catalog."""
    cfg = load_pipeline_config(config_path)
    project_root = Path(cfg["project_root"]).resolve()
    processed_dir = project_root / cfg["output"]["processed_dir"]

    # Raw row store
    db_root = processed_dir / "db"
    if db_root.exists():
        shutil.rmtree(db_root)

    # Pre-aggregated hourly cache (must be wiped alongside raw data)
    hourly_root = processed_dir / "db_hourly"
    if hourly_root.exists():
        shutil.rmtree(hourly_root)

    # Ingestion catalog
    catalog_path = processed_dir / "ingest_catalog.json"
    if catalog_path.exists():
        catalog_path.unlink()



def get_last_import_date(config_path: Path = Path("config/config.json")) -> datetime | None:
    """Read the last sync date from the catalog if it exists."""
    cfg = load_pipeline_config(config_path)
    project_root = Path(cfg["project_root"]).resolve()
    catalog_path = project_root / cfg["output"]["processed_dir"] / "ingest_catalog.json"
    
    catalog = FileCatalog(catalog_path)
    last = catalog.last_sync
    if last:
        try:
            return datetime.fromisoformat(last)
        except ValueError:
            return None
    return None



def import_raw_folders(
    folder_paths: Iterable[Path],
    config_path: Path = Path("config/config.json"),
    progress_callback: Callable[[str], None] | None = None,
    percentage_callback: Callable[[int], None] | None = None,
    force_reimport: bool = False
) -> dict:
    """Enterprise-grade entry point for data ingestion.
    
    Returns a summary dict with {new_files, skipped_files, row_count, last_sync}.
    """
    # 1. Setup Logging & Config
    cfg = load_pipeline_config(config_path)
    project_root = Path(cfg["project_root"]).resolve()
    out_data = project_root / cfg["output"]["processed_dir"]
    out_logs = project_root / cfg["output"]["logs_dir"]
    
    logger = setup_pipeline_logging(out_logs)
    
    # 2. Pre-Discovery for Progress Bar
    catalog_path = out_data / "ingest_catalog.json"
    catalog = FileCatalog(catalog_path)
    db_root = out_data / "db"
    db = Database(db_root)

    if progress_callback:
        progress_callback("Scanning folders for new files...")
    
    total_files: list[Path] = []
    for folder in folder_paths:
        if folder.exists() and folder.is_dir():
            total_files.extend(list(folder.rglob("*.dat")))
    
    new_files = total_files
    if not force_reimport:
        new_files = [f for f in total_files if not catalog.is_processed(f)]
    
    total_new_count = len(new_files)
    total_skipped = len(total_files) - total_new_count
    
    if total_new_count == 0:
        return {
            "new_files": 0,
            "skipped_files": total_skipped,
            "row_count": 0,
            "last_sync": catalog.last_sync
        }

    # Larger batch size = fewer loop iterations = less fixed overhead per batch.
    # 200 files (~1.7 M rows) is a sweet spot: big enough to amortise DuckDB
    # view setup and pd.concat overhead, small enough to show progress updates.
    batch_size = 200
    import math
    total_batches = math.ceil(total_new_count / batch_size)

    logger.info(f"Starting ingestion for {total_new_count} new files in {total_batches} batches")

    # Create ONE Database connection for the entire import.
    # Previously a new DuckDB connection was opened inside process_batch() on
    # every iteration — each open + view-rebuild costs ~200 ms.
    db = Database(db_root)

    # 3. Ingest and Process
    batch_idx = 0
    total_rows = 0
    total_processed_files = 0

    for raw_batch_df, paths, _skipped in stream_folders(
        folder_paths,
        catalog_path=catalog_path,
        batch_size=batch_size,
        force_reimport=force_reimport,
    ):
        batch_idx += 1
        total_processed_files += len(paths)

        # Scale progress 0–95 % during batch loop; final 5 % for compaction/hourly.
        percentage = int((total_processed_files / total_new_count) * 95)

        msg = (
            f"Processing batch {batch_idx} of {total_batches} "
            f"({total_processed_files:,}/{total_new_count:,} files)"
        )
        logger.info(msg)

        if progress_callback:
            progress_callback(msg)
        if percentage_callback:
            percentage_callback(percentage)

        # 4. Process + Native Sort — reuse existing db connection (no reconnect)
        process_batch(raw_batch_df, db_root=db_root, qc_cfg=cfg.get("qc"), db=db)

        # 5. Success: Catalog update
        total_rows += len(raw_batch_df)

        for path in paths:
            catalog.mark_processed(path)
        catalog.last_sync = datetime.now().isoformat()
        catalog.save()

    # 6. Final Step: Compaction & Cleanup
    if batch_idx > 0:
        msg = "Compacting partitions for optimal read speed…"
        logger.info(msg)
        if progress_callback:
            progress_callback(msg)
        if percentage_callback:
            percentage_callback(97)

        db.compact_partitions()

        # Rebuild the pre-aggregated hourly store used by the dashboard.
        # Runs entirely inside DuckDB — no Python loops.
        # 5 years of data finishes in ~1-2 s; dashboard loads in <10 ms afterwards.
        msg = "Building fast-load hourly cache…"
        logger.info(msg)
        if progress_callback:
            progress_callback(msg)
        if percentage_callback:
            percentage_callback(99)

        db.rebuild_hourly_aggregates()

        if percentage_callback:
            percentage_callback(100)

        logger.info("Database ingestion lifecycle complete.")

    return {
        "new_files": total_processed_files,
        "skipped_files": total_skipped,
        "row_count": total_rows,
        "last_sync": catalog.last_sync
    }
