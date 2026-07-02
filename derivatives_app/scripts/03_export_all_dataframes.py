from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.chart_registry import CHARTS
from src.io.bcch_api import BCCHClient
from src.series_registry import SeriesRegistry


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta dataframes finales de cada gráfico a CSV para Power BI o revisión.")
    parser.add_argument("--series-map", default="config/series_map.csv")
    parser.add_argument("--start", default="2020-01-01")
    parser.add_argument("--end", default="2026-12-31")
    parser.add_argument("--out-dir", default="exports")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    registry = SeriesRegistry.from_csv(ROOT / args.series_map)
    client = None if args.demo else BCCHClient.from_env()
    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    for spec in CHARTS:
        df = spec.build_dataframe(client, registry, args.start, args.end, args.demo)
        file_path = out_dir / f"{spec.module_name}.csv"
        df.to_csv(file_path, index=False, encoding="utf-8-sig")
        print(f"OK -> {file_path} ({len(df):,} filas)")


if __name__ == "__main__":
    main()
