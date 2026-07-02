from __future__ import annotations

import pandas as pd
from derivatives_src.charts.d02_fx_helpers import DER_BM_SPC_02, MM_USD, SECTOR_ORDER, _filter_dates, _base, sector_from_label, stacked_bar_line
from derivatives_src.io.bde_table import fetch_bde_table, normalize_text
from derivatives_src.io.bcch_api import BCCHClient
from derivatives_src.series_registry import SeriesRegistry

CHART_ID = "d02_fx_derivados_sector"
TITLE = "D02 - Montos transados en derivados USD/CLP por sector de contraparte"

EXCLUDE_NORMS = {"compras", "ventas", "netas", "neto", "sectores", "notas"}


def _is_sector_or_total(label: str) -> bool:
    norm = normalize_text(label)
    if norm in EXCLUDE_NORMS:
        return False
    if norm.startswith("monto transado total"):
        return True
    sector = sector_from_label(label)
    return sector in SECTOR_ORDER


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    # Fuente correcta para derivados USD/CLP por contraparte: DER_BM_SPC_02.
    raw = fetch_bde_table(DER_BM_SPC_02).long.copy()
    raw = _filter_dates(raw, start_date, end_date)
    raw = raw[raw["bde_series"].map(_is_sector_or_total)].copy()
    if raw.empty:
        return _base(pd.DataFrame(), CHART_ID, "sector")
    raw["sector"] = raw["bde_series"].map(sector_from_label)
    raw.loc[raw["bde_series_norm"].str.startswith("monto transado total", na=False), "sector"] = "Total"
    out = raw.groupby(["date", "sector"], as_index=False)["value"].sum()
    return _base(out, CHART_ID, "sector", "sector", "DER_BM_SPC_02")


def build_figure(df: pd.DataFrame):
    if df.empty:
        from derivatives_src.charts.siid_style import empty_siid_figure
        return empty_siid_figure("Sin datos de derivados por sector")
    return stacked_bar_line(df.rename(columns={"dimension_1": "sector"}), "sector", TITLE, preferred_order=SECTOR_ORDER, yaxis_title=MM_USD)
