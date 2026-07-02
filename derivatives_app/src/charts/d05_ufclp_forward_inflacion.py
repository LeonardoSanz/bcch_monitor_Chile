from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.charts._common import build_basic_dataframe, empty_figure
from src.charts.siid_style import apply_siid_layout
from src.io.bcch_api import BCCHClient
from src.series_registry import SeriesRegistry

CHART_ID = "d05_ufclp_forward_12m_vs_spot"
TITLE = "D05 - Forward UF/CLP 12m vs spot e inflación implícita simple"


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    df = build_basic_dataframe(CHART_ID, client, registry, start_date, end_date, demo)
    if df.empty:
        return df
    wide = df.pivot_table(index="date", columns="dimension_1", values="value", aggfunc="sum").reset_index()
    # Espera dimension_1: Forward 12m y UF Spot. Si no existe alguna, se deja NaN.
    if {"Forward 12m", "UF Spot"}.issubset(wide.columns):
        wide["inflacion_implicita_12m"] = (wide["Forward 12m"] / wide["UF Spot"] - 1.0) * 100
    else:
        wide["inflacion_implicita_12m"] = np.nan
    return wide


def build_figure(df: pd.DataFrame):
    if df.empty:
        return empty_figure("Faltan series para forward UF/CLP")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    if "Forward 12m" in df.columns:
        fig.add_trace(go.Scatter(x=df["date"], y=df["Forward 12m"], name="Forward 12m", mode="lines"), secondary_y=False)
    if "UF Spot" in df.columns:
        fig.add_trace(go.Scatter(x=df["date"], y=df["UF Spot"], name="UF Spot", mode="lines"), secondary_y=False)
    if "inflacion_implicita_12m" in df.columns and df["inflacion_implicita_12m"].notna().any():
        fig.add_trace(go.Scatter(x=df["date"], y=df["inflacion_implicita_12m"], name="Inflación implícita 12m (%)", mode="lines"), secondary_y=True)
    fig = apply_siid_layout(fig, TITLE, yaxis_title="UF/CLP", unit="UF/CLP y %", height=560)
    fig.update_yaxes(title_text="UF/CLP", secondary_y=False)
    fig.update_yaxes(title_text="%", secondary_y=True)
    return fig
