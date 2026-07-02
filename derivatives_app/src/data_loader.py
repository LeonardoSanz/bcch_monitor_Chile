from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.demo_data import build_demo_series
from src.io.bcch_api import BCCHClient
from src.series_registry import SeriesRegistry
from src.monitor_links import links_for_chart
from src.io.bde_table import fetch_bde_table


BASE_COLUMNS = [
    "date",
    "value",
    "chart_id",
    "logical_series",
    "series_id",
    "label",
    "market",
    "dimension_1",
    "dimension_2",
    "frequency",
    "unit",
    "status_code",
]


def load_chart_data_from_bde_routes(chart_id: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fallback controlado: lee las rutas BDE oficiales del Excel/Monitor SIID.

    Se usa cuando no hay series_id validados. No usa SearchSeries ni auto-mapeo;
    simplemente parsea la tabla HTML BDE asociada al gráfico.
    """
    links = links_for_chart(chart_id=chart_id)
    if links.empty:
        return pd.DataFrame(columns=BASE_COLUMNS)

    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    frames: list[pd.DataFrame] = []

    for _, link in links.drop_duplicates(subset=["bde_url"]).iterrows():
        url = str(link.get("bde_url", "")).strip()
        code = str(link.get("bde_code", "")).strip()
        if not url:
            continue
        try:
            raw = fetch_bde_table(url).long.copy()
        except Exception:
            continue
        if raw.empty:
            continue
        raw = raw[(raw["date"] >= start) & (raw["date"] <= end)].copy()
        if raw.empty:
            continue
        raw["chart_id"] = chart_id
        raw["logical_series"] = raw["bde_series_norm"]
        raw["series_id"] = code + "::" + raw["bde_series"]
        raw["label"] = raw["bde_series"]
        raw["market"] = raw["bde_series"]
        raw["dimension_1"] = raw["bde_series"]
        raw["dimension_2"] = code
        raw["frequency"] = "MONTHLY"
        raw["unit"] = "MM USD"
        raw["status_code"] = "BDE_HTML"
        frames.append(raw[BASE_COLUMNS])

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=BASE_COLUMNS)


def load_chart_data(
    client: BCCHClient | None,
    registry: SeriesRegistry,
    chart_id: str,
    start_date: str,
    end_date: str,
    demo: bool = False,
) -> pd.DataFrame:
    """Carga y normaliza las series de un gráfico específico."""
    mapping = registry.for_chart(chart_id)
    if mapping.empty:
        return pd.DataFrame(columns=BASE_COLUMNS)

    configured = mapping[mapping["series_id"].astype(str).str.strip().ne("")].copy()
    frames: list[pd.DataFrame] = []

    if not configured.empty and client is not None:
        for _, row in configured.iterrows():
            try:
                raw = client.get_series(row["series_id"], firstdate=start_date, lastdate=end_date)
            except Exception:
                # Si la API falla para una serie específica, no botamos el módulo:
                # seguimos con las demás y si no queda nada usamos el fallback BDE HTML.
                continue
            if raw.empty:
                continue
            raw["value"] = raw["value"] * float(row.get("scale", 1.0)) * float(row.get("sign", 1.0))
            for col in mapping.columns:
                raw[col] = row[col]
            frames.append(raw)

    if frames:
        df = pd.concat(frames, ignore_index=True)
    elif demo:
        df = build_demo_series(mapping, start_date, end_date)
    else:
        # Sin series_id validados: usar rutas BDE oficiales del Monitor SIID como fuente.
        df = load_chart_data_from_bde_routes(chart_id, start_date, end_date)

    if df.empty:
        return pd.DataFrame(columns=BASE_COLUMNS)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["date"])
    return df[BASE_COLUMNS].sort_values(["date", "label"]).reset_index(drop=True)


def load_all_configured_data(
    client: BCCHClient | None,
    registry: SeriesRegistry,
    start_date: str,
    end_date: str,
    demo: bool = False,
) -> pd.DataFrame:
    charts = registry.mapping["chart_id"].dropna().unique().tolist()
    frames = [load_chart_data(client, registry, chart, start_date, end_date, demo=demo) for chart in charts]
    frames = [f for f in frames if not f.empty]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=BASE_COLUMNS)


def export_dataframe(df: pd.DataFrame, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".parquet":
        df.to_parquet(path, index=False)
    else:
        df.to_csv(path, index=False, encoding="utf-8-sig")
    return path
