from __future__ import annotations

import pandas as pd
from src.charts.d02_fx_helpers import SPT_USDCLP_S02, MM_USD, SECTOR_ORDER, _filter_dates, _base, sector_from_parent, stacked_bar_line
from src.io.bde_table import fetch_bde_table
from src.io.bcch_api import BCCHClient
from src.series_registry import SeriesRegistry

CHART_ID = "d02_spot_compra_usd_sector"
SPOT_SECTOR_ORDER = [
    "No Residentes",
    "Interbancario",
    "Fondos de Pensiones",
    "Sector Real",
    "Cías. de Seguros",
    "Corredores de Bolsa",
    "AGF",
    "Otros Sectores",
]

TITLE = "D02 - Montos transados spot USD/CLP por sector de contraparte, monto compra USD"


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    raw = fetch_bde_table(SPT_USDCLP_S02).long.copy()
    raw = _filter_dates(raw, start_date, end_date)
    raw = raw[raw["bde_series_norm"].eq("compras")].copy()
    if raw.empty:
        return _base(pd.DataFrame(), CHART_ID, "sector")
    raw["sector"] = raw["bde_parent"].map(sector_from_parent)
    # Excluye el agregado "Residentes no bancos" y mantiene solo sectores no duplicados.
    raw = raw[raw["sector"].isin(["Total", *SPOT_SECTOR_ORDER])].copy()
    out = raw.groupby(["date", "sector"], as_index=False)["value"].sum()
    return _base(out, CHART_ID, "sector", "sector", "SPT_USDCLP_S02")


def build_figure(df: pd.DataFrame):
    if df.empty:
        from src.charts.siid_style import empty_siid_figure
        return empty_siid_figure("Sin datos compras USD spot")
    # La línea usa las Compras oficiales bajo "Monto transado total, total, USD-CLP".
    return stacked_bar_line(
        df.rename(columns={"dimension_1": "sector"}),
        "sector",
        TITLE,
        preferred_order=SPOT_SECTOR_ORDER,
        yaxis_title=MM_USD,
        use_existing_total=False,
    )
