from __future__ import annotations

import textwrap

import plotly.graph_objects as go

# Paleta institucional inspirada en tonos CMF: morados/azules profundos.
# La idea es NO copiar la paleta del Banco Central/SIID, pero mantener lectura ejecutiva.
CMF_PURPLE = "#3B1A63"
CMF_DARK = "#24113F"
CMF_LIGHT_PURPLE = "#EEE8F7"
CMF_GRID = "#D9D3E6"
CMF_TEXT = "#1D1630"
CMF_MUTED = "#6E6385"
CMF_PALETTE = [
    "#5B2A86",  # morado principal
    "#8A4FFF",  # violeta
    "#C77DFF",  # lila
    "#2D6CDF",  # azul de apoyo
    "#7B2CBF",  # morado medio
    "#B5179E",  # magenta sobrio
    "#4CC9F0",  # celeste contraste
    "#7209B7",  # violeta oscuro
    "#560BAD",  # violeta profundo
    "#A663CC",  # lila medio
]


def _wrap_title(title: str, width: int = 58) -> str:
    """Corta títulos largos para que no se pierdan dentro de columnas Streamlit."""
    if not title:
        return ""
    lines = textwrap.wrap(title, width=width, break_long_words=False, break_on_hyphens=False)
    return "<br>".join(lines[:2])


def _title_font_size(title: str) -> int:
    if len(title) > 88:
        return 11
    if len(title) > 68:
        return 12
    return 14

# Alias antiguos para no romper imports existentes.
SIID_BLUE = CMF_PURPLE
SIID_LIGHT_BLUE = CMF_LIGHT_PURPLE
SIID_GRID = CMF_GRID
SIID_TEXT = CMF_TEXT
SIID_MUTED = CMF_MUTED
SIID_PALETTE = CMF_PALETTE


def apply_siid_layout(
    fig: go.Figure,
    title: str,
    yaxis_title: str = "MM USD",
    unit: str | None = None,
    subtitle: str | None = None,
    source_note: str = "Fuente: Banco Central de Chile, BDE/SIID público.",
    height: int = 520,
    rotate_months: bool = True,
    show_header: bool = False,
) -> go.Figure:
    """Layout limpio para reporte.

    En v40 el título se renderiza fuera del gráfico con Streamlit/HTML.
    Plotly queda solo para el área de datos, ejes, leyenda y fuente.
    """
    fig.update_layout(
        template=None,
        height=height,
        hovermode="x unified",
        font={"family": "Arial, sans-serif", "size": 11, "color": CMF_TEXT},
        legend_title_text="",
        margin={"l": 78, "r": 120, "t": 34, "b": 185},
        paper_bgcolor="#0B1B4D",
        plot_bgcolor="#0F1E4A",
        colorway=CMF_PALETTE,
        uniformtext_minsize=9,
        uniformtext_mode="show",
    )

    for trace in fig.data:
        if hasattr(trace, "cliponaxis"):
            try:
                trace.update(cliponaxis=False)
            except Exception:
                pass

    fig.update_xaxes(
        title_text="Fecha",
        showgrid=False,
        tickangle=-90 if rotate_months else 0,
        tickformat="%b-%y",
        linecolor=CMF_GRID,
        mirror=False,
        zeroline=False,
        automargin=True,
    )
    fig.update_yaxes(
        title_text=yaxis_title,
        gridcolor=CMF_GRID,
        linecolor=CMF_GRID,
        separatethousands=True,
        tickformat=",.0f",
        exponentformat="none",
        showexponent="none",
        zerolinecolor=CMF_GRID,
        automargin=True,
    )

    # Opción de respaldo por si algún gráfico explícitamente pide header.
    if show_header:
        unit_display = unit or yaxis_title or ""
        wrapped_title = _wrap_title(title, width=62)
        fig.add_annotation(
            xref="paper",
            yref="paper",
            x=0,
            y=1.10,
            text=f"<b>{wrapped_title}</b>",
            showarrow=False,
            align="left",
            xanchor="left",
            font={"color": CMF_TEXT, "size": 13},
        )
        if unit_display:
            fig.add_annotation(
                xref="paper",
                yref="paper",
                x=0,
                y=1.02,
                text=f"Unidad: {unit_display}",
                showarrow=False,
                align="left",
                xanchor="left",
                font={"color": CMF_MUTED, "size": 10},
            )

    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=0,
        y=-0.56,
        text=source_note,
        showarrow=False,
        align="left",
        xanchor="left",
        font={"color": CMF_MUTED, "size": 9},
    )
    return fig

def empty_siid_figure(message: str = "Sin datos para graficar") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, x=0.5, y=0.5, showarrow=False, font={"size": 16, "color": CMF_MUTED})
    return apply_siid_layout(fig, "Sin datos", yaxis_title="", height=440)
