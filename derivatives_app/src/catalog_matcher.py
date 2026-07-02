from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from src.io.bcch_api import BCCHClient
from src.series_registry import SeriesRegistry

try:
    from src.monitor_links import source_terms_for_chart
except Exception:  # pragma: no cover
    def source_terms_for_chart(chart_id: str | None = None, chart_module: str | None = None) -> list[str]:
        return []



CATALOG_DIR = Path("data/catalog_cache")
AUTO_MAP_PATH = Path("config/series_map_auto.csv")


STOPWORDS = {
    "buscar", "por", "de", "del", "la", "el", "los", "las", "y", "en", "a", "con",
    "para", "serie", "bcch", "bde", "mensual", "diario", "daily", "monthly", "mm", "usd",
}

SYNONYMS: dict[str, list[str]] = {
    "FX": ["monedas", "moneda extranjera", "tipos de cambio", "tipo de cambio", "me-ml", "usd-clp", "usd clp"],
    "FX USD/CLP": ["usd-clp", "usd clp", "dolar", "dólar", "monedas"],
    "Tasas": ["tasa de interes", "tasas de interes", "tasas de interés", "swap promedio camara", "swap promedio cámara", "spc"],
    "SPC CLP": ["swap promedio camara", "swap promedio cámara", "spc", "pesos"],
    "UF-CLP": ["unidad de fomento", "uf-clp", "uf clp", "peso chileno"],
    "Interbancario": ["interbancario"],
    "No residentes": ["no residentes", "no residente"],
    "Residentes no bancos": ["residentes no bancos", "residentes no bancarios"],
    "Fondos de pensiones": ["fondos de pensiones", "fondo de pensiones", "afp"],
    "Sector real": ["sector real", "empresas sector real", "empresas del sector real"],
    "AGF": ["administradoras generales de fondos", "agf"],
    "Seguros": ["compañias de seguros", "compañías de seguros", "seguros"],
    "Corredoras": ["corredoras de bolsa", "agencias de valores", "corredoras"],
    "Forward/FX Swap": ["forward", "fx swap", "swap cambiario"],
    "Cross Currency Swap": ["cross currency swap", "ccs"],
    "Opciones": ["opciones", "opcion"],
    "Otros": ["otros"],
    "Compras": ["compras", "compra"],
    "Ventas": ["ventas", "venta"],
    "Neto": ["neto", "posicion neta", "posición neta"],
    "Hasta 2 años": ["hasta 2 anos", "hasta 2 años", "0-2", "menor a 2"],
    "Mayor a 2 años": ["mayor a 2 anos", "mayor a 2 años", "mas de 2", "más de 2"],
    "<= 30d": ["hasta 30 dias", "hasta 30 días", "<= 30", "0-30"],
    "31-90d": ["31-90", "31 a 90", "31 hasta 90"],
    "91-180d": ["91-180", "91 a 180", "91 hasta 180"],
    "181-360d": ["181-360", "181 a 360", "181 hasta 360"],
    "> 1y": ["mayor a 1 ano", "mayor a 1 año", "mas de 1", "más de 1"],
    "<= 1y": ["hasta 1 ano", "hasta 1 año", "menor a 1", "0-1"],
    "1-2y": ["1-2", "1 a 2", "1 hasta 2"],
    "2-5y": ["2-5", "2 a 5", "2 hasta 5"],
    "> 5y": ["mayor a 5 anos", "mayor a 5 años", "mas de 5", "más de 5"],
}

CHART_TERMS: dict[str, list[str]] = {
    "d01_resumen_stock_monto_vigente": ["derivados", "bancos", "monto vigente"],
    "d01_resumen_flujo_monto_transado": ["derivados", "bancos", "monto transado"],
    "d02_fx_usdclp_vigente_contraparte": ["derivados", "monedas", "bancos", "mensual", "monto vigente", "contraparte", "usd-clp"],
    "d02_fx_usdclp_neto_contraparte": ["derivados", "monedas", "bancos", "mensual", "monto vigente", "neto", "contraparte", "usd-clp"],
    "d02_fx_usdclp_vigente_instrumento": ["derivados", "monedas", "bancos", "mensual", "monto vigente", "instrumento", "usd-clp"],
    "d02_fx_ndf_no_residentes_plazo": ["ndf", "no residentes", "plazo contractual", "usd-clp"],
    "d03_fx_usdclp_transado_diario": ["derivados", "monedas", "bancos", "diario", "monto transado", "usd-clp"],
    "d03_spot_vs_derivados_usdclp": ["usd-clp", "mensual", "monto transado", "bancos"],
    "d03_fx_compras_ventas_neto_sector": ["total", "derivados", "spot", "posiciones netas", "montos transados", "sectores"],
    "d04_spc_clp_vigente_plazo_residual": ["swap promedio cámara", "pesos", "bancos", "mensual", "monto vigente", "plazo residual"],
    "d04_spc_clp_neto_contraparte": ["swap promedio cámara", "pesos", "bancos", "mensual", "monto vigente", "neto", "contraparte"],
    "d04_spc_clp_transado_plazo_contraparte": ["swap promedio cámara", "pesos", "bancos", "mensual", "monto transado", "plazo contractual", "contraparte"],
    "d05_ufclp_vigente_contraparte": ["unidad de fomento", "peso chileno", "bancos", "mensual", "monto vigente", "contraparte"],
    "d05_ufclp_forward_12m_vs_spot": ["precio forward", "uf", "clp", "12"],
    "d05_ufclp_volumen_precio": ["unidad de fomento", "peso chileno", "bancos", "mensual"],
}

SPECIAL_LOGICAL_TERMS: dict[str, list[str]] = {
    "stock_fx": ["tipos de cambio", "monto vigente"],
    "flujo_fx": ["tipos de cambio", "monto transado"],
    "stock_tasas": ["tasa de interes", "monto vigente"],
    "flujo_tasas": ["tasa de interes", "monto transado"],
    "stock_uf-clp": ["uf-clp", "monto vigente"],
    "flujo_uf-clp": ["uf-clp", "monto transado"],
    "spot_usdclp_mensual": ["spot", "usd-clp", "mensual", "monto transado"],
    "deriv_usdclp_mensual": ["derivados", "usd-clp", "mensual", "monto transado"],
    "uf_spot": ["unidad de fomento", "uf", "diaria"],
    "ufclp_forward_12m": ["precio forward", "12 meses", "uf-clp"],
    "ufclp_precio_forward": ["precio forward", "uf-clp"],
    "ufclp_volumen": ["monto transado", "uf-clp"],
}


@dataclass
class AutoMapResult:
    registry: SeriesRegistry
    report: pd.DataFrame
    output_path: Path | None = None


def normalize_text(value: object) -> str:
    text = "" if value is None or pd.isna(value) else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = text.replace("/", " ").replace("_", "-")
    text = re.sub(r"[^a-z0-9<>=%\-\.\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def catalog_text(catalog: pd.DataFrame) -> pd.Series:
    parts = []
    for col in ["seriesId", "spanishTitle", "englishTitle", "frequency", "unit"]:
        if col in catalog.columns:
            parts.append(catalog[col].fillna("").astype(str))
    if not parts:
        return pd.Series("", index=catalog.index)
    raw = parts[0]
    for p in parts[1:]:
        raw = raw + " " + p
    return raw.map(normalize_text)


def split_terms(text: str) -> list[str]:
    text = normalize_text(text)
    raw = re.split(r"[\s,;:()\[\]{}]+", text)
    terms = [t for t in raw if len(t) >= 2 and t not in STOPWORDS]
    return list(dict.fromkeys(terms))


def row_terms(row: pd.Series) -> list[str]:
    terms: list[str] = []
    chart_id = str(row.get("chart_id", ""))
    terms += CHART_TERMS.get(chart_id, [])
    # Términos desde config/monitor_mensual_links.csv: links oficiales del Monitor SIID.
    # Se usan como ancla para que el auto-mapeo busque cerca del cuadro BDE correcto.
    terms += source_terms_for_chart(chart_id=chart_id)
    terms += SPECIAL_LOGICAL_TERMS.get(str(row.get("logical_series", "")), [])

    for field in ["market", "dimension_1", "dimension_2"]:
        value = str(row.get(field, "")).strip()
        if not value:
            continue
        terms.append(value)
        terms += SYNONYMS.get(value, [])

    # Las notas ayudan, pero se usan con menor peso en el scoring.
    notes = str(row.get("notes", ""))
    if "Buscar:" in notes:
        notes = notes.split("Buscar:", 1)[1]
    terms += split_terms(notes)

    # Agregar algunos términos del label solo cuando son distintivos.
    label = str(row.get("label", ""))
    for keyword in ["neto", "vigente", "transado", "spot", "forward", "precio", "volumen", "compra", "venta", "ndf"]:
        if keyword in normalize_text(label):
            terms.append(keyword)

    out = []
    for term in terms:
        n = normalize_text(term)
        if n and n not in out:
            out.append(n)
    return out


def score_candidate(text: str, terms: Iterable[str], row: pd.Series) -> float:
    score = 0.0
    for term in terms:
        if not term:
            continue
        # Frases largas pesan más que tokens sueltos.
        if term in text:
            score += 3.0 if " " in term or "-" in term else 1.0

    logical = normalize_text(row.get("logical_series", ""))
    chart_id = str(row.get("chart_id", ""))

    # Penalizaciones/bonos por tema, para evitar que mezcle ramas parecidas.
    if "usdclp" in logical or "usd-clp" in normalize_text(row.get("label", "")):
        if "usd-clp" in text or "usd clp" in text:
            score += 6
        if "me-ml" in text and "usd-clp" not in text:
            score -= 4

    if chart_id.startswith("d04"):
        if "swap promedio camara" in text or "swap promedio cámara" in text:
            score += 8
        if "unidad de fomento" in text or "monedas" in text:
            score -= 4

    if chart_id.startswith("d05"):
        if "unidad de fomento" in text or "uf-clp" in text or "uf clp" in text:
            score += 8
        if "swap promedio camara" in text:
            score -= 4

    if chart_id.startswith("d02") or chart_id.startswith("d03"):
        if "monedas" in text or "tipo de cambio" in text or "usd-clp" in text:
            score += 5
        if "swap promedio camara" in text or "unidad de fomento" in text:
            score -= 4

    if "neto" in logical or "neto" in normalize_text(row.get("label", "")):
        if "neto" in text or "posicion neta" in text:
            score += 7
        if "monto transado" in text and "neto" not in text:
            score -= 3

    if "vigente" in normalize_text(row.get("label", "")) or "stock" in logical:
        if "monto vigente" in text or "montos vigentes" in text:
            score += 6
        if "monto transado" in text or "montos transados" in text:
            score -= 3

    if "transado" in normalize_text(row.get("label", "")) or "flujo" in logical:
        if "monto transado" in text or "montos transados" in text:
            score += 6
        if "monto vigente" in text or "montos vigentes" in text:
            score -= 3

    return score


def top_candidates_for_row(row: pd.Series, catalog: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    if catalog.empty:
        return pd.DataFrame()
    terms = row_terms(row)
    text = catalog_text(catalog)
    scores = text.map(lambda t: score_candidate(t, terms, row))
    out = catalog.copy()
    out["_score"] = scores
    out["_matched_terms"] = [", ".join([t for t in terms if t in text.iloc[i]]) for i in range(len(text))]
    out = out.sort_values("_score", ascending=False).head(top_n)
    keep = [c for c in ["seriesId", "spanishTitle", "englishTitle", "frequency", "unit", "firstObservation", "lastObservation", "_score", "_matched_terms"] if c in out.columns]
    return out[keep].reset_index(drop=True)


def download_catalogs(client: BCCHClient, frequencies: Iterable[str], cache_dir: str | Path = CATALOG_DIR) -> dict[str, pd.DataFrame]:
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    catalogs: dict[str, pd.DataFrame] = {}
    for freq in frequencies:
        freq_u = str(freq).upper().strip()
        path = cache / f"catalog_{freq_u}.csv"
        try:
            df = client.search_series(freq_u)
            if not df.empty:
                df.to_csv(path, index=False, encoding="utf-8-sig")
        except Exception:
            if path.exists():
                df = pd.read_csv(path, dtype=str).fillna("")
            else:
                raise
        catalogs[freq_u] = df
    return catalogs


def auto_fill_registry(
    registry: SeriesRegistry,
    catalogs: dict[str, pd.DataFrame],
    min_score: float = 18.0,
    save_path: str | Path | None = None,
) -> AutoMapResult:
    mapping = registry.mapping.copy()
    report_rows: list[dict[str, object]] = []

    for idx, row in mapping.iterrows():
        current = str(row.get("series_id", "")).strip()
        if current:
            report_rows.append({
                "row": idx,
                "chart_id": row.get("chart_id", ""),
                "logical_series": row.get("logical_series", ""),
                "label": row.get("label", ""),
                "series_id": current,
                "score": None,
                "status": "manual",
                "candidate_title": "",
            })
            continue

        freq = str(row.get("frequency", "MONTHLY")).upper().strip() or "MONTHLY"
        catalog = catalogs.get(freq, pd.DataFrame())
        candidates = top_candidates_for_row(row, catalog, top_n=1)
        if not candidates.empty:
            best = candidates.iloc[0]
            score = float(best.get("_score", 0.0))
            series_id = str(best.get("seriesId", "")).strip()
            title = str(best.get("spanishTitle", best.get("englishTitle", "")))
            if score >= min_score and series_id:
                mapping.at[idx, "series_id"] = series_id
                status = "auto_ok"
            else:
                status = "auto_low_score"
        else:
            score = 0.0
            series_id = ""
            title = ""
            status = "sin_candidato"
        report_rows.append({
            "row": idx,
            "chart_id": row.get("chart_id", ""),
            "logical_series": row.get("logical_series", ""),
            "label": row.get("label", ""),
            "series_id": series_id,
            "score": score,
            "status": status,
            "candidate_title": title,
        })

    out_path = None
    if save_path is not None:
        out_path = Path(save_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        mapping.to_csv(out_path, index=False, encoding="utf-8-sig")

    return AutoMapResult(SeriesRegistry(mapping), pd.DataFrame(report_rows), out_path)
