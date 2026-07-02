from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd
import plotly.graph_objects as go

from src.charts.siid_style import apply_siid_layout, empty_siid_figure, CMF_DARK, CMF_PALETTE
from src.io.bde_table import fetch_bde_table, normalize_text

MM_USD = "Millones de USD"

SPT_MEML_02 = "https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_DERYSPOT/MN_DERYSPOT/SPT_MEML_02/638042099185536021"
DER_BM_SPC_02 = "https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_DERYSPOT/MN_DERYSPOT/DER_BM_SPC_02/637933232741863236"
DER_BM_TRA_INST_02 = "https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_DERYSPOT/MN_DERYSPOT/DER_BM_TRA_INST_02/638276104180881091"
DER_BM_PPC_02 = "https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_DERYSPOT/MN_DERYSPOT/DER_BM_PPC_02/637933230812956640"
DER_BM_VIG_INST_02 = "https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_DERYSPOT/MN_DERYSPOT/DER_BM_VIG_INST_02/638276103327126037"
SPT_USDCLP_S02 = "https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_DERYSPOT/MN_DERYSPOT/SPT_USDCLP_S02/638043023447783403"
NDF_VIG_DAILY = "https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_DERYSPOT/MN_DERYSPOT/DER_BD_PPC_03/638628555628490922"
NDF_TRA_MONTHLY = "https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_DERYSPOT/MN_DERYSPOT/DER_BD_SPC_04/638628569922717983"
DER_BD_PPC_04 = "https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_DERYSPOT/MN_DERYSPOT/DER_BD_PPC_04/638628569273512705"
DER_BD_SPC_04 = "https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_DERYSPOT/MN_DERYSPOT/DER_BD_SPC_04/638628569922717983"

SECTOR_LABELS = {
    "interbancario": "Interbancario",
    "residentes no bancos": "Residentes no bancos",
    "fondos de pensiones": "Fondos de Pensiones",
    "empresas sector real": "Sector Real",
    "sector real": "Sector Real",
    "companias de seguro": "Cías. de Seguros",
    "companias de seguros": "Cías. de Seguros",
    "cias de seguros": "Cías. de Seguros",
    "corredores de bolsa": "Corredores de Bolsa",
    "corredoras de bolsa": "Corredores de Bolsa",
    "corredoras de bolsa y agencias de valores": "Corredores de Bolsa",
    "corredores de bolsa y agencias de valores": "Corredores de Bolsa",
    "agf": "AGF",
    "administradoras generales de fondos": "AGF",
    "no residentes": "No Residentes",
    "otros sectores": "Otros Sectores",
}

SECTOR_ORDER = [
    "No Residentes",
    "Interbancario",
    "Fondos de Pensiones",
    "Sector Real",
    "Otros Sectores",
    "Corredores de Bolsa",
    "AGF",
    "Cías. de Seguros",
]

INSTRUMENT_ORDER = ["Forward y FX Swap", "Cross Currency Swap", "Opciones y otros"]
PLAZO_ORDER = ["Hasta 7 días", "8 a 35 días", "36 a 95 días", "96 a 185 días", "186 a 370 días", "Mayor a 370 días"]


def _filter_dates(df: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
    if df.empty:
        return df
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    return df[(df["date"] >= start) & (df["date"] <= end)].copy()


def _base(df: pd.DataFrame, chart_id: str, label_col: str, dim1_col: str = "", dim2: str = "") -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["date", "value", "chart_id", "logical_series", "series_id", "label", "market", "dimension_1", "dimension_2", "frequency", "unit", "status_code"])
    out = df.copy()
    out["chart_id"] = chart_id
    out["logical_series"] = out[label_col].astype(str)
    out["series_id"] = chart_id + "::" + out[label_col].astype(str)
    out["label"] = out[label_col].astype(str)
    out["market"] = out[label_col].astype(str)
    out["dimension_1"] = out[dim1_col].astype(str) if dim1_col else out[label_col].astype(str)
    out["dimension_2"] = dim2
    out["frequency"] = "MONTHLY"
    out["unit"] = MM_USD
    out["status_code"] = "BDE_HTML"
    cols = ["date", "value", "chart_id", "logical_series", "series_id", "label", "market", "dimension_1", "dimension_2", "frequency", "unit", "status_code"]
    return out[cols].sort_values(["date", "dimension_1"]).reset_index(drop=True)


def sector_from_parent(parent: str) -> str:
    norm = normalize_text(parent)
    if norm.startswith("monto transado total") or norm.startswith("monto vigente total"):
        # Usualmente viene: Monto transado total, interbancario
        parts = [p.strip() for p in parent.split(",")]
        if len(parts) >= 2:
            candidate = normalize_text(parts[1])
        else:
            candidate = norm
    else:
        candidate = norm
    if candidate == "total":
        return "Total"
    if "corredoras de bolsa" in candidate or "corredores de bolsa" in candidate or "agencias de valores" in candidate:
        return "Corredores de Bolsa"
    return SECTOR_LABELS.get(candidate, parent if parent else "Sin clasificación")


def sector_from_label(label: str) -> str:
    norm = normalize_text(label)
    if norm.startswith("monto transado total") or norm.startswith("monto vigente total"):
        parts = [p.strip() for p in label.split(",")]
        if len(parts) >= 2:
            norm = normalize_text(parts[1])
    if norm == "total":
        return "Total"
    if "corredoras de bolsa" in norm or "corredores de bolsa" in norm or "agencias de valores" in norm:
        return "Corredores de Bolsa"
    return SECTOR_LABELS.get(norm, label)


def normalize_instrument(label: str) -> str:
    norm = normalize_text(label)
    if "forward" in norm and "fx" in norm:
        return "Forward y FX Swap"
    if "cross" in norm or "currency" in norm:
        return "Cross Currency Swap"
    if "opciones" in norm:
        return "Opciones y otros"
    if "monto transado total" in norm or "monto vigente total" in norm:
        return "Total"
    return label


def normalize_plazo(label: str) -> str:
    norm = normalize_text(label)
    if "hasta 7" in norm:
        return "Hasta 7 días"
    if "8 a 35" in norm:
        return "8 a 35 días"
    if "36 a 95" in norm:
        return "36 a 95 días"
    if "96 a 185" in norm:
        return "96 a 185 días"
    if "186 a 370" in norm:
        return "186 a 370 días"
    if "mayor a 370" in norm:
        return "Mayor a 370 días"
    if "total" in norm:
        return "Total"
    return label


def _ordered_categories(values: list[str], preferred: list[str]) -> list[str]:
    seen = list(dict.fromkeys(values))
    ordered = [x for x in preferred if x in seen]
    ordered.extend([x for x in seen if x not in ordered and x != "Total"])
    return ordered


def stacked_bar_line(
    df: pd.DataFrame,
    category_col: str,
    title: str,
    total_label: str = "Total",
    yaxis_title: str = MM_USD,
    height: int = 520,
    preferred_order: list[str] | None = None,
    barmode: str = "stack",
    use_existing_total: bool = False,
) -> go.Figure:
    if df.empty:
        return empty_siid_figure("Sin datos para graficar")
    value_df = df[df[category_col].ne(total_label)].copy()
    total_source = df[df[category_col].eq(total_label)].copy()
    if use_existing_total and not total_source.empty:
        total_df = total_source.groupby("date", as_index=False)["value"].sum()
    else:
        # Por defecto, se calcula desde las categorías visibles.
        # Para cuadros con total oficial explícito, usar use_existing_total=True.
        total_df = value_df.groupby("date", as_index=False)["value"].sum()
    fig = go.Figure()
    cats = _ordered_categories(value_df[category_col].dropna().astype(str).tolist(), preferred_order or [])
    for i, cat in enumerate(cats):
        tmp = value_df[value_df[category_col].eq(cat)]
        fig.add_trace(go.Bar(x=tmp["date"], y=tmp["value"], name=cat, marker_color=CMF_PALETTE[i % len(CMF_PALETTE)]))
    fig.add_trace(go.Scatter(x=total_df["date"], y=total_df["value"], mode="lines", name=total_label, line=dict(color=CMF_DARK, width=2.5)))
    fig.update_layout(barmode=barmode)
    return apply_siid_layout(fig, title=title, yaxis_title=yaxis_title, unit=yaxis_title, height=height)


def bar_variation_line(
    df: pd.DataFrame,
    category_col: str,
    title: str,
    total_label: str = "Var. total",
    yaxis_title: str = MM_USD,
    height: int = 520,
    preferred_order: list[str] | None = None,
    use_existing_total: bool = False,
) -> go.Figure:
    if df.empty:
        return empty_siid_figure("Sin datos para graficar")
    value_df = df[df[category_col].ne(total_label)].copy()
    total_source = df[df[category_col].eq(total_label)].copy()
    if use_existing_total and not total_source.empty:
        total_df = total_source.groupby("date", as_index=False)["value"].sum()
    else:
        # Por defecto, se calcula desde las categorías visibles.
        # Para cuadros con total oficial explícito, usar use_existing_total=True.
        total_df = value_df.groupby("date", as_index=False)["value"].sum()
    fig = go.Figure()
    cats = _ordered_categories(value_df[category_col].dropna().astype(str).tolist(), preferred_order or [])
    for i, cat in enumerate(cats):
        tmp = value_df[value_df[category_col].eq(cat)]
        fig.add_trace(go.Bar(x=tmp["date"], y=tmp["value"], name=cat, marker_color=CMF_PALETTE[i % len(CMF_PALETTE)]))
    fig.add_trace(go.Scatter(x=total_df["date"], y=total_df["value"], mode="lines", name=total_label, line=dict(color=CMF_DARK, width=2.5)))
    fig.update_layout(barmode="relative")
    return apply_siid_layout(fig, title=title, yaxis_title=yaxis_title, unit=yaxis_title, height=height)


def monthly_diff(df: pd.DataFrame, group_cols: list[str], value_col: str = "value") -> pd.DataFrame:
    if df.empty:
        return df
    out = df.groupby([*group_cols, "date"], as_index=False)[value_col].sum().sort_values([*group_cols, "date"])
    out["value"] = out.groupby(group_cols)[value_col].diff()
    return out.dropna(subset=["value"]).copy()


def monthly_last_from_daily(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    if df.empty:
        return df
    tmp = df.copy()
    tmp["month"] = tmp["date"].dt.to_period("M").dt.to_timestamp()
    tmp = tmp.sort_values([*group_cols, "date"])
    return tmp.groupby([*group_cols, "month"], as_index=False).tail(1).assign(date=lambda x: x["month"]).drop(columns=["month"])
