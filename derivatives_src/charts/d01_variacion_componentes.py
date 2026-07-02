from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from derivatives_src.charts._common import base_layout, empty_figure
from derivatives_src.io.bcch_api import BCCHClient
from derivatives_src.io.bde_table import load_bde_rows
from derivatives_src.series_registry import SeriesRegistry
from derivatives_src.charts.d01_waterfall_variacion import (
    METRIC_FLOW,
    METRIC_STOCK,
    month_label,
    default_compare_months,
)
from derivatives_src.charts.siid_style import CMF_PALETTE, CMF_MUTED

CHART_ID = "d01_variacion_componentes"
TITLE = "D01 - Descomposición de la variación por componente"

STOCK_URL = "https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_DERYSPOT/MN_DERYSPOT/DER_RES_POS_01"
FLOW_URL = "https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_DERYSPOT/MN_DERYSPOT/DER_RES_SUS_01/637932256639652707"

MARKET_ORDER = ["Tipos de cambio", "Tasas de interés", "UF/CLP"]

# Componentes visibles en DER_RES_POS_01 y, en general, en el cuadro equivalente de montos transados.
COMPONENT_ROWS = {
    "USD-CLP": {"logical_series": "fx_usd_clp", "label": "USD-CLP", "market": "Tipos de cambio", "dimension_1": "FX"},
    "OME-CLP": {"logical_series": "fx_ome_clp", "label": "OME-CLP", "market": "Tipos de cambio", "dimension_1": "FX"},
    "USD-CLF": {"logical_series": "fx_usd_clf", "label": "USD-CLF", "market": "Tipos de cambio", "dimension_1": "FX"},
    "OME-CLF": {"logical_series": "fx_ome_clf", "label": "OME-CLF", "market": "Tipos de cambio", "dimension_1": "FX"},
    "ME-ME": {"logical_series": "fx_me_me", "label": "ME-ME", "market": "Tipos de cambio", "dimension_1": "FX"},

    "SPC CLP": {"logical_series": "tasas_spc_clp", "label": "SPC CLP", "market": "Tasas de interés", "dimension_1": "Tasas"},
    "SPC CLF": {"logical_series": "tasas_spc_clf", "label": "SPC CLF", "market": "Tasas de interés", "dimension_1": "Tasas"},
    "Tasa extranjera, fijo-variable": {"logical_series": "tasas_ext_fijo_variable", "label": "Tasa extranjera fijo-variable", "market": "Tasas de interés", "dimension_1": "Tasas"},
    "Tasa extranjera, OIS": {"logical_series": "tasas_ext_ois", "label": "Tasa extranjera OIS", "market": "Tasas de interés", "dimension_1": "Tasas"},
    "Basis swaps": {"logical_series": "tasas_basis_swaps", "label": "Basis swaps", "market": "Tasas de interés", "dimension_1": "Tasas"},

    "Inflación CLF-CLP": {"logical_series": "ufclp_inflacion_clf_clp", "label": "Inflación CLF-CLP", "market": "UF/CLP", "dimension_1": "UF/CLP"},
}


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    stock = load_bde_rows(STOCK_URL, COMPONENT_ROWS, start_date, end_date, unit="Millones de USD", chart_id=CHART_ID)
    if not stock.empty:
        stock["metric"] = METRIC_STOCK
        frames.append(stock)

    flow = load_bde_rows(FLOW_URL, COMPONENT_ROWS, start_date, end_date, unit="Millones de USD", chart_id=CHART_ID)
    if not flow.empty:
        flow["metric"] = METRIC_FLOW
        frames.append(flow)

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True, sort=False)
    # En este gráfico label representa el componente.
    return df.groupby(["date", "market", "label", "unit", "metric"], as_index=False)["value"].sum()


def available_markets(df: pd.DataFrame) -> list[str]:
    if df.empty or "market" not in df.columns:
        return MARKET_ORDER
    existing = set(df["market"].dropna().astype(str))
    ordered = [m for m in MARKET_ORDER if m in existing]
    return ordered or sorted(existing)


def build_comparison_dataframe(
    df: pd.DataFrame,
    base_month: pd.Timestamp | str | None = None,
    compare_month: pd.Timestamp | str | None = None,
    metric: str | None = None,
    market: str = "Tipos de cambio",
) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    if metric and "metric" in out.columns:
        out = out[out["metric"].eq(metric)].copy()
    if market and "market" in out.columns:
        out = out[out["market"].eq(market)].copy()
    if out.empty:
        return pd.DataFrame()

    default_base, default_compare = default_compare_months(out, metric)
    base = pd.Timestamp(base_month) if base_month is not None else default_base
    comp = pd.Timestamp(compare_month) if compare_month is not None else default_compare
    if base is None or comp is None:
        return pd.DataFrame()

    base_df = out[out["date"].eq(base)].groupby("label", as_index=False)["value"].sum().rename(columns={"value": "value_base"})
    comp_df = out[out["date"].eq(comp)].groupby("label", as_index=False)["value"].sum().rename(columns={"value": "value_compare"})
    merged = base_df.merge(comp_df, on="label", how="outer").fillna(0)
    merged["variation"] = merged["value_compare"] - merged["value_base"]
    merged["base_month"] = base
    merged["compare_month"] = comp
    merged["base_month_label"] = month_label(base)
    merged["compare_month_label"] = month_label(comp)
    merged["metric"] = metric or (out["metric"].dropna().iloc[0] if "metric" in out.columns and not out["metric"].dropna().empty else METRIC_STOCK)
    merged["market"] = market
    return merged.sort_values("variation", ascending=True)


def build_figure(
    df: pd.DataFrame,
    base_month: pd.Timestamp | str | None = None,
    compare_month: pd.Timestamp | str | None = None,
    metric: str | None = None,
    market: str = "Tipos de cambio",
):
    if df.empty:
        return empty_figure("Faltan datos para descomponer la variación")

    comp_df = build_comparison_dataframe(df, base_month, compare_month, metric, market)
    if comp_df.empty:
        return empty_figure("No hay datos para la combinación seleccionada")

    metric_label = comp_df["metric"].iloc[0]
    base_lbl = comp_df["base_month_label"].iloc[0]
    comp_lbl = comp_df["compare_month_label"].iloc[0]
    total_var = comp_df["variation"].sum()

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=comp_df["label"],
            x=comp_df["variation"],
            orientation="h",
            marker_color=[CMF_PALETTE[1] if v >= 0 else CMF_PALETTE[5] for v in comp_df["variation"]],
            text=comp_df["variation"].map(lambda x: f"{x:,.0f}"),
            textposition="outside",
            customdata=comp_df[["value_base", "value_compare", "base_month_label", "compare_month_label"]],
            hovertemplate=(
                "%{y}<br>"
                "Base %{customdata[2]}: %{customdata[0]:,.0f} MM USD<br>"
                "Comparación %{customdata[3]}: %{customdata[1]:,.0f} MM USD<br>"
                "Variación: %{x:,.0f} MM USD<extra></extra>"
            ),
        )
    )
    fig.add_vline(x=0, line_width=1, line_color="#24113F")
    fig = base_layout(
        fig,
        f"BANCOS. DESCOMPOSICIÓN DE LA VARIACIÓN - {market.upper()}",
        yaxis_title="Componente",
    )
    fig.update_layout(showlegend=False, bargap=0.30, height=520, margin={"l": 92, "r": 110, "t": 135, "b": 185})
    fig.update_xaxes(title_text="Variación en millones de USD", tickformat=",.0f", tickangle=0)
    fig.update_yaxes(title_text="", categoryorder="array", categoryarray=comp_df["label"].tolist())
    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=0.72,
        y=0.98,
        text=f"{metric_label} | {base_lbl} vs {comp_lbl}<br>Variación {market}: <b>{total_var:,.0f}</b> MM USD",
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
