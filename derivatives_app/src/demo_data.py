from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd


def build_demo_series(mapping: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """Genera datos sintéticos solo para validar layout cuando faltan series_id."""
    frames: list[pd.DataFrame] = []
    if mapping.empty:
        return pd.DataFrame()

    for _, row in mapping.iterrows():
        freq = str(row.get("frequency", "MONTHLY")).upper()
        pandas_freq = "B" if freq == "DAILY" else "MS"
        dates = pd.date_range(start=start, end=end, freq=pandas_freq)
        if len(dates) == 0:
            continue

        seed = int(hashlib.md5(str(row.get("logical_series", "demo")).encode()).hexdigest(), 16) % (2**32)
        rng = np.random.default_rng(seed)
        base = 1000 + (seed % 8000)
        noise = rng.normal(0, base * 0.03, len(dates)).cumsum()
        seasonal = np.sin(np.arange(len(dates)) / 6) * base * 0.08
        values = np.maximum(base + noise + seasonal, 0)

        # Para series netas permitir signo mixto
        logical = str(row.get("logical_series", "")).lower()
        if "neto" in logical or "neta" in logical:
            values = values - np.nanmean(values)

        frame = pd.DataFrame({"date": dates, "value": values})
        for col in mapping.columns:
            frame[col] = row[col]
        frame["series_id"] = row.get("series_id", "DEMO") or "DEMO"
        frame["status_code"] = "DEMO"
        frames.append(frame)

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
