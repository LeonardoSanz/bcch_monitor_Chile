"""Ejemplo para generar todos los dataframes finales y luego consumirlos desde Power BI como CSV."""
from pathlib import Path
import sys

ROOT = Path(r"C:\ruta\a\bcch_derivados_monitor")
sys.path.insert(0, str(ROOT))

from src.chart_registry import CHARTS
from src.io.bcch_api import BCCHClient
from src.series_registry import SeriesRegistry

client = BCCHClient.from_env()
registry = SeriesRegistry.from_csv(ROOT / "config" / "series_map.csv")
out_dir = ROOT / "exports"
out_dir.mkdir(exist_ok=True)

for spec in CHARTS:
    df = spec.build_dataframe(client, registry, "2020-01-01", "2026-12-31", demo=False)
    df.to_csv(out_dir / f"{spec.module_name}.csv", index=False, encoding="utf-8-sig")
