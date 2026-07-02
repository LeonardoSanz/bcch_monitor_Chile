from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from derivatives_src.charts._common import base_layout, empty_figure
from derivatives_src.io.bcch_api import BCCHClient
from derivatives_src.io.bde_table import load_bde_rows
from derivatives_src.series_registry import SeriesRegistry

CHART_ID = "d01_resumen_flujo_monto_transado"
TITLE = "D01 - Montos transados mensuales de derivados bancarios por mercado"
BDE_URL = "https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_DERYSPOT/MN_DERYSPOT/DER_RES_SUS_01/637932256639652707"

ROW_MAP = {
    "FX": {"logical_series": "flujo_fx", "label": "Tipos de cambio", "market": "Tipos de cambio"},
    "Tasas de interés": {"logical_series": "flujo_tasas", "label": "Tasas de interés", "market": "Tasas de interés"},
    "Inflación CLF-CLP": {"logical_series": "flujo_ufclp", "label": "UF/CLP", "market": "UF/CLP"},
    "Monto transado total, total": {"logical_series": "flujo_total", "label": "Total", "market": "Total"},
}
ORDER = ["Tipos de cambio", "Tasas de interés", "UF/CLP"]


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    df = load_bde_rows(BDE_URL, ROW_MAP, start_date, end_date, unit="Millones de USD", chart_id=CHART_ID)
    if df.empty:
        return df
    return df.groupby(["date", "market", "label", "unit"], as_index=False)["value"].sum()


def build_figure(df: pd.DataFrame):
    if df.empty:
        return empty_figure("No se pudo leer el cuadro BDE DER_RES_SUS_01")
    fig = go.Figure()
    bars = df[df["market"].isin(ORDER)].copy()
    total = df[df["market"].eq("Total")].copy().sort_values("date")
    for mercado in ORDER:
        tmp = bars[bars["market"].eq(mercado)].sort_values("date")
        if tmp.empty:
            continue
        fig.add_trace(go.Bar(x=tmp["date"], y=tmp["value"], name=mercado))
    if not total.empty:
        fig.add_trace(go.Scatter(x=total["date"], y=total["value"], name="Total", mode="lines", line={"color": "black", "width": 2}))
    fig.update_layout(barmode="stack")
    return base_layout(fig, "BANCOS. MONTO TRANSADO TOTAL EN DERIVADOS, POR ACTIVO SUBYACENTE", yaxis_title="Millones de USD")
