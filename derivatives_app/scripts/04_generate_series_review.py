from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.io.bcch_api import BCCHClient  # noqa: E402

OUT_DIR = ROOT / "outputs" / "mapeo_series"
CATALOG_CACHE = ROOT / "data" / "catalog_cache"


def norm(x: object) -> str:
    text = "" if x is None or pd.isna(x) else str(x)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("/", "-").replace("_", " ")
    text = text.replace("usd clp", "usd-clp").replace("uf clp", "uf-clp")
    text = re.sub(r"[^a-z0-9<>=%\-\.\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def split_terms(x: object) -> list[str]:
    raw = [norm(t) for t in str(x or "").split("|")]
    return [t for t in raw if t]


def ensure_catalog(frequencies: list[str], refresh: bool = False) -> pd.DataFrame:
    CATALOG_CACHE.mkdir(parents=True, exist_ok=True)
    frames = []
    client = None
    for freq in frequencies:
        freq = freq.upper().strip()
        path = CATALOG_CACHE / f"catalog_{freq}.csv"
        if refresh or not path.exists():
            if client is None:
                client = BCCHClient.from_env()
            print(f"Descargando catálogo {freq} desde BCCh...")
            df = client.search_series(freq)
            df.to_csv(path, index=False, encoding="utf-8-sig")
        df = pd.read_csv(path, dtype=str).fillna("")
        if "frequencyCode" not in df.columns:
            df["frequencyCode"] = freq
        frames.append(df.assign(catalog_file=path.name))
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True).fillna("")
    return out


def score_row(req: pd.Series, cand_text: str) -> tuple[float, str, str, str]:
    mandatory = split_terms(req.get("mandatory_terms", ""))
    optional = split_terms(req.get("optional_terms", ""))
    exclude = split_terms(req.get("exclude_terms", ""))

    matched_m = [t for t in mandatory if t in cand_text]
    missing_m = [t for t in mandatory if t not in cand_text]
    matched_o = [t for t in optional if t in cand_text]
    matched_ex = [t for t in exclude if t in cand_text]

    score = 0.0
    score += 12.0 * len(matched_m)
    score -= 10.0 * len(missing_m)
    score += 3.0 * len(matched_o)
    score -= 15.0 * len(matched_ex)

    # Bonos puntuales para evitar cruces entre ramas.
    chart_id = str(req.get("chart_id", ""))
    label = norm(req.get("label", ""))
    logical = norm(req.get("logical_series", ""))

    if "usdclp" in logical or "usd-clp" in label:
        if "usd-clp" in cand_text:
            score += 20
        if "me-ml" in cand_text and "usd-clp" not in cand_text:
            score -= 25

    if chart_id.startswith("d04"):
        if "swap promedio camara" in cand_text and "pesos" in cand_text:
            score += 25
        if "unidad de fomento" in cand_text or "monedas" in cand_text:
            score -= 25

    if chart_id.startswith("d05"):
        if "unidad de fomento" in cand_text or "uf-clp" in cand_text:
            score += 25
        if "swap promedio camara" in cand_text or "monedas" in cand_text:
            score -= 25

    if "neto" in label or "neto" in logical:
        if "neto" in cand_text or "posicion neta" in cand_text:
            score += 18
        if "monto transado" in cand_text and "neto" not in cand_text:
            score -= 15

    if "vigente" in label or "stock" in logical:
        if "monto vigente" in cand_text or "montos vigentes" in cand_text:
            score += 18
        if "monto transado" in cand_text or "montos transados" in cand_text:
            score -= 15

    if "transado" in label or "flujo" in logical or "volumen" in label:
        if "monto transado" in cand_text or "montos transados" in cand_text:
            score += 18
        if "monto vigente" in cand_text or "montos vigentes" in cand_text:
            score -= 15

    return score, "; ".join(matched_m), "; ".join(missing_m), "; ".join(matched_o)


def build_review(requirements: pd.DataFrame, catalog: pd.DataFrame, top: int) -> pd.DataFrame:
    text_cols = [c for c in ["seriesId", "spanishTitle", "englishTitle", "frequencyCode"] if c in catalog.columns]
    catalog = catalog.copy()
    catalog["_search_text"] = catalog[text_cols].astype(str).agg(" ".join, axis=1).map(norm)

    rows = []
    for _, req in requirements.iterrows():
        freq = str(req.get("frequency", "")).upper().strip()
        cands = catalog[catalog["frequencyCode"].astype(str).str.upper().eq(freq)].copy()
        scored = []
        for idx, cand in cands.iterrows():
            score, matched_m, missing_m, matched_o = score_row(req, cand["_search_text"])
            if score > 0 or matched_m:
                scored.append((idx, score, matched_m, missing_m, matched_o))
        scored = sorted(scored, key=lambda x: x[1], reverse=True)[:top]
        for rank, (idx, score, matched_m, missing_m, matched_o) in enumerate(scored, start=1):
            cand = catalog.loc[idx]
            rows.append({
                "selected": "",
                "rank": rank,
                "score": round(score, 2),
                "chart_id": req.get("chart_id", ""),
                "logical_series": req.get("logical_series", ""),
                "target_label": req.get("label", ""),
                "frequency": freq,
                "bde_path": req.get("bde_path", ""),
                "seriesId": cand.get("seriesId", ""),
                "spanishTitle": cand.get("spanishTitle", ""),
                "englishTitle": cand.get("englishTitle", ""),
                "firstObservation": cand.get("firstObservation", ""),
                "lastObservation": cand.get("lastObservation", ""),
                "matched_mandatory": matched_m,
                "missing_mandatory": missing_m,
                "matched_optional": matched_o,
                "review_note": "",
            })
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera un archivo de revisión para seleccionar las series BCCh correctas por gráfico.")
    parser.add_argument("--requirements", default="config/series_requirements.csv")
    parser.add_argument("--top", type=int, default=15)
    parser.add_argument("--refresh-catalog", action="store_true")
    args = parser.parse_args()

    req_path = ROOT / args.requirements
    requirements = pd.read_csv(req_path, dtype=str).fillna("")
    freqs = sorted(requirements["frequency"].str.upper().dropna().unique().tolist())
    catalog = ensure_catalog(freqs, refresh=args.refresh_catalog)
    review = build_review(requirements, catalog, top=args.top)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_csv = OUT_DIR / "series_candidates_review.csv"
    review.to_csv(out_csv, index=False, encoding="utf-8-sig")

    # Resumen por serie lógica: mejor candidato y estado preliminar.
    best = review.sort_values(["logical_series", "rank"]).groupby("logical_series", as_index=False).first()
    summary = best[["chart_id", "logical_series", "target_label", "frequency", "score", "seriesId", "spanishTitle", "missing_mandatory", "bde_path"]]
    summary_path = OUT_DIR / "series_candidates_best_summary.csv"
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")

    print(f"Archivo de revisión generado: {out_csv}")
    print(f"Resumen de mejores candidatos: {summary_path}")
    print("Abre series_candidates_review.csv, marca selected=1 en la fila correcta de cada logical_series y luego corre scripts/05_apply_review_selection.py")


if __name__ == "__main__":
    main()
