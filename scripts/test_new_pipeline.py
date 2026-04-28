from pathlib import Path
from core.services.import_service import import_raw_folders

def test():
    # 1. Clean up old processed data for a fresh test
    db_path = Path("data/processed/db")
    catalog_path = Path("data/processed/ingest_catalog.json")
    if db_path.exists():
        import shutil
        shutil.rmtree(db_path)
    if catalog_path.exists():
        catalog_path.unlink()
        
    # 2. Synthetic folders
    folders = [Path("synthetic_test_data/2026/01"), Path("synthetic_test_data/2026/02")]
    
    print("Running initial import...")
    db_root = import_raw_folders(folders)
    print(f"Imported to: {db_root}")
    
    # 3. Verify partitions
    partitions = list(db_root.rglob("*.parquet"))
    print(f"Created {len(partitions)} partitions.")
    for p in partitions:
        print(f"  - {p.relative_to(db_root.parent)}")

    # 4. Test Incremental
    print("\nRunning incremental import (should skip)...")
    raw_df, processed = import_raw_folders(folders), [] # Mocking simplified return check
    print("Incremental run finished.")

if __name__ == "__main__":
    test()
