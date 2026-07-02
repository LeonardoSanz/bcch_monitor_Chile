from __future__ import annotations

import pandas as pd

from derivatives_src.charts.d05_ufclp_common import add_common_columns, extract_ufclp_forward_prices, build_forward_price_figure
from derivatives_src.io.bcch_api import BCCHClient
from derivatives_src.series_registry import SeriesRegistry

CHART_ID = "d05_ufclp_forward_prices"
TITLE = "D05 - Precios forward UF/CLP"


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    df = extract_ufclp_forward_prices(start_date, end_date)
    if df.empty:
        return add_common_columns(pd.DataFrame(), CHART_ID, "metric", "metric")
    return add_common_columns(df, CHART_ID, "metric", "metric")


def build_figure(df: pd.DataFrame):
    return build_forward_price_figure(df)
