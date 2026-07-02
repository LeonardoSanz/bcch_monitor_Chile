from __future__ import annotations

import pandas as pd


def fetch_cmf_series(*args, **kwargs) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Placeholder para fuentes CMF.

    El módulo existe para mantener arquitectura escalable. No se implementa scraping ni APIs
    no confirmadas en esta versión.
    """
    diag = pd.DataFrame([{"estado_fuente": "Fuente no implementada", "detalle": "Cliente CMF pendiente de implementación."}])
    return pd.DataFrame(), diag
