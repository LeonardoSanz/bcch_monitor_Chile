from __future__ import annotations

import pandas as pd

from derivatives_src.charts.d05_ufclp_common import (
    INSTRUMENT_SWAP,
    add_common_columns,
    extract_ufclp_transados,
    build_transado_figure,
)
from derivatives_src.io.bcch_api import BCCHClient
from derivatives_src.series_registry import SeriesRegistry

CHART_ID = "d05_ufclp_swap_sector"
TITLE = "D05 - Swap UF/CLP por sector de contraparte"


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    df = extract_ufclp_transados(start_date, end_date)
    if df.empty:
        return add_common_columns(pd.DataFrame(), CHART_ID, "sector", "sector", "apertura")
    df = df[df["instrumento"].eq(INSTRUMENT_SWAP)].copy()
    return add_common_columns(df, CHART_ID, "sector", "sector", "apertura")


def build_figure(df: pd.DataFrame, apertura: str = "Total"):
    return build_transado_figure(df, INSTRUMENT_SWAP, apertura)
