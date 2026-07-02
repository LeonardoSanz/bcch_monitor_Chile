from __future__ import annotations

import pandas as pd


def fetch_ine_series(*args, **kwargs) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Placeholder para fuentes INE directas.

    Muchas series INE relevantes ya se consumen indirectamente vía BDE/BCCh.
    """
    diag = pd.DataFrame([{"estado_fuente": "Fuente no implementada", "detalle": "Cliente INE directo pendiente."}])
    return pd.DataFrame(), diag
