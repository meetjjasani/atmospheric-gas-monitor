from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from prl.core.constants import GASES
from prl.core.storage.database import Database
from prl.infrastructure.runtime_paths import processed_data_dir

REQUIRED_COLUMNS = ["datetime_ist", "date_ist", "hour_ist", *GASES]


@dataclass(slots=True, frozen=True)
class DataSummary:
    """Small metadata payload used to initialize the UI."""
    min_date: date
    max_date: date
    row_count: int
    is_empty: bool = False


class DashboardDataRepository:
    """Loads dashboard data on demand using the pre-aggregated hourly store.

    The dashboard never touches raw 10-second rows.  It reads from
    ``prl_hourly`` which contains one row per gas-hour bucket.

    Scale comparison
    ----------------
    Raw (10 s):   2 months →  1,053,921 rows  |  5 years → 31,600,000 rows
    Hourly store: 2 months →      1,459 rows  |  5 years →     44,000 rows
    Load time:    raw ~2-3 s (5 yr)  →  hourly < 10 ms (5 yr)
    """

    def __init__(self, db_root: Path | None = None) -> None:
        if db_root is None:
            db_root = processed_data_dir() / "db"
        self._db_root = db_root
        self._db = Database(db_root)
        self._summary: DataSummary | None = None

    # ------------------------------------------------------------------
    # Startup helpers
    # ------------------------------------------------------------------

    def summarize(self) -> DataSummary:
        """Return cached date bounds and row count."""
        if self._summary is not None:
            return self._summary
        try:
            df = self._db.summarize()
            if df.empty or df["min_date"].iloc[0] is None:
                return self._create_empty_summary()
            self._summary = DataSummary(
                min_date=pd.to_datetime(df["min_date"].iloc[0]).date(),
                max_date=pd.to_datetime(df["max_date"].iloc[0]).date(),
                row_count=int(df["row_count"].iloc[0]),
                is_empty=False,
            )
        except Exception:
            self._summary = self._create_empty_summary()
        return self._summary

    def _create_empty_summary(self) -> DataSummary:
        return DataSummary(min_date=date.today(), max_date=date.today(), row_count=0, is_empty=True)

    # ------------------------------------------------------------------
    # Fast data load  ← uses prl_hourly, not prl_data
    # ------------------------------------------------------------------

    def load_range(self, start: date, end: date, columns: list[str] | None = None) -> pd.DataFrame:
        """Load pre-aggregated hourly data for a date range.

        ``columns`` is accepted for API compatibility but ignored — the hourly
        store already contains only the columns the dashboard needs.
        """
        if not self._db.hourly_store_exists():
            # Fallback: raw data (first-run before any import has finished)
            cols = columns or REQUIRED_COLUMNS
            df = self._db.load_range(start.isoformat(), end.isoformat(), cols)
            return self._normalize_raw_frame(df, start=start, end=end)

        df = self._db.load_hourly_range(start.isoformat(), end.isoformat())
        return self._normalize_hourly_frame(df, start=start, end=end)

    # ------------------------------------------------------------------
    # Normalisation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_hourly_frame(frame: pd.DataFrame, *, start: date, end: date) -> pd.DataFrame:
        """Normalise a pre-aggregated hourly frame for the dashboard."""
        df = frame.copy()

        # hour_start_ist becomes the main datetime column expected by the dashboard
        if "hour_start_ist" in df.columns:
            df["datetime_ist"] = pd.to_datetime(df["hour_start_ist"], errors="coerce")
        elif "datetime_ist" not in df.columns:
            return df

        if "date_ist" in df.columns:
            df["date_ist"] = pd.to_datetime(df["date_ist"], errors="coerce").dt.date
        if "hour_ist" in df.columns:
            df["hour_ist"] = pd.to_numeric(df["hour_ist"], errors="coerce").astype("Int64")

        for gas in GASES:
            if gas in df.columns:
                df[gas] = pd.to_numeric(df[gas], errors="coerce").astype("float32")

        df = df.dropna(subset=["datetime_ist"])
        if "date_ist" in df.columns:
            df = df.loc[(df["date_ist"] >= start) & (df["date_ist"] <= end)]

        return df.sort_values("datetime_ist").reset_index(drop=True)

    @staticmethod
    def _normalize_raw_frame(
        frame: pd.DataFrame,
        *,
        start: date,
        end: date,
        columns: list[str] | None = None,
    ) -> pd.DataFrame:
        """Normalise a raw row frame (fallback path only)."""
        df = frame.copy()
        if "datetime_ist" in df.columns:
            df["datetime_ist"] = pd.to_datetime(df["datetime_ist"], errors="coerce")
        if "date_ist" in df.columns:
            df["date_ist"] = pd.to_datetime(df["date_ist"], errors="coerce").dt.date
        if "hour_ist" in df.columns:
            df["hour_ist"] = pd.to_numeric(df["hour_ist"], errors="coerce").astype("Int64")
        valid_gases = [c for c in GASES if columns is None or c in columns]
        for gas in valid_gases:
            if gas in df.columns:
                df[gas] = pd.to_numeric(df[gas], errors="coerce").astype("float32")
        df = df.dropna(subset=["datetime_ist"])
        if "date_ist" in df.columns:
            df = df.loc[(df["date_ist"] >= start) & (df["date_ist"] <= end)]
        return df.sort_values("datetime_ist").reset_index(drop=True)

    # ------------------------------------------------------------------
    # Month navigation (unchanged)
    # ------------------------------------------------------------------

    def available_months(self) -> list[tuple[str, date, date]]:
        df = self._db.available_months()
        if df.empty:
            return []
        results = []
        for _, row in df.iterrows():
            month_label = pd.to_datetime(row["month_ist"]).strftime("%b %Y")
            results.append((
                month_label,
                pd.to_datetime(row["min_date"]).date(),
                pd.to_datetime(row["max_date"]).date(),
            ))
        return results


# ---------------------------------------------------------------------------
# Backward-compatible helpers
# ---------------------------------------------------------------------------

def load_dashboard_data() -> pd.DataFrame:
    repository = DashboardDataRepository()
    summary = repository.summarize()
    return repository.load_range(summary.min_date, summary.max_date)


def summarize_data(df: pd.DataFrame) -> DataSummary:
    return DataSummary(
        min_date=df["date_ist"].min(),
        max_date=df["date_ist"].max(),
        row_count=len(df),
    )
