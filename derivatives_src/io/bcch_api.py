from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import requests


BCCH_ENDPOINT = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Credenciales internas para uso local del proyecto. No se muestran en la app.
DEFAULT_BCCH_USER = ""
DEFAULT_BCCH_PASS = ""


class BCCHAPIError(RuntimeError):
    """Error controlado para respuestas no exitosas de la API BDE."""


def _load_project_env() -> None:
    """No carga .env en Streamlit Cloud; las credenciales las inyecta la app principal."""
    return None


def _load_local_credentials() -> tuple[str, str]:
    """Lee credenciales desde src/local_credentials.py si existe.

    Es útil para depurar en ambiente local, pero no se debe versionar.
    """
    try:
        from derivatives_src.local_credentials import BCCH_PASS, BCCH_USER  # type: ignore

        return str(BCCH_USER).strip(), str(BCCH_PASS).strip()
    except Exception:
        return "", ""


@dataclass(frozen=True)
class BCCHClient:
    """Cliente REST simple para la API BDE del Banco Central de Chile.

    Usa GetSeries para obtener una serie y SearchSeries para bajar el catálogo.
    Las credenciales se pueden leer desde:
    1) src/local_credentials.py
    2) .env
    3) variables de entorno
    """

    user: str
    password: str
    endpoint: str = BCCH_ENDPOINT
    timeout: int = 60

    @staticmethod
    def resolve_credentials() -> tuple[str, str]:
        # Prioridad 1: credenciales internas pedidas para uso local.
        if DEFAULT_BCCH_USER and DEFAULT_BCCH_PASS:
            return DEFAULT_BCCH_USER.strip(), DEFAULT_BCCH_PASS.strip()

        # Prioridad 2: archivo local opcional.
        local_user, local_pass = _load_local_credentials()
        if local_user and local_pass:
            return local_user, local_pass

        # Prioridad 3: .env / variables de entorno.
        _load_project_env()
        user = os.getenv("BCCH_USER", "").strip()
        password = os.getenv("BCCH_PASS", "").strip()
        return user, password

    @classmethod
    def from_env(cls) -> "BCCHClient":
        user, password = cls.resolve_credentials()
        if not user or not password:
            raise BCCHAPIError(
                "Faltan credenciales internas BCCh."
            )
        return cls(user=user, password=password)

    def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        base_params = {"user": self.user, "pass": self.password}
        base_params.update(params)
        response = requests.get(self.endpoint, params=base_params, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        codigo = payload.get("Codigo")
        if codigo not in (0, "0", None):
            raise BCCHAPIError(f"Error API BCCh: {payload.get('Descripcion', payload)}")
        return payload

    def get_series(
        self,
        series_id: str,
        firstdate: str | None = None,
        lastdate: str | None = None,
    ) -> pd.DataFrame:
        """Baja una serie y retorna DataFrame con date, value, status_code, series_id."""
        if not series_id or pd.isna(series_id):
            raise ValueError("series_id vacío")

        params: dict[str, Any] = {
            "function": "GetSeries",
            "timeseries": series_id,
        }
        if firstdate:
            params["firstdate"] = firstdate
        if lastdate:
            params["lastdate"] = lastdate

        payload = self._get(params)
        series = payload.get("Series") or {}
        obs = series.get("Obs") or []
        df = pd.DataFrame(obs)
        if df.empty:
            return pd.DataFrame(columns=["date", "value", "status_code", "series_id"])

        df = df.rename(columns={"indexDateString": "date", "statusCode": "status_code"})
        df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
        df["value"] = df["value"].map(parse_bcch_number)
        df["series_id"] = series.get("seriesId", series_id)
        return df[["date", "value", "status_code", "series_id"]].sort_values("date")

    def search_series(self, frequency: str) -> pd.DataFrame:
        """Baja catálogo de series por frecuencia: DAILY, MONTHLY, QUARTERLY, ANNUAL."""
        frequency = frequency.upper().strip()
        payload = self._get({"function": "SearchSeries", "frequency": frequency})
        infos = payload.get("SeriesInfos") or []
        df = pd.DataFrame(infos)
        if df.empty:
            return pd.DataFrame()
        for col in ["firstObservation", "lastObservation", "updatedAt", "createdAt"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format="%d-%m-%Y", errors="coerce")
        return df

    def search_catalog_keywords(self, frequency: str, keywords: Iterable[str]) -> pd.DataFrame:
        """Filtra catálogo oficial por keywords sobre títulos español/inglés e ID."""
        catalog = self.search_series(frequency)
        if catalog.empty:
            return catalog
        kw = [k.lower().strip() for k in keywords if k.strip()]
        text = (
            catalog.get("spanishTitle", pd.Series(index=catalog.index, dtype=str)).fillna("")
            + " "
            + catalog.get("englishTitle", pd.Series(index=catalog.index, dtype=str)).fillna("")
            + " "
            + catalog.get("seriesId", pd.Series(index=catalog.index, dtype=str)).fillna("")
        ).str.lower()
        mask = pd.Series(True, index=catalog.index)
        for term in kw:
            mask &= text.str.contains(term, regex=False)
        return catalog.loc[mask].copy()


def parse_bcch_number(value: Any) -> float:
    """Parsea números de BDE.

    La API normalmente entrega strings numéricos. Se limpian valores tipo NeuN/ND.
    No se eliminan puntos por defecto porque muchas series usan punto decimal.
    """
    if value is None:
        return float("nan")
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if text in {"", "NeuN", "NaN", "nan", "ND", "N.D.", "S/I"}:
        return float("nan")
    text = text.replace(" ", "")
    # Si viene con coma decimal chilena, convertir a punto decimal.
    # Si viene con coma y punto, asumimos punto miles y coma decimal.
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return float("nan")


def save_catalog(client: BCCHClient, frequencies: list[str], out_dir: str | Path) -> list[Path]:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for freq in frequencies:
        df = client.search_series(freq)
        file_path = out_path / f"catalog_{freq.upper()}.csv"
        df.to_csv(file_path, index=False, encoding="utf-8-sig")
        paths.append(file_path)
    return paths
