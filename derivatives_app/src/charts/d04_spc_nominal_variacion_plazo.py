from __future__ import annotations

import pandas as pd

from src.charts.d01_waterfall_variacion import month_label
from src.charts.d04_spc_nominal_common import (
    APERTURA_TOTAL,
    APERTURA_ORDER,
    PLAZO_ORDER,
    UNIT_CLP,
    add_common_columns,
    default_compare_months,
    extract_spc_nominal,
    variation_bar,
    variation_ranking,
)
from src.io.bcch_api import BCCHClient
from src.series_registry import SeriesRegistry

CHART_ID = "d04_spc_nominal_variacion_plazo"
TITLE = "D04 - Variación de montos transados SPC nominal por plazo contractual"


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    _, plazo_df, _ = extract_spc_nominal(start_date, end_date)
    if plazo_df.empty:
        return add_common_columns(pd.DataFrame(), CHART_ID, "plazo", "plazo", "apertura")

    raw = plazo_df.copy()
    raw = raw[raw["plazo"].isin(PLAZO_ORDER)].copy()
    out = raw.groupby(["date", "plazo", "apertura"], as_index=False)["value"].sum()
    return add_common_columns(out, CHART_ID, "plazo", "plazo", "apertura")


def available_aperturas(df: pd.DataFrame) -> list[str]:
    # Mostrar siempre las cuatro opciones esperadas por el monitor.
    # Si alguna no existe en la data, el gráfico quedará vacío para esa selección,
    # pero evitamos perder Compra/Venta por diferencias singular/plural en la BDE.
    return APERTURA_ORDER



def available_months(df: pd.DataFrame, apertura: str | None = None) -> list[pd.Timestamp]:
    if df.empty or "date" not in df.columns:
        return []
    out = df.copy()
    if apertura and "apertura" in out.columns:
        out = out[out["apertura"].eq(apertura)]
    return sorted(pd.to_datetime(out["date"]).dropna().unique())


def build_comparison_dataframe(df: pd.DataFrame, base_month=None, compare_month=None, apertura: str = APERTURA_TOTAL) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["plazo", "value_base", "value_compare", "variation"])

    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out = out[out["apertura"].eq(apertura)].copy()
    if out.empty:
        return pd.DataFrame(columns=["plazo", "value_base", "value_compare", "variation"])

    default_base, default_compare = default_compare_months(out, apertura)
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
    merged["apertura"] = apertura
    return merged


def build_figure_plazo(df: pd.DataFrame, base_month=None, compare_month=None, apertura: str = APERTURA_TOTAL):
    comp = build_comparison_dataframe(df, base_month, compare_month, apertura)
    return variation_bar(comp, "plazo", f"BANCOS. VARIACIÓN SPC-CLP POR PLAZO CONTRACTUAL. {apertura.upper()}", PLAZO_ORDER)


def build_figure_ranking(df: pd.DataFrame, base_month=None, compare_month=None, apertura: str = APERTURA_TOTAL):
    comp = build_comparison_dataframe(df, base_month, compare_month, apertura)
    return variation_ranking(comp, "plazo", f"BANCOS. RANKING DE CONTRIBUCIÓN SPC-CLP. {apertura.upper()}")


def build_figure(df: pd.DataFrame):
    return build_figure_plazo(df)
