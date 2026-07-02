from __future__ import annotations

import pandas as pd
import streamlit as st


def show_table(df: pd.DataFrame, title: str | None = None, height: int | str = "content") -> None:
    """Muestra tablas sin romper en Streamlit Cloud >=1.58.

    Streamlit 1.58 no acepta height nulo y recomienda width="stretch"
    en reemplazo de width="stretch".
    """
    if title:
        st.markdown(f"#### {title}")
    if df is None or df.empty:
        st.info("Sin datos para mostrar.")
        return
    safe_height = height if height is not None else "content"
    st.dataframe(df, width="stretch", hide_index=True, height=safe_height)
