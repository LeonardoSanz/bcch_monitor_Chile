from __future__ import annotations

import pandas as pd
from pandas.tseries.offsets import MonthBegin
from derivatives_src.charts.d02_fx_helpers import DER_BM_PPC_02, MM_USD, SECTOR_ORDER, _filter_dates, _base, sector_from_label, monthly_diff, bar_variation_line
from derivatives_src.io.bde_table import fetch_bde_table, normalize_text
from derivatives_src.io.bcch_api import BCCHClient
from derivatives_src.series_registry import SeriesRegistry

CHART_ID = "d02_fx_usdclp_variacion_vigentes_contraparte"
TITLE = "D02 - Variación de montos vigentes en derivados USD/CLP por sector de contraparte"

EXCLUDE_NORMS = {"monto vigente comprador", "monto vigente vendedor", "monto vigente neto", "sectores", "notas"}


def _is_sector_row(label: str) -> bool:
    norm = normalize_text(label)
    if norm in EXCLUDE_NORMS:
        return False
    if norm.startswith("monto vigente total"):
        return True
    sector = sector_from_label(label)
    return sector in SECTOR_ORDER


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    # Para calcular la variación mensual correctamente, necesitamos incluir un mes
    # previo al inicio del rango visible. Si se filtra antes de hacer diff(), se pierde
    # el primer mes (ej. junio-2024 debería compararse contra mayo-2024).
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    calc_start = start - MonthBegin(1)

    raw = fetch_bde_table(DER_BM_PPC_02).long.copy()
    raw = raw[(raw["date"] >= calc_start) & (raw["date"] <= end)].copy()
    raw = raw[raw["bde_series"].map(_is_sector_row)].copy()
    if raw.empty:
        return _base(pd.DataFrame(), CHART_ID, "sector")

    raw["sector"] = raw["bde_series"].map(sector_from_label)
    raw.loc[raw["bde_series_norm"].str.startswith("monto vigente total", na=False), "sector"] = "Var. total"

    out = raw.groupby(["date", "sector"], as_index=False)["value"].sum()
    out = monthly_diff(out, ["sector"])
    out = out[(out["date"] >= start) & (out["date"] <= end)].copy()
    return _base(out, CHART_ID, "sector", "sector", "DER_BM_PPC_02")


def build_figure(df: pd.DataFrame):
    if df.empty:
        from derivatives_src.charts.siid_style import empty_siid_figure
        return empty_siid_figure("Sin datos para variación de vigentes")
    preferred = [x for x in SECTOR_ORDER if x != "Interbancario"]
    return bar_variation_line(df.rename(columns={"dimension_1": "sector"}), "sector", TITLE, preferred_order=preferred, yaxis_title=MM_USD)
