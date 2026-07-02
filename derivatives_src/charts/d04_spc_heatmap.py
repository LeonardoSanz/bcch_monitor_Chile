from __future__ import annotations

import pandas as pd
import plotly.express as px

from derivatives_src.charts._common import build_basic_dataframe, empty_figure, latest_snapshot
from derivatives_src.charts.siid_style import apply_siid_layout
from derivatives_src.io.bcch_api import BCCHClient
from derivatives_src.series_registry import SeriesRegistry

CHART_ID = "d04_spc_clp_transado_plazo_contraparte"
TITLE = "D04 - Heatmap SPC CLP transado por plazo contractual y contraparte"


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    df = build_basic_dataframe(CHART_ID, client, registry, start_date, end_date, demo)
    if df.empty:
        return df
    return (
        df.groupby(["date", "dimension_1", "dimension_2", "label", "unit"], as_index=False)["value"]
        .sum()
        .rename(columns={"dimension_1": "plazo_contractual", "dimension_2": "contraparte"})
    )


def build_figure(df: pd.DataFrame):
    if df.empty:
        return empty_figure("Faltan series para heatmap SPC")
    snap = latest_snapshot(df)
    matrix = snap.pivot_table(index="contraparte", columns="plazo_contractual", values="value", aggfunc="sum").fillna(0)
    fig = px.imshow(matrix, text_auto=",.0f", aspect="auto", labels={"color": snap["unit"].iloc[0]})
    fig = apply_siid_layout(fig, TITLE + " - último dato", yaxis_title="Contraparte", unit=snap["unit"].iloc[0], height=560, rotate_months=False)
    fig.update_xaxes(title_text="Plazo contractual")
    return fig
