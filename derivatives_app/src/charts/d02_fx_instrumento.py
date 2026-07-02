from __future__ import annotations

import pandas as pd
from src.charts.d02_fx_helpers import DER_BM_TRA_INST_02, MM_USD, INSTRUMENT_ORDER, _filter_dates, _base, normalize_instrument, stacked_bar_line
from src.io.bde_table import fetch_bde_table
from src.io.bcch_api import BCCHClient
from src.series_registry import SeriesRegistry

CHART_ID = "d02_fx_usdclp_transado_instrumento"
TITLE = "D02 - Montos transados totales en derivados USD/CLP por tipo de instrumento"


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    raw = fetch_bde_table(DER_BM_TRA_INST_02).long.copy()
    raw = _filter_dates(raw, start_date, end_date)
    raw["instrumento"] = raw["bde_series"].map(normalize_instrument)
    raw = raw[raw["instrumento"].isin(["Total", *INSTRUMENT_ORDER])].copy()
    if raw.empty:
        return _base(pd.DataFrame(), CHART_ID, "instrumento")
    out = raw.groupby(["date", "instrumento"], as_index=False)["value"].sum()
    return _base(out, CHART_ID, "instrumento", "instrumento", "DER_BM_TRA_INST_02")


def build_figure(df: pd.DataFrame):
    if df.empty:
        from src.charts.siid_style import empty_siid_figure
        return empty_siid_figure("Sin datos por instrumento")
    return stacked_bar_line(df.rename(columns={"dimension_1": "instrumento"}), "instrumento", TITLE, preferred_order=INSTRUMENT_ORDER, yaxis_title=MM_USD)
