from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Aplica al series_map.csv las series seleccionadas en el archivo de revisión.")
    parser.add_argument("--review", default="outputs/mapeo_series/series_candidates_review.csv")
    parser.add_argument("--series-map", default="config/series_map.csv")
    parser.add_argument("--output", default="config/series_map_validado.csv")
    args = parser.parse_args()

    review_path = ROOT / args.review
    map_path = ROOT / args.series_map
    output_path = ROOT / args.output

    review = pd.read_csv(review_path, dtype=str).fillna("")
    selected = review[review["selected"].astype(str).str.strip().isin(["1", "x", "X", "ok", "OK", "si", "sí", "SI", "SÍ"])]
    if selected.empty:
        raise ValueError("No hay filas seleccionadas. Marca selected=1 en series_candidates_review.csv")

    duplicates = selected["logical_series"].value_counts()
    duplicates = duplicates[duplicates > 1]
    if not duplicates.empty:
        raise ValueError(f"Hay logical_series con más de una selección: {duplicates.to_dict()}")

    mapping = pd.read_csv(map_path, dtype=str).fillna("")
    lookup = selected.set_index("logical_series")["seriesId"].to_dict()
    mapping["series_id"] = mapping.apply(
        lambda r: lookup.get(r["logical_series"], r.get("series_id", "")),
        axis=1,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    mapping.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"series_map validado generado: {output_path}")
    print("Para producción, revisa el archivo y reemplaza config/series_map.csv por config/series_map_validado.csv si está correcto.")


if __name__ == "__main__":
    main()
