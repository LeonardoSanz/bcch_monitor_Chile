from __future__ import annotations

import pandas as pd
from derivatives_src.charts.d02_fx_helpers import SPT_MEML_02, MM_USD, _filter_dates, _base, stacked_bar_line
from derivatives_src.io.bde_table import fetch_bde_table
from derivatives_src.io.bcch_api import BCCHClient
from derivatives_src.series_registry import SeriesRegistry

CHART_ID = "d02_fx_derivados_spot_total"
TITLE = "D02 - Montos transados totales USD/CLP en derivados y spot"


def build_dataframe(client: BCCHClient | None, registry: SeriesRegistry, start_date: str, end_date: str, demo: bool = False) -> pd.DataFrame:
    raw = fetch_bde_table(SPT_MEML_02).long.copy()
    raw = _filter_dates(raw, start_date, end_date)
    raw = raw[raw["bde_series_norm"].isin(["spot", "derivados"])].copy()
    if raw.empty:
        return _base(pd.DataFrame(), CHART_ID, "tipo")
    raw["tipo"] = raw["bde_series"].map(lambda x: "Spot" if str(x).strip().lower() == "spot" else "Derivados")
    out = raw.groupby(["date", "tipo"], as_index=False)["value"].sum()
    total = out.groupby("date", as_index=False)["value"].sum().assign(tipo="Total")
    out = pd.concat([out, total], ignore_index=True)
    return _base(out, CHART_ID, "tipo", "tipo", "SPT_MEML_02")


def build_figure(df: pd.DataFrame):
    if df.empty:
        from derivatives_src.charts.siid_style import empty_siid_figure
        return empty_siid_figure("Sin datos para derivados + spot")
    return stacked_bar_line(df.rename(columns={"dimension_1": "tipo"}), "tipo", TITLE, preferred_order=["Derivados", "Spot"], yaxis_title=MM_USD)
