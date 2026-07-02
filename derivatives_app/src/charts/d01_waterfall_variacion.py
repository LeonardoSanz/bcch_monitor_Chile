from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.charts._common import base_layout, empty_figure
from src.io.bcch_api import BCCHClient
from src.series_registry import SeriesRegistry
from src.charts.d01_resumen_stock import build_dataframe as build_stock_dataframe
from src.charts.d01_resumen_flujo import build_dataframe as build_flow_dataframe
from src.charts.siid_style import CMF_PALETTE, CMF_MUTED

CHART_ID = "d01_variacion_mercado"
TITLE = "D01 - Variación por mercado"
ORDER = ["Tipos de cambio", "Tasas de interés", "UF/CLP"]
METRIC_STOCK = "Monto vigente"
METRIC_FLOW = "Monto transado"


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    """Devuelve stock y flujo mensual por mercado para comparar cualquier par de meses.

    La figura permite elegir si la comparación se hace sobre montos vigentes o montos
    transados. La fuente sigue siendo directa desde los cuadros BDE del Monitor SIID.
    """
    frames: list[pd.DataFrame] = []

    stock = build_stock_dataframe(client, registry, start_date, end_date, demo)
    if not stock.empty:
        stock = stock[stock["market"].isin(ORDER)].copy()
        stock["metric"] = METRIC_STOCK
        frames.append(stock)

    flow = build_flow_dataframe(client, registry, start_date, end_date, demo)
    if not flow.empty:
        flow = flow[flow["market"].isin(ORDER)].copy()
        flow["metric"] = METRIC_FLOW
        frames.append(flow)

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True, sort=False)
    return df.groupby(["date", "market", "label", "unit", "metric"], as_index=False)["value"].sum()


def available_months(df: pd.DataFrame, metric: str | None = None) -> list[pd.Timestamp]:
    if df.empty or "date" not in df.columns:
        return []
    out = df.copy()
    if metric and "metric" in out.columns:
        out = out[out["metric"].eq(metric)]
    return sorted(pd.to_datetime(out["date"]).dropna().unique())


def available_metrics(df: pd.DataFrame) -> list[str]:
    if df.empty or "metric" not in df.columns:
        return [METRIC_STOCK]
    preferred = [METRIC_STOCK, METRIC_FLOW]
    existing = [m for m in preferred if m in set(df["metric"].dropna().astype(str))]
    return existing or sorted(df["metric"].dropna().astype(str).unique().tolist())


def month_label(dt) -> str:
    ts = pd.Timestamp(dt)
    meses = {
        1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
        7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic",
    }
    return f"{meses[ts.month]}-{ts.year}"


def default_compare_months(df: pd.DataFrame, metric: str | None = None) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    months = available_months(df, metric)
    if len(months) >= 2:
        return pd.Timestamp(months[-2]), pd.Timestamp(months[-1])
    if len(months) == 1:
        return pd.Timestamp(months[0]), pd.Timestamp(months[0])
    return None, None


def build_comparison_dataframe(
    df: pd.DataFrame,
    base_month: pd.Timestamp | str | None = None,
    compare_month: pd.Timestamp | str | None = None,
    metric: str | None = None,
) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])

    metric_value = metric or (available_metrics(out)[0] if available_metrics(out) else METRIC_STOCK)
    if "metric" in out.columns:
        out = out[out["metric"].eq(metric_value)].copy()

    default_base, default_compare = default_compare_months(out, metric_value)
    base = pd.Timestamp(base_month) if base_month is not None else default_base
    comp = pd.Timestamp(compare_month) if compare_month is not None else default_compare
    if base is None or comp is None:
        return pd.DataFrame()

    base_df = out[out["date"].eq(base)].groupby("market", as_index=False)["value"].sum().rename(columns={"value": "value_base"})
    comp_df = out[out["date"].eq(comp)].groupby("market", as_index=False)["value"].sum().rename(columns={"value": "value_compare"})

    merged = pd.DataFrame({"market": ORDER}).merge(base_df, on="market", how="left").merge(comp_df, on="market", how="left")
    merged[["value_base", "value_compare"]] = merged[["value_base", "value_compare"]].fillna(0)
    merged["variation"] = merged["value_compare"] - merged["value_base"]
    merged["pct_variation"] = merged.apply(
        lambda r: r["variation"] / r["value_base"] if abs(r["value_base"]) > 0 else pd.NA,
        axis=1,
    )
    merged["base_month"] = base
    merged["compare_month"] = comp
    merged["base_month_label"] = month_label(base)
    merged["compare_month_label"] = month_label(comp)
    merged["metric"] = metric_value
    return merged


def build_figure(
    df: pd.DataFrame,
    base_month: pd.Timestamp | str | None = None,
    compare_month: pd.Timestamp | str | None = None,
    metric: str | None = None,
):
    if df.empty:
        return empty_figure("Faltan datos para calcular variación")

    comp_df = build_comparison_dataframe(df, base_month, compare_month, metric)
    if comp_df.empty:
        return empty_figure("No hay meses suficientes para comparar")

    metric_label = comp_df["metric"].iloc[0]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=comp_df["market"],
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
        )
    )
    fig.add_hline(y=0, line_width=1, line_color="#24113F")

    base_lbl = comp_df["base_month_label"].iloc[0]
    comp_lbl = comp_df["compare_month_label"].iloc[0]
    total_var = comp_df["variation"].sum()
    fig = base_layout(
        fig,
        "BANCOS. VARIACIÓN POR MERCADO",
        yaxis_title="Millones de USD",
    )
    fig.update_layout(showlegend=False, bargap=0.35, height=520, margin={"l": 78, "r": 110, "t": 135, "b": 185})
    fig.update_xaxes(title_text="Mercado", tickangle=0)
    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=0.72,
        y=0.98,
        text=f"{metric_label} | {base_lbl} vs {comp_lbl}<br>Variación total: <b>{total_var:,.0f}</b> MM USD",
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
