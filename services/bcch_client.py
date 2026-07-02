from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode
import re

import pandas as pd
import requests

from config.settings import BCCH_MAX_WORKERS, BCCH_TIMEOUT_SECONDS

SIETEWS_URL = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"


class SieteWSError(RuntimeError):
    """Error general del cliente SieteWS."""


class MissingCredentials(SieteWSError):
    """Credenciales no disponibles."""


class InvalidCredentials(SieteWSError):
    """Usuario o clave SieteWS inválidos."""


@dataclass(frozen=True)
class Credentials:
    user: str
    password: str


def sanitize_error(message: str) -> str:
    """Limpia mensajes para evitar mostrar datos sensibles."""
    if not message:
        return "Error sin detalle."
    text = str(message)
    text = re.sub(r"pass=[^&\s]+", "pass=***", text, flags=re.IGNORECASE)
    text = re.sub(r"password[^,}\n]+", "password=***", text, flags=re.IGNORECASE)
    return text[:700]


def parse_sietews_date(value: object) -> pd.Timestamp | pd.NaT:
    text = "" if value is None else str(value).strip()
    if not text:
        return pd.NaT
    if re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}", text):
        dt = pd.to_datetime(text, errors="coerce")
        if pd.notna(dt):
            return pd.Timestamp(dt).normalize()
    for dayfirst in (True, False):
        dt = pd.to_datetime(text, errors="coerce", dayfirst=dayfirst)
        if pd.notna(dt):
            return pd.Timestamp(dt).normalize()
    return pd.NaT


def parse_sietews_value(value: object) -> float:
    if value is None:
        return float("nan")
    text = str(value).strip().replace("\xa0", "").replace(" ", "")
    if text in {"", "nan", "None", "S/I", "ND", "--", "-"}:
        return float("nan")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")
    try:
        return float(text)
    except Exception:
        return float("nan")


def extract_obs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    series = payload.get("Series") or payload.get("series")
    if isinstance(series, dict):
        obs = series.get("Obs") or series.get("obs") or series.get("OBS")
        if isinstance(obs, list):
            return obs
        if isinstance(obs, dict):
            return [obs]
    for key in ["Obs", "obs", "data", "Data"]:
        obs = payload.get(key)
        if isinstance(obs, list):
            return obs
    return []


def _payload_error(payload: dict[str, Any]) -> tuple[bool, str]:
    code = payload.get("Codigo") or payload.get("codigo") or payload.get("Code")
    if code in {None, "", 0, "0"}:
        return False, ""
    description = payload.get("Descripcion") or payload.get("descripcion") or payload.get("Description") or "Error SieteWS"
    if str(code) == "-5":
        raise InvalidCredentials("Credenciales SieteWS inválidas.")
    return True, f"SieteWS error {code}: {description}"


def fetch_series_raw(code: str, firstdate: str, lastdate: str, credentials: Credentials) -> pd.DataFrame:
    """Consulta una serie SieteWS y devuelve columnas fecha/valor/code."""
    if credentials is None or not credentials.user or not credentials.password:
        raise MissingCredentials("Faltan credenciales SieteWS.")
    params = {
        "user": credentials.user,
        "pass": credentials.password,
        "function": "GetSeries",
        "timeseries": code,
        "firstdate": firstdate,
        "lastdate": lastdate,
    }
    try:
        response = requests.get(f"{SIETEWS_URL}?{urlencode(params)}", timeout=BCCH_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
    except requests.Timeout as exc:
        raise SieteWSError("Timeout consultando SieteWS.") from exc
    except requests.HTTPError as exc:
        raise SieteWSError(f"Error HTTP SieteWS: {response.status_code}") from exc
    except ValueError as exc:
        raise SieteWSError("Respuesta SieteWS no es JSON válido.") from exc
    except requests.RequestException as exc:
        raise SieteWSError(f"Error de red SieteWS: {sanitize_error(str(exc))}") from exc

    has_error, msg = _payload_error(payload)
    if has_error:
        raise SieteWSError(msg)

    rows: list[tuple[str, float]] = []
    for item in extract_obs(payload):
        date_value = item.get("indexDateString") or item.get("IndexDateString") or item.get("date") or item.get("fecha")
        raw_value = item.get("value") if "value" in item else item.get("valor", item.get("Value"))
        dt = parse_sietews_date(date_value)
        val = parse_sietews_value(raw_value)
        if pd.notna(dt) and pd.notna(val):
            rows.append((pd.Timestamp(dt).strftime("%Y-%m-%d"), float(val)))

    frame = pd.DataFrame(rows, columns=["fecha", "valor"])
    if frame.empty:
        return pd.DataFrame(columns=["fecha", "valor", "code"])
    frame["fecha"] = pd.to_datetime(frame["fecha"])
    frame["valor"] = pd.to_numeric(frame["valor"], errors="coerce")
    frame["code"] = code
    return frame.dropna(subset=["fecha", "valor"]).drop_duplicates(["fecha", "code"], keep="last").sort_values("fecha").reset_index(drop=True)


def normalize_series(df: pd.DataFrame, indicator: dict[str, Any]) -> pd.DataFrame:
    """Normaliza una serie al DataFrame estándar del monitor."""
    if df.empty:
        return pd.DataFrame(columns=[
            "fecha", "valor", "serie_id", "nombre_indicador", "categoria", "frecuencia",
            "unidad", "fuente", "fecha_actualizacion", "estado_fuente", "code"
        ])
    out = df.copy()
    out["serie_id"] = indicator["id"]
    out["nombre_indicador"] = indicator["name"]
    out["categoria"] = indicator["category"]
    out["frecuencia"] = indicator.get("frequency", "")
    out["unidad"] = indicator.get("unit", "")
    out["fuente"] = indicator.get("source", "BCCh")
    out["fecha_actualizacion"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    out["estado_fuente"] = "OK"
    out["code"] = indicator.get("code")
    for col in ["tenor_days"]:
        if col in indicator:
            out[col] = indicator[col]
    return out[[c for c in [
        "fecha", "valor", "serie_id", "nombre_indicador", "categoria", "frecuencia",
        "unidad", "fuente", "fecha_actualizacion", "estado_fuente", "code", "tenor_days"
    ] if c in out.columns]]


def fetch_indicator(indicator: dict[str, Any], firstdate: str, lastdate: str, credentials: Credentials) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Consulta un indicador y devuelve (datos_normalizados, diagnóstico)."""
    status = "OK"
    detail = ""
    code = indicator.get("code")
    if indicator.get("method") != "sietews" or not code or str(code).startswith("TODO"):
        status = "Pendiente de configuración" if str(code).startswith("TODO") else "Fuente no implementada"
        return pd.DataFrame(), {
            "serie_id": indicator["id"], "nombre_indicador": indicator["name"], "categoria": indicator["category"],
            "code": code, "estado_fuente": status, "detalle": indicator.get("notes", "No implementado."),
            "fuente": indicator.get("source", "")
        }
    try:
        raw = fetch_series_raw(str(code), firstdate, lastdate, credentials)
        if raw.empty:
            status = "Sin datos"
            detail = f"SieteWS respondió sin observaciones entre {firstdate} y {lastdate}."
            return pd.DataFrame(), {
                "serie_id": indicator["id"], "nombre_indicador": indicator["name"], "categoria": indicator["category"],
                "code": code, "estado_fuente": status, "detalle": detail, "fuente": indicator.get("source", "")
            }
        data = normalize_series(raw, indicator)
        return data, {
            "serie_id": indicator["id"], "nombre_indicador": indicator["name"], "categoria": indicator["category"],
            "code": code, "estado_fuente": "OK", "detalle": f"{len(data):,} observaciones", "fuente": indicator.get("source", "")
        }
    except InvalidCredentials:
        raise
    except Exception as exc:
        return pd.DataFrame(), {
            "serie_id": indicator["id"], "nombre_indicador": indicator["name"], "categoria": indicator["category"],
            "code": code, "estado_fuente": "Error API", "detalle": sanitize_error(str(exc)), "fuente": indicator.get("source", "")
        }


def fetch_many_indicators(indicators: list[dict[str, Any]], firstdate: str, lastdate: str, credentials: Credentials) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Consulta múltiples indicadores SieteWS en paralelo con diagnóstico por serie."""
    if credentials is None or not credentials.user or not credentials.password:
        raise MissingCredentials("Faltan credenciales SieteWS.")
    frames: list[pd.DataFrame] = []
    diagnostics: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=BCCH_MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_indicator, ind, firstdate, lastdate, credentials): ind for ind in indicators}
        for future in as_completed(futures):
            try:
                data, diag = future.result()
                if not data.empty:
                    frames.append(data)
                diagnostics.append(diag)
            except InvalidCredentials:
                raise
            except Exception as exc:
                ind = futures[future]
                diagnostics.append({
                    "serie_id": ind["id"], "nombre_indicador": ind["name"], "categoria": ind["category"],
                    "code": ind.get("code"), "estado_fuente": "Error API", "detalle": sanitize_error(str(exc)),
                    "fuente": ind.get("source", "")
                })

    data = pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame(columns=[
        "fecha", "valor", "serie_id", "nombre_indicador", "categoria", "frecuencia",
        "unidad", "fuente", "fecha_actualizacion", "estado_fuente", "code"
    ])
    diag = pd.DataFrame(diagnostics)
    if not diag.empty:
        diag = diag.sort_values(["categoria", "nombre_indicador"]).reset_index(drop=True)
    return data, diag
