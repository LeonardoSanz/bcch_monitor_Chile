from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = [
    "chart_id",
    "logical_series",
    "series_id",
    "label",
    "market",
    "dimension_1",
    "dimension_2",
    "frequency",
    "unit",
    "scale",
    "sign",
    "notes",
]


@dataclass
class SeriesRegistry:
    """Registro de series usadas por los gráficos."""

    mapping: pd.DataFrame

    @classmethod
    def from_csv(cls, path: str | Path) -> "SeriesRegistry":
        df = pd.read_csv(path, dtype=str).fillna("")
        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        df["scale"] = pd.to_numeric(df["scale"].replace("", "1"), errors="coerce").fillna(1.0)
        df["sign"] = pd.to_numeric(df["sign"].replace("", "1"), errors="coerce").fillna(1.0)
        return cls(df[REQUIRED_COLUMNS].copy())

    def for_chart(self, chart_id: str) -> pd.DataFrame:
        return self.mapping[self.mapping["chart_id"].eq(chart_id)].copy()

    def missing_for_chart(self, chart_id: str) -> pd.DataFrame:
        df = self.for_chart(chart_id)
        return df[df["series_id"].astype(str).str.strip().eq("")].copy()

    def all_configured(self) -> pd.DataFrame:
        return self.mapping[self.mapping["series_id"].astype(str).str.strip().ne("")].copy()
