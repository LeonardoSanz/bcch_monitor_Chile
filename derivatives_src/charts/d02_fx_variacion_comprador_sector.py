from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from derivatives_src.charts._common import base_layout, empty_figure
from derivatives_src.charts.d01_waterfall_variacion import month_label
from derivatives_src.charts.d02_fx_helpers import DER_BM_PPC_02, MM_USD, SECTOR_ORDER, _base, _filter_dates, sector_from_parent
from derivatives_src.charts.siid_style import CMF_MUTED, CMF_PALETTE
from derivatives_src.io.bde_table import fetch_bde_table, normalize_text
from derivatives_src.io.bcch_api import BCCHClient
from derivatives_src.series_registry import SeriesRegistry

SIDE_ROW = "monto vigente comprador"
CHART_ID = "d02_fx_variacion_comprador_sector"
TITLE = "D02 - Variación de montos vigentes comprador por sector de contraparte"


def _is_side_row(row: pd.Series) -> bool:
    label_norm = normalize_text(str(row.get("bde_series", "")))
    sector = sector_from_parent(str(row.get("bde_parent", "")))
    return label_norm == SIDE_ROW and sector in SECTOR_ORDER


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    # En DER_BM_PPC_02, las filas comprador/vendedor vienen como hijos del sector:
    #   No residentes
    #       Monto vigente comprador
    #       Monto vigente vendedor
    # Por eso el sector debe leerse desde bde_parent, no desde bde_series.
    raw = fetch_bde_table(DER_BM_PPC_02).long.copy()
    raw = _filter_dates(raw, start_date, end_date)
    raw = raw[raw.apply(_is_side_row, axis=1)].copy()
    if raw.empty:
        return _base(pd.DataFrame(), CHART_ID, "sector")

    raw["sector"] = raw["bde_parent"].map(sector_from_parent)
    raw = raw[raw["sector"].isin(SECTOR_ORDER)].copy()
    out = raw.groupby(["date", "sector"], as_index=False)["value"].sum()
    return _base(out, CHART_ID, "sector", "sector", "DER_BM_PPC_02")


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
        return pd.DataFrame()
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])

    default_base, default_compare = default_compare_months(out)
    base = pd.Timestamp(base_month) if base_month is not None else default_base
    comp = pd.Timestamp(compare_month) if compare_month is not None else default_compare
    if base is None or comp is None:
        return pd.DataFrame()

    base_df = out[out["date"].eq(base)].groupby("dimension_1", as_index=False)["value"].sum().rename(columns={"dimension_1": "sector", "value": "value_base"})
    comp_df = out[out["date"].eq(comp)].groupby("dimension_1", as_index=False)["value"].sum().rename(columns={"dimension_1": "sector", "value": "value_compare"})

    merged = pd.DataFrame({"sector": SECTOR_ORDER}).merge(base_df, on="sector", how="left").merge(comp_df, on="sector", how="left")
    merged[["value_base", "value_compare"]] = merged[["value_base", "value_compare"]].fillna(0)
    merged["variation"] = merged["value_compare"] - merged["value_base"]
    merged["base_month"] = base
    merged["compare_month"] = comp
    merged["base_month_label"] = month_label(base)
    merged["compare_month_label"] = month_label(comp)
    return merged


def build_figure(df: pd.DataFrame, base_month=None, compare_month=None):
    if df.empty:
        return empty_figure("Faltan datos para calcular variación")

    comp_df = build_comparison_dataframe(df, base_month, compare_month)
    if comp_df.empty:
        return empty_figure("No hay meses suficientes para comparar")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=comp_df["sector"],
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

    fig = base_layout(fig, TITLE.replace("D02 - ", "BANCOS. ").upper(), yaxis_title="Millones de USD")
    fig.update_layout(showlegend=False, bargap=0.32, height=520)
    fig.update_xaxes(title_text="Sector de contraparte", tickangle=0)
    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=0.99,
        y=0.99,
        text=f"{base_lbl} vs {comp_lbl}<br>Variación total: <b>{total_var:,.0f}</b> MM USD",
        showarrow=False,
        align="right",
        bgcolor="rgba(255,255,255,0.86)",
        bordercolor="#E6E0EF",
        borderwidth=1,
        borderpad=4,
        font={"size": 11, "color": CMF_MUTED},
    )
    return fig
