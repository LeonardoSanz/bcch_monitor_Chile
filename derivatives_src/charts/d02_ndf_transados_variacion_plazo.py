from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from derivatives_src.charts._common import base_layout, empty_figure
from derivatives_src.charts.d01_waterfall_variacion import month_label
from derivatives_src.charts.d02_fx_helpers import MM_USD, PLAZO_ORDER
from derivatives_src.charts.d02_ndf_transados_plazo import build_dataframe as build_stock_dataframe
from derivatives_src.charts.siid_style import CMF_MUTED, CMF_PALETTE
from derivatives_src.io.bcch_api import BCCHClient
from derivatives_src.series_registry import SeriesRegistry

CHART_ID = "d02_ndf_variacion_transados_plazo"
TITLE = "D02 - Variación de montos transados netos NDF por plazo contractual"


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    df = build_stock_dataframe(client, registry, start_date, end_date, demo)
    if df.empty:
        return df
    out = df.copy()
    out["chart_id"] = CHART_ID
    out["series_id"] = CHART_ID + "::" + out["dimension_1"].astype(str)
    out["status_code"] = "BDE_HTML_COMPARISON"
    return out


def available_months(df: pd.DataFrame) -> list[pd.Timestamp]:
    if df.empty or "date" not in df.columns:
        return []
    return sorted(pd.to_datetime(df["date"]).dropna().unique())


def default_compare_months(df: pd.DataFrame) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    months = available_months(df)
    if len(months) >= 2:
        return pd.Timestamp(months[-2]), pd.Timestamp(months[-1])
    if len(months) == 1:
        return pd.Timestamp(months[0]), pd.Timestamp(months[0])
    return None, None


def build_comparison_dataframe(df: pd.DataFrame, base_month=None, compare_month=None) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["plazo", "value_base", "value_compare", "variation"])

    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out["plazo"] = out["dimension_1"].astype(str)

    default_base, default_compare = default_compare_months(out)
    base = pd.Timestamp(base_month) if base_month is not None else default_base
    comp = pd.Timestamp(compare_month) if compare_month is not None else default_compare
    if base is None or comp is None:
        return pd.DataFrame(columns=["plazo", "value_base", "value_compare", "variation"])

    base_df = out[out["date"].eq(base)].groupby("plazo", as_index=False)["value"].sum().rename(columns={"value": "value_base"})
    comp_df = out[out["date"].eq(comp)].groupby("plazo", as_index=False)["value"].sum().rename(columns={"value": "value_compare"})

    merged = pd.DataFrame({"plazo": PLAZO_ORDER}).merge(base_df, on="plazo", how="left").merge(comp_df, on="plazo", how="left")
    merged[["value_base", "value_compare"]] = merged[["value_base", "value_compare"]].fillna(0)
    merged["variation"] = merged["value_compare"] - merged["value_base"]
    merged["base_month"] = base
    merged["compare_month"] = comp
    merged["base_month_label"] = month_label(base)
    merged["compare_month_label"] = month_label(comp)
    return merged


def build_figure(df: pd.DataFrame, base_month=None, compare_month=None) -> go.Figure:
    comp_df = build_comparison_dataframe(df, base_month, compare_month)
    if comp_df.empty:
        return empty_figure("Faltan datos para calcular variación")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=comp_df["plazo"],
        y=comp_df["variation"],
        marker_color=[CMF_PALETTE[1] if v >= 0 else CMF_PALETTE[5] for v in comp_df["variation"]],
        text=comp_df["variation"].map(lambda x: f"{x:,.0f}"),
        textposition="outside",
        customdata=comp_df[["value_base", "value_compare", "base_month_label", "compare_month_label"]],
        hovertemplate=(
            "%{x}<br>"
            "Base %{customdata[2]}: %{customdata[0]:,.0f} MM USD<br>"
            "Comparación %{customdata[3]}: %{customdata[1]:,.0f} MM USD<br>"
            "Variación: %{y:,.0f} MM USD<extra></extra>"
        ),
    ))
    fig.add_hline(y=0, line_width=1, line_color="#24113F")

    base_lbl = comp_df["base_month_label"].iloc[0]
    comp_lbl = comp_df["compare_month_label"].iloc[0]
    total_var = comp_df["variation"].sum()

    fig = base_layout(fig, TITLE.replace("D02 - ", "BANCOS. ").upper(), yaxis_title=MM_USD)
    fig.update_layout(
        showlegend=False,
        height=520,
        bargap=0.32,
        margin={"l": 78, "r": 110, "t": 135, "b": 185},
    )
    for ann in fig.layout.annotations:
        if isinstance(getattr(ann, "text", None), str) and "Fuente: Banco Central de Chile" in ann.text:
            ann.y = -0.48

    fig.update_xaxes(title_text="", tickangle=-90)
    fig.update_yaxes(title_text=MM_USD)
    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=0.72,
        y=0.98,
        text=f"{base_lbl} vs {comp_lbl}<br>Variación total: <b>{total_var:,.0f}</b> MM USD",
        showarrow=False,
        align="left",
        xanchor="left",
        yanchor="top",
        bgcolor="rgba(255,255,255,0.86)",
        bordercolor="#E6E0EF",
        borderwidth=1,
        borderpad=3,
        font={"size": 10, "color": CMF_MUTED},
    )
    return fig
