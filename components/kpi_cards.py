from __future__ import annotations

import html
import pandas as pd
import streamlit as st

from utils.formatting import fmt_date, fmt_delta, fmt_number, signal_color


def kpi_card_html(title: str, value: str, date: str, delta: str, unit: str, source: str, status: str, message: str) -> str:
    """HTML compacto de una card KPI.

    Importante: se devuelve en una sola línea para evitar que Markdown/Streamlit
    lo interprete como bloque de código cuando hay varias cards concatenadas.
    """
    color = signal_color(status)
    title = html.escape(str(title))
    value = html.escape(str(value))
    date = html.escape(str(date))
    delta = html.escape(str(delta))
    unit = html.escape(str(unit))
    source = html.escape(str(source))
    status = html.escape(str(status))
    message = html.escape(str(message))
    return (
        f'<div class="kpi-card" style="border-left: 5px solid {color};">'
        f'<div class="kpi-top"><span class="kpi-title">{title}</span>'
        f'<span class="kpi-status" style="color:{color};">● {status}</span></div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-meta">{unit} · {source} · último dato {date}</div>'
        f'<div class="kpi-delta">Dato previo: {delta}</div>'
        f'<div class="kpi-message">{message}</div>'
        f'</div>'
    )


def render_kpi_grid(latest: pd.DataFrame, signals: pd.DataFrame, ids: list[str], columns: int = 4) -> None:
    if latest is None or latest.empty:
        st.info("No hay datos para KPIs.")
        return

    cards: list[str] = []
    for sid in ids:
        rowdf = latest[latest["serie_id"].eq(sid)]
        if rowdf.empty:
            continue
        row = rowdf.iloc[-1]
        sig = None
        if signals is not None and not signals.empty and "serie_id" in signals.columns:
            s = signals[signals["serie_id"].eq(sid)]
            if not s.empty:
                sig = s.iloc[0]
        status = sig["estado"] if sig is not None else "gris"
        message = sig["mensaje"] if sig is not None else "Sin señal"
        suffix = "%" if str(row.get("unidad", "")) == "%" else ""
        value = fmt_number(row.get("valor"), 2, suffix)
        delta = fmt_delta(row.get("var_abs"), "", 2)
        cards.append(kpi_card_html(
            title=str(row.get("nombre_indicador", sid)),
            value=value,
            date=fmt_date(row.get("fecha")),
            delta=delta,
            unit=str(row.get("unidad", "")),
            source=str(row.get("fuente", "")),
            status=status,
            message=message,
        ))

    if not cards:
        st.info("No hay KPIs con datos para esta selección.")
        return

    st.markdown('<div class="kpi-grid">' + "".join(cards) + '</div>', unsafe_allow_html=True)
