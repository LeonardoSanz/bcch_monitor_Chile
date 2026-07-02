from __future__ import annotations

import pandas as pd

from derivatives_src.charts.d04_spc_nominal_common import (
    APERTURA_TOTAL,
    APERTURA_COMPRA,
    APERTURA_VENTA,
    APERTURA_NETO,
    APERTURA_ORDER,
    PLAZO_ORDER,
    UNIT_CLP,
    add_common_columns,
    extract_spc_nominal,
    stacked_bar_line,
)
from derivatives_src.io.bcch_api import BCCHClient
from derivatives_src.series_registry import SeriesRegistry

CHART_ID = "d04_spc_nominal_transado_plazo"
TITLE = "D04 - Montos transados SPC nominal por plazo contractual"


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    _, plazo_df, _ = extract_spc_nominal(start_date, end_date)
    if plazo_df.empty:
        return add_common_columns(pd.DataFrame(), CHART_ID, "plazo", "plazo", "apertura")

    raw = plazo_df.copy()
    raw = raw[raw["plazo"].isin(PLAZO_ORDER)].copy()
    out = raw.groupby(["date", "plazo", "apertura"], as_index=False)["value"].sum()
    return add_common_columns(out, CHART_ID, "plazo", "plazo", "apertura")


def available_aperturas(df: pd.DataFrame) -> list[str]:
    # Mostrar siempre las cuatro opciones esperadas por el monitor.
    # Si alguna no existe en la data, el gráfico quedará vacío para esa selección,
    # pero evitamos perder Compra/Venta por diferencias singular/plural en la BDE.
    return APERTURA_ORDER



def _filter_for_plot(df: pd.DataFrame, apertura: str = APERTURA_TOTAL) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if apertura:
        out = out[out["apertura"].eq(apertura)].copy()
    if out.empty:
        return out
    return out.groupby(["date", "plazo"], as_index=False)["value"].sum()


def build_figure(df: pd.DataFrame, apertura: str = APERTURA_TOTAL):
    plot = _filter_for_plot(df, apertura)
    title = f"BANCOS. MONTOS TRANSADOS EN DERIVADOS SPC-CLP POR PLAZO CONTRACTUAL. {apertura.upper()}"
    return stacked_bar_line(plot, "plazo", title, preferred_order=PLAZO_ORDER, yaxis_title=UNIT_CLP)
