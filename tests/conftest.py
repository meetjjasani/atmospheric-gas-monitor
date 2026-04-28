"""Shared test fixtures for PRL Dashboard test suite."""
from __future__ import annotations

import pytest
import pandas as pd
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_dat_dir() -> Path:
    """Path to sample .dat fixture files."""
    return FIXTURES_DIR / "sample_data"


@pytest.fixture
def sample_raw_df() -> pd.DataFrame:
    """Minimal raw DataFrame matching .dat file schema."""
    return pd.DataFrame({
        "DATE": ["2025-11-01", "2025-11-01", "2025-11-01"],
        "TIME": ["05:30:00", "05:30:10", "05:30:20"],
        "CO_sync": [0.234, 0.231, 0.229],
        "CO2_sync": [412.1, 412.0, 411.9],
        "CH4_sync": [1.89, 1.88, 1.87],
    })
