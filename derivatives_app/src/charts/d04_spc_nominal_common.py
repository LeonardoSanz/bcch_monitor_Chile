from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.charts._common import base_layout, empty_figure
from src.charts.d01_waterfall_variacion import month_label
from src.charts.siid_style import CMF_DARK, CMF_PALETTE, CMF_MUTED
from src.io.bde_table import fetch_bde_table, normalize_text, clean_label, parse_bde_period, parse_bde_number

DER_IR_SPC_07 = "https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_DERYSPOT/MN_DERYSPOT/DER_IR_SPC_07/638013466190000243"
DER_POS_MVCP_01 = "https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_DERYSPOT/MN_DERYSPOT/DER_POS_MVCP_01/638013462283630132"
UNIT_CLP = "Miles de millones de CLP"

APERTURA_TOTAL = "Total"
APERTURA_COMPRA = "Compra tasa variable"
APERTURA_VENTA = "Venta tasa variable"
APERTURA_NETO = "Neto"

APERTURA_ORDER = [APERTURA_TOTAL, APERTURA_COMPRA, APERTURA_VENTA, APERTURA_NETO]

PLAZO_BUCKET_ORDER = ["Hasta 2 años", "Mayor de 2 años"]
PLAZO_FILTER_ORDER = ["Todas", *PLAZO_BUCKET_ORDER]
PLAZO_ORDER = ["3 meses", "6 meses", "9 meses", "12 meses", "18 meses", "2 años", "5 años", "10 años y más"]

# Para el gráfico por sector usamos una partición no duplicada del total.
# En el cuadro BDE, para cada plazo aparece:
#   Interbancario
#   Compras tasa variable
#   Ventas tasa variable
#   Neto
# La suma Total = Interbancario + Compras + Ventas.
SECTOR_ORDER = ["No residentes", "Interbancario", "Residentes no bancos"]
SECTOR_FALLBACK_MAP = {
    "interbancario": "Interbancario",
    "compra tasa variable": "No residentes",
    "compras tasa variable": "No residentes",
    "venta tasa variable": "Residentes no bancos",
    "ventas tasa variable": "Residentes no bancos",
    "neto": "Neto",
}


def _period_columns(wide: pd.DataFrame) -> list[str]:
    return [c for c in wide.columns if pd.notna(parse_bde_period(c))]


def _is_plazo(label: object) -> bool:
    return normalize_plazo(label) in PLAZO_ORDER


def normalize_plazo(label: object) -> str:
    norm = normalize_text(label)
    if norm == "3 meses":
        return "3 meses"
    if norm == "6 meses":
        return "6 meses"
    if norm == "9 meses":
        return "9 meses"
    if norm in {"12 meses", "1 ano", "1 año"}:
        return "12 meses"
    if norm == "18 meses":
        return "18 meses"
    if norm in {"2 anos", "2 años"}:
        return "2 años"
    if norm in {"5 anos", "5 años"}:
        return "5 años"
    if "10" in norm and ("mas" in norm or "anos" in norm or "años" in norm):
        return "10 años y más"
    return clean_label(label)


def normalize_bucket(label: object) -> str | None:
    norm = normalize_text(label)
    if "hasta 2" in norm:
        return "Hasta 2 años"
    if "mayor de 2" in norm or "mayor a 2" in norm:
        return "Mayor de 2 años"
    return None


def normalize_apertura(label: object) -> str | None:
    norm = normalize_text(label)
    if norm == "interbancario":
        return "Interbancario"
    if norm in {"compra tasa variable", "compras tasa variable"}:
        return APERTURA_COMPRA
    if norm in {"venta tasa variable", "ventas tasa variable"}:
        return APERTURA_VENTA
    if norm == "neto":
        return APERTURA_NETO
    if norm.startswith("monto transado total") or norm.startswith("monto vigente total"):
        return APERTURA_TOTAL
    return None


def _iter_values(row: pd.Series, period_cols: list[str], start: pd.Timestamp, end: pd.Timestamp):
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
        yield dt, value


def extract_spc_nominal_from_url(source_url: str, start_date: str, end_date: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Extrae tres bases desde una tabla SPC nominal BDE.

    Devuelve:
    - sector_df: detalle por plazo agregado y fila BDE (Interbancario/Compra/Venta/Neto)
    - plazo_df: detalle por plazo contractual y apertura
    - total_df: total mensual oficial de la tabla
    """
    table = fetch_bde_table(source_url)
    wide = table.wide.copy()
    period_cols = _period_columns(wide)
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)

    sector_records: list[dict] = []
    plazo_records: list[dict] = []
    total_records: list[dict] = []

    mode = "bucket"
    current_bucket: str | None = None
    current_plazo: str | None = None

    for _, row in wide.iterrows():
        raw_label = row.get("bde_series_raw", row.get("bde_series", ""))
        label = clean_label(raw_label)
        norm = normalize_text(label)

        if norm == "plazos":
            mode = "plazo"
            current_bucket = None
            current_plazo = None
            continue
        if norm == "notas":
            break

        if norm.startswith("monto transado total"):
            for dt, value in _iter_values(row, period_cols, start, end):
                total_records.append({"date": dt, "value": value, "apertura": APERTURA_TOTAL})
            continue

        bucket = normalize_bucket(label)
        if bucket is not None and mode == "bucket":
            current_bucket = bucket
            current_plazo = None
            # Fila agregada por bucket, útil si después se quiere revisar.
            for dt, value in _iter_values(row, period_cols, start, end):
                sector_records.append({
                    "date": dt,
                    "plazo_bucket": bucket,
                    "raw_item": bucket,
                    "apertura": APERTURA_TOTAL,
                    "value": value,
                })
            continue

        plazo = normalize_plazo(label)
        if plazo in PLAZO_ORDER and mode == "plazo":
            current_plazo = plazo
            current_bucket = None
            for dt, value in _iter_values(row, period_cols, start, end):
                plazo_records.append({
                    "date": dt,
                    "plazo": plazo,
                    "apertura": APERTURA_TOTAL,
                    "raw_item": plazo,
                    "value": value,
                })
            continue

        apertura = normalize_apertura(label)
        if apertura is None:
            continue

        if mode == "bucket" and current_bucket in PLAZO_BUCKET_ORDER:
            for dt, value in _iter_values(row, period_cols, start, end):
                sector_records.append({
                    "date": dt,
                    "plazo_bucket": current_bucket,
                    "raw_item": label,
                    "apertura": apertura,
                    "value": value,
                })

        if mode == "plazo" and current_plazo in PLAZO_ORDER:
            for dt, value in _iter_values(row, period_cols, start, end):
                plazo_records.append({
                    "date": dt,
                    "plazo": current_plazo,
                    "apertura": apertura,
                    "raw_item": label,
                    "value": value,
                })

    sector_df = pd.DataFrame(sector_records, columns=["date", "plazo_bucket", "raw_item", "apertura", "value"])
    plazo_df = pd.DataFrame(plazo_records, columns=["date", "plazo", "apertura", "raw_item", "value"])
    total_df = pd.DataFrame(total_records, columns=["date", "value", "apertura"])
    return sector_df, plazo_df, total_df



def extract_spc_nominal(start_date: str, end_date: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Compatibilidad: montos transados SPC nominal."""
    return extract_spc_nominal_from_url(DER_IR_SPC_07, start_date, end_date)


def extract_spc_nominal_vigentes(start_date: str, end_date: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Montos vigentes SPC nominal."""
    return extract_spc_nominal_from_url(DER_POS_MVCP_01, start_date, end_date)

def add_common_columns(df: pd.DataFrame, chart_id: str, label_col: str, dim1_col: str, dim2_col: str = "") -> pd.DataFrame:
    cols = [
        "date", "value", "chart_id", "logical_series", "series_id", "label", "market",
        "dimension_1", "dimension_2", "frequency", "unit", "status_code"
    ]
    if df.empty:
        return pd.DataFrame(columns=cols)
    out = df.copy()
    out["chart_id"] = chart_id
    out["logical_series"] = out[label_col].astype(str)
    out["series_id"] = chart_id + "::" + out[label_col].astype(str)
    out["label"] = out[label_col].astype(str)
    out["market"] = "SPC nominal"
    out["dimension_1"] = out[dim1_col].astype(str)
    out["dimension_2"] = out[dim2_col].astype(str) if dim2_col and dim2_col in out.columns else ""
    out["frequency"] = "MONTHLY"
    out["unit"] = UNIT_CLP
    out["status_code"] = "DER_IR_SPC_07"
    keep_extra = [c for c in ["apertura", "plazo", "plazo_bucket", "sector", "raw_item"] if c in out.columns]
    return out[cols + keep_extra].sort_values(["date", "dimension_1", "dimension_2"]).reset_index(drop=True)


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


def _ordered_categories(values: list[str], preferred: list[str]) -> list[str]:
    seen = list(dict.fromkeys(values))
    ordered = [x for x in preferred if x in seen]
    ordered.extend([x for x in seen if x not in ordered and x != "Total"])
    return ordered


def stacked_bar_line(
    df: pd.DataFrame,
    category_col: str,
    title: str,
    preferred_order: list[str],
    yaxis_title: str = UNIT_CLP,
    total_label: str = "Total",
    height: int = 520,
    barmode: str = "stack",
) -> go.Figure:
    if df.empty:
        return empty_figure("Sin datos para graficar")
    value_df = df[df[category_col].ne(total_label)].copy()
    total_df = value_df.groupby("date", as_index=False)["value"].sum()

    fig = go.Figure()
    cats = _ordered_categories(value_df[category_col].dropna().astype(str).tolist(), preferred_order)
    for i, cat in enumerate(cats):
        tmp = value_df[value_df[category_col].eq(cat)]
        fig.add_trace(go.Bar(
            x=tmp["date"],
            y=tmp["value"],
            name=cat,
            marker_color=CMF_PALETTE[i % len(CMF_PALETTE)],
        ))
    fig.add_trace(go.Scatter(
        x=total_df["date"],
        y=total_df["value"],
        mode="lines",
        name=total_label,
        line=dict(color=CMF_DARK, width=2.5),
    ))
    fig.update_layout(barmode=barmode, height=height)
    fig = base_layout(fig, title, yaxis_title=yaxis_title)
    fig.update_layout(margin={"l": 78, "r": 120, "t": 34, "b": 185})
    return fig


def variation_bar(df: pd.DataFrame, x_col: str, title: str, preferred_order: list[str]) -> go.Figure:
    if df.empty:
        return empty_figure("Faltan datos para calcular variación")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df[x_col],
        y=df["variation"],
        marker_color=[CMF_PALETTE[1] if v >= 0 else CMF_PALETTE[5] for v in df["variation"]],
        text=df["variation"].map(lambda x: f"{x:,.0f}"),
        textposition="outside",
        customdata=df[["value_base", "value_compare", "base_month_label", "compare_month_label"]],
        hovertemplate=(
            "%{x}<br>"
            "Base %{customdata[2]}: %{customdata[0]:,.0f}<br>"
            "Comparación %{customdata[3]}: %{customdata[1]:,.0f}<br>"
            "Variación: %{y:,.0f}<extra></extra>"
        ),
    ))
    fig.add_hline(y=0, line_width=1, line_color=CMF_DARK)
    fig = base_layout(fig, title, yaxis_title=UNIT_CLP)
    fig.update_layout(showlegend=False, height=520, bargap=0.32, margin={"l": 78, "r": 120, "t": 34, "b": 185})
    fig.update_xaxes(title_text="", tickangle=-90, categoryorder="array", categoryarray=preferred_order)
    return fig


def variation_ranking(df: pd.DataFrame, y_col: str, title: str) -> go.Figure:
    if df.empty:
        return empty_figure("Faltan datos para ranking")
    rank = df.copy().sort_values("variation", ascending=True)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=rank[y_col],
        x=rank["variation"],
        orientation="h",
        marker_color=[CMF_PALETTE[1] if v >= 0 else CMF_PALETTE[5] for v in rank["variation"]],
        text=rank["variation"].map(lambda x: f"{x:,.0f}"),
        textposition="outside",
        customdata=rank[["value_base", "value_compare", "base_month_label", "compare_month_label"]],
        hovertemplate=(
            "%{y}<br>"
            "Base %{customdata[2]}: %{customdata[0]:,.0f}<br>"
            "Comparación %{customdata[3]}: %{customdata[1]:,.0f}<br>"
            "Variación: %{x:,.0f}<extra></extra>"
        ),
    ))
    fig.add_vline(x=0, line_width=1, line_color=CMF_DARK)
    fig = base_layout(fig, title, yaxis_title=UNIT_CLP)
    fig.update_layout(showlegend=False, height=520, margin={"l": 90, "r": 120, "t": 34, "b": 185})
    fig.update_xaxes(title_text=f"Variación en {UNIT_CLP.lower()}", tickformat=",.0f", tickangle=0)
    fig.update_yaxes(title_text="", categoryorder="array", categoryarray=rank[y_col].tolist())
    return fig
