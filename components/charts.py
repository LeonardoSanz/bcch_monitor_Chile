from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config.settings import COLORS

PALETTE = [COLORS["primary"], COLORS["cyan"], COLORS["blue"], "#B56CFF", "#7AD3F7", "#F06BFF", COLORS["yellow"], COLORS["red"]]


def _break_large_date_gaps(part: pd.DataFrame, date_col: str = "fecha", gap_days: int = 45) -> pd.DataFrame:
    """Inserta filas NaN para que Plotly no dibuje líneas rectas sobre brechas largas."""
    if part is None or part.empty or date_col not in part.columns:
        return part
    p = part.copy().sort_values(date_col)
    p[date_col] = pd.to_datetime(p[date_col], errors="coerce")
    p = p.dropna(subset=[date_col])
    if len(p) < 2:
        return p
    rows = []
    prev = None
    for _, row in p.iterrows():
        if prev is not None:
            delta = (row[date_col] - prev[date_col]).days
            if delta > gap_days:
                gap = prev.copy()
                gap[date_col] = prev[date_col] + pd.Timedelta(days=1)
                for col in ["valor", "base_100", "ma_50", "ma_200", "ma_30", "ma_7"]:
                    if col in gap.index:
                        gap[col] = None
                rows.append(gap)
        rows.append(row)
        prev = row
    return pd.DataFrame(rows)


def coverage_table_for_ids(df: pd.DataFrame, ids: list[str], max_gap_days: int = 45) -> pd.DataFrame:
    """Resumen de cobertura para diagnosticar brechas de curva."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["serie_id", "indicador", "observaciones", "desde", "hasta", "brecha_max_dias", "brechas_mayores_a_umbral"])
    rows = []
    for sid in ids:
        part = df[df["serie_id"].eq(sid)].dropna(subset=["fecha", "valor"]).sort_values("fecha")
        if part.empty:
            rows.append({"serie_id": sid, "indicador": sid, "observaciones": 0, "desde": None, "hasta": None, "brecha_max_dias": None, "brechas_mayores_a_umbral": None})
            continue
        gaps = pd.to_datetime(part["fecha"]).diff().dt.days.dropna()
        rows.append({
            "serie_id": sid,
            "indicador": part["nombre_indicador"].iloc[-1] if "nombre_indicador" in part.columns else sid,
            "observaciones": int(len(part)),
            "desde": pd.to_datetime(part["fecha"].min()).date().isoformat(),
            "hasta": pd.to_datetime(part["fecha"].max()).date().isoformat(),
            "brecha_max_dias": int(gaps.max()) if not gaps.empty else 0,
            "brechas_mayores_a_umbral": int((gaps > max_gap_days).sum()) if not gaps.empty else 0,
        })
    return pd.DataFrame(rows)


def apply_layout(fig: go.Figure, ytitle: str = "", height: int = 520) -> go.Figure:
    fig.update_layout(
        height=height,
        paper_bgcolor=COLORS["panel"],
        plot_bgcolor=COLORS["panel"],
        font=dict(color=COLORS["text"], size=12),
        margin=dict(l=58, r=62, t=34, b=78),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#062252", bordercolor="rgba(255,255,255,0.16)", font_color=COLORS["text"]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, color=COLORS["text"], linecolor="rgba(255,255,255,0.18)", tickfont=dict(color=COLORS["text"]))
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"], zeroline=False, color=COLORS["text"], title_text=ytitle, title_font=dict(color=COLORS["text"]), tickfont=dict(color=COLORS["text"]), tickformat=".2f")
    fig.add_annotation(text="Fuente: BCCh BDE/SieteWS y cálculos propios cuando aplica.", xref="paper", yref="paper", x=0, y=-0.18, showarrow=False, align="left", font=dict(size=10, color=COLORS["muted"]))
    return fig


def empty_chart(message: str = "Sin datos") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, x=0.5, y=0.5, showarrow=False, font=dict(size=15, color=COLORS["muted"]))
    return apply_layout(fig, height=420)


def line_chart(df: pd.DataFrame, ids: list[str] | None = None, title: str = "", y_col: str = "valor", show_ma: bool = False, normalize: bool = False, log_y: bool = False) -> go.Figure:
    if df is None or df.empty:
        return empty_chart("Sin datos")
    plot = df.copy()
    if ids:
        plot = plot[plot["serie_id"].isin(ids)]
    if plot.empty:
        return empty_chart("Sin datos para selección")
    y = "base_100" if normalize and "base_100" in plot.columns else y_col
    fig = go.Figure()
    for i, (sid, part) in enumerate(plot.sort_values("fecha").groupby("serie_id")):
        name = part["nombre_indicador"].iloc[-1] if "nombre_indicador" in part else sid
        # Umbral dinámico de brechas:
        # - diario: mantiene corte en gaps largos
        # - mensual/trimestral: evita cortar TODA la serie, que era lo que pasaba con PIB trimestral
        fechas = pd.to_datetime(part["fecha"], errors="coerce").dropna().sort_values()
        if len(fechas) >= 3:
            med_gap = fechas.diff().dt.days.dropna().median()
            gap_threshold = max(45, int(med_gap * 3)) if pd.notna(med_gap) else 45
        else:
            gap_threshold = 180
        part_plot = _break_large_date_gaps(part, "fecha", gap_days=gap_threshold)
        mode = "lines+markers" if len(part.dropna(subset=[y])) <= 30 else "lines"
        fig.add_trace(go.Scatter(x=part_plot["fecha"], y=part_plot[y], mode=mode, name=name, connectgaps=False, line=dict(width=2.5, color=PALETTE[i % len(PALETTE)]), marker=dict(size=6, color=PALETTE[i % len(PALETTE)])))
        if show_ma and "ma_50" in part_plot.columns:
            fig.add_trace(go.Scatter(x=part_plot["fecha"], y=part_plot["ma_50"], mode="lines", name=f"{name} MM50", connectgaps=False, line=dict(width=1.5, dash="dot", color=PALETTE[i % len(PALETTE)])))
        if show_ma and "ma_200" in part_plot.columns:
            fig.add_trace(go.Scatter(x=part_plot["fecha"], y=part_plot["ma_200"], mode="lines", name=f"{name} MM200", connectgaps=False, line=dict(width=1.5, dash="dash", color=PALETTE[i % len(PALETTE)])))
    unit = "Base 100" if normalize else (plot["unidad"].dropna().iloc[0] if "unidad" in plot.columns and plot["unidad"].notna().any() else "")
    fig = apply_layout(fig, ytitle=unit, height=560)
    if log_y:
        fig.update_yaxes(type="log")
    return fig


def dual_axis_chart(df_left: pd.DataFrame, left_id: str, df_right: pd.DataFrame, right_id: str, left_name: str, right_name: str) -> go.Figure:
    if df_left.empty or df_right.empty:
        return empty_chart("Sin datos para doble eje")
    left = df_left[df_left["serie_id"].eq(left_id)].sort_values("fecha")
    right = df_right[df_right["serie_id"].eq(right_id)].sort_values("fecha")
    if left.empty or right.empty:
        return empty_chart("Sin datos para doble eje")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=left["fecha"], y=left["valor"], name=left_name, mode="lines", line=dict(width=2.7, color=COLORS["primary"])), secondary_y=False)
    fig.add_trace(go.Scatter(x=right["fecha"], y=right["valor"], name=right_name, mode="lines", line=dict(width=2.7, color=COLORS["cyan"])), secondary_y=True)
    fig = apply_layout(fig, ytitle=left_name, height=560)
    fig.update_yaxes(title_text=left_name, secondary_y=False)
    fig.update_yaxes(title_text=right_name, secondary_y=True)
    return fig


def curve_chart(df: pd.DataFrame, ids: list[str], title: str = "Curva") -> go.Figure:
    if df.empty:
        return empty_chart("Sin datos curva")
    latest_rows = []
    for sid in ids:
        part = df[df["serie_id"].eq(sid)].sort_values("fecha")
        if not part.empty:
            latest_rows.append(part.iloc[-1])
    if not latest_rows:
        return empty_chart("Sin datos curva")
    cur = pd.DataFrame(latest_rows)
    if "tenor_days" not in cur.columns:
        return empty_chart("Curva sin tenores")
    cur = cur.sort_values("tenor_days")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cur["nombre_indicador"], y=cur["valor"], mode="lines+markers", name=title, line=dict(width=3, color=COLORS["primary"]), marker=dict(size=8)))
    return apply_layout(fig, ytitle="%", height=480)


def bar_variation_chart(df: pd.DataFrame, ids: list[str], metric: str = "var_30d_pct") -> go.Figure:
    if df.empty:
        return empty_chart("Sin datos")
    rows = []
    for sid in ids:
        part = df[df["serie_id"].eq(sid)].dropna(subset=[metric]).sort_values("fecha") if metric in df.columns else pd.DataFrame()
        if not part.empty:
            rows.append(part.iloc[-1])
    if not rows:
        return empty_chart(f"Sin datos para {metric}")
    cur = pd.DataFrame(rows)
    fig = go.Figure(go.Bar(x=cur["nombre_indicador"], y=cur[metric], name=metric))
    return apply_layout(fig, ytitle=metric, height=460)


def heatmap_signals(signals: pd.DataFrame) -> go.Figure:
    if signals.empty:
        return empty_chart("Sin señales")
    pivot = signals.pivot_table(index="categoria", columns="estado", values="severidad", aggfunc="count", fill_value=0)
    cols = ["verde", "amarillo", "rojo", "gris"]
    for c in cols:
        if c not in pivot.columns:
            pivot[c] = 0
    pivot = pivot[cols]
    fig = go.Figure(data=go.Heatmap(z=pivot.values, x=pivot.columns, y=pivot.index, colorscale="Viridis", showscale=True))
    return apply_layout(fig, ytitle="", height=480)


def scatter_chart(df: pd.DataFrame, x_id: str, y_id: str, x_name: str, y_name: str) -> go.Figure:
    if df.empty:
        return empty_chart("Sin datos")
    x = df[df["serie_id"].eq(x_id)][["fecha", "valor"]].rename(columns={"valor": "x"}).sort_values("fecha")
    y = df[df["serie_id"].eq(y_id)][["fecha", "valor"]].rename(columns={"valor": "y"}).sort_values("fecha")
    if x.empty or y.empty:
        return empty_chart("Sin datos para dispersión")
    merged = pd.merge_asof(x, y, on="fecha", direction="nearest", tolerance=pd.Timedelta("10D")).dropna()
    if merged.empty:
        return empty_chart("Sin fechas comparables")
    fig = go.Figure(go.Scatter(x=merged["x"], y=merged["y"], mode="markers", marker=dict(size=8, opacity=0.75), text=merged["fecha"].dt.strftime("%Y-%m-%d")))
    fig = apply_layout(fig, ytitle=y_name, height=500)
    fig.update_xaxes(title_text=x_name)
    return fig


# ---------------------------------------------------------------------
# Gráficos específicos para Tasas y expectativas.
# ---------------------------------------------------------------------

def _series_label_df(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte esquema estándar a date/value/label para gráficos especializados."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["date", "value", "label", "block", "tenor_days", "serie_id"])
    out = df.copy()
    out["date"] = pd.to_datetime(out["fecha"], errors="coerce")
    out["value"] = pd.to_numeric(out["valor"], errors="coerce")
    if "label" not in out.columns:
        out["label"] = out.get("nombre_indicador", out.get("serie_id", ""))
    if "block" not in out.columns:
        out["block"] = out.get("categoria", "")
    return out.dropna(subset=["date", "value"])


def tpm_step_chart_clean(df: pd.DataFrame) -> go.Figure:
    p = _series_label_df(df)
    plot = p[p["serie_id"].eq("tpm")].sort_values("date") if "serie_id" in p.columns else pd.DataFrame()
    if plot.empty:
        return empty_chart("Sin datos TPM")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=plot["date"], y=plot["value"], mode="lines", name="TPM", line=dict(width=3.1, color=COLORS["cyan"], shape="hv")))
    fig = apply_layout(fig, ytitle="%", height=500)
    fig.update_yaxes(tickformat=",.2f")
    return fig


def eee_expectations_chart_clean(df: pd.DataFrame) -> go.Figure:
    p = _series_label_df(df)
    if p.empty or "serie_id" not in p.columns:
        return empty_chart("Sin datos de expectativas de TPM")
    label_map = {"eee_tpm_11m": "EEE TPM 11M", "eee_tpm_23m": "EEE TPM 23M", "eof_tpm_12m": "EOF TPM 12M"}
    p["horizonte"] = p["serie_id"].map(label_map).fillna(p["label"])
    order = ["EEE TPM 11M", "EEE TPM 23M", "EOF TPM 12M"]
    plot = p[p["horizonte"].isin(order)].sort_values("date")
    if plot.empty:
        return empty_chart("Sin datos de expectativas de TPM")
    fig = go.Figure()
    for i, label in enumerate(order):
        tmp = plot[plot["horizonte"].eq(label)]
        if tmp.empty:
            continue
        fig.add_trace(go.Scatter(x=tmp["date"], y=tmp["value"], mode="lines+markers", name=label, line=dict(width=2.35, color=PALETTE[i % len(PALETTE)]), marker=dict(size=6)))
    fig = apply_layout(fig, ytitle="%", height=540)
    fig.update_xaxes(tickformat="%b<br>%Y")
    return fig


def eee_snapshot_chart_clean(df: pd.DataFrame) -> go.Figure:
    p = _series_label_df(df)
    if p.empty or "serie_id" not in p.columns:
        return empty_chart("Sin snapshot TPM/expectativas")
    label_map = {"tpm": "TPM", "eee_tpm_11m": "EEE 11M", "eee_tpm_23m": "EEE 23M", "eof_tpm_12m": "EOF 12M"}
    p["horizonte"] = p["serie_id"].map(label_map).fillna(p["label"])
    latest = p[p["serie_id"].isin(label_map.keys())].sort_values("date").groupby("horizonte", as_index=False).tail(1)
    if latest.empty:
        return empty_chart("Sin snapshot TPM/expectativas")
    order = ["TPM", "EEE 11M", "EEE 23M", "EOF 12M"]
    latest["order"] = latest["horizonte"].map({v: i for i, v in enumerate(order)})
    latest = latest.sort_values("order")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=latest["horizonte"], y=latest["value"], mode="lines+markers", name="Último dato disponible", line=dict(width=2.9, color=COLORS["primary"]), marker=dict(size=9)))
    fig = apply_layout(fig, ytitle="%", height=500)
    fig.update_yaxes(tickformat=",.2f")
    return fig


def eee_gap_to_tpm_chart_clean(df: pd.DataFrame) -> go.Figure:
    p = _series_label_df(df)
    if p.empty or "serie_id" not in p.columns:
        return empty_chart("Sin datos para brecha")
    latest = p.sort_values("date").groupby("serie_id", as_index=False).tail(1)
    tpm = latest[latest["serie_id"].eq("tpm")]
    if tpm.empty:
        return empty_chart("Sin TPM para brecha")
    tpm_value = float(tpm["value"].iloc[-1])
    eee = latest[latest["serie_id"].isin(["eee_tpm_11m", "eee_tpm_23m", "eof_tpm_12m"])].copy()
    if eee.empty:
        return empty_chart("Sin expectativas")
    eee["horizonte"] = eee["serie_id"].map({"eee_tpm_11m": "EEE 11M", "eee_tpm_23m": "EEE 23M", "eof_tpm_12m": "EOF 12M"})
    eee["gap_bp"] = (eee["value"] - tpm_value) * 100
    fig = go.Figure(go.Bar(x=eee["horizonte"], y=eee["gap_bp"], name="Expectativa - TPM"))
    fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="rgba(255,255,255,0.25)")
    fig = apply_layout(fig, ytitle="pb", height=480)
    fig.update_yaxes(tickformat=",.0f")
    return fig


def latest_curve_clean(df: pd.DataFrame, ids: list[str], title: str = "Curva") -> go.Figure:
    return curve_chart(df, ids, title)


def variation_bars_clean(df: pd.DataFrame, ids: list[str], metric: str = "var_abs") -> go.Figure:
    if df is None or df.empty:
        return empty_chart("Sin datos")
    rows = []
    for sid in ids:
        part = df[df["serie_id"].eq(sid)].dropna(subset=[metric]).sort_values("fecha") if metric in df.columns else pd.DataFrame()
        if not part.empty:
            rows.append(part.iloc[-1])
    if not rows:
        return empty_chart("Sin variaciones disponibles")
    cur = pd.DataFrame(rows)
    cur["pb"] = pd.to_numeric(cur[metric], errors="coerce") * 100
    fig = go.Figure(go.Bar(x=cur["nombre_indicador"], y=cur["pb"], name="Variación"))
    return apply_layout(fig, ytitle="pb", height=460)


def gap_windows_for_ids(df: pd.DataFrame, ids: list[str], max_gap_days: int = 45) -> pd.DataFrame:
    """Lista brechas de datos mayores al umbral por serie."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["serie_id", "indicador", "desde", "hasta", "dias_sin_dato"])
    rows = []
    for sid in ids:
        part = df[df["serie_id"].eq(sid)].dropna(subset=["fecha", "valor"]).sort_values("fecha")
        if part.empty:
            rows.append({"serie_id": sid, "indicador": sid, "desde": None, "hasta": None, "dias_sin_dato": None})
            continue
        fechas = pd.to_datetime(part["fecha"], errors="coerce").dropna().sort_values()
        indicador = part["nombre_indicador"].iloc[-1] if "nombre_indicador" in part.columns else sid
        for prev, cur in zip(fechas.iloc[:-1], fechas.iloc[1:]):
            gap = int((cur - prev).days)
            if gap > max_gap_days:
                rows.append({"serie_id": sid, "indicador": indicador, "desde": prev.date().isoformat(), "hasta": cur.date().isoformat(), "dias_sin_dato": gap})
    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(columns=["serie_id", "indicador", "desde", "hasta", "dias_sin_dato"])
    return out.sort_values(["dias_sin_dato", "serie_id"], ascending=[False, True]).reset_index(drop=True)


def coverage_by_year_for_ids(df: pd.DataFrame, ids: list[str]) -> pd.DataFrame:
    """Conteo anual de observaciones por serie para ubicar discontinuidades."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["serie_id", "indicador", "year", "observaciones"])
    rows = []
    for sid in ids:
        part = df[df["serie_id"].eq(sid)].dropna(subset=["fecha", "valor"]).copy()
        if part.empty:
            rows.append({"serie_id": sid, "indicador": sid, "year": None, "observaciones": 0})
            continue
        part["year"] = pd.to_datetime(part["fecha"], errors="coerce").dt.year
        indicador = part["nombre_indicador"].iloc[-1] if "nombre_indicador" in part.columns else sid
        counts = part.groupby("year").size().reset_index(name="observaciones")
        for _, row in counts.iterrows():
            rows.append({"serie_id": sid, "indicador": indicador, "year": int(row["year"]), "observaciones": int(row["observaciones"])})
    return pd.DataFrame(rows)



def signals_summary_chart(signals: pd.DataFrame) -> go.Figure:
    """Resumen más legible que un heatmap: barras apiladas por categoría y estado."""
    if signals is None or signals.empty:
        return empty_chart("Sin señales")

    order_status = ["rojo", "amarillo", "verde", "gris"]
    plot = (
        signals.groupby(["categoria", "estado"], dropna=False)
        .size()
        .reset_index(name="conteo")
    )
    categories = (
        plot.groupby("categoria")["conteo"].sum().sort_values(ascending=True).index.tolist()
    )

    fig = go.Figure()
    color_map = {
        "rojo": COLORS["red"],
        "amarillo": COLORS["yellow"],
        "verde": COLORS["green"],
        "gris": COLORS["muted"],
    }
    for status in order_status:
        tmp = plot[plot["estado"].eq(status)].set_index("categoria").reindex(categories).fillna(0).reset_index()
        fig.add_trace(go.Bar(
            y=tmp["categoria"],
            x=tmp["conteo"],
            name=status,
            orientation="h",
            marker_color=color_map.get(status, COLORS["muted"]),
            hovertemplate="%{y}<br>%{x:.0f} señales<extra>" + status + "</extra>",
        ))

    fig.update_layout(barmode="stack")
    fig = apply_layout(fig, ytitle="", height=max(460, 42 * len(categories) + 160))
    fig.update_xaxes(title_text="Cantidad de señales", tickformat=",.0f")
    return fig
