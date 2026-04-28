from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from prl.app.data_access import DashboardDataRepository, DataSummary
from prl.app.view_models import (
    CorrelationSectionState,
    DailyStatsSectionState,
    DashboardSnapshot,
    DateRange,
    DiurnalSectionState,
    FilterState,
    HeatmapSectionState,
    HourlyMeanSectionState,
    SummaryState,
    TableRow,
)
from prl.core.services import dashboard_service


class DashboardController:
    """Coordinates filtered data access, caching, and dashboard view models."""

    PAIR_MAP = {
        "CO vs CO₂": ("co2_sync", "co_sync"),
        "CH₄ vs CO₂": ("co2_sync", "ch4_sync"),
        "CH₄ vs CO₂/(CO+CO₂)": ("co2_over_co_plus_co2", "ch4_sync"),
    }

    def __init__(self, repository: DashboardDataRepository | None = None) -> None:
        self._repository = repository or DashboardDataRepository()
        self.data_summary: DataSummary = self._repository.summarize()
        self.available_months: list[tuple[str, DateRange]] = [
            (label, DateRange(start=start_date, end=end_date))
            for label, start_date, end_date in self._repository.available_months()
        ]
        # Column-aware cache: (start, end, tuple(columns)) -> pd.DataFrame
        self._filtered_cache: dict[tuple[date, date, tuple[str, ...]], pd.DataFrame] = {}
        self._correlation_cache: dict[tuple[date, date], pd.DataFrame] = {}
        self._hourly_cache: dict[tuple[date, date, str], pd.DataFrame] = {}
        self._matrix_cache: dict[tuple[date, date, str], pd.DataFrame] = {}


    def default_filter_state(self) -> FilterState:
        """Return a lightweight first-load state using the first available day."""
        if self.data_summary.is_empty:
             return FilterState(
                date_range=DateRange(start=date.today(), end=date.today()),
                correlation_pair="CO vs CO₂",
                fit_start_hour=0,
                fit_end_hour=23,
                diurnal_gas="co2_sync",
                daily_stats_gas="co2_sync",
                hourly_mean_gas="co2_sync",
                heatmap_gas="co2_sync",
            )

        default_range = DateRange(
            start=self.data_summary.min_date,
            end=self.data_summary.min_date,
        )
        return FilterState(
            date_range=default_range,
            correlation_pair="CO vs CO₂",
            fit_start_hour=0,
            fit_end_hour=23,
            diurnal_gas="co2_sync",
            daily_stats_gas="co2_sync",
            hourly_mean_gas="co2_sync",
            heatmap_gas="co2_sync",
        )


    def full_range(self) -> DateRange:
        return DateRange(
            start=self.data_summary.min_date,
            end=self.data_summary.max_date,
        )

    def reload_data(self) -> None:
        """Clear all caches and re-initialize from the data repository."""
        self._repository = DashboardDataRepository() # Fresh instance
        self.data_summary = self._repository.summarize()
        self.available_months = [
            (label, DateRange(start=start_date, end=end_date))
            for label, start_date, end_date in self._repository.available_months()
        ]
        self._filtered_cache.clear()
        self._correlation_cache.clear()
        self._hourly_cache.clear()
        self._matrix_cache.clear()


    def build_snapshot(self, state: FilterState, theme_name: str = "light") -> DashboardSnapshot:
        """Build all view models and BAKE charts to HTML strings asynchronously."""
        normalized_range = self.normalize_range(state.date_range)
        
        # 1. Summary only needs temporal columns to count rows
        summary_df = self._get_data(normalized_range, ["date_ist"])
        summary = SummaryState(
            row_count=len(summary_df),
            range_label=self._format_date_range(normalized_range),
            sidebar_text=(
                f"{len(summary_df):,} rows\n{self._format_date_range(normalized_range)}"
            ),
            status_text=f"Loaded {len(summary_df):,} rows for selected range",
        )

        # 2. Fetch required columns for remaining sections
        target_cols = {state.diurnal_gas, state.daily_stats_gas, state.hourly_mean_gas, state.heatmap_gas}
        if state.correlation_pair in self.PAIR_MAP:
            x_col, y_col = self.PAIR_MAP[state.correlation_pair]
            target_cols.update([x_col, y_col])
                
        physical_cols = {"datetime_ist", "date_ist", "hour_ist"}
        for col in target_cols:
            if col == "co2_over_co_plus_co2" or col == "co_over_co_plus_co2":
                physical_cols.update(["co_sync", "co2_sync"])
            else:
                physical_cols.add(col)
                
        filtered = self._get_data(normalized_range, sorted(list(physical_cols)))

        # 3. Build Section States
        correlation = self._build_correlation_state(filtered, normalized_range, state)
        diurnal = self._build_diurnal_state(filtered, normalized_range, state.diurnal_gas)
        daily_stats = self._build_daily_stats_state(
            filtered,
            normalized_range,
            state.daily_stats_gas,
        )
        hourly_mean = self._build_hourly_mean_state(
            filtered,
            normalized_range,
            state.hourly_mean_gas,
        )
        heatmap = self._build_heatmap_state(filtered, normalized_range, state.heatmap_gas)

        # 4. BAKE Figures to HTML (Heavy lifting on Background Thread)
        from prl.core.plotting import chart_builder
        correlation.plot_html = chart_builder.build_correlation_html(
            correlation.data, correlation.fit_data, correlation.x_col, correlation.y_col, theme_name
        )
        diurnal.plot_html = chart_builder.build_diurnal_html(diurnal.stats, diurnal.gas, theme_name)
        daily_stats.plot_html = chart_builder.build_daily_stats_html(
            daily_stats.stats, daily_stats.gas, theme_name
        )
        hourly_mean.plot_html = chart_builder.build_hourly_mean_html(
            hourly_mean.values, hourly_mean.gas, theme_name
        )
        heatmap.plot_html = chart_builder.build_heatmap_html(heatmap.matrix, heatmap.gas, theme_name)

        return DashboardSnapshot(
            selected_range=normalized_range,
            summary=summary,
            has_data=not filtered.empty,
            correlation=correlation,
            diurnal=diurnal,
            daily_stats=daily_stats,
            hourly_mean=hourly_mean,
            heatmap=heatmap,
        )

    def normalize_range(self, date_range: DateRange) -> DateRange:
        """Clamp user input into the available data bounds."""
        start = min(max(date_range.start, self.data_summary.min_date), self.data_summary.max_date)
        end = min(max(date_range.end, self.data_summary.min_date), self.data_summary.max_date)
        if end < start:
            start, end = end, start
        return DateRange(start=start, end=end)

    def _get_data(self, date_range: DateRange, columns: list[str]) -> pd.DataFrame:
        """Fetch targeted columns for a range with intelligent column-aware caching."""
        cols_tuple = tuple(sorted(columns))
        cache_key = (date_range.start, date_range.end, cols_tuple)
        
        if cache_key not in self._filtered_cache:
            self._filtered_cache[cache_key] = self._repository.load_range(
                date_range.start,
                date_range.end,
                columns=list(cols_tuple)
            )
        return self._filtered_cache[cache_key]

    def _correlation_df(self, date_range: DateRange, x_col: str, y_col: str, filtered: pd.DataFrame) -> pd.DataFrame:
        cache_key = (date_range.start, date_range.end, x_col, y_col)
        if cache_key not in self._correlation_cache:
            self._correlation_cache[cache_key] = dashboard_service.build_correlation_frame(filtered)
        return self._correlation_cache[cache_key]

    def _hourly_df(self, date_range: DateRange, gas: str, filtered: pd.DataFrame) -> pd.DataFrame:
        cache_key = (date_range.start, date_range.end, gas)
        if cache_key not in self._hourly_cache:
            self._hourly_cache[cache_key] = dashboard_service.build_hourly_mean_timeseries(filtered)
        return self._hourly_cache[cache_key]

    def _matrix_df(self, date_range: DateRange, gas: str, filtered: pd.DataFrame) -> pd.DataFrame:
        cache_key = (date_range.start, date_range.end, gas)
        if cache_key not in self._matrix_cache:
            self._matrix_cache[cache_key] = dashboard_service.build_daily_diurnal_matrix(
                filtered,
                gas=gas,
            )
        return self._matrix_cache[cache_key]

    def _build_correlation_state(
        self,
        filtered: pd.DataFrame,
        date_range: DateRange,
        state: FilterState,
    ) -> CorrelationSectionState:
        label = state.correlation_pair
        x_col, y_col = self.PAIR_MAP[label]
        fit_start = min(state.fit_start_hour, state.fit_end_hour)
        fit_end = max(state.fit_start_hour, state.fit_end_hour)

        corr_df = self._correlation_df(date_range, x_col, y_col, filtered)
        fit_df = corr_df.loc[corr_df["datetime_ist"].dt.hour.between(fit_start, fit_end)]
        stats = dashboard_service.regression_stats(fit_df, x_col, y_col)
        slope_val = stats["slope"] if pd.notna(stats["slope"]) else None

        rows = [
            TableRow("Pair", label),
            TableRow("n", "" if pd.isna(stats["n"]) else str(int(stats["n"]))),
            TableRow(
                "r",
                "" if pd.isna(stats["pearson_r"]) else f"{float(stats['pearson_r']):.4f}",
            ),
            TableRow("r2", "" if pd.isna(stats["r2"]) else f"{float(stats['r2']):.4f}"),
            TableRow(
                "Slope",
                "" if slope_val is None or pd.isna(slope_val) else f"{float(slope_val):.4f}",
            ),
            TableRow(
                "Intercept",
                "" if pd.isna(stats["intercept"]) else f"{float(stats['intercept']):.4f}",
            ),
        ]
        return CorrelationSectionState(
            title=label,
            x_col=x_col,
            y_col=y_col,
            fit_start_hour=fit_start,
            fit_end_hour=fit_end,
            data=corr_df,
            fit_data=fit_df,
            table_rows=rows,
        )

    def _build_diurnal_state(
        self,
        filtered: pd.DataFrame,
        date_range: DateRange,
        gas: str,
    ) -> DiurnalSectionState:
        matrix = self._matrix_df(date_range, gas, filtered)
        stats_df = dashboard_service.build_hourly_diurnal_stats(matrix)
        metric_text = ["", "", ""]
        if not stats_df.empty:
            metric_text = [
                f"Avg: {float(stats_df['mean'].mean()):.4f}",
                f"Median: {float(stats_df['median'].median()):.4f}",
                f"SD: {float(stats_df['std'].mean()):.4f}",
            ]
        return DiurnalSectionState(gas=gas, stats=stats_df, metric_text=metric_text)

    def _build_daily_stats_state(
        self,
        filtered: pd.DataFrame,
        date_range: DateRange,
        gas: str,
    ) -> DailyStatsSectionState:
        matrix = self._matrix_df(date_range, gas, filtered)
        daily_stats = dashboard_service.build_daily_mean_median_stats(matrix)
        metric_text = ["", "", ""]
        if not daily_stats.empty:
            metric_text = [
                f"Days: {len(daily_stats):,}",
                f"Mean avg: {float(daily_stats['mean'].mean()):.4f}",
                f"Median avg: {float(daily_stats['median'].mean()):.4f}",
            ]
        return DailyStatsSectionState(gas=gas, stats=daily_stats, metric_text=metric_text)

    def _build_hourly_mean_state(
        self,
        filtered: pd.DataFrame,
        date_range: DateRange,
        gas: str,
    ) -> HourlyMeanSectionState:
        hourly = self._hourly_df(date_range, gas, filtered)
        metric_text = ["", "", ""]
        if not hourly.empty:
            metric_text = [
                f"Points: {len(hourly):,}",
                f"Min: {float(hourly[gas].min()):.4f}",
                f"Max: {float(hourly[gas].max()):.4f}",
            ]
        return HourlyMeanSectionState(gas=gas, values=hourly, metric_text=metric_text)

    def _build_heatmap_state(
        self,
        filtered: pd.DataFrame,
        date_range: DateRange,
        gas: str,
    ) -> HeatmapSectionState:
        matrix = self._matrix_df(date_range, gas, filtered)
        metric_text = ["", "", ""]
        if not matrix.empty:
            flat_values = matrix.to_numpy(dtype=float).ravel()
            flat_values = flat_values[np.isfinite(flat_values)]
            if len(flat_values):
                metric_text = [
                    f"Min: {float(flat_values.min()):.4f}",
                    f"Avg: {float(flat_values.mean()):.4f}",
                    f"Max: {float(flat_values.max()):.4f}",
                ]
        return HeatmapSectionState(gas=gas, matrix=matrix, metric_text=metric_text)

    @staticmethod
    def _format_date_range(date_range: DateRange) -> str:
        start_text = date_range.start.strftime("%d/%m/%Y")
        end_text = date_range.end.strftime("%d/%m/%Y")
        return start_text if start_text == end_text else f"{start_text} to {end_text}"
