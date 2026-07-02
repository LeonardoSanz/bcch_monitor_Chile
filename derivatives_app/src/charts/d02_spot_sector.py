from __future__ import annotations

import pandas as pd
from src.charts.d02_fx_helpers import (
    SPT_USDCLP_S02,
    MM_USD,
    SECTOR_ORDER,
    _filter_dates,
    _base,
    sector_from_label,
    sector_from_parent,
    stacked_bar_line,
)
from src.io.bde_table import fetch_bde_table, normalize_text
from src.io.bcch_api import BCCHClient
from src.series_registry import SeriesRegistry

CHART_ID = "d02_spot_sector_total"
TITLE = "D02 - Montos transados totales spot USD/CLP por sector de contraparte"

# Categorías que sí se grafican: partición sin duplicación.
# "Residentes no bancos" se excluye porque es agregado padre de los sectores de detalle.
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

PLOT_SECTORS = set(SPOT_SECTOR_ORDER)
KEEP_SECTORS = {"Total", *PLOT_SECTORS}
EXCLUDE_SERIES = {"compras", "ventas", "neto", "sectores", "notas"}


def _candidate_sector(row: pd.Series) -> str:
    """Identifica sector usando la fila y, si es necesario, el parent BDE."""
    series = row.get("bde_series", "")
    parent = row.get("bde_parent", "")

    sector = sector_from_label(series)
    if sector not in KEEP_SECTORS and sector != "Residentes no bancos":
        sector = sector_from_parent(parent)
    return sector


def _is_candidate(row: pd.Series) -> bool:
    norm = normalize_text(row.get("bde_series", ""))
    if norm in EXCLUDE_SERIES:
        return False
    sector = _candidate_sector(row)
    return sector in KEEP_SECTORS or sector == "Residentes no bancos"


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    raw = fetch_bde_table(SPT_USDCLP_S02).long.copy()
    raw = _filter_dates(raw, start_date, end_date)

    if raw.empty:
        return _base(pd.DataFrame(), CHART_ID, "sector")

    raw = raw[raw.apply(_is_candidate, axis=1)].copy()
    if raw.empty:
        return _base(pd.DataFrame(), CHART_ID, "sector")

    raw["sector"] = raw.apply(_candidate_sector, axis=1)

    # Punto clave:
    # - Total oficial se mantiene solo para control/exportación.
    # - Residentes no bancos se excluye porque duplicaría a:
    #   Fondos de Pensiones + Sector Real + Seguros + Corredores + AGF + Otros.
    raw = raw[raw["sector"].isin(KEEP_SECTORS)].copy()

    out = raw.groupby(["date", "sector"], as_index=False)["value"].sum()
    return _base(out, CHART_ID, "sector", "sector", "SPT_USDCLP_S02")


def build_figure(df: pd.DataFrame):
    if df.empty:
        from src.charts.siid_style import empty_siid_figure
        return empty_siid_figure("Sin datos spot por sector")

    # Como ya excluimos el agregado "Residentes no bancos", la suma de barras
    # debe calzar con el total oficial. Para que visualmente quede pegado al stack,
    # la línea se calcula desde las categorías visibles no duplicadas.
    return stacked_bar_line(
        df.rename(columns={"dimension_1": "sector"}),
        "sector",
        TITLE,
        preferred_order=SPOT_SECTOR_ORDER,
        yaxis_title=MM_USD,
        use_existing_total=False,
    )
