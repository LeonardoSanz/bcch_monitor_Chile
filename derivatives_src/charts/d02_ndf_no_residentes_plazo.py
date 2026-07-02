from __future__ import annotations

import pandas as pd

from derivatives_src.charts.d02_fx_helpers import DER_BD_PPC_04, MM_USD, PLAZO_ORDER, _filter_dates, _base, normalize_plazo, stacked_bar_line
from derivatives_src.io.bde_table import fetch_bde_table
from derivatives_src.io.bcch_api import BCCHClient
from derivatives_src.series_registry import SeriesRegistry

CHART_ID = "d02_ndf_vigentes_netos_plazo"
TITLE = "D02 - Montos vigentes netos NDF USD/CLP con no residentes por plazo contractual"
SOURCE_TAG = "DER_BD_PPC_04"


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    raw = fetch_bde_table(DER_BD_PPC_04).long.copy()
    raw = _filter_dates(raw, start_date, end_date)
    raw["plazo"] = raw["bde_series"].map(normalize_plazo)
    raw = raw[raw["plazo"].isin(["Total", *PLAZO_ORDER])].copy()

    if raw.empty:
        return _base(pd.DataFrame(), CHART_ID, "plazo")

    out = raw.groupby(["date", "plazo"], as_index=False)["value"].sum()
    return _base(out, CHART_ID, "plazo", "plazo", SOURCE_TAG)


def build_figure(df: pd.DataFrame):
    if df.empty:
        from derivatives_src.charts.siid_style import empty_siid_figure
        return empty_siid_figure("Sin datos NDF por plazo")
    return stacked_bar_line(
        df.rename(columns={"dimension_1": "plazo"}),
        "plazo",
        TITLE,
        preferred_order=PLAZO_ORDER,
        yaxis_title=MM_USD,
    )
