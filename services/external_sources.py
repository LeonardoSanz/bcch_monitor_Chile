from __future__ import annotations

import pandas as pd


def fetch_external_indicator(indicator: dict, start: str, end: str) -> tuple[pd.DataFrame, dict]:
    """Placeholder para fuentes externas no BCCh."""
    return pd.DataFrame(), {
        "serie_id": indicator.get("id"),
        "nombre_indicador": indicator.get("name"),
        "categoria": indicator.get("category"),
        "code": indicator.get("code"),
        "estado_fuente": "Fuente no implementada",
        "detalle": indicator.get("notes", "Fuente externa pendiente."),
        "fuente": indicator.get("source", ""),
    }
