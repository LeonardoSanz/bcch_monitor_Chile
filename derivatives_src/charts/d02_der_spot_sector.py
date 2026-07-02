from __future__ import annotations

import pandas as pd
from derivatives_src.charts.d02_fx_helpers import SPT_MEML_02, MM_USD, SECTOR_ORDER, _filter_dates, _base, sector_from_label, stacked_bar_line
from derivatives_src.io.bde_table import fetch_bde_table
from derivatives_src.io.bcch_api import BCCHClient
from derivatives_src.series_registry import SeriesRegistry

CHART_ID = "d02_fx_derivados_spot_sector"
TITLE = "D02 - Montos transados USD/CLP en derivados más spot por sector de contraparte"


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    raw = fetch_bde_table(SPT_MEML_02).long.copy()
    raw = _filter_dates(raw, start_date, end_date)
    raw = raw[raw["bde_series_norm"].str.startswith("monto transado total", na=False)].copy()
    raw = raw[~raw["bde_series_norm"].str.contains("total usd clp|total me clp", na=False)].copy()
    if raw.empty:
        return _base(pd.DataFrame(), CHART_ID, "sector")
    raw["sector"] = raw["bde_series"].map(sector_from_label)
    out = raw.groupby(["date", "sector"], as_index=False)["value"].sum()
    total = out.groupby("date", as_index=False)["value"].sum().assign(sector="Total")
    out = pd.concat([out, total], ignore_index=True)
    return _base(out, CHART_ID, "sector", "sector", "SPT_MEML_02")


def build_figure(df: pd.DataFrame):
    if df.empty:
        from derivatives_src.charts.siid_style import empty_siid_figure
        return empty_siid_figure("Sin datos por sector")
    return stacked_bar_line(df.rename(columns={"dimension_1": "sector"}), "sector", TITLE, preferred_order=SECTOR_ORDER, yaxis_title=MM_USD)
