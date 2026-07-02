from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.charts._common import base_layout, empty_figure
from src.io.bcch_api import BCCHClient
from src.io.bde_table import load_bde_rows
from src.series_registry import SeriesRegistry

CHART_ID = "d01_resumen_stock_monto_vigente"
TITLE = "D01 - Montos vigentes de derivados bancarios por mercado"
BDE_URL = "https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_DERYSPOT/MN_DERYSPOT/DER_RES_POS_01"

ROW_MAP = {
    "FX": {"logical_series": "stock_fx", "label": "Tipos de cambio", "market": "Tipos de cambio"},
    "Tasas de interés": {"logical_series": "stock_tasas", "label": "Tasas de interés", "market": "Tasas de interés"},
    "Inflación CLF-CLP": {"logical_series": "stock_ufclp", "label": "UF/CLP", "market": "UF/CLP"},
    "Monto vigente total, total": {"logical_series": "stock_total", "label": "Total", "market": "Total"},
}

ORDER = ["Tipos de cambio", "Tasas de interés", "UF/CLP"]


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    # Fuente directa: cuadro BDE usado por el Monitor SIID. No usa auto-mapeo ni API SearchSeries.
    df = load_bde_rows(BDE_URL, ROW_MAP, start_date, end_date, unit="Millones de USD", chart_id=CHART_ID)
    if df.empty:
        return df
    return df.groupby(["date", "market", "label", "unit"], as_index=False)["value"].sum()


def build_figure(df: pd.DataFrame):
    if df.empty:
        return empty_figure("No se pudo leer el cuadro BDE DER_RES_POS_01")

    fig = go.Figure()
    bars = df[df["market"].isin(ORDER)].copy()
    total = df[df["market"].eq("Total")].copy().sort_values("date")

    for mercado in ORDER:
        tmp = bars[bars["market"].eq(mercado)].sort_values("date")
        if tmp.empty:
            continue
        fig.add_trace(
            go.Bar(
                x=tmp["date"],
                y=tmp["value"],
                name=mercado,
                hovertemplate="%{x|%b-%Y}<br>%{y:,.0f} MM USD<extra>" + mercado + "</extra>",
            )
        )

    if not total.empty:
        fig.add_trace(
            go.Scatter(
                x=total["date"],
                y=total["value"],
                name="Total",
                mode="lines",
                line={"color": "black", "width": 2},
                hovertemplate="%{x|%b-%Y}<br>%{y:,.0f} MM USD<extra>Total</extra>",
            )
        )

    fig.update_layout(barmode="stack")
    fig = base_layout(
        fig,
        "BANCOS. MONTO VIGENTE TOTAL EN DERIVADOS, POR ACTIVO SUBYACENTE",
        yaxis_title="Millones de USD",
    )
    return fig
