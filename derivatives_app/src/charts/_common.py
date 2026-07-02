from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.charts.siid_style import apply_siid_layout, empty_siid_figure
from src.data_loader import load_chart_data, load_all_configured_data
from src.io.bcch_api import BCCHClient
from src.series_registry import SeriesRegistry


def empty_figure(message: str = "Sin datos para graficar") -> go.Figure:
    return empty_siid_figure(message)


def base_layout(fig: go.Figure, title: str, yaxis_title: str = "MM USD") -> go.Figure:
    return apply_siid_layout(
        fig,
        title=title,
        yaxis_title=yaxis_title,
        unit=yaxis_title,
        source_note="Fuente: Banco Central de Chile, BDE/SIID público.",
    )


def build_basic_dataframe(
    chart_id: str,
    client: BCCHClient | None,
    registry: SeriesRegistry,
    start_date: str,
    end_date: str,
    demo: bool = False,
) -> pd.DataFrame:
    return load_chart_data(client, registry, chart_id, start_date, end_date, demo=demo)


def latest_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    latest = df["date"].max()
    return df[df["date"].eq(latest)].copy()


def pivot_latest(df: pd.DataFrame, index_col: str, column_col: str = "dimension_2") -> pd.DataFrame:
    snap = latest_snapshot(df)
    if snap.empty:
        return pd.DataFrame()
    return snap.pivot_table(index=index_col, columns=column_col, values="value", aggfunc="sum").fillna(0)


def monthly_change_table(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    if df.empty:
        return df
    out = (
        df.groupby([*group_cols, "date"], as_index=False)["value"]
        .sum()
        .sort_values([*group_cols, "date"])
    )
    out["value_lag_1m"] = out.groupby(group_cols)["value"].shift(1)
    out["value_lag_12m"] = out.groupby(group_cols)["value"].shift(12)
    out["var_mom"] = out["value"] - out["value_lag_1m"]
    out["var_yoy"] = out["value"] - out["value_lag_12m"]
    out["pct_mom"] = np.where(out["value_lag_1m"].abs() > 0, out["var_mom"] / out["value_lag_1m"], np.nan)
    out["pct_yoy"] = np.where(out["value_lag_12m"].abs() > 0, out["var_yoy"] / out["value_lag_12m"], np.nan)
    return out


def zscore_table(df: pd.DataFrame, group_cols: list[str], window: int = 36) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.groupby([*group_cols, "date"], as_index=False)["value"].sum().sort_values([*group_cols, "date"])
    roll_mean = out.groupby(group_cols)["value"].transform(lambda s: s.rolling(window, min_periods=12).mean())
    roll_std = out.groupby(group_cols)["value"].transform(lambda s: s.rolling(window, min_periods=12).std())
    out["zscore"] = (out["value"] - roll_mean) / roll_std
    return out
