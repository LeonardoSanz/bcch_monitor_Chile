from __future__ import annotations

import math
import pandas as pd


def fmt_date(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    return pd.to_datetime(value).strftime("%Y-%m-%d")


def fmt_number(value, decimals: int = 2, suffix: str = "") -> str:
    if value is None or pd.isna(value):
        return "—"
    try:
        val = float(value)
    except Exception:
        return "—"
    if abs(val) >= 1_000_000:
        text = f"{val/1_000_000:,.{decimals}f}MM"
    elif abs(val) >= 1_000:
        text = f"{val:,.{decimals}f}"
    else:
        text = f"{val:,.{decimals}f}"
    return f"{text}{suffix}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_delta(value, suffix: str = "%", decimals: int = 2) -> str:
    if value is None or pd.isna(value):
        return "—"
    sign = "+" if float(value) >= 0 else ""
    return f"{sign}{fmt_number(value, decimals, suffix)}"


def signal_color(status: str) -> str:
    return {
        "verde": "#22C55E",
        "amarillo": "#FACC15",
        "rojo": "#FB7185",
        "gris": "#94A3B8",
    }.get(str(status).lower(), "#94A3B8")


def source_status_color(status: str) -> str:
    status = str(status)
    if status == "OK":
        return "verde"
    if status in {"Sin datos", "Pendiente de configuración", "Fuente no implementada"}:
        return "gris"
    if status in {"Credenciales inválidas", "Error API"}:
        return "rojo"
    return "amarillo"
