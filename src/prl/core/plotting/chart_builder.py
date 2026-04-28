from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from prl.core.correlation.service import regression_stats


def _date_tick_step(count: int) -> int:
    if count <= 10:
        return 1
    if count <= 20:
        return 2
    if count <= 45:
        return 5
    return 7


def _sample_tick_labels(labels: list) -> list:
    if not labels:
        return []

    step = _date_tick_step(len(labels))
    sampled = labels[::step]
    if sampled[-1] != labels[-1]:
        sampled.append(labels[-1])
    return sampled


def _chem_label(col: str) -> str:
    mapping = {
        "co_sync": "CO (ppm)",
        "co2_sync": "CO<sub>2</sub> (ppm)",
        "ch4_sync": "CH<sub>4</sub> (ppm)",
        "co_over_co_plus_co2": "CO / (CO + CO<sub>2</sub>)",
        "co2_over_co_plus_co2": "CO<sub>2</sub> / (CO + CO<sub>2</sub>)",
    }
    return mapping.get(col, col)


def _chem_name(col: str) -> str:
    mapping = {
        "co_sync": "CO",
        "co2_sync": "CO<sub>2</sub>",
        "ch4_sync": "CH<sub>4</sub>",
    }
    return mapping.get(col, col)


def _apply_responsive_layout(
    fig: go.Figure, 
    title: str, 
    *, 
    title_y: float = 0.98,
    legend: dict | None = None
) -> None:
    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>",
            y=0.84, # Stacked below the centered 8-function toolbar
            yanchor="top",
            x=0.5,
            xanchor="center",
            font=dict(size=14)
        ),
        autosize=True,
        template="plotly_white",
        margin=dict(autoexpand=True, l=90, r=50, t=100, b=45),
        hovermode="closest",
        dragmode="pan",
        uirevision="keep",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
    )
    if legend:
        fig.update_layout(legend=legend)


def scatter_with_fit(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    point_label: str = "Data points",
    show_hour_colorbar: bool = True,
    fit_df: pd.DataFrame | None = None,
    fit_label: str | None = None,
):
    fit_source = fit_df if fit_df is not None else df
    stats = regression_stats(fit_source, x_col, y_col)
    fig = go.Figure()
    scale = 1.15
    text_scale = 1.15

    pair = df[[x_col, y_col, "datetime_ist"]].dropna()
    if len(pair) > 0:
        hour_ist = pd.to_datetime(pair["datetime_ist"], errors="coerce").dt.hour.to_numpy()
        fig.add_trace(
            go.Scattergl(
                x=pair[x_col].to_numpy(dtype=float),
                y=pair[y_col].to_numpy(dtype=float),
                mode="markers",
                name=point_label,
                marker=dict(
                    size=6.2 * scale,
                    opacity=0.9,
                    color=hour_ist,
                    colorscale="Jet",
                    cmin=0,
                    cmax=23,
                    line=dict(color="black", width=0.5 * scale),
                    colorbar=dict(
                        title=dict(
                            text=f"<b>IST</b>" if show_hour_colorbar else None,
                            font=dict(size=12 * text_scale),
                        ),
                        tickvals=[0, 6, 12, 18, 23],
                        len=0.95,
                        thickness=14,
                        tickfont=dict(size=11 * text_scale),
                    ),
                ),
                showlegend=False,
            )
        )

    if stats["n"] >= 2:
        xline = np.array([np.nanmin(stats["x"]), np.nanmax(stats["x"])])
        yline = stats["slope"] * xline + stats["intercept"]
        label = f"Best-fit line (r = {stats['pearson_r']:.3f})"
        if fit_label:
            label = f"Best-fit line ({fit_label}, r = {stats['pearson_r']:.3f})"
        fig.add_trace(
            go.Scatter(
                x=xline,
                y=yline,
                mode="lines",
                line=dict(color="black", width=1.2 * scale),
                name=label,
                showlegend=False, # Hide from legend as requested
            )
        )

    fig.update_layout(
        font=dict(size=12 * text_scale),
        legend=dict(font=dict(size=11 * text_scale)),
    )
    _apply_responsive_layout(
        fig,
        title,
        legend=dict(
            font=dict(size=11 * text_scale),
            orientation="h",
            yanchor="top",
            y=-0.28, # Safe distance below the axis title in the 70px bottom margin
            xanchor="center",
            x=0.5
        ),
    )
    fig.update_xaxes(
        automargin=True,
        title_text=f"<b>{_chem_label(x_col)}</b>",
        title_font=dict(size=13 * text_scale),
        tickfont=dict(size=11 * text_scale),
    )
    fig.update_yaxes(
        automargin=True,
        title_text=f"<b>{_chem_label(y_col)}</b>",
        title_font=dict(size=13 * text_scale),
        tickfont=dict(size=11 * text_scale),
    )
    return fig, stats


def build_correlation_html(df, fit_df, x_col, y_col, theme_name="light") -> str:
    fig, _stats = scatter_with_fit(df, x_col, y_col, f"{_chem_name(x_col)} vs {_chem_name(y_col)}", fit_df=fit_df)
    return fig.to_html(include_plotlyjs=False, full_html=False, config={"responsive": True})


def build_diurnal_html(stats_df, gas, theme_name="light") -> str:
    fig = plot_single_gas_24_point(stats_df, gas, "Start", "End")
    return fig.to_html(include_plotlyjs=False, full_html=False, config={"responsive": True})


def build_daily_stats_html(daily_stats, gas, theme_name="light") -> str:
    fig = plot_daily_mean_median_bars(daily_stats, gas, "Start", "End")
    return fig.to_html(include_plotlyjs=False, full_html=False, config={"responsive": True})


def build_hourly_mean_html(hourly_df, gas, theme_name="light") -> str:
    fig = plot_single_gas_hourly_mean(hourly_df, gas, "Start", "End")
    return fig.to_html(include_plotlyjs=False, full_html=False, config={"responsive": True})


def build_heatmap_html(matrix, gas, theme_name="light") -> str:
    fig = plot_gas_heatmap(matrix, gas, "Start", "End")
    return fig.to_html(include_plotlyjs=False, full_html=False, config={"responsive": True})


def plot_single_gas_24_point(stats_df: pd.DataFrame, gas: str, start_date, end_date):
    x = stats_df["hour_ist"]
    mean_by_hour = stats_df["mean"]
    median_by_hour = stats_df["median"]
    lower = stats_df["lower"]
    upper = stats_df["upper"]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x,
            y=mean_by_hour,
            mode="lines+markers",
            name=f"{_chem_name(gas)} mean",
            line=dict(color="#1f77b4", width=2.2),
            marker=dict(size=6),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=median_by_hour,
            mode="lines",
            name="Median",
            line=dict(color="#ff7f0e", width=2.0, dash="dash"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=upper,
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=lower,
            mode="lines",
            fill="tonexty",
            name="Avg ± SD",
            line=dict(width=0),
            fillcolor="rgba(31, 119, 180, 0.16)",
        )
    )

    _apply_responsive_layout(
        fig,
        f"24-point diurnal average ({_chem_name(gas)}) | {start_date} to {end_date}",
    )
    fig.update_xaxes(title_text="<b>Hour IST</b>", tickmode="array", tickvals=list(range(24)), automargin=True)
    fig.update_yaxes(title_text=f"<b>{_chem_label(gas)}</b>", automargin=True)
    return fig


def plot_daily_mean_median_bars(daily_stats: pd.DataFrame, gas: str, start_date, end_date):
    labels = [pd.to_datetime(d).strftime("%d/%m") for d in daily_stats["date_ist"]]
    visible_labels = _sample_tick_labels(labels)
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=labels,
            y=daily_stats["mean"],
            name="Mean",
            marker_color="#1f77b4",
        )
    )
    fig.add_trace(
        go.Bar(
            x=labels,
            y=daily_stats["median"],
            name="Median",
            marker_color="#ff7f0e",
        )
    )

    _apply_responsive_layout(
        fig,
        f"Daily mean & median ({_chem_name(gas)}) | {start_date} to {end_date}",
    )
    fig.update_layout(barmode="group", bargap=0.18)
    fig.update_xaxes(
        title_text="<b>Date (IST)</b>",
        tickmode="array",
        tickvals=visible_labels,
        automargin=True,
    )
    fig.update_yaxes(title_text=f"<b>{_chem_label(gas)}</b>", automargin=True)
    return fig


def plot_all_gases_24_point(profile: pd.DataFrame, gases: list[str], start_date, end_date):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    x = profile["hour_ist"]

    if "co2_sync" in profile.columns:
        fig.add_trace(
            go.Scatter(
                x=x,
                y=profile["co2_sync"],
                mode="lines+markers",
                name=_chem_name("co2_sync"),
                line=dict(color="#d62728", width=2.3),
                marker=dict(size=6),
            ),
            secondary_y=False,
        )

    for gas, color in [("co_sync", "#1f77b4"), ("ch4_sync", "#2ca02c")]:
        if gas in profile.columns:
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=profile[gas],
                    mode="lines+markers",
                    name=_chem_name(gas),
                    line=dict(color=color, width=2.1),
                    marker=dict(size=6),
                ),
                secondary_y=True,
            )

    _apply_responsive_layout(
        fig,
        f"All-gases 24-point average | {start_date} to {end_date}",
    )
    fig.update_xaxes(title_text="Hour IST", tickmode="array", tickvals=list(range(24)), automargin=True)
    fig.update_yaxes(title_text="CO2 concentration (ppm)", secondary_y=False, automargin=True)
    fig.update_yaxes(title_text="CO / CH4 concentration (ppm)", secondary_y=True, automargin=True)
    return fig


def plot_single_gas_hourly_mean(hourly_df: pd.DataFrame, gas: str, start_date, end_date):
    values = hourly_df[["datetime_ist", gas]].dropna()
    unique_dates = (
        pd.to_datetime(values["datetime_ist"], errors="coerce")
        .dt.normalize()
        .dropna()
        .drop_duplicates()
        .sort_values()
    )
    tick_step = _date_tick_step(len(unique_dates))
    dtick_ms = tick_step * 24 * 60 * 60 * 1000
    fig = go.Figure()
    fig.add_trace(
        go.Scattergl(
            x=values["datetime_ist"],
            y=values[gas],
            mode="lines+markers",
            line=dict(color="#1f77b4", width=1.6),
            marker=dict(size=4.0),
        )
    )

    _apply_responsive_layout(
        fig,
        f"Hourly mean ({_chem_name(gas)}) | {start_date} to {end_date}",
    )
    fig.update_xaxes(
        title_text="<b>IST DateTime</b>",
        tickangle=30,
        dtick=dtick_ms,
        tickformat="%d/%m",
        automargin=True,
    )
    fig.update_yaxes(title_text=f"<b>{_chem_label(gas)}</b>", automargin=True)
    return fig


def plot_gas_heatmap(matrix: pd.DataFrame, gas: str, start_date, end_date):
    values = matrix.copy()
    x_labels = values.index.astype(int).tolist()
    y_labels = [pd.to_datetime(col).strftime("%d/%m") for col in values.columns]
    visible_y_labels = _sample_tick_labels(y_labels)

    fig = go.Figure(
        data=[
            go.Heatmap(
                z=values.transpose().to_numpy(dtype=float),
                x=x_labels,
                y=y_labels,
                colorscale="Jet",
                zsmooth=False,
                colorbar=dict(title=_chem_label(gas)),
                hovertemplate=(
                    "Hour (IST): %{x:02d}<br>"
                    "Date: %{y}<br>"
                    "Concentration: %{z:.4f}<extra></extra>"
                ),
            )
        ]
    )

    _apply_responsive_layout(
        fig,
        f"Concentration heatmap ({_chem_name(gas)}) | {start_date} to {end_date}",
    )
    fig.update_xaxes(
        title_text="<b>Hour (IST)</b>",
        tickmode="array",
        tickvals=x_labels,
        automargin=True,
    )
    fig.update_yaxes(
        title_text="<b>Date (IST)</b>",
        tickmode="array",
        tickvals=visible_y_labels,
        automargin=True,
    )
    return fig
