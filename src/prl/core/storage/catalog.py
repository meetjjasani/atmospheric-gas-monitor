from __future__ import annotations

import json
from pathlib import Path


class FileCatalog:
    """Registry of processed files to enable incremental ingestion.
    
    Tracks file paths and their modification metadata to skip redundant processing.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.data: dict[str, Any] = {"files": {}, "partitions": {}, "last_sync": None}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            with self.path.open("r", encoding="utf-8") as f:
                self.data = json.load(f)
        except (json.JSONDecodeError, IOError):
            self.data = {"files": {}, "partitions": {}, "last_sync": None}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    @property
    def last_sync(self) -> str | None:
        return self.data.get("last_sync")

    @last_sync.setter
    def last_sync(self, value: str | None) -> None:
        self.data["last_sync"] = value

    def is_processed(self, file_path: Path) -> bool:
        """Return True if the file matches an entry in the catalog."""
        key = str(file_path.absolute())
        if key not in self.data["files"]:
            return False
            
        entry = self.data["files"][key]
        stats = file_path.stat()
        return (
            entry.get("mtime") == stats.st_mtime and
            entry.get("size") == stats.st_size
        )

    def mark_processed(self, path: Path) -> None:
        """Record file metadata once successfully processed."""
        self.data["files"][str(path)] = {
            "mtime": path.stat().st_mtime,
            "size": path.stat().st_size
        }

    def update_partition_metadata(self, partition_key: str, stats: dict[str, Any]) -> None:
        """Store row counts, min/max dates, etc. for a specific year/month partition."""
        if "partitions" not in self.data:
            self.data["partitions"] = {}
        self.data["partitions"][partition_key] = stats
