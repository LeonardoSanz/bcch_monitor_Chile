from __future__ import annotations

import pandas as pd

from derivatives_src.charts.d04_spc_nominal_common import (
    APERTURA_TOTAL,
    APERTURA_COMPRA,
    APERTURA_VENTA,
    APERTURA_NETO,
    APERTURA_ORDER,
    PLAZO_FILTER_ORDER,
    SECTOR_FALLBACK_MAP,
    SECTOR_ORDER,
    UNIT_CLP,
    add_common_columns,
    extract_spc_nominal_vigentes,
    stacked_bar_line,
)
from derivatives_src.io.bcch_api import BCCHClient
from derivatives_src.io.bde_table import normalize_text
from derivatives_src.series_registry import SeriesRegistry

CHART_ID = "d04_spc_nominal_vigente_sector"
TITLE = "D04 - Montos vigentes SPC nominal por sector de contraparte"


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    sector_df, _, _ = extract_spc_nominal_vigentes(start_date, end_date)
    if sector_df.empty:
        return add_common_columns(pd.DataFrame(), CHART_ID, "sector", "sector", "apertura")

    raw = sector_df.copy()
    raw = raw[raw["raw_item"].map(normalize_text).isin([
        "interbancario",
        "compra tasa variable", "compras tasa variable",
        "venta tasa variable", "ventas tasa variable",
        "neto",
    ])].copy()
    if raw.empty:
        return add_common_columns(pd.DataFrame(), CHART_ID, "sector", "sector", "apertura")

    raw["sector"] = raw["raw_item"].map(lambda x: SECTOR_FALLBACK_MAP.get(normalize_text(x), x))
    out = raw.groupby(["date", "plazo_bucket", "sector", "apertura"], as_index=False)["value"].sum()
    return add_common_columns(out, CHART_ID, "sector", "sector", "apertura")


def available_aperturas(df: pd.DataFrame) -> list[str]:
    # Mostrar siempre las cuatro opciones esperadas por el monitor.
    # Si alguna no existe en la data, el gráfico quedará vacío para esa selección,
    # pero evitamos perder Compra/Venta por diferencias singular/plural en la BDE.
    return APERTURA_ORDER



def available_plazos(df: pd.DataFrame) -> list[str]:
    if df.empty or "plazo_bucket" not in df.columns:
        return PLAZO_FILTER_ORDER
    existing = set(df["plazo_bucket"].dropna().astype(str))
    ordered = ["Todas"] + [x for x in PLAZO_FILTER_ORDER if x != "Todas" and x in existing]
    return ordered or PLAZO_FILTER_ORDER


def _filter_for_plot(df: pd.DataFrame, apertura: str = APERTURA_TOTAL, plazo_residual: str = "Todas") -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()

    if plazo_residual and plazo_residual != "Todas" and "plazo_bucket" in out.columns:
        out = out[out["plazo_bucket"].eq(plazo_residual)].copy()

    if apertura == APERTURA_TOTAL:
        # Total = Interbancario + Compra tasa variable + Venta tasa variable.
        # Neto no se suma porque es diferencia.
        out = out[out["apertura"].isin(["Interbancario", APERTURA_COMPRA, APERTURA_VENTA])].copy()
        out = out[out["sector"].isin(SECTOR_ORDER)].copy()
    elif apertura in {APERTURA_COMPRA, APERTURA_VENTA}:
        out = out[out["apertura"].eq(apertura)].copy()
        out = out[out["sector"].isin(SECTOR_ORDER)].copy()
    elif apertura == APERTURA_NETO:
        out = out[out["apertura"].eq(APERTURA_NETO)].copy()
        out["sector"] = APERTURA_NETO
    else:
        out = out[out["apertura"].eq(apertura)].copy()

    if out.empty:
        return out

    return out.groupby(["date", "sector"], as_index=False)["value"].sum()


def build_figure(df: pd.DataFrame, apertura: str = APERTURA_TOTAL, plazo_residual: str = "Todas"):
    plot = _filter_for_plot(df, apertura, plazo_residual)
    title = f"BANCOS. MONTOS VIGENTES EN DERIVADOS SPC-CLP POR SECTOR DE CONTRAPARTE. {apertura.upper()}"
    order = SECTOR_ORDER if apertura != APERTURA_NETO else [APERTURA_NETO]
    return stacked_bar_line(plot, "sector", title, preferred_order=order, yaxis_title=UNIT_CLP)
