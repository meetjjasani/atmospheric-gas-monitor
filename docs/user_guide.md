# PRL Dashboard — User Guide

## Opening the App

Double-click `PRL Dashboard.exe` (Windows) or run `prl-app` from terminal.

## Importing New Data

1. Click **Import Data** in the top bar
2. Select your `.dat` file folder (e.g. `data/raw/2025/12/`)
3. Click **Import** — the pipeline runs automatically and the dashboard refreshes

## Dashboards

### Correlations
Scatter plot of hourly-mean gas pairs with a linear regression fit line.

- **Gas pairs:** CO vs CO₂ | CH₄ vs CO₂ | CH₄ vs CO₂/(CO+CO₂)
- **Fit hour range:** Restrict regression to specific IST hours (e.g. 06–18 for daytime only)
- **Stats shown:** n, r, r², slope, intercept

### Daily Diurnal
24-point hourly average profile showing the typical daily pattern for a selected gas.

- Select gas: CO | CO₂ | CH₄
- Stats: mean, median, standard deviation per hour

### Daily Mean & Median
Bar chart of daily mean and median concentrations across the selected date range.

### Hourly Mean
Time series of hourly-mean concentrations for a selected gas.

### Heatmap
2D grid — rows = dates, columns = hours (IST). Color intensity = concentration.

## Filters

Use the **Filters Panel** (left side) to:
- Set date range (or click a month preset)
- Select gas or correlation pair
- Set regression fit hour range

Click **Apply** to refresh the dashboard.

## Exporting Charts

Click the **Download** button on any chart to save as PNG.
Exports are saved to `~/Library/Application Support/PRL/exports/plots/` (macOS) or `%LOCALAPPDATA%\PRL\exports\plots\` (Windows).
