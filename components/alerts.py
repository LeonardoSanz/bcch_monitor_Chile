from __future__ import annotations

import pandas as pd
import streamlit as st

from components.tables import show_table


def render_alerts(signals: pd.DataFrame, title: str = "Alertas activas") -> None:
    if signals.empty:
        st.info("Sin señales disponibles.")
        return
    active = signals[signals["estado"].isin(["rojo", "amarillo"])].copy()
    if active.empty:
        st.success("No hay alertas rojas o amarillas activas.")
        return
    cols = ["estado", "indicador", "categoria", "mensaje", "explicacion", "metrica_gatillante", "recomendacion_analitica"]
    show_table(active[cols], title)
