from __future__ import annotations

import pandas as pd
import plotly.express as px

from src.charts._common import base_layout, build_basic_dataframe, empty_figure
from src.io.bcch_api import BCCHClient
from src.series_registry import SeriesRegistry

CHART_ID = "d03_spot_vs_derivados_usdclp"
TITLE = "D03 - Spot vs derivados USD/CLP, monto transado mensual"


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    df = build_basic_dataframe(CHART_ID, client, registry, start_date, end_date, demo)
    if df.empty:
        return df
    return df.groupby(["date", "dimension_1", "label", "unit"], as_index=False)["value"].sum().rename(columns={"dimension_1": "mercado"})


def build_figure(df: pd.DataFrame):
    if df.empty:
        return empty_figure("Faltan series para spot vs derivados")
    fig = px.bar(df, x="date", y="value", color="mercado", barmode="group", hover_data=["label", "unit"])
    return base_layout(fig, TITLE, yaxis_title=df["unit"].iloc[0])
