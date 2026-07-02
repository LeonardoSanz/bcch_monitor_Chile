from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.charts._common import base_layout, empty_figure
from src.charts.d01_waterfall_variacion import month_label
from src.charts.d02_fx_helpers import DER_BM_PPC_02, MM_USD
from src.charts.siid_style import CMF_MUTED, CMF_PALETTE
from src.io.bde_table import fetch_bde_table, normalize_text, clean_label, parse_bde_period, parse_bde_number
from src.io.bcch_api import BCCHClient
from src.series_registry import SeriesRegistry

CHART_ID = "d02_fx_variacion_apertura_sector"
TITLE = "D02 - Variación de montos vigentes por apertura y sector"

DETAIL_SECTOR_ORDER = [
    "No Residentes",
    "Fondos de Pensiones",
    "Sector Real",
    "Otros Sectores",
    "Corredores de Bolsa",
    "AGF",
    "Cías. de Seguros",
]

APERTURA_ORDER = ["Comprador", "Vendedor", "Neto"]
APERTURA_MAP = {
    "monto vigente comprador": "Comprador",
    "monto vigente vendedor": "Vendedor",
    "monto vigente neto": "Neto",
}


def _sector_from_label(label: object) -> str | None:
    norm = normalize_text(label)
    if norm == "no residentes":
        return "No Residentes"
    if norm == "fondos de pensiones":
        return "Fondos de Pensiones"
    if norm in {"empresas sector real", "sector real"}:
        return "Sector Real"
    if "corredoras de bolsa" in norm or "corredores de bolsa" in norm:
        return "Corredores de Bolsa"
    if "administradoras generales de fondos" in norm or norm == "agf":
        return "AGF"
    if "companias de seguros" in norm or "companias de seguro" in norm or "cias de seguros" in norm:
        return "Cías. de Seguros"
    if norm == "otros sectores":
        return "Otros Sectores"
    return None


def _period_columns(wide: pd.DataFrame) -> list[str]:
    return [c for c in wide.columns if pd.notna(parse_bde_period(c))]


def _indent(value: object) -> int:
    raw = "" if value is None or pd.isna(value) else str(value)
    raw = raw.replace("\xa0", " ")
    return len(raw) - len(raw.lstrip(" "))


def _extract_aperturas_from_wide(start_date: str, end_date: str) -> pd.DataFrame:
    """Extrae comprador/vendedor/neto desde la jerarquía visible del cuadro BDE.

    DER_BM_PPC_02 tiene la forma:
        No residentes
            Monto vigente comprador
            Monto vigente vendedor
            Monto vigente neto

    Por lo tanto:
    - el sector se toma de la fila padre anterior;
    - la apertura se toma de la fila hija;
    - se excluyen agregados como Interbancario y Residentes no bancos para evitar duplicaciones.
    """
    table = fetch_bde_table(DER_BM_PPC_02)
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
        level_indent = _indent(raw_label)

        sector = _sector_from_label(label)
        if sector is not None:
            current_sector = sector
            continue

        # Cuando aparece un agregado o una cabecera, no debe contaminar los hijos siguientes.
        if norm in {"sectores", "residentes no bancos", "interbancario", "notas"} or norm.startswith("monto vigente total"):
            current_sector = None
            continue

        apertura = APERTURA_MAP.get(norm)
        if apertura is None:
            continue

        # Solo aceptamos comprador/vendedor/neto si venían debajo de un sector de detalle.
        if current_sector not in DETAIL_SECTOR_ORDER:
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
            records.append(
                {
                    "date": dt,
                    "sector": current_sector,
                    "apertura": apertura,
                    "value": value,
                }
            )

    cols = ["date", "sector", "apertura", "value"]
    if not records:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(records, columns=cols)


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    df = _extract_aperturas_from_wide(start_date, end_date)

    cols = [
        "date", "value", "chart_id", "logical_series", "series_id", "label", "market",
        "dimension_1", "dimension_2", "apertura", "sector", "frequency", "unit", "status_code"
    ]
    if df.empty:
        return pd.DataFrame(columns=cols)

    out = df.groupby(["date", "sector", "apertura"], as_index=False)["value"].sum()
    out["chart_id"] = CHART_ID
    out["logical_series"] = out["sector"] + " - " + out["apertura"]
    out["series_id"] = CHART_ID + "::" + out["logical_series"]
    out["label"] = out["sector"]
    out["market"] = "USD/CLP"
    out["dimension_1"] = out["sector"]
    out["dimension_2"] = out["apertura"]
    out["frequency"] = "MONTHLY"
    out["unit"] = MM_USD
    out["status_code"] = "BDE_HTML"
    return out[cols].sort_values(["apertura", "date", "sector"]).reset_index(drop=True)


def available_openings(df: pd.DataFrame) -> list[str]:
    if df.empty or "apertura" not in df.columns:
        return APERTURA_ORDER
    existing = set(df["apertura"].dropna().astype(str))
    ordered = [x for x in APERTURA_ORDER if x in existing]
    return ordered or APERTURA_ORDER


def available_months(df: pd.DataFrame, apertura: str | None = None) -> list[pd.Timestamp]:
    if df.empty or "date" not in df.columns:
        return []
    out = df.copy()
    if apertura and "apertura" in out.columns:
        out = out[out["apertura"].eq(apertura)]
    return sorted(pd.to_datetime(out["date"]).dropna().unique())


def default_compare_months(df: pd.DataFrame, apertura: str | None = None) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    months = available_months(df, apertura)
    if len(months) >= 2:
        return pd.Timestamp(months[-2]), pd.Timestamp(months[-1])
    if len(months) == 1:
        return pd.Timestamp(months[0]), pd.Timestamp(months[0])
    return None, None


def build_comparison_dataframe(df: pd.DataFrame, base_month=None, compare_month=None, apertura: str = "Comprador") -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["sector", "value_base", "value_compare", "variation"])

    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])

    if apertura and "apertura" in out.columns:
        out = out[out["apertura"].eq(apertura)].copy()
    if out.empty:
        return pd.DataFrame(columns=["sector", "value_base", "value_compare", "variation"])

    default_base, default_compare = default_compare_months(out, apertura)
    base = pd.Timestamp(base_month) if base_month is not None else default_base
    comp = pd.Timestamp(compare_month) if compare_month is not None else default_compare
    if base is None or comp is None:
        return pd.DataFrame(columns=["sector", "value_base", "value_compare", "variation"])

    sector_col = "sector" if "sector" in out.columns else "dimension_1"
    base_df = out[out["date"].eq(base)].groupby(sector_col, as_index=False)["value"].sum().rename(columns={sector_col: "sector", "value": "value_base"})
    comp_df = out[out["date"].eq(comp)].groupby(sector_col, as_index=False)["value"].sum().rename(columns={sector_col: "sector", "value": "value_compare"})

    merged = pd.DataFrame({"sector": DETAIL_SECTOR_ORDER}).merge(base_df, on="sector", how="left").merge(comp_df, on="sector", how="left")
    merged[["value_base", "value_compare"]] = merged[["value_base", "value_compare"]].fillna(0)
    merged["variation"] = merged["value_compare"] - merged["value_base"]
    merged["base_month"] = base
    merged["compare_month"] = comp
    merged["base_month_label"] = month_label(base)
    merged["compare_month_label"] = month_label(comp)
    merged["apertura"] = apertura
    return merged


def _figure_common(fig: go.Figure, title: str, total_var: float, base_lbl: str, comp_lbl: str, apertura: str) -> go.Figure:
    fig = base_layout(fig, title, yaxis_title="Millones de USD")
    fig.update_layout(
        showlegend=False,
        height=520,
        margin={"l": 78, "r": 110, "t": 135, "b": 185},
    )

    # Baja la fuente para que no tape el eje / etiquetas.
    for ann in fig.layout.annotations:
        if isinstance(getattr(ann, "text", None), str) and "Fuente: Banco Central de Chile" in ann.text:
            ann.y = -0.48

    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=0.72,
        y=0.98,
        text=f"{apertura} | {base_lbl} vs {comp_lbl}<br>Variación total: <b>{total_var:,.0f}</b> MM USD",
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


def build_figure_sector(df: pd.DataFrame, base_month=None, compare_month=None, apertura: str = "Comprador") -> go.Figure:
    comp_df = build_comparison_dataframe(df, base_month, compare_month, apertura)
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
    fig.update_layout(bargap=0.32)
    fig = _figure_common(
        fig,
        "BANCOS. VARIACIÓN POR SECTOR",
        comp_df["variation"].sum(),
        comp_df["base_month_label"].iloc[0],
        comp_df["compare_month_label"].iloc[0],
        apertura,
    )
    # En este gráfico el eje X ya contiene los sectores; no necesita título "Fecha".
    fig.update_xaxes(title_text="", tickangle=-90)
    fig.update_yaxes(title_text="Millones de USD")
    return fig


def build_figure_ranking(df: pd.DataFrame, base_month=None, compare_month=None, apertura: str = "Comprador") -> go.Figure:
    comp_df = build_comparison_dataframe(df, base_month, compare_month, apertura)
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
        "BANCOS. RANKING DE CONTRIBUCIÓN",
        comp_df["variation"].sum(),
        comp_df["base_month_label"].iloc[0],
        comp_df["compare_month_label"].iloc[0],
        apertura,
    )
    # Aquí el eje X sí es monto; el eje Y ya muestra los sectores.
    fig.update_xaxes(title_text="Variación en millones de USD", tickformat=",.0f", tickangle=0)
    fig.update_yaxes(title_text="", categoryorder="array", categoryarray=rank["sector"].tolist())
    return fig


def build_figure(df: pd.DataFrame):
    return build_figure_sector(df)
