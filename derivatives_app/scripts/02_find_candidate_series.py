from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def normalize(text: str) -> str:
    return str(text).lower().strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Busca candidatos dentro del catálogo local bajado desde la API BDE.")
    parser.add_argument("--query", required=True, help="Palabras a buscar; todas deben aparecer")
    parser.add_argument("--catalog-dir", default="data/catalog")
    parser.add_argument("--top", type=int, default=50)
    args = parser.parse_args()

    catalog_dir = ROOT / args.catalog_dir
    files = list(catalog_dir.glob("catalog_*.csv"))
    if not files:
        raise FileNotFoundError("No hay catálogos. Corre primero scripts/01_build_catalog.py")

    df = pd.concat([pd.read_csv(f, dtype=str).assign(catalog_file=f.name) for f in files], ignore_index=True).fillna("")
    terms = [normalize(t) for t in args.query.split() if t.strip()]
    text = (df["seriesId"] + " " + df.get("spanishTitle", "") + " " + df.get("englishTitle", "")).map(normalize)
    mask = pd.Series(True, index=df.index)
    for term in terms:
        mask &= text.str.contains(term, regex=False)

    out = df.loc[mask, ["seriesId", "frequencyCode", "spanishTitle", "englishTitle", "firstObservation", "lastObservation", "catalog_file"]].head(args.top)
    if out.empty:
        print("Sin candidatos. Prueba menos palabras o sin tildes.")
    else:
        print(out.to_string(index=False))
        out_dir = ROOT / "data" / "catalog"
        out_dir.mkdir(parents=True, exist_ok=True)
        out.to_csv(out_dir / "last_candidates.csv", index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
