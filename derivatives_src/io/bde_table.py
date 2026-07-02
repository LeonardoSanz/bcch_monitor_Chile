from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from io import StringIO
from typing import Iterable
import re
import unicodedata

import pandas as pd
import requests


SPANISH_MONTHS = {
    "ene": 1, "enero": 1,
    "feb": 2, "febrero": 2,
    "mar": 3, "marzo": 3,
    "abr": 4, "abril": 4,
    "may": 5, "mayo": 5,
    "jun": 6, "junio": 6,
    "jul": 7, "julio": 7,
    "ago": 8, "agosto": 8,
    "sep": 9, "sept": 9, "septiembre": 9,
    "oct": 10, "octubre": 10,
    "nov": 11, "noviembre": 11,
    "dic": 12, "diciembre": 12,
}


class BDETableError(RuntimeError):
    """Error controlado para lectura de cuadros HTML BDE."""


def normalize_text(value: object) -> str:
    text = "" if value is None or pd.isna(value) else str(value)
    text = text.replace("\xa0", " ").strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = text.replace("/", " ").replace("-", " ")
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_label(value: object) -> str:
    text = "" if value is None or pd.isna(value) else str(value)
    text = text.replace("\xa0", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def parse_bde_number(value: object) -> float:
    if value is None or pd.isna(value):
        return float("nan")
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("\xa0", "").replace(" ", "")
    if text in {"", "-", "--", "ND", "N.D.", "S/I", "NeuN", "nan", "NaN"}:
        return float("nan")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    else:
        if text.count(".") >= 2:
            text = text.replace(".", "")
        elif text.count(".") == 1:
            left, right = text.split(".", 1)
            if len(right) == 3 and left.replace("-", "").isdigit() and right.isdigit():
                text = left + right
    try:
        return float(text)
    except Exception:
        return float("nan")


def parse_bde_period(label: object) -> pd.Timestamp | pd.NaT:
    """Reconoce columnas mensuales (Ene.2026) y diarias (02.Ene.2026)."""
    raw = clean_label(label)
    # Diario: 02.Ene.2026
    d = re.search(r"^(\d{1,2})\s*[\.\-/]\s*([A-Za-zÁÉÍÓÚáéíóúñÑ\.]+)\s*[\.\-/]?\s*(\d{4})$", raw)
    if d:
        day = int(d.group(1))
        token = normalize_text(d.group(2)).replace(".", "")
        year = int(d.group(3))
        month = SPANISH_MONTHS.get(token)
        if month:
            return pd.Timestamp(year=year, month=month, day=day)
    # Mensual: Ene.2026, Ene-2026
    m = re.search(r"^([A-Za-zÁÉÍÓÚáéíóúñÑ\.]+)\s*[\.-]?\s*(\d{4})$", raw)
    if not m:
        return pd.NaT
    month_token = normalize_text(m.group(1)).replace(".", "")
    year = int(m.group(2))
    month = SPANISH_MONTHS.get(month_token)
    if not month:
        return pd.NaT
    return pd.Timestamp(year=year, month=month, day=1)


# Compatibilidad con versiones anteriores.
def parse_bde_month(label: object) -> pd.Timestamp | pd.NaT:
    return parse_bde_period(label)


@dataclass(frozen=True)
class BDETable:
    url: str
    title: str
    wide: pd.DataFrame
    long: pd.DataFrame


def _flatten_columns(columns: Iterable[object]) -> list[str]:
    out: list[str] = []
    for col in columns:
        if isinstance(col, tuple):
            parts = [clean_label(x) for x in col if clean_label(x) and not str(x).startswith("Unnamed")]
            name = " ".join(parts)
        else:
            name = clean_label(col)
        out.append(name)
    return out


def _pick_bde_table(tables: list[pd.DataFrame]) -> pd.DataFrame:
    candidates: list[pd.DataFrame] = []
    for t in tables:
        if t.empty:
            continue
        tmp = t.copy()
        tmp.columns = _flatten_columns(tmp.columns)
        cols_norm = [normalize_text(c) for c in tmp.columns]
        has_serie = any(c == "serie" or c.endswith(" serie") for c in cols_norm)
        has_period = sum(pd.notna(parse_bde_period(c)) for c in tmp.columns) >= 3
        if has_serie and has_period:
            candidates.append(tmp)
    if not candidates:
        raise BDETableError("No encontré una tabla BDE con columna Serie y columnas de período.")
    candidates.sort(key=lambda d: sum(pd.notna(parse_bde_period(c)) for c in d.columns), reverse=True)
    return candidates[0]


def _leading_indent(value: object) -> int:
    raw = "" if value is None or pd.isna(value) else str(value)
    raw = raw.replace("\u00a0", " ")
    return len(raw) - len(raw.lstrip(" "))


def _add_hierarchy(wide: pd.DataFrame) -> pd.DataFrame:
    """Agrega bde_parent para filas indentadas de la BDE.

    En cuadros como SPT_MEML_02, la BDE muestra:
      Monto transado total, interbancario
          Spot
          Derivados
    El parent permite recuperar que Spot/Derivados pertenecen a Interbancario.
    """
    out = wide.copy()
    raw_values = out["bde_series_raw"].tolist()
    parents: list[str] = []
    levels: list[int] = []
    current_parent = ""
    current_level1 = ""
    metric_norms = {"compras", "ventas", "neto", "spot", "derivados", "monto vigente comprador", "monto vigente vendedor", "monto vigente neto"}

    for raw in raw_values:
        indent = _leading_indent(raw)
        label = clean_label(raw)
        norm = normalize_text(label)
        if not label:
            parents.append("")
            levels.append(0)
            continue
        is_header = norm in {"sectores", "notas"}
        is_metric = norm in metric_norms
        if indent <= 1:
            parent = ""
            level = 0
            if not is_header:
                current_parent = label
                current_level1 = label
        elif indent <= 5:
            # En algunos cuadros las métricas (Compras/Ventas/Neto) aparecen con el mismo indent
            # que el sector. En ese caso el parent correcto es el último sector visto.
            parent = (current_level1 or current_parent) if is_metric else current_parent
            level = 1
            if not is_metric and not is_header:
                current_level1 = label
        else:
            parent = current_level1 or current_parent
            level = 2
        parents.append(parent)
        levels.append(level)

    out["bde_parent"] = parents
    out["bde_parent_norm"] = [normalize_text(x) for x in parents]
    out["bde_level"] = levels
    return out


@lru_cache(maxsize=96)
def fetch_bde_table(url: str, timeout: int = 60) -> BDETable:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    html = resp.text
    tables = pd.read_html(StringIO(html), thousands=".", decimal=",", keep_default_na=False)
    wide = _pick_bde_table(tables)

    serie_col = None
    for col in wide.columns:
        if normalize_text(col) == "serie" or normalize_text(col).endswith(" serie"):
            serie_col = col
            break
    if serie_col is None:
        raise BDETableError("La tabla BDE no trae columna Serie.")

    period_cols = [c for c in wide.columns if pd.notna(parse_bde_period(c))]
    keep = [serie_col] + period_cols
    wide = wide[keep].copy()
    wide = wide.rename(columns={serie_col: "bde_series_raw"})
    wide["bde_series"] = wide["bde_series_raw"].map(clean_label)
    wide = wide[wide["bde_series"].astype(str).str.strip().ne("")].copy()
    wide = _add_hierarchy(wide)

    long = wide.melt(
        id_vars=["bde_series_raw", "bde_series", "bde_parent", "bde_parent_norm", "bde_level"],
        value_vars=period_cols,
        var_name="period_label",
        value_name="value",
    )
    long["date"] = long["period_label"].map(parse_bde_period)
    long["value"] = long["value"].map(parse_bde_number)
    long = long.dropna(subset=["date", "value"]).copy()
    long["date"] = pd.to_datetime(long["date"])
    long["bde_series_norm"] = long["bde_series"].map(normalize_text)
    long["source_url"] = url
    cols = [
        "date", "bde_series", "bde_series_norm", "bde_parent", "bde_parent_norm", "bde_level",
        "period_label", "value", "source_url",
    ]
    long = long[cols].sort_values(["bde_series", "date"])
    return BDETable(url=url, title="", wide=wide, long=long.reset_index(drop=True))


def load_bde_rows(
    url: str,
    row_map: dict[str, dict[str, str]],
    start_date: str,
    end_date: str,
    unit: str = "MM USD",
    chart_id: str = "",
) -> pd.DataFrame:
    table = fetch_bde_table(url)
    long = table.long.copy()
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    long = long[(long["date"] >= start) & (long["date"] <= end)].copy()

    frames = []
    lookup = {normalize_text(k): v for k, v in row_map.items()}
    for norm_key, meta in lookup.items():
        hit = long[long["bde_series_norm"].eq(norm_key)].copy()
        if hit.empty:
            hit = long[long["bde_series_norm"].str.contains(re.escape(norm_key), na=False)].copy()
        if hit.empty:
            continue
        hit["chart_id"] = chart_id
        hit["logical_series"] = meta.get("logical_series", norm_key)
        hit["series_id"] = meta.get("series_id", meta.get("logical_series", norm_key))
        hit["label"] = meta.get("label", hit["bde_series"].iloc[0])
        hit["market"] = meta.get("market", meta.get("label", hit["bde_series"].iloc[0]))
        hit["dimension_1"] = meta.get("dimension_1", "")
        hit["dimension_2"] = meta.get("dimension_2", "")
        hit["frequency"] = "MONTHLY"
        hit["unit"] = unit
        hit["status_code"] = "BDE_HTML"
        frames.append(hit)

    base_cols = ["date", "value", "chart_id", "logical_series", "series_id", "label", "market", "dimension_1", "dimension_2", "frequency", "unit", "status_code"]
    if not frames:
        return pd.DataFrame(columns=base_cols)

    df = pd.concat(frames, ignore_index=True)
    return df[base_cols].sort_values(["date", "label"]).reset_index(drop=True)


def test_bde_url(url: str) -> tuple[int, int]:
    table = fetch_bde_table(url)
    rows = table.long["bde_series"].nunique()
    periods = table.long["date"].nunique()
    return int(rows), int(periods)
