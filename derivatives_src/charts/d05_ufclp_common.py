from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from derivatives_src.charts._common import base_layout, empty_figure
from derivatives_src.charts.siid_style import CMF_DARK, CMF_MUTED, CMF_PALETTE
from derivatives_src.io.bde_table import fetch_bde_table, normalize_text, clean_label, parse_bde_period, parse_bde_number

DER_FX_MLML_10 = "https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_DERYSPOT/MN_DERYSPOT/DER_FX_MLML_10/638345409388280585"
DER_FX_MLML_02 = "https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_DERYSPOT/MN_DERYSPOT/DER_FX_MLML_02/638125003604255019"
UNIT_USD = "Miles de UF"
UNIT_FORWARD = "Precio forward"

APERTURA_TOTAL = "Total"
APERTURA_COMPRA = "Compra UF"
APERTURA_VENTA = "Venta UF"
APERTURA_NETO = "Neto"
APERTURA_ORDER = [APERTURA_TOTAL, APERTURA_COMPRA, APERTURA_VENTA, APERTURA_NETO]

INSTRUMENT_FORWARD = "Forward"
INSTRUMENT_SWAP = "Swap"
INSTRUMENT_ORDER = [INSTRUMENT_FORWARD, INSTRUMENT_SWAP]

SECTOR_INTER = "Interbancario"
SECTOR_NRES = "No residentes"
SECTOR_RNB = "Residentes no bancos"
SECTOR_ORDER = [SECTOR_INTER, SECTOR_NRES, SECTOR_RNB]


def _period_columns(wide: pd.DataFrame) -> list[str]:
    return [c for c in wide.columns if pd.notna(parse_bde_period(c))]


def normalize_instrument(label: object) -> str | None:
    norm = normalize_text(label)
    if "forward" in norm:
        return INSTRUMENT_FORWARD
    if "swap" in norm:
        return INSTRUMENT_SWAP
    return None


def normalize_apertura(label: object) -> str | None:
    norm = normalize_text(label)
    # Compra/venta UF
    if "compra" in norm and "uf" in norm:
        return APERTURA_COMPRA
    if "venta" in norm and "uf" in norm:
        return APERTURA_VENTA
    if norm == "neto" or "neto" in norm:
        return APERTURA_NETO
    if norm.startswith("monto transado total") or norm == "total":
        return APERTURA_TOTAL
    return None


def normalize_sector(label: object) -> str | None:
    norm = normalize_text(label)
    if norm == "interbancario":
        return SECTOR_INTER
    if norm == "no residentes" or norm == "no residente":
        return SECTOR_NRES
    if norm == "residentes no bancos" or norm == "residentes no banco":
        return SECTOR_RNB
    return None


def _iter_values(row: pd.Series, period_cols: list[str], start: pd.Timestamp, end: pd.Timestamp):
    for col in period_cols:
        dt = parse_bde_period(col)
        if pd.isna(dt):
            continue
        dt = pd.Timestamp(dt)
        if dt < start or dt > end:
            continue
        value = parse_bde_number(row[col])
        if pd.isna(value):
            continue
        yield dt, value


def extract_ufclp_transados(start_date: str, end_date: str) -> pd.DataFrame:
    """Extrae DER_FX_MLML_02 según la jerarquía real del cuadro.

    Estructura esperada:
      Forward / Swap
        Interbancario
        Compras UF a terceros
        Ventas UF a terceros
        Neto
        Sectores
          No residentes
            Compras UF
            Ventas UF
            Neto
          Residentes no bancos
            Compras UF
            Ventas UF
            Neto

    Para el gráfico:
    - Total = Interbancario total + No residentes total + Residentes no bancos total.
    - Compra/Venta/Neto se muestran para terceros por sector; Interbancario no trae apertura UF,
      por lo que no se fuerza artificialmente dentro de Compra/Venta/Neto.
    """
    table = fetch_bde_table(DER_FX_MLML_02)
    wide = table.wide.copy()
    period_cols = _period_columns(wide)
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)

    records: list[dict] = []
    current_instrument: str | None = None
    in_sector_detail = False
    current_sector: str | None = None

    def add_row(row: pd.Series, instrumento: str, apertura: str, sector: str, raw_item: str) -> None:
        for dt, value in _iter_values(row, period_cols, start, end):
            records.append(
                {
                    "date": dt,
                    "instrumento": instrumento,
                    "apertura": apertura,
                    "sector": sector,
                    "value": value,
                    "raw_item": raw_item,
                }
            )

    for _, row in wide.iterrows():
        raw_label = row.get("bde_series_raw", row.get("bde_series", ""))
        label = clean_label(raw_label)
        norm = normalize_text(label)

        if not label:
            continue
        if norm == "notas":
            break
        if norm == "sectores":
            in_sector_detail = True
            current_sector = None
            continue

        instr = normalize_instrument(label)
        # Evitar que textos como "Monto transado, total" se interpreten como instrumento.
        if instr is not None and (norm == "forward" or norm.startswith("swap")):
            current_instrument = instr
            in_sector_detail = False
            current_sector = None
            continue

        if current_instrument is None:
            continue

        # Primer nivel del instrumento: Interbancario total.
        if not in_sector_detail and normalize_sector(label) == SECTOR_INTER:
            add_row(row, current_instrument, APERTURA_TOTAL, SECTOR_INTER, label)
            continue

        # Dentro de "Sectores": No residentes / Residentes no bancos y sus aperturas.
        if in_sector_detail:
            sector = normalize_sector(label)
            if sector in {SECTOR_NRES, SECTOR_RNB}:
                current_sector = sector
                add_row(row, current_instrument, APERTURA_TOTAL, sector, label)
                continue

            apertura = normalize_apertura(label)
            if apertura in {APERTURA_COMPRA, APERTURA_VENTA, APERTURA_NETO} and current_sector in {SECTOR_NRES, SECTOR_RNB}:
                add_row(row, current_instrument, apertura, current_sector, label)
                continue

    df = pd.DataFrame(records, columns=["date", "instrumento", "apertura", "sector", "value", "raw_item"])
    if not df.empty:
        df = (
            df.groupby(["date", "instrumento", "apertura", "sector"], as_index=False)["value"]
            .sum()
            .sort_values(["date", "instrumento", "apertura", "sector"])
            .reset_index(drop=True)
        )
    return df

def extract_ufclp_forward_prices(start_date: str, end_date: str) -> pd.DataFrame:
    """Extrae DER_FX_MLML_10 para monto transado y precio forward 12 meses interbancario."""
    table = fetch_bde_table(DER_FX_MLML_10)
    wide = table.wide.copy()
    period_cols = _period_columns(wide)
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    records: list[dict] = []

    for _, row in wide.iterrows():
        raw_label = row.get("bde_series_raw", row.get("bde_series", ""))
        label = clean_label(raw_label)
        norm = normalize_text(label)
        if norm == "notas":
            break

        metric = None
        unit = None
        if "monto transado" in norm and "forward" in norm and "interbancario" in norm:
            metric = "Montos transados"
            unit = "Miles de UF"
        elif "precio forward" in norm and "interbancario" in norm:
            metric = "Promedio precios"
            unit = "CLP"

        if metric is None:
            continue

        for dt, value in _iter_values(row, period_cols, start, end):
            records.append({"date": dt, "metric": metric, "serie": label, "unit_metric": unit, "value": value})

    df = pd.DataFrame(records, columns=["date", "metric", "serie", "unit_metric", "value"])
    if not df.empty:
        df = (
            df.groupby(["date", "metric", "serie", "unit_metric"], as_index=False)["value"]
            .sum()
            .sort_values(["date", "metric"])
            .reset_index(drop=True)
        )
    return df


def add_common_columns(df: pd.DataFrame, chart_id: str, label_col: str, dim1_col: str, dim2_col: str = "") -> pd.DataFrame:
    cols = [
        "date", "value", "chart_id", "logical_series", "series_id", "label", "market",
        "dimension_1", "dimension_2", "frequency", "unit", "status_code"
    ]
    if df.empty:
        return pd.DataFrame(columns=cols)
    out = df.copy()
    out["chart_id"] = chart_id
    out["logical_series"] = out[label_col].astype(str)
    out["series_id"] = chart_id + "::" + out[label_col].astype(str)
    out["label"] = out[label_col].astype(str)
    out["market"] = "UF/CLP"
    out["dimension_1"] = out[dim1_col].astype(str)
    out["dimension_2"] = out[dim2_col].astype(str) if dim2_col and dim2_col in out.columns else ""
    out["frequency"] = "MONTHLY"
    out["unit"] = UNIT_USD if "sector" in out.columns else UNIT_FORWARD
    out["status_code"] = "DER_FX_MLML_02" if chart_id != "d05_ufclp_forward_prices" else "DER_FX_MLML_10"
    keep_extra = [c for c in ["instrumento", "apertura", "sector", "serie", "metric", "unit_metric"] if c in out.columns]
    return out[cols + keep_extra].sort_values(["date", "dimension_1", "dimension_2"]).reset_index(drop=True)


def available_aperturas(df: pd.DataFrame) -> list[str]:
    return APERTURA_ORDER


def _filter_transado_plot(df: pd.DataFrame, instrumento: str, apertura: str) -> pd.DataFrame:
    if df.empty:
        return df

    out = df.copy()
    out = out[out["instrumento"].eq(instrumento)].copy()
    if out.empty:
        return out

    if apertura == APERTURA_TOTAL:
        # Para total usar las filas agregadas del cuadro:
        # Interbancario + No residentes + Residentes no bancos.
        out = out[out["apertura"].eq(APERTURA_TOTAL)].copy()
    else:
        # La BDE no descompone Interbancario en Compra/Venta UF.
        # Para no perder el sector interbancario en el gráfico, se mantiene su total
        # y se combina con la apertura seleccionada para No residentes y Residentes no bancos.
        inter = out[(out["sector"].eq(SECTOR_INTER)) & (out["apertura"].eq(APERTURA_TOTAL))].copy()
        terceros = out[(out["sector"].isin([SECTOR_NRES, SECTOR_RNB])) & (out["apertura"].eq(apertura))].copy()
        out = pd.concat([inter, terceros], ignore_index=True)

    if out.empty:
        return out

    return out.groupby(["date", "sector"], as_index=False)["value"].sum()


def build_transado_figure(df: pd.DataFrame, instrumento: str, apertura: str) -> go.Figure:
    plot = _filter_transado_plot(df, instrumento, apertura)
    if plot.empty:
        return empty_figure(f"Sin datos para {instrumento} - {apertura}")

    total_df = plot.groupby("date", as_index=False)["value"].sum()
    fig = go.Figure()
    for i, sector in enumerate(SECTOR_ORDER):
        tmp = plot[plot["sector"].eq(sector)]
        fig.add_trace(go.Bar(x=tmp["date"], y=tmp["value"], name=sector, marker_color=CMF_PALETTE[i % len(CMF_PALETTE)]))
    fig.add_trace(go.Scatter(x=total_df["date"], y=total_df["value"], mode="lines", name="Total", line=dict(color=CMF_DARK, width=2.5)))
    fig.update_layout(barmode="stack")
    fig = base_layout(fig, f"BANCOS. UF/CLP MONTOS TRANSADOS {instrumento.upper()} POR SECTOR. {apertura.upper()}", yaxis_title=UNIT_USD)
    fig.update_layout(margin={"l": 78, "r": 120, "t": 34, "b": 185})
    return fig


def build_forward_price_figure(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return empty_figure("Sin datos de montos/precios forward UF/CLP")

    plot = df.copy()
    plot["date"] = pd.to_datetime(plot["date"])

    # Robustez: versiones anteriores podían perder la columna metric al pasar por add_common_columns.
    if "metric" not in plot.columns:
        if "dimension_1" in plot.columns:
            plot["metric"] = plot["dimension_1"]
        elif "label" in plot.columns:
            plot["metric"] = plot["label"]
        else:
            return empty_figure("Falta columna metric para separar montos y precios forward")

    wide = plot.pivot_table(index="date", columns="metric", values="value", aggfunc="sum").reset_index()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    if "Montos transados" in wide.columns:
        fig.add_trace(
            go.Bar(
                x=wide["date"],
                y=wide["Montos transados"],
                name="Montos transados",
                marker_color=CMF_PALETTE[1],
                hovertemplate="%{x|%b %Y}<br>Montos transados: %{y:,.0f} miles de UF<extra></extra>",
            ),
            secondary_y=False,
        )

    if "Promedio precios" in wide.columns:
        fig.add_trace(
            go.Scatter(
                x=wide["date"],
                y=wide["Promedio precios"],
                mode="lines",
                name="Promedio precios (eje der.)",
                line=dict(width=2.5, color=CMF_DARK),
                hovertemplate="%{x|%b %Y}<br>Promedio precios: %{y:,.0f} CLP<extra></extra>",
            ),
            secondary_y=True,
        )

    fig = base_layout(
        fig,
        "BANCOS. MONTOS TOTALES Y PROMEDIO DE PRECIOS FORWARD INTERBANCARIOS A UN AÑO PLAZO",
        yaxis_title="Montos transados",
    )
    fig.update_yaxes(title_text="Montos transados", tickformat=",.0f", secondary_y=False)
    fig.update_yaxes(title_text="Promedio precios (CLP)", tickformat=",.0f", secondary_y=True)
    fig.update_layout(
        height=560,
        barmode="overlay",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        margin={"l": 78, "r": 120, "t": 34, "b": 185},
    )
    return fig

