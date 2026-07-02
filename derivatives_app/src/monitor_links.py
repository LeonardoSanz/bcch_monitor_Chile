from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LINKS_PATH = ROOT / "config" / "monitor_mensual_links.csv"


@dataclass(frozen=True)
class MonitorLink:
    source_group: str
    chart_module: str
    chart_id: str
    sheet: str
    excel_label: str
    bde_code: str
    bde_url: str
    reference_image: str
    usage_note: str


@lru_cache(maxsize=4)
def load_monitor_links(path: str | Path = DEFAULT_LINKS_PATH) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, dtype=str).fillna("")
    for col in ["source_group", "chart_module", "chart_id", "sheet", "excel_label", "bde_code", "bde_url", "reference_image", "usage_note"]:
        if col not in df.columns:
            df[col] = ""
    return df


def links_for_chart(chart_id: str | None = None, chart_module: str | None = None) -> pd.DataFrame:
    df = load_monitor_links()
    if df.empty:
        return df
    mask = pd.Series(True, index=df.index)
    if chart_id:
        mask &= df["chart_id"].eq(chart_id)
    if chart_module:
        mask &= df["chart_module"].eq(chart_module)
    return df.loc[mask].copy()


def source_text_for_chart(chart_id: str | None = None, chart_module: str | None = None) -> str:
    df = links_for_chart(chart_id=chart_id, chart_module=chart_module)
    if df.empty:
        return "Fuente: Banco Central de Chile, BDE/SIID público."
    codes = ", ".join(dict.fromkeys([x for x in df["bde_code"].astype(str) if x.strip()]))
    if codes:
        return f"Fuente: Banco Central de Chile, BDE/SIID público. Cuadro(s): {codes}."
    return "Fuente: Banco Central de Chile, BDE/SIID público."


def source_terms_for_chart(chart_id: str | None = None, chart_module: str | None = None) -> list[str]:
    df = links_for_chart(chart_id=chart_id, chart_module=chart_module)
    terms: list[str] = []
    if df.empty:
        return terms
    for _, row in df.iterrows():
        for col in ["excel_label", "bde_code", "usage_note", "source_group"]:
            value = str(row.get(col, "")).strip()
            if value and value not in terms:
                terms.append(value)
    return terms
