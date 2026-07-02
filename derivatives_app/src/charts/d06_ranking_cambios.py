from __future__ import annotations

import pandas as pd
import plotly.express as px

from src.charts.siid_style import apply_siid_layout
from src.charts._common import empty_figure, monthly_change_table
from src.data_loader import load_all_configured_data
from src.io.bcch_api import BCCHClient
from src.series_registry import SeriesRegistry

TITLE = "D06 - Ranking de cambios mensuales por serie"


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    df = load_all_configured_data(client, registry, start_date, end_date, demo=demo)
    if df.empty:
        return df
    changes = monthly_change_table(df, ["chart_id", "label", "market", "dimension_1", "dimension_2", "unit"])
    latest = changes[changes["date"].eq(changes["date"].max())].copy()
    latest["abs_var_mom"] = latest["var_mom"].abs()
    latest = latest.sort_values("abs_var_mom", ascending=False).head(20)
    latest["serie"] = latest["market"].fillna("") + " | " + latest["label"].fillna("")
    return latest


def build_figure(df: pd.DataFrame):
    if df.empty:
        return empty_figure("No hay datos para ranking de cambios")
    fig = px.bar(df.sort_values("var_mom"), x="var_mom", y="serie", orientation="h", hover_data=["date", "value", "value_lag_1m", "pct_mom", "unit"])
    fig.update_layout(title=TITLE, template=None, height=650, margin={"l": 40, "r": 40, "t": 70, "b": 40})
    fig.update_xaxes(title_text="Cambio mensual")
    fig.update_yaxes(title_text="")
    fig.add_vline(x=0, line_dash="dash")
    return fig
