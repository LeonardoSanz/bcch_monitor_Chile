"""Ejemplo para usar en Power BI / Transformar datos / Ejecutar script de Python.

Power BI espera que el último objeto dataframe se llame, por ejemplo, df.
Ajusta ROOT a la carpeta donde guardaste el proyecto.
"""
from pathlib import Path
import sys

ROOT = Path(r"C:\ruta\a\bcch_derivados_monitor")
sys.path.insert(0, str(ROOT))

from src.io.bcch_api import BCCHClient
from src.series_registry import SeriesRegistry
from src.charts.d02_fx_neto_contraparte import build_dataframe

client = BCCHClient.from_env()
registry = SeriesRegistry.from_csv(ROOT / "config" / "series_map.csv")

df = build_dataframe(
    client=client,
    registry=registry,
    start_date="2020-01-01",
    end_date="2026-12-31",
    demo=False,
)
