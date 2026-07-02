from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path
import base64

import pandas as pd
import streamlit as st

from components.alerts import render_alerts
try:
    from components.derivatives_section import render_derivatives_module
except Exception as _deriv_import_exc:
    def render_derivatives_module(start, end, user, password):
        st.error(
            "El módulo de derivados no está disponible completo. "
            "Sube el proyecto completo, incluyendo components/derivatives_section.py, "
            "derivatives_src/ y derivatives_app/config/. "
            f"Detalle: {_deriv_import_exc}"
        )
        return {"derivados_error": pd.DataFrame({"error": [str(_deriv_import_exc)]})}
from components.charts import bar_variation_chart, curve_chart, dual_axis_chart, heatmap_signals, signals_summary_chart, line_chart, scatter_chart, tpm_step_chart_clean, eee_expectations_chart_clean, eee_snapshot_chart_clean, eee_gap_to_tpm_chart_clean, latest_curve_clean, variation_bars_clean, coverage_table_for_ids, gap_windows_for_ids, coverage_by_year_for_ids
from components.kpi_cards import render_kpi_grid
from components.tables import show_table
from config.indicators import CATEGORIES, all_indicators, implemented_indicators, indicator_map, indicators_dataframe, pending_indicators
from config.settings import APP_NAME, APP_VERSION, CACHE_TTL_SECONDS, COLORS, DEFAULT_START, RANGE_PRESETS, FREQUENCIES
from services.bcch_client import Credentials, InvalidCredentials, MissingCredentials, fetch_many_indicators
from utils.dates import preset_to_dates, to_bcch_date
from utils.formatting import fmt_date
from utils.signals import automatic_reading, generate_all_signals, market_state, generate_signal
from utils.transformations import add_transformations, build_derived_indicators, latest_by_indicator, resample_data
from utils.validation import build_health_table

ROOT = Path(__file__).resolve().parent
LOGO_PATH = ROOT / "assets" / "cmf_logo.png"

st.set_page_config(page_title=APP_NAME, page_icon="📈", layout="wide", initial_sidebar_state="collapsed")


def logo_html() -> str:
    if LOGO_PATH.exists():
        encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode("utf-8")
        return f'<img src="data:image/png;base64,{encoded}" class="cmf-logo-img" />'
    return '<div class="cmf-logo-fallback">CMF</div>'


def inject_css() -> None:
    """Inyecta CSS sin f-string para evitar NameError por llaves CSS."""
    css = """
    <style>
    :root {
        --cmf-bg: __BG__;
        --cmf-panel: __PANEL__;
        --cmf-panel-2: __PANEL2__;
        --cmf-text: __TEXT__;
        --cmf-muted: __MUTED__;
        --cmf-primary: __PRIMARY__;
    }
    .stApp { background: radial-gradient(circle at top right, #1a2386 0%, var(--cmf-bg) 34%, #03133D 100%); color: var(--cmf-text); }
    section[data-testid="stSidebar"] { display: none !important; }
    button[kind="header"] { display: none !important; }
    .block-container { padding-top: 1.4rem; padding-bottom: 2.5rem; max-width: 100% !important; width: 100% !important; padding-left: 2.0rem; padding-right: 2.0rem; }
    .cmf-header { width: 100%; padding: 1.35rem 1.4rem; border-radius: 1.2rem; border: 1px solid rgba(255,255,255,.12); background: linear-gradient(135deg, rgba(8,27,69,.96), rgba(10,42,102,.86)); box-shadow: 0 18px 42px rgba(0,0,0,.22); margin-bottom: 1rem; }
    .cmf-logo-img { width: 15rem; max-width: 42vw; display:block; margin-bottom: .8rem; background: transparent; }
    .cmf-logo-fallback { font-size: 3rem; font-weight: 950; color: white; letter-spacing: -.06em; margin-bottom: .7rem; }
    .cmf-title { font-size: 2.35rem; font-weight: 950; line-height: 1.05; letter-spacing: -.045em; }
    .cmf-subtitle { color: var(--cmf-muted); margin-top: .35rem; font-size: .98rem; }
    .control-shell { margin: .8rem 0 1.0rem; padding: 1rem; border-radius: 1rem; border: 1px solid rgba(255,255,255,.12); background: rgba(8,27,69,.86); }
    .status-row { display:flex; flex-wrap:wrap; gap:.55rem; margin-bottom:.75rem; }
    .status-pill { border:1px solid rgba(255,255,255,.13); background:rgba(255,255,255,.055); color:var(--cmf-muted); padding:.35rem .6rem; border-radius:999px; font-size:.78rem; font-weight:800; }
    .section-title { margin-top: 1rem; margin-bottom: .65rem; padding:.85rem 1rem; border:1px solid rgba(255,255,255,.13); border-left:5px solid var(--cmf-primary); border-radius:.8rem; background:rgba(8,27,69,.82); font-weight:900; font-size:1.08rem; }
    .chart-title { margin-top:.9rem; padding:.7rem .85rem; border:1px solid rgba(255,255,255,.12); border-left:5px solid var(--cmf-primary); border-radius:.75rem .75rem 0 0; background:rgba(8,27,69,.84); font-weight:900; }
    .kpi-grid { display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap:.75rem; margin:.8rem 0 1rem; }
    .kpi-card { min-height: 148px; border-radius: .9rem; border:1px solid rgba(255,255,255,.13); background:linear-gradient(180deg, rgba(8,27,69,.96), rgba(11,42,102,.72)); padding:.85rem .9rem; box-shadow: 0 14px 30px rgba(0,0,0,.18); }
    .kpi-top { display:flex; justify-content:space-between; gap:.5rem; align-items:start; }
    .kpi-title { font-size:.77rem; text-transform:uppercase; letter-spacing:.04em; color:var(--cmf-muted); font-weight:950; }
    .kpi-status { font-size:.72rem; font-weight:900; white-space:nowrap; }
    .kpi-value { font-size:1.72rem; font-weight:950; margin-top:.55rem; letter-spacing:-.03em; }
    .kpi-meta,.kpi-delta { color:var(--cmf-muted); font-size:.78rem; margin-top:.25rem; }
    .kpi-message { color:var(--cmf-text); font-size:.78rem; margin-top:.45rem; }
    .reading-box { border:1px solid rgba(255,255,255,.12); border-radius:1rem; background:rgba(8,27,69,.72); padding:1rem 1.2rem; margin:.8rem 0; }
    .muted-note { color:var(--cmf-muted); font-size:.86rem; line-height:1.45; }
    [data-testid="stPlotlyChart"] { background: var(--cmf-panel); border-radius: 0 0 .75rem .75rem; overflow:hidden; }
    div[data-testid="stTabs"] button {
        border: 1px solid rgba(255,255,255,.20) !important;
        background: rgba(8,27,69,.72) !important;
        border-radius: .65rem .65rem 0 0 !important;
        padding: .82rem 1rem !important;
        font-weight: 900 !important;
    }
    div[data-testid="stTabs"] button[aria-selected="true"] {
        background: linear-gradient(135deg, #8B3DFF, #5b7cfa) !important;
        color: white !important;
    }
    div[data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap: .45rem !important;
        border-bottom: 1px solid rgba(255,255,255,.18);
    }
    .clean-caption { color: var(--cmf-muted); font-size: .84rem; margin: .35rem 0 .8rem 0; }
    @media (max-width: 1100px) { .kpi-grid { grid-template-columns: repeat(2, minmax(0,1fr)); } .cmf-title { font-size: 1.8rem; } }
    @media (max-width: 720px) { .kpi-grid { grid-template-columns: 1fr; } }
    
    /* Radios horizontales usados como menú tipo tabs en Derivados */
    div[role="radiogroup"] {
        gap: .45rem;
    }
    div[role="radiogroup"] label {
        background: rgba(8,27,69,.72) !important;
        border: 1px solid rgba(255,255,255,.22) !important;
        border-radius: .65rem .65rem 0 0 !important;
        padding: .70rem .95rem !important;
        margin-right: .35rem !important;
        min-height: 2.4rem !important;
        font-weight: 900 !important;
    }
    div[role="radiogroup"] label:has(input:checked) {
        background: linear-gradient(135deg, #8B3DFF, #5b7cfa) !important;
        color: white !important;
    }

    
    
    /* Derivados: radios como tabs visibles */
    div[role="radiogroup"] label,
    div[role="radiogroup"] label * {
        visibility: visible !important;
        opacity: 1 !important;
        color: var(--cmf-text) !important;
    }
    div[role="radiogroup"] label p {
        font-weight: 900 !important;
        margin: 0 !important;
        white-space: nowrap !important;
    }
    div[role="radiogroup"] label:has(input:checked) p,
    div[role="radiogroup"] label:has(input:checked) span {
        color: #FFFFFF !important;
    }

    </style>
    """
    css = (css
        .replace("__BG__", COLORS["bg"])
        .replace("__PANEL__", COLORS["panel"])
        .replace("__PANEL2__", COLORS["panel_2"])
        .replace("__TEXT__", COLORS["text"])
        .replace("__MUTED__", COLORS["muted"])
        .replace("__PRIMARY__", COLORS["primary"]))
    st.markdown(css, unsafe_allow_html=True)


def get_credentials() -> Credentials | None:
    user = st.session_state.get("bcch_user")
    password = st.session_state.get("bcch_pass")
    if user and password:
        return Credentials(user=str(user), password=str(password))
    return None


def clear_credentials() -> None:
    for key in ["bcch_user", "bcch_pass", "monitor_cache_token"]:
        st.session_state.pop(key, None)


def render_login() -> None:
    st.markdown(f"""
    <div class="cmf-header" style="max-width:880px; margin:5rem auto 1rem;">
        {logo_html()}
        <div class="cmf-title">Monitor Mercado Chile</div>
        <div class="cmf-subtitle">Ingresa tus credenciales SieteWS del Banco Central. No se guardan en archivos ni se suben a GitHub.</div>
    </div>
    """, unsafe_allow_html=True)
    with st.form("login_sietews"):
        user = st.text_input("Usuario SieteWS", placeholder="usuario@dominio.cl")
        password = st.text_input("Clave SieteWS", type="password")
        submitted = st.form_submit_button("Ingresar", width="stretch")
    if submitted:
        if not user or not password:
            st.error("Debes ingresar usuario y clave SieteWS.")
            st.stop()
        st.session_state["bcch_user"] = user.strip()
        st.session_state["bcch_pass"] = password
        st.rerun()


def render_hero(creds: Credentials) -> None:
    st.markdown(f"""
    <div class="cmf-header">
        {logo_html()}
        <div class="cmf-title">División de Riesgo Financiero - DR</div>
        <div class="cmf-subtitle">Monitor Mercado Chile · indicadores macrofinancieros, señales y calidad de datos vía SieteWS · <b>{APP_VERSION}</b></div>
    </div>
    """, unsafe_allow_html=True)


def section_title(title: str) -> None:
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def chart_title(title: str, subtitle: str = "") -> None:
    extra = f'<div class="muted-note">{subtitle}</div>' if subtitle else ""
    st.markdown(f'<div class="chart-title">{title}{extra}</div>', unsafe_allow_html=True)


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def cached_load(user: str, _password: str, start: str, end: str, indicator_ids: tuple[str, ...], cache_token: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    ids = set(indicator_ids)
    indicators = [i for i in all_indicators() if i["id"] in ids]
    data, diag = fetch_many_indicators(indicators, start, end, Credentials(user=user, password=_password))
    data = build_derived_indicators(data)
    data = add_transformations(data)
    return data, diag


def make_excel(sheets: dict[str, pd.DataFrame]) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, df in sheets.items():
            safe_name = str(name)[:31].replace("/", "_")
            (df if df is not None else pd.DataFrame()).to_excel(writer, sheet_name=safe_name, index=False)
    return output.getvalue()


def top_controls(creds: Credentials, catalog_df: pd.DataFrame) -> tuple[date, date, list[str], str, dict]:
    """Controles limpios tipo Monitor AFP: sin multiselect gigante ni categorías pendientes."""
    st.markdown('<div class="control-shell">', unsafe_allow_html=True)
    implemented_count = int((catalog_df["method"].eq("sietews")).sum()) if "method" in catalog_df.columns else len(catalog_df)
    st.markdown(f"""
    <div class="status-row">
        <span class="status-pill">SieteWS activo</span>
        <span class="status-pill">Usuario SieteWS: activo</span>
        <span class="status-pill">Indicadores implementados: {implemented_count}</span>
        <span class="status-pill">Solo series con código confirmado</span>
        <span class="status-pill">Sin fallback HTML</span>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns([1.0, 1.0, 1.0, 1.0, 1.15], gap="large")
    with c1:
        preset = st.selectbox("Rango", ["6M", "1Y", "3Y", "5Y", "Máximo", "Personalizado"], index=3)
    default_start, default_end = preset_to_dates(preset)
    with c2:
        frequency = st.selectbox("Frecuencia", ["Original", "Mensual", "Trimestral"], index=0)
    with c3:
        show_ma = st.checkbox("Medias móviles", value=True)
    with c4:
        show_signals = st.checkbox("Señales", value=True)
    with c5:
        if st.button("Recargar datos", width="stretch"):
            st.session_state["monitor_cache_token"] = st.session_state.get("monitor_cache_token", 0) + 1
            st.cache_data.clear()
            st.rerun()

    if preset == "Personalizado":
        d1, d2, d3 = st.columns([1, 1, 3])
        with d1:
            start = st.date_input("Fecha inicio", value=DEFAULT_START)
        with d2:
            end = st.date_input("Fecha fin", value=date.today())
    else:
        start, end = default_start, default_end
        st.markdown(f'<div class="clean-caption">Rango aplicado: <b>{start}</b> → <b>{end}</b>. Se cargan solo indicadores implementados, nada pendiente/TODO.</div>', unsafe_allow_html=True)

    cA, cB = st.columns([1, 4])
    with cA:
        if st.button("Cerrar sesión", width="stretch"):
            clear_credentials()
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    selected_ids = [
        "usdclp", "euroclp", "mer", "mer5", "merx",
        "uf", "utm", "ipc_mensual", "ipc_anual",
        "tpm", "tib", "spc_90d", "spc_180d", "spc_360d", "bcp_2y", "bcp_5y", "bcp_10y", "bcu_1y", "bcu_2y", "bcu_5y", "bcu_10y", "bcu_20y", "bcu_30y",
        "imacec_total", "imacec_no_minero", "imacec_mineria", "imacec_comercio", "imacec_servicios", "pib_trimestral",
        "desempleo", "ocupados", "asalariados", "fuerza_trabajo",
        "cobre", "oro", "plata", "ipsa",
        "reservas_internacionales", "us10y", "fed_funds_proxy",
        "eee_ipc_12m", "eee_tpm_11m", "eee_tpm_23m", "eof_ipc_12m", "eof_tpm_12m",
        "deuda_publica_pib",
    ]
    implemented = {i["id"] for i in implemented_indicators(load_default_only=True)}
    selected_ids = [sid for sid in selected_ids if sid in implemented]
    opts = {"show_var": True, "show_ma": show_ma, "show_signals": show_signals, "normalize": False, "log_y": False}
    return start, end, selected_ids, frequency, opts


def empty_market_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "fecha", "valor", "serie_id", "nombre_indicador", "categoria", "frecuencia",
        "unidad", "fuente", "fecha_actualizacion", "estado_fuente", "code"
    ])


def filter_data(df: pd.DataFrame, ids: list[str], frequency: str) -> pd.DataFrame:
    """Filtra, remuestrea y recalcula transformaciones sin caerse si df viene vacío."""
    if df is None or df.empty or "serie_id" not in df.columns:
        return empty_market_frame()

    keep_ids = ids + ["tasa_real_ex_post", "pendiente_nominal", "pendiente_uf"]
    out = df[df["serie_id"].isin(keep_ids)].copy() if ids else df.copy()

    if out.empty:
        return empty_market_frame()

    try:
        out = resample_data(out, frequency)
    except Exception:
        # Si falla el remuestreo, continuamos con frecuencia original.
        out = out.copy()

    try:
        out = add_transformations(out) if not out.empty else out
    except Exception:
        # Si falla una transformación puntual, seguimos con datos base.
        out = out.copy()

    return out if not out.empty else empty_market_frame()


def render_resumen(data: pd.DataFrame, indicators: list[dict], signals: pd.DataFrame, opts: dict) -> dict[str, pd.DataFrame]:
    section_title("Resumen Mercado Chile")
    latest = latest_by_indicator(data)
    summary_ids = [i["id"] for i in indicators if i.get("summary")] + ["tasa_real_ex_post", "pib_trimestral"]
    summary_ids = list(dict.fromkeys(summary_ids))
    render_kpi_grid(latest, signals, summary_ids)
    state, state_msg = market_state(signals)
    bullets = automatic_reading(signals)
    st.markdown('<div class="reading-box">', unsafe_allow_html=True)
    st.markdown(f"### Lectura del mercado: **{state.upper()}**")
    st.caption(state_msg)
    for bullet in bullets:
        st.markdown(f"- {bullet}")
    st.markdown('</div>', unsafe_allow_html=True)

    if opts.get("show_signals"):
        render_alerts(signals.head(8), "Principales alertas activas")

    c1, c2 = st.columns(2, gap="large")
    with c1:
        chart_title("USD/CLP vs cobre", "Doble eje, datos SieteWS")
        st.plotly_chart(dual_axis_chart(data, "usdclp", data, "cobre", "USD/CLP", "Cobre USD/libra"), width="stretch", key="res_usd_cobre")
    with c2:
        chart_title("IPSA", "Nivel con medias móviles si aplica")
        st.plotly_chart(line_chart(data, ["ipsa"], show_ma=opts.get("show_ma"), normalize=opts.get("normalize"), log_y=opts.get("log_y")), width="stretch", key="res_ipsa")
    c3, c4 = st.columns(2, gap="large")
    with c3:
        chart_title("IMACEC total", "Actividad económica")
        st.plotly_chart(line_chart(data, ["imacec_total"], normalize=opts.get("normalize")), width="stretch", key="res_imacec")
    with c4:
        chart_title("TPM vs IPC anual", "Política monetaria e inflación")
        st.plotly_chart(dual_axis_chart(data, "tpm", data, "ipc_anual", "TPM %", "IPC anual %"), width="stretch", key="res_tpm_ipc")

    c5, c6 = st.columns(2, gap="large")
    with c5:
        chart_title("PIB trimestral", "Actividad económica trimestral")
        st.plotly_chart(line_chart(data, ["pib_trimestral"], normalize=opts.get("normalize")), width="stretch", key="res_pib_trimestral")
    with c6:
        chart_title("Tasa de desocupación", "Mercado laboral")
        st.plotly_chart(line_chart(data, ["desempleo"], normalize=opts.get("normalize")), width="stretch", key="res_desempleo")
    chart_title("Heatmap de señales", "Conteo de semáforos por categoría")
    st.plotly_chart(heatmap_signals(signals), width="stretch", key="res_heatmap")
    return {"datos_filtrados": data, "resumen_kpis": latest, "senales": signals}


def render_category(category: str, data: pd.DataFrame, indicators: list[dict], signals: pd.DataFrame, opts: dict) -> dict[str, pd.DataFrame]:
    section_title(category)
    cat_inds = [i for i in indicators if i["category"] == category]
    ids = [i["id"] for i in cat_inds]
    cat_data = data[data["serie_id"].isin(ids + ["tasa_real_ex_post", "pendiente_nominal", "pendiente_uf"])]
    pending = pd.DataFrame([i for i in pending_indicators() if i["category"] == category])
    st.markdown(f'<div class="muted-note">Indicadores implementados en la sección: <b>{len(ids)}</b>. Pendientes explícitos: <b>{len(pending)}</b>.</div>', unsafe_allow_html=True)
    render_kpi_grid(latest_by_indicator(cat_data), signals, ids[:8])
    if opts.get("show_signals"):
        render_alerts(signals[signals["categoria"].eq(category)], f"Señales asociadas · {category}")

    if category == "Tipo de cambio":
        chart_title("USD/CLP nivel con medias móviles", "Variación diaria, 7 y 30 días disponibles en tabla")
        st.plotly_chart(line_chart(cat_data, ["usdclp"], show_ma=opts.get("show_ma"), normalize=opts.get("normalize"), log_y=opts.get("log_y")), width="stretch", key="tc_usd")
        chart_title("USD/CLP vs cobre", "Doble eje")
        st.plotly_chart(dual_axis_chart(data, "usdclp", data, "cobre", "USD/CLP", "Cobre"), width="stretch", key="tc_cobre")
        chart_title("MER / MER-5 / MER-X", "Índices de tipo de cambio multilateral")
        st.plotly_chart(line_chart(cat_data, ["mer", "mer5", "merx"], normalize=opts.get("normalize")), width="stretch", key="tc_mer")
        chart_title("Variación 30 días", "Indicadores FX")
        st.plotly_chart(bar_variation_chart(cat_data, ["usdclp", "euroclp"], "var_30d_pct"), width="stretch", key="tc_var30")
    elif category == "Inflación y reajustes":
        chart_title("IPC mensual e IPC anual", "Inflación")
        st.plotly_chart(line_chart(cat_data, ["ipc_mensual", "ipc_anual"], normalize=False), width="stretch", key="inf_ipc")
        chart_title("UF diaria", "Unidad de Fomento")
        st.plotly_chart(line_chart(cat_data, ["uf"], show_ma=opts.get("show_ma")), width="stretch", key="inf_uf")
        chart_title("TPM vs inflación anual", "Doble eje")
        st.plotly_chart(dual_axis_chart(data, "tpm", data, "ipc_anual", "TPM %", "IPC anual %"), width="stretch", key="inf_tpm_ipc")
        chart_title("Tasa real aproximada", "TPM menos inflación anual")
        st.plotly_chart(line_chart(data, ["tasa_real_ex_post"], normalize=False), width="stretch", key="inf_real")
    elif category == "Tasas y renta fija":
        chart_title("TPM histórica", "Tasa política monetaria")
        st.plotly_chart(line_chart(cat_data, ["tpm"], show_ma=False), width="stretch", key="tasas_tpm")
        c1, c2 = st.columns(2)
        with c1:
            chart_title("Curva nominal", "Último dato por plazo")
            st.plotly_chart(curve_chart(cat_data, ["spc_90d", "spc_180d", "spc_360d", "bcp_2y", "bcp_5y", "bcp_10y"], "Curva nominal"), width="stretch", key="tasas_curva_nom")
        with c2:
            chart_title("Curva UF", "Último dato por plazo")
            st.plotly_chart(curve_chart(cat_data, ["bcu_1y", "bcu_2y", "bcu_5y", "bcu_10y", "bcu_20y", "bcu_30y"], "Curva UF"), width="stretch", key="tasas_curva_uf")
        chart_title("Pendientes de curva", "10Y - 2Y")
        st.plotly_chart(line_chart(data, ["pendiente_nominal", "pendiente_uf"], normalize=False), width="stretch", key="tasas_pendiente")
    elif category == "Commodities":
        chart_title("Cobre, oro y plata", "Niveles o base 100")
        st.plotly_chart(line_chart(cat_data, ["cobre", "oro", "plata"], normalize=opts.get("normalize"), log_y=opts.get("log_y")), width="stretch", key="comm_line")
        chart_title("Cobre vs USD/CLP", "Relación visual")
        st.plotly_chart(dual_axis_chart(data, "cobre", data, "usdclp", "Cobre", "USD/CLP"), width="stretch", key="comm_fx")
    elif category == "Bolsa local":
        chart_title("IPSA con medias móviles", "Señal técnica")
        st.plotly_chart(line_chart(cat_data, ["ipsa"], show_ma=opts.get("show_ma"), normalize=opts.get("normalize"), log_y=opts.get("log_y")), width="stretch", key="bolsa_ipsa")
        chart_title("IPSA vs cobre", "Doble eje")
        st.plotly_chart(dual_axis_chart(data, "ipsa", data, "cobre", "IPSA", "Cobre"), width="stretch", key="bolsa_cobre")
        chart_title("IPSA vs USD/CLP", "Doble eje")
        st.plotly_chart(dual_axis_chart(data, "ipsa", data, "usdclp", "IPSA", "USD/CLP"), width="stretch", key="bolsa_fx")
    else:
        chart_title(f"Evolución · {category}", "Indicadores disponibles")
        st.plotly_chart(line_chart(cat_data, ids, show_ma=opts.get("show_ma"), normalize=opts.get("normalize"), log_y=opts.get("log_y")), width="stretch", key=f"cat_{category}")

    show_table(cat_data.sort_values(["serie_id", "fecha"]).tail(500), f"Datos · {category}", height=420)
    if not pending.empty:
        show_table(pending[["id", "name", "source", "code", "method", "notes"]], f"Pendientes/TODO · {category}")
    return {"datos_categoria": cat_data, "senales_categoria": signals[signals["categoria"].eq(category)], "pendientes": pending}



def render_tasas_clean(data: pd.DataFrame, opts: dict) -> dict[str, pd.DataFrame]:
    section_title("Tasas y renta fija")
    st.markdown('<div class="muted-note">Recuperamos la vista validada: TPM efectiva, expectativas EEE/EOF, curva nominal, curva UF, interbancario y spreads. La pendiente 10Y-2Y es la diferencia entre tasa larga y corta; se usa para mirar empinamiento o inversión de la curva.</div>', unsafe_allow_html=True)

    df_tpm = data[data["serie_id"].isin(["tpm", "eee_tpm_11m", "eee_tpm_23m", "eof_tpm_12m"])].copy()
    df_nom = data[data["serie_id"].isin(["spc_90d", "spc_180d", "spc_360d", "bcp_2y", "bcp_5y", "bcp_10y"])].copy()
    df_uf = data[data["serie_id"].isin(["bcu_1y", "bcu_2y", "bcu_5y", "bcu_10y", "bcu_20y", "bcu_30y"])].copy()
    df_inter = data[data["serie_id"].isin(["tib"])].copy()
    df_spreads = data[data["serie_id"].isin(["pendiente_nominal", "pendiente_uf"])].copy()

    tabs = st.tabs(["TPM y expectativas", "Curva nominal", "Curva UF", "Interbancario", "Spreads técnicos"])

    with tabs[0]:
        chart_title("TPM efectiva", "% · serie diaria tipo escalón")
        st.plotly_chart(tpm_step_chart_clean(df_tpm), width="stretch", key="tasas_clean_tpm")
        c1, c2 = st.columns(2, gap="large")
        with c1:
            chart_title("Expectativas de TPM", "% · horizontes disponibles")
            st.plotly_chart(eee_expectations_chart_clean(df_tpm), width="stretch", key="tasas_clean_eee")
        with c2:
            chart_title("Snapshot TPM vs expectativas", "% · último dato disponible")
            st.plotly_chart(eee_snapshot_chart_clean(df_tpm), width="stretch", key="tasas_clean_snapshot")
        chart_title("Brecha expectativas - TPM", "Puntos base")
        st.plotly_chart(eee_gap_to_tpm_chart_clean(df_tpm), width="stretch", key="tasas_clean_gap")

    with tabs[1]:
        c1, c2 = st.columns(2, gap="large")
        with c1:
            chart_title("Curva nominal · último dato", "%")
            st.plotly_chart(latest_curve_clean(df_nom, ["spc_90d", "spc_180d", "spc_360d", "bcp_2y", "bcp_5y", "bcp_10y"], "Curva nominal"), width="stretch", key="tasas_clean_curva_nom")
        with c2:
            chart_title("Variación de tasas nominales", "pb vs dato previo")
            st.plotly_chart(variation_bars_clean(df_nom, ["spc_90d", "spc_180d", "spc_360d", "bcp_2y", "bcp_5y", "bcp_10y"]), width="stretch", key="tasas_clean_var_nom")
        chart_title("Evolución curva nominal", "%")
        st.plotly_chart(line_chart(df_nom, ["spc_90d", "spc_360d", "bcp_2y", "bcp_5y", "bcp_10y"], show_ma=False), width="stretch", key="tasas_clean_nom_line")

    with tabs[2]:
        c1, c2 = st.columns(2, gap="large")
        with c1:
            chart_title("Curva UF · último dato", "%")
            st.plotly_chart(latest_curve_clean(df_uf, ["bcu_1y", "bcu_2y", "bcu_5y", "bcu_10y", "bcu_20y", "bcu_30y"], "Curva UF"), width="stretch", key="tasas_clean_curva_uf")
        with c2:
            chart_title("Variación curva UF", "pb vs dato previo")
            st.plotly_chart(variation_bars_clean(df_uf, ["bcu_1y", "bcu_2y", "bcu_5y", "bcu_10y", "bcu_20y", "bcu_30y"]), width="stretch", key="tasas_clean_var_uf")
        chart_title("Evolución tasas UF", "%")
        st.plotly_chart(line_chart(df_uf, ["bcu_1y", "bcu_2y", "bcu_5y", "bcu_10y", "bcu_20y", "bcu_30y"], show_ma=False), width="stretch", key="tasas_clean_uf_line")
        with st.expander("Cobertura datos curva UF", expanded=False):
            st.caption("La curva UF ahora usa tasas de mercado secundario de bonos en UF (BCU/BTU), no licitaciones primarias BCU. Esto debería entregar una curva diaria más continua.")
            st.dataframe(coverage_table_for_ids(df_uf, ["bcu_1y", "bcu_2y", "bcu_5y", "bcu_10y", "bcu_20y", "bcu_30y"]), width="stretch", hide_index=True)

    with tabs[3]:
        chart_title("Tasa interbancaria promedio", "%")
        st.plotly_chart(line_chart(df_inter, ["tib"], show_ma=False), width="stretch", key="tasas_clean_tib")

    with tabs[4]:
        st.markdown(
            '<div class="muted-note"><b>Pendiente 10Y-2Y:</b> diferencia entre tasa a 10 años y tasa a 2 años. '
            'Si sube, la curva se empina; si baja o es negativa, la curva se aplana o invierte. '
            '<br><br><b>Importante:</b> no se interpolan datos. Si falta una pata o no hay fechas comparables, el spread queda vacío.</div>',
            unsafe_allow_html=True,
        )

        chart_title("Componentes nominales del spread", "2Y y 10Y")
        st.plotly_chart(line_chart(data, ["bcp_2y", "bcp_10y"], show_ma=False), width="stretch", key="tasas_clean_spread_nom_legs")

        chart_title("Componentes UF del spread", "2Y y 10Y")
        st.plotly_chart(line_chart(data, ["bcu_2y", "bcu_10y"], show_ma=False), width="stretch", key="tasas_clean_spread_uf_legs")

        chart_title("Pendientes de curva", "Puntos porcentuales")
        st.plotly_chart(line_chart(df_spreads, ["pendiente_nominal", "pendiente_uf"], show_ma=False), width="stretch", key="tasas_clean_spreads")

        audit_ids = ["bcp_2y", "bcp_10y", "pendiente_nominal", "bcu_2y", "bcu_10y", "pendiente_uf"]
        with st.expander("Auditoría de brechas 10Y-2Y", expanded=True):
            st.markdown(
                '<div class="muted-note">Esta tabla permite distinguir si el vacío viene de la pata 2Y, la pata 10Y o del spread calculado.</div>',
                unsafe_allow_html=True,
            )
            st.dataframe(coverage_table_for_ids(data, audit_ids, max_gap_days=45), width="stretch", hide_index=True)

            gap_df = gap_windows_for_ids(data, audit_ids, max_gap_days=45)
            if gap_df.empty:
                st.success("No se detectan brechas mayores a 45 días en las series auditadas.")
            else:
                st.markdown("**Brechas detectadas mayores a 45 días**")
                st.dataframe(gap_df, width="stretch", hide_index=True)

            yearly = coverage_by_year_for_ids(data, audit_ids)
            if not yearly.empty:
                st.markdown("**Observaciones por año**")
                st.dataframe(yearly, width="stretch", hide_index=True)

    return {
        "tasas_tpm_expectativas": df_tpm,
        "tasas_curva_nominal": df_nom,
        "tasas_curva_uf": df_uf,
        "tasas_interbancario": df_inter,
        "tasas_spreads": df_spreads,
    }


def render_tipo_cambio_clean(data: pd.DataFrame, opts: dict) -> dict[str, pd.DataFrame]:
    section_title("Tipo de cambio")
    ids = ["usdclp", "euroclp", "mer", "mer5", "merx"]
    render_kpi_grid(latest_by_indicator(data), pd.DataFrame(), ["usdclp", "euroclp", "mer"])
    tabs = st.tabs(["USD/CLP", "Euro", "Multilateral", "USD/CLP vs cobre"])
    with tabs[0]:
        chart_title("USD/CLP con medias móviles", "CLP por USD")
        st.plotly_chart(line_chart(data, ["usdclp"], show_ma=opts.get("show_ma")), width="stretch", key="tc_clean_usd")
    with tabs[1]:
        chart_title("Euro/CLP", "CLP por EUR")
        st.plotly_chart(line_chart(data, ["euroclp"], show_ma=opts.get("show_ma")), width="stretch", key="tc_clean_eur")
    with tabs[2]:
        chart_title("Índices de tipo de cambio multilateral", "Índice")
        st.plotly_chart(line_chart(data, ["mer", "mer5", "merx"], show_ma=False), width="stretch", key="tc_clean_mer")
    with tabs[3]:
        chart_title("USD/CLP vs cobre", "Doble eje")
        st.plotly_chart(dual_axis_chart(data, "usdclp", data, "cobre", "USD/CLP", "Cobre USD/libra"), width="stretch", key="tc_clean_usd_cobre")
    return {"tipo_cambio": data[data["serie_id"].isin(ids + ["cobre"])]}


def render_inflacion_clean(data: pd.DataFrame, opts: dict) -> dict[str, pd.DataFrame]:
    section_title("Inflación y reajustes")
    ids = ["uf", "utm", "ipc_mensual", "ipc_anual", "tasa_real_ex_post"]
    render_kpi_grid(latest_by_indicator(data), pd.DataFrame(), ["uf", "ipc_mensual", "ipc_anual", "tasa_real_ex_post"])
    tabs = st.tabs(["IPC", "UF / UTM", "TPM vs IPC", "Tasa real"])
    with tabs[0]:
        chart_title("IPC mensual y anual", "%")
        st.plotly_chart(line_chart(data, ["ipc_mensual", "ipc_anual"], show_ma=False), width="stretch", key="inf_clean_ipc")
    with tabs[1]:
        chart_title("UF diaria y UTM mensual", "CLP")
        st.plotly_chart(line_chart(data, ["uf", "utm"], show_ma=False), width="stretch", key="inf_clean_uf_utm")
    with tabs[2]:
        chart_title("TPM vs inflación anual", "%")
        st.plotly_chart(line_chart(data, ["tpm", "ipc_anual"], show_ma=False), width="stretch", key="inf_clean_tpm_ipc")
    with tabs[3]:
        chart_title("Tasa real ex post aproximada", "TPM - IPC anual, pp")
        st.plotly_chart(line_chart(data, ["tasa_real_ex_post"], show_ma=False), width="stretch", key="inf_clean_real")
    return {"inflacion": data[data["serie_id"].isin(ids + ["tpm"])]}


def render_actividad_clean(data: pd.DataFrame, opts: dict) -> dict[str, pd.DataFrame]:
    section_title("Actividad económica")
    ids = ["imacec_total", "imacec_no_minero", "imacec_mineria", "imacec_comercio", "imacec_servicios", "pib_trimestral"]
    render_kpi_grid(latest_by_indicator(data), pd.DataFrame(), ["imacec_total", "imacec_no_minero", "pib_trimestral"])
    chart_title("IMACEC por componentes", "Índice / nivel")
    st.plotly_chart(line_chart(data, ids[:-1], show_ma=False), width="stretch", key="act_clean_imacec")
    chart_title("PIB trimestral", "MM CLP encadenado")
    st.plotly_chart(line_chart(data, ["pib_trimestral"], show_ma=False), width="stretch", key="act_clean_pib")
    return {"actividad": data[data["serie_id"].isin(ids)]}


def render_laboral_clean(data: pd.DataFrame, opts: dict) -> dict[str, pd.DataFrame]:
    section_title("Mercado laboral")
    ids = ["desempleo", "ocupados", "asalariados", "fuerza_trabajo"]
    render_kpi_grid(latest_by_indicator(data), pd.DataFrame(), ["desempleo", "ocupados"])
    chart_title("Desempleo y mercado laboral", "% / miles de personas")
    st.plotly_chart(line_chart(data, ids, show_ma=False), width="stretch", key="lab_clean_main")
    return {"mercado_laboral": data[data["serie_id"].isin(ids)]}


def render_commodities_bolsa_clean(data: pd.DataFrame, opts: dict) -> dict[str, pd.DataFrame]:
    section_title("Commodities y bolsa local")
    ids = ["cobre", "oro", "plata", "ipsa"]
    render_kpi_grid(latest_by_indicator(data), pd.DataFrame(), ["cobre", "ipsa"])
    c1, c2 = st.columns(2, gap="large")
    with c1:
        chart_title("Cobre, oro y plata", "USD")
        st.plotly_chart(line_chart(data, ["cobre", "oro", "plata"], show_ma=opts.get("show_ma")), width="stretch", key="com_clean_metals")
    with c2:
        chart_title("IPSA con medias móviles", "Índice")
        st.plotly_chart(line_chart(data, ["ipsa"], show_ma=opts.get("show_ma")), width="stretch", key="com_clean_ipsa")
    chart_title("IPSA vs cobre", "Doble eje")
    st.plotly_chart(dual_axis_chart(data, "ipsa", data, "cobre", "IPSA", "Cobre USD/libra"), width="stretch", key="com_clean_ipsa_cobre")
    return {"commodities_bolsa": data[data["serie_id"].isin(ids)]}


def render_alerts_page(signals: pd.DataFrame) -> dict[str, pd.DataFrame]:
    section_title("Señales y alertas")
    render_alerts(signals, "Ranking de alertas por severidad")
    chart_title("Resumen de semáforos", "Conteo por categoría y estado")
    st.plotly_chart(signals_summary_chart(signals), width="stretch", key="alert_summary_bar")

    if signals is not None and not signals.empty:
        resumen = (
            signals.groupby(["categoria", "estado"], dropna=False)
            .size()
            .reset_index(name="conteo")
            .sort_values(["categoria", "estado"])
        )
        show_table(resumen, "Tabla resumen por categoría")
    show_table(signals, "Todas las señales")
    return {"senales": signals}


def render_quality_page(data: pd.DataFrame, indicators: list[dict], diag: pd.DataFrame, health: pd.DataFrame) -> dict[str, pd.DataFrame]:
    section_title("Calidad de datos")
    show_table(health, "Salud de datos por indicador", height=500)
    show_table(diag, "Estado de fuentes SieteWS", height=500)
    return {"salud_datos": health, "diagnostico_fuentes": diag}


def render_downloads(data: pd.DataFrame, latest: pd.DataFrame, signals: pd.DataFrame, catalog: pd.DataFrame, health: pd.DataFrame) -> dict[str, pd.DataFrame]:
    section_title("Descargas")
    sheets = {"datos_filtrados": data, "resumen": latest, "senales": signals, "catalogo": catalog, "calidad": health}
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("Datos filtrados CSV", data.to_csv(index=False).encode("utf-8"), "datos_filtrados.csv", "text/csv", width="stretch")
    with c2:
        st.download_button("Señales CSV", signals.to_csv(index=False).encode("utf-8"), "senales.csv", "text/csv", width="stretch")
    with c3:
        st.download_button("Excel multihoja", make_excel(sheets), "monitor_mercado_chile.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
    show_table(catalog, "Catálogo de indicadores", height=500)
    return sheets


def render_methodology(catalog: pd.DataFrame, health: pd.DataFrame) -> dict[str, pd.DataFrame]:
    section_title("Metodología")
    st.markdown("""
    ### Fuentes de datos
    La fuente principal es la API BDE/SieteWS del Banco Central de Chile. Algunas series provienen originalmente de INE, Bolsa o fuentes externas, pero se consumen a través de BDE cuando existe código confirmado. Los módulos CMF, INE directo y fuentes externas quedan preparados como estructura, sin inventar datos.

    ### Frecuencia de actualización
    La app consulta SieteWS bajo demanda y usa caché temporal configurable. El usuario puede forzar actualización con **Recargar datos**.

    ### Transformaciones
    Se calculan variaciones contra dato anterior, 7 días, 30 días, 3 meses, 12 meses, variación YTD, medias móviles 7/30/50/200, z-score y base 100. Para series mensuales o trimestrales, las variaciones por número de observaciones deben interpretarse según frecuencia.

    ### Señales
    Los semáforos se calculan con reglas configurables en `config/settings.py`. Verde indica normalidad, amarillo atención, rojo alerta y gris datos insuficientes o fuente pendiente.

    ### Limitaciones
    El monitor es informativo y depende de disponibilidad, rezago y definiciones metodológicas de cada fuente. No reemplaza validación oficial ni constituye recomendación de inversión.
    """)
    st.caption(f"Última actualización de la app: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    show_table(catalog[["id", "name", "category", "source", "code", "method", "notes"]], "Catálogo metodológico", height=500)
    return {"catalogo": catalog, "calidad": health}



def generate_signals(indicators: list[dict], data: pd.DataFrame) -> pd.DataFrame:
    """Genera señales para varios indicadores sin botar la app si una regla falla."""
    rows = []
    if not indicators:
        return pd.DataFrame(columns=[
            "estado", "color", "severidad", "mensaje", "explicacion", "indicador",
            "serie_id", "categoria", "metrica_gatillante", "fecha_dato",
            "recomendacion_analitica",
        ])

    for indicator in indicators:
        try:
            rows.append(generate_signal(indicator, data))
        except Exception as exc:
            rows.append({
                "estado": "gris",
                "color": "#94A3B8",
                "severidad": 0,
                "mensaje": "Señal no calculada",
                "explicacion": f"No se pudo calcular la señal: {str(exc)[:220]}",
                "indicador": indicator.get("name", indicator.get("id", "Indicador")),
                "serie_id": indicator.get("id"),
                "categoria": indicator.get("category", "Sin categoría"),
                "metrica_gatillante": "error_signal",
                "fecha_dato": None,
                "recomendacion_analitica": "Revisar regla o disponibilidad de datos.",
            })

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    if "severidad" in out.columns:
        out = out.sort_values(["severidad", "categoria", "indicador"], ascending=[False, True, True])
    return out.reset_index(drop=True)


def main() -> None:
    inject_css()
    creds = get_credentials()
    if creds is None:
        render_login()
        st.stop()

    render_hero(creds)
    catalog = indicators_dataframe()
    start, end, selected_ids, frequency, opts = top_controls(creds, catalog)

    if start > end:
        st.error("La fecha de inicio no puede ser posterior a la fecha fin.")
        st.stop()

    token = st.session_state.get("monitor_cache_token", 0)
    try:
        with st.spinner("Cargando indicadores implementados vía SieteWS..."):
            raw_data, diagnostics = cached_load(creds.user, creds.password, to_bcch_date(start), to_bcch_date(end), tuple(sorted(selected_ids)), token)
    except InvalidCredentials:
        st.error("Credenciales SieteWS inválidas. Cierra sesión e ingresa usuario/clave nuevamente.")
        st.stop()
    except MissingCredentials:
        st.error("Faltan credenciales SieteWS.")
        st.stop()
    except Exception as exc:
        st.error(f"No se pudo cargar SieteWS: {str(exc)[:400]}")
        raw_data, diagnostics = pd.DataFrame(), pd.DataFrame()

    data = filter_data(raw_data, selected_ids, frequency)
    active_indicators = [indicator_map()[sid] for sid in selected_ids if sid in indicator_map()]
    for did in ["tasa_real_ex_post", "pendiente_nominal", "pendiente_uf"]:
        if did in indicator_map() and not data.empty and did in set(data["serie_id"]):
            active_indicators.append(indicator_map()[did])

    signals = generate_signals(active_indicators, data)
    latest = latest_by_indicator(data)
    health = build_health_table(data, active_indicators, diagnostics)
    st.caption(f"Última actualización visual: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')} · Observaciones cargadas: {len(data):,.0f}")

    tabs = st.tabs([
        "1. Resumen",
        "2. Tipo de cambio",
        "3. Inflación y reajustes",
        "4. Tasas y renta fija",
        "5. Actividad",
        "6. Mercado laboral",
        "7. Commodities y bolsa",
        "8. Derivados",
        "9. Señales",
        "10. Calidad / descargas",
        "11. Metodología",
    ])

    export_sheets = {}
    with tabs[0]:
        export_sheets.update(render_resumen(data, active_indicators, signals, opts))
    with tabs[1]:
        export_sheets.update(render_tipo_cambio_clean(data, opts))
    with tabs[2]:
        export_sheets.update(render_inflacion_clean(data, opts))
    with tabs[3]:
        export_sheets.update(render_tasas_clean(data, opts))
    with tabs[4]:
        export_sheets.update(render_actividad_clean(data, opts))
    with tabs[5]:
        export_sheets.update(render_laboral_clean(data, opts))
    with tabs[6]:
        export_sheets.update(render_commodities_bolsa_clean(data, opts))
    with tabs[7]:
        export_sheets.update(render_derivatives_module(start, end, creds.user, creds.password))
    with tabs[8]:
        export_sheets.update(render_alerts_page(signals))
    with tabs[9]:
        export_sheets.update(render_quality_page(data, active_indicators, diagnostics, health))
        export_sheets.update(render_downloads(data, latest, signals, catalog, health))
    with tabs[10]:
        export_sheets.update(render_methodology(catalog, health))


if __name__ == "__main__":
    main()
