from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd


@dataclass(frozen=True, slots=True)
class DateRange:
    """Normalized date range used across the dashboard."""

    start: date
    end: date


@dataclass(frozen=True, slots=True)
class FilterState:
    """Current UI filter values."""

    date_range: DateRange
    correlation_pair: str
    fit_start_hour: int
    fit_end_hour: int
    diurnal_gas: str
    daily_stats_gas: str
    hourly_mean_gas: str
    heatmap_gas: str


@dataclass(frozen=True, slots=True)
class SummaryState:
    """Summary content shown in the left sidebar and status bar."""

    row_count: int
    range_label: str
    sidebar_text: str
    status_text: str


@dataclass(frozen=True, slots=True)
class TableRow:
    """Simple key/value row for metrics tables."""

    label: str
    value: str


@dataclass(slots=True)
class CorrelationSectionState:
    """View model for the correlation tab."""

    title: str
    x_col: str
    y_col: str
    fit_start_hour: int
    fit_end_hour: int
    data: pd.DataFrame
    fit_data: pd.DataFrame
    table_rows: list[TableRow]
    plot_html: str | None = None


@dataclass(slots=True)
class DiurnalSectionState:
    """View model for the 24-point diurnal tab."""

    gas: str
    stats: pd.DataFrame
    metric_text: list[str]
    plot_html: str | None = None


@dataclass(slots=True)
class DailyStatsSectionState:
    """View model for the daily mean/median tab."""

    gas: str
    stats: pd.DataFrame
    metric_text: list[str]
    plot_html: str | None = None


@dataclass(slots=True)
class HourlyMeanSectionState:
    """View model for the hourly mean tab."""

    gas: str
    values: pd.DataFrame
    metric_text: list[str]
    plot_html: str | None = None


@dataclass(slots=True)
class HeatmapSectionState:
    """View model for the heatmap tab."""

    gas: str
    matrix: pd.DataFrame
    metric_text: list[str]
    plot_html: str | None = None


@dataclass(slots=True)
class DashboardSnapshot:
    """Complete state required to render the dashboard."""

    selected_range: DateRange
    summary: SummaryState
    has_data: bool
    correlation: CorrelationSectionState
    diurnal: DiurnalSectionState
    daily_stats: DailyStatsSectionState
    hourly_mean: HourlyMeanSectionState
    heatmap: HeatmapSectionState
