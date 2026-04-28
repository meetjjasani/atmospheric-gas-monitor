from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)


class DuckDBEngine:
    """High-performance query engine for partitioned Parquet datasets.
    
    DuckDB handles Hive-style partitioning (year=YYYY/month=MM) automatically.
    """

    def __init__(self, database_root: Path) -> None:
        self.root = database_root
        self.conn = duckdb.connect(database=":memory:")
        self._setup_view()

    def _setup_view(self) -> None:
        """Create a virtual table pointing to all parquet files in the database root."""
        if not self.root.exists():
            return
            
        parquet_glob = str(self.root / "**/*.parquet")
        # DuckDB automatically detects hive partitioning from the directory structure
        self.conn.execute(
            f"CREATE OR REPLACE VIEW prl_data AS SELECT * FROM read_parquet('{parquet_glob}', hive_partitioning=1)"
        )

    def query(self, sql: str, params: list[Any] | None = None) -> pd.DataFrame:
        """Execute a SQL query and return results as a Pandas DataFrame."""
        try:
            return self.conn.execute(sql, params or []).df()
        except Exception as e:
            logger.error(f"DuckDB query failed: {e}")
            return pd.DataFrame()

    def summarize(self) -> pd.DataFrame:
        """Fetch min/max dates and total row count across all partitions."""
        if not self.root.exists():
            return pd.DataFrame()
            
        return self.query(
            "SELECT MIN(date_ist) as min_date, MAX(date_ist) as max_date, COUNT(*) as row_count FROM prl_data"
        )

    def load_range(self, start_date: str, end_date: str, columns: list[str]) -> pd.DataFrame:
        """Fetch specific columns for a date range with partition pruning."""
        cols_str = ", ".join(columns)
        return self.query(
            f"SELECT {cols_str} FROM prl_data WHERE date_ist >= ? AND date_ist <= ? ORDER BY datetime_ist",
            [start_date, end_date]
        )

    def available_months(self) -> pd.DataFrame:
        """Return distinct months and their date bounds."""
        return self.query(
            "SELECT month_ist, MIN(date_ist) as min_date, MAX(date_ist) as max_date FROM prl_data GROUP BY month_ist ORDER BY month_ist"
        )
