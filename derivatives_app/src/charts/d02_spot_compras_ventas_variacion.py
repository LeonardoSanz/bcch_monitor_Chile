from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.charts._common import base_layout, empty_figure
from src.charts.d01_waterfall_variacion import month_label
from src.charts.d02_fx_helpers import SPT_USDCLP_S02, MM_USD
from src.charts.siid_style import CMF_MUTED, CMF_PALETTE
from src.io.bde_table import fetch_bde_table, normalize_text, clean_label, parse_bde_period, parse_bde_number
from src.io.bcch_api import BCCHClient
from src.series_registry import SeriesRegistry

CHART_ID = "d02_spot_compras_ventas_variacion_sector"
TITLE = "D02 - Variación compras/ventas spot USD/CLP por sector"

# Partición solicitada: no incluye Interbancario ni el agregado Residentes no bancos.
SPOT_CV_SECTOR_ORDER = [
    "Fondos de Pensiones",
    "Sector Real",
    "Cías. de Seguros",
    "Corredores de Bolsa",
    "AGF",
    "Otros Sectores",
    "No Residentes",
]

METRIC_ORDER = ["Compras USD", "Ventas USD"]
METRIC_MAP = {
    "compras": "Compras USD",
    "ventas": "Ventas USD",
}


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "date", "value", "chart_id", "logical_series", "series_id", "label", "market",
        "dimension_1", "dimension_2", "metrica", "sector", "frequency", "unit", "status_code"
    ])


def _sector_from_label(label: object) -> str | None:
    norm = normalize_text(label)
    if norm == "fondos de pensiones":
        return "Fondos de Pensiones"
    if norm in {"empresas sector real", "sector real"}:
        return "Sector Real"
    if "companias de seguro" in norm or "companias de seguros" in norm or "cias de seguros" in norm:
        return "Cías. de Seguros"
    if "corredoras de bolsa" in norm or "corredores de bolsa" in norm or "agencias de valores" in norm:
        return "Corredores de Bolsa"
    if "administradoras generales de fondos" in norm or norm == "agf":
        return "AGF"
    if norm == "otros sectores":
        return "Otros Sectores"
    if norm == "no residentes":
        return "No Residentes"
    return None


def _is_reset_label(label: object) -> bool:
    norm = normalize_text(label)
    return (
        norm in {"sectores", "residentes no bancos", "interbancario", "notas"}
        or norm.startswith("monto transado total")
    )


def _period_columns(wide: pd.DataFrame) -> list[str]:
    return [c for c in wide.columns if pd.notna(parse_bde_period(c))]


def _extract_compras_ventas(start_date: str, end_date: str) -> pd.DataFrame:
    """Lee SPT_USDCLP_S02 por orden visual de filas.

    La BDE muestra cada sector padre y debajo sus filas Compras/Ventas/Neto.
    En vez de depender de bde_parent, se mantiene el último sector de detalle visto.
    Así evitamos perder datos cuando el HTML/pd.read_html cambia las sangrías.
    """
    table = fetch_bde_table(SPT_USDCLP_S02)
    wide = table.wide.copy()
    period_cols = _period_columns(wide)
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)

    records: list[dict] = []
    current_sector: str | None = None

    for _, row in wide.iterrows():
        raw_label = row.get("bde_series_raw", row.get("bde_series", ""))
        label = clean_label(raw_label)
        norm = normalize_text(label)

        sector = _sector_from_label(label)
        if sector is not None:
            current_sector = sector
            continue

        if _is_reset_label(label):
            current_sector = None
            continue

        metrica = METRIC_MAP.get(norm)
        if metrica is None or current_sector not in SPOT_CV_SECTOR_ORDER:
            continue

        for col in period_cols:
            dt = parse_bde_period(col)
            if pd.isna(dt):
                continue
            dt = pd.Timestamp(dt)
            if dt < start or dt > end:
                continue

            value = parse_bde_number(row[col])
            if pd.isna(value):
                continue

            records.append({
                "date": dt,
                "sector": current_sector,
                "metrica": metrica,
                "value": value,
            })

    if not records:
        return pd.DataFrame(columns=["date", "sector", "metrica", "value"])
    return pd.DataFrame(records)


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    raw = _extract_compras_ventas(start_date, end_date)
    if raw.empty:
        return _empty()

    out = raw.groupby(["date", "sector", "metrica"], as_index=False)["value"].sum()
    out["chart_id"] = CHART_ID
    out["logical_series"] = out["metrica"] + " - " + out["sector"]
    out["series_id"] = CHART_ID + "::" + out["logical_series"]
    out["label"] = out["sector"]
    out["market"] = "USD/CLP"
    out["dimension_1"] = out["sector"]
    out["dimension_2"] = out["metrica"]
    out["frequency"] = "MONTHLY"
    out["unit"] = MM_USD
    out["status_code"] = "SPT_USDCLP_S02"

    cols = [
        "date", "value", "chart_id", "logical_series", "series_id", "label", "market",
        "dimension_1", "dimension_2", "metrica", "sector", "frequency", "unit", "status_code"
    ]
    return out[cols].sort_values(["metrica", "date", "sector"]).reset_index(drop=True)


def available_metrics(df: pd.DataFrame) -> list[str]:
    if df.empty or "metrica" not in df.columns:
        return METRIC_ORDER
    existing = set(df["metrica"].dropna().astype(str))
    ordered = [x for x in METRIC_ORDER if x in existing]
    return ordered or METRIC_ORDER


def available_months(df: pd.DataFrame, metrica: str | None = None) -> list[pd.Timestamp]:
    if df.empty or "date" not in df.columns:
        return []
    out = df.copy()
    if metrica and "metrica" in out.columns:
        out = out[out["metrica"].eq(metrica)]
    return sorted(pd.to_datetime(out["date"]).dropna().unique())


def default_compare_months(df: pd.DataFrame, metrica: str | None = None) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    months = available_months(df, metrica)
    if len(months) >= 2:
        return pd.Timestamp(months[-2]), pd.Timestamp(months[-1])
    if len(months) == 1:
        return pd.Timestamp(months[0]), pd.Timestamp(months[0])
    return None, None


def build_comparison_dataframe(df: pd.DataFrame, base_month=None, compare_month=None, metrica: str = "Compras USD") -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["sector", "value_base", "value_compare", "variation"])

    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])

    if metrica and "metrica" in out.columns:
        out = out[out["metrica"].eq(metrica)].copy()
    elif metrica and "dimension_2" in out.columns:
        out = out[out["dimension_2"].eq(metrica)].copy()

    if out.empty:
        return pd.DataFrame(columns=["sector", "value_base", "value_compare", "variation"])

    default_base, default_compare = default_compare_months(out, metrica)
    base = pd.Timestamp(base_month) if base_month is not None else default_base
    comp = pd.Timestamp(compare_month) if compare_month is not None else default_compare
    if base is None or comp is None:
        return pd.DataFrame(columns=["sector", "value_base", "value_compare", "variation"])

    sector_col = "sector" if "sector" in out.columns else "dimension_1"
    base_df = out[out["date"].eq(base)].groupby(sector_col, as_index=False)["value"].sum().rename(columns={sector_col: "sector", "value": "value_base"})
    comp_df = out[out["date"].eq(comp)].groupby(sector_col, as_index=False)["value"].sum().rename(columns={sector_col: "sector", "value": "value_compare"})

    merged = pd.DataFrame({"sector": SPOT_CV_SECTOR_ORDER}).merge(base_df, on="sector", how="left").merge(comp_df, on="sector", how="left")
    merged[["value_base", "value_compare"]] = merged[["value_base", "value_compare"]].fillna(0)
    merged["variation"] = merged["value_compare"] - merged["value_base"]
    merged["base_month"] = base
    merged["compare_month"] = comp
    merged["base_month_label"] = month_label(base)
    merged["compare_month_label"] = month_label(comp)
    merged["metrica"] = metrica
    return merged


def _figure_common(fig: go.Figure, title: str, total_var: float, base_lbl: str, comp_lbl: str, metrica: str) -> go.Figure:
    fig = base_layout(fig, title, yaxis_title=MM_USD)
    fig.update_layout(
        showlegend=False,
        height=520,
        margin={"l": 78, "r": 110, "t": 135, "b": 185},
    )
    for ann in fig.layout.annotations:
        if isinstance(getattr(ann, "text", None), str) and "Fuente: Banco Central de Chile" in ann.text:
            ann.y = -0.48

    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=0.72,
        y=0.98,
        text=f"{metrica} | {base_lbl} vs {comp_lbl}<br>Variación total: <b>{total_var:,.0f}</b> MM USD",
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


def build_figure_sector(df: pd.DataFrame, base_month=None, compare_month=None, metrica: str = "Compras USD") -> go.Figure:
    comp_df = build_comparison_dataframe(df, base_month, compare_month, metrica)
    if comp_df.empty:
        return empty_figure("Faltan datos para calcular variación")

    fig = go.Figure()
    fig.add_trace(go.Bar(
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
    ))
    fig.add_hline(y=0, line_width=1, line_color="#24113F")
    fig = _figure_common(
        fig,
        "BANCOS. VARIACIÓN SPOT POR SECTOR",
        comp_df["variation"].sum(),
        comp_df["base_month_label"].iloc[0],
        comp_df["compare_month_label"].iloc[0],
        metrica,
    )
    fig.update_xaxes(title_text="", tickangle=-90)
    fig.update_yaxes(title_text=MM_USD)
    return fig


def build_figure_ranking(df: pd.DataFrame, base_month=None, compare_month=None, metrica: str = "Compras USD") -> go.Figure:
    comp_df = build_comparison_dataframe(df, base_month, compare_month, metrica)
    if comp_df.empty:
        return empty_figure("Faltan datos para ranking")

    rank = comp_df.copy().sort_values("variation", ascending=True)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=rank["sector"],
        x=rank["variation"],
        orientation="h",
        marker_color=[CMF_PALETTE[1] if v >= 0 else CMF_PALETTE[5] for v in rank["variation"]],
        text=rank["variation"].map(lambda x: f"{x:,.0f}"),
        textposition="outside",
        customdata=rank[["value_base", "value_compare", "base_month_label", "compare_month_label"]],
        hovertemplate=(
            "%{y}<br>"
            "Base %{customdata[2]}: %{customdata[0]:,.0f} MM USD<br>"
            "Comparación %{customdata[3]}: %{customdata[1]:,.0f} MM USD<br>"
            "Variación: %{x:,.0f} MM USD<extra></extra>"
        ),
    ))
    fig.add_vline(x=0, line_width=1, line_color="#24113F")
    fig = _figure_common(
        fig,
        "BANCOS. RANKING DE CONTRIBUCIÓN SPOT",
        comp_df["variation"].sum(),
        comp_df["base_month_label"].iloc[0],
        comp_df["compare_month_label"].iloc[0],
        metrica,
    )
    fig.update_xaxes(title_text="Variación en millones de USD", tickformat=",.0f", tickangle=0)
    fig.update_yaxes(title_text="", categoryorder="array", categoryarray=rank["sector"].tolist())
    return fig


def build_figure(df: pd.DataFrame):
    return build_figure_sector(df)
