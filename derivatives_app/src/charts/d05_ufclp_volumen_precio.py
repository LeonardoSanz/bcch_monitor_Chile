from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.charts._common import build_basic_dataframe, empty_figure
from src.charts.siid_style import apply_siid_layout
from src.io.bcch_api import BCCHClient
from src.series_registry import SeriesRegistry

CHART_ID = "d05_ufclp_volumen_precio"
TITLE = "D05 - UF/CLP volumen transado vs precio forward"


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    df = build_basic_dataframe(CHART_ID, client, registry, start_date, end_date, demo)
    if df.empty:
        return df
    return df.pivot_table(index="date", columns="dimension_1", values="value", aggfunc="sum").reset_index()


def build_figure(df: pd.DataFrame):
    if df.empty:
        return empty_figure("Faltan series para UF/CLP volumen/precio")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    if "Volumen" in df.columns:
        fig.add_trace(go.Bar(x=df["date"], y=df["Volumen"], name="Volumen"), secondary_y=False)
    if "Precio forward" in df.columns:
        fig.add_trace(go.Scatter(x=df["date"], y=df["Precio forward"], name="Precio forward", mode="lines+markers"), secondary_y=True)
    fig = apply_siid_layout(fig, TITLE, yaxis_title="Volumen", unit="Volumen y UF/CLP", height=560)
    fig.update_yaxes(title_text="Volumen", secondary_y=False)
    fig.update_yaxes(title_text="UF/CLP", secondary_y=True)
    return fig
