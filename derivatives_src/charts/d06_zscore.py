from __future__ import annotations

import pandas as pd
import plotly.express as px

from derivatives_src.charts.siid_style import apply_siid_layout
from derivatives_src.charts._common import empty_figure, latest_snapshot, zscore_table
from derivatives_src.data_loader import load_all_configured_data
from derivatives_src.io.bcch_api import BCCHClient
from derivatives_src.series_registry import SeriesRegistry

TITLE = "D06 - Z-score histórico de actividad y stock"


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    df = load_all_configured_data(client, registry, start_date, end_date, demo=demo)
    if df.empty:
        return df
    z = zscore_table(df, ["chart_id", "label", "market", "dimension_1", "dimension_2", "unit"], window=36)
    latest = latest_snapshot(z).copy()
    latest["abs_zscore"] = latest["zscore"].abs()
    latest["serie"] = latest["market"].fillna("") + " | " + latest["label"].fillna("")
    return latest.sort_values("abs_zscore", ascending=False).head(20)


def build_figure(df: pd.DataFrame):
    if df.empty or df["zscore"].isna().all():
        return empty_figure("No hay historia suficiente para z-score")
    fig = px.bar(df.sort_values("zscore"), x="zscore", y="serie", orientation="h", hover_data=["date", "value", "unit"])
    fig.update_layout(title=TITLE, template=None, height=650, margin={"l": 40, "r": 40, "t": 70, "b": 40})
    fig.update_xaxes(title_text="Z-score 36m")
    fig.update_yaxes(title_text="")
    fig.add_vline(x=0, line_dash="dash")
    fig.add_vline(x=2, line_dash="dot")
    fig.add_vline(x=-2, line_dash="dot")
    return fig
