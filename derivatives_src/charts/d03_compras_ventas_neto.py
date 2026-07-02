from __future__ import annotations

import pandas as pd
import plotly.express as px

from derivatives_src.charts._common import base_layout, build_basic_dataframe, empty_figure, latest_snapshot
from derivatives_src.io.bcch_api import BCCHClient
from derivatives_src.series_registry import SeriesRegistry

CHART_ID = "d03_fx_compras_ventas_neto_sector"
TITLE = "D03 - Compras, ventas y neto por sector"


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    df = build_basic_dataframe(CHART_ID, client, registry, start_date, end_date, demo)
    if df.empty:
        return df
    return (
        df.groupby(["date", "dimension_1", "dimension_2", "label", "unit"], as_index=False)["value"]
        .sum()
        .rename(columns={"dimension_1": "tipo_flujo", "dimension_2": "sector"})
    )


def build_figure(df: pd.DataFrame):
    if df.empty:
        return empty_figure("Faltan series para compras/ventas/neto")
    snap = latest_snapshot(df)
    fig = px.bar(snap, x="sector", y="value", color="tipo_flujo", barmode="group", hover_data=["date", "unit"])
    return base_layout(fig, TITLE + " - último dato", yaxis_title=df["unit"].iloc[0])
