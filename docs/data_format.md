# Data Format Specification

## Input: CRDS .dat Files

Whitespace-delimited text files produced by the CRDS instrument.

**Required filename pattern:** `*DataLog_User_Sync.dat`

**Required columns:**

| Column | Type | Description |
|--------|------|-------------|
| `DATE` | string | UTC date (YYYY-MM-DD) |
| `TIME` | string | UTC time (HH:MM:SS) |
| `CO_sync` | float | CO concentration (ppb) |
| `CO2_sync` | float | CO₂ concentration (ppm) |
| `CH4_sync` | float | CH₄ concentration (ppm) |

**Example:**
```
DATE        TIME        CO_sync    CO2_sync    CH4_sync
2025-11-01  05:30:00    0.234      412.1       1.89
2025-11-01  05:30:10    0.231      412.0       1.88
```

## Folder Structure

Place raw files under `data/raw/<year>/<month>/`:

```
data/raw/
  2025/
    11/
      2025-11-01_DataLog_User_Sync.dat
      2025-11-02_DataLog_User_Sync.dat
    12/
      2025-12-01_DataLog_User_Sync.dat
```

Configure which months to ingest in `config/config.json`:

```json
{
  "data_root": "data/raw/2025",
  "month_dirs": ["11", "12"]
}
```

## Output: Processed Storage

Data is stored as Hive-partitioned Parquet files in `data/processed/db/`:

```
data/processed/db/
  year=2025/
    month=11/data.parquet
    month=12/data.parquet
```

### Processed Columns

| Column | Description |
|--------|-------------|
| `datetime_utc` | Original UTC timestamp (timezone-aware) |
| `datetime_ist` | Converted IST timestamp (UTC+5:30) |
| `date_ist` | IST date |
| `hour_ist` | IST hour (0–23) |
| `co_sync` | QC-cleaned CO |
| `co2_sync` | QC-cleaned CO₂ |
| `ch4_sync` | QC-cleaned CH₄ |
| `co_sync_raw` | Original CO before QC |
| `*_flag_hard` | Hard bounds flag |
| `*_flag_point_spike` | Point-level spike flag |
| `*_flag_hourly_spike` | Hourly spike flag |
| `*_flag_sustained_shift` | Sustained anomaly flag |
