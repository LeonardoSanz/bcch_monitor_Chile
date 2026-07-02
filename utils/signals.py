from __future__ import annotations

import pandas as pd

from config.settings import SIGNAL_RULES

SEVERITY = {"gris": 0, "verde": 1, "amarillo": 2, "rojo": 3}


def _latest(df: pd.DataFrame, serie_id: str) -> pd.Series | None:
    if df.empty:
        return None
    p = df[df["serie_id"].eq(serie_id)].dropna(subset=["fecha", "valor"]).sort_values("fecha")
    if p.empty:
        return None
    return p.iloc[-1]


def signal(status: str, indicator: dict, row: pd.Series | None, message: str, explanation: str, metric: str = "") -> dict:
    return {
        "estado": status,
        "color": {"verde":"#22C55E", "amarillo":"#FACC15", "rojo":"#FB7185", "gris":"#94A3B8"}.get(status, "#94A3B8"),
        "severidad": SEVERITY.get(status, 0),
        "mensaje": message,
        "explicacion": explanation,
        "indicador": indicator.get("name", indicator.get("id")),
        "serie_id": indicator.get("id"),
        "categoria": indicator.get("category"),
        "metrica_gatillante": metric,
        "fecha_dato": None if row is None else row.get("fecha"),
        "recomendacion_analitica": recommendation(status),
    }


def recommendation(status: str) -> str:
    if status == "rojo":
        return "Revisar drivers y confirmar con indicadores relacionados."
    if status == "amarillo":
        return "Mantener seguimiento y revisar persistencia de la señal."
    if status == "verde":
        return "Sin alerta relevante bajo la regla configurada."
    return "Datos insuficientes o fuente pendiente."


def generate_signal(indicator: dict, df: pd.DataFrame, rules: dict | None = None) -> dict:
    """Genera semáforo para un indicador usando datos reales y reglas configurables."""
    rules = rules or SIGNAL_RULES
    sid = indicator["id"]
    row = _latest(df, sid)
    if row is None:
        return signal("gris", indicator, None, "Sin datos suficientes", "No hay observaciones válidas para evaluar la señal.", "sin_datos")

    rule = indicator.get("signal_rule", "generic")
    value = row.get("valor")
    var30 = row.get("var_30d_pct")
    yoy = row.get("var_12m_pct")
    yoy_pp = row.get("var_12m_pp")

    if rule == "usdclp":
        r = rules["usdclp"]
        if pd.isna(var30):
            return signal("gris", indicator, row, "Dólar sin historia suficiente", "No hay suficientes datos para variación 30 días.", "var_30d_pct")
        if var30 > r["red_30d_up"]:
            return signal("rojo", indicator, row, "Dólar con presión alcista relevante", f"USD/CLP sube {var30:.2f}% en 30 días.", "var_30d_pct")
        if var30 > r["yellow_30d_up"]:
            return signal("amarillo", indicator, row, "Dólar al alza", f"USD/CLP sube {var30:.2f}% en 30 días.", "var_30d_pct")
        return signal("verde", indicator, row, "Dólar estable o a la baja", f"Variación 30 días: {var30:.2f}%.", "var_30d_pct")

    if rule == "copper":
        r = rules["copper"]
        if pd.isna(var30):
            return signal("gris", indicator, row, "Cobre sin historia suficiente", "No hay suficientes datos para variación 30 días.", "var_30d_pct")
        if var30 < r["red_30d_down"]:
            return signal("rojo", indicator, row, "Cobre cae fuerte", f"Cobre cae {var30:.2f}% en 30 días.", "var_30d_pct")
        if var30 < r["yellow_30d_down"]:
            return signal("amarillo", indicator, row, "Cobre débil", f"Cobre cae {var30:.2f}% en 30 días.", "var_30d_pct")
        return signal("verde", indicator, row, "Cobre estable o al alza", f"Variación 30 días: {var30:.2f}%.", "var_30d_pct")

    if rule == "ipc":
        r = rules["ipc"]
        if pd.isna(value):
            return signal("gris", indicator, row, "IPC sin dato", "No hay dato actual de inflación anual.", "valor")
        if value >= r["red_upper"]:
            return signal("rojo", indicator, row, "Inflación anual muy elevada", f"IPC anual en {value:.2f}%.", "valor")
        if value >= r["yellow_upper"]:
            return signal("amarillo", indicator, row, "Inflación sobre zona de confort", f"IPC anual en {value:.2f}%.", "valor")
        return signal("verde", indicator, row, "Inflación moderada", f"IPC anual en {value:.2f}%.", "valor")

    if rule == "tasa_real":
        r = rules["tasa_real"]
        if pd.isna(value):
            return signal("gris", indicator, row, "Tasa real sin dato", "No se pudo calcular TPM menos IPC anual.", "valor")
        if value >= r["red"]:
            return signal("rojo", indicator, row, "Tasa real muy restrictiva", f"Tasa real ex post aprox. en {value:.2f} pp.", "valor")
        if value >= r["yellow"]:
            return signal("amarillo", indicator, row, "Tasa real restrictiva", f"Tasa real ex post aprox. en {value:.2f} pp.", "valor")
        return signal("verde", indicator, row, "Tasa real menos restrictiva", f"Tasa real ex post aprox. en {value:.2f} pp.", "valor")

    if rule == "imacec":
        p = df[df["serie_id"].eq(sid)].sort_values("fecha")
        if len(p) < 13 or pd.isna(yoy):
            return signal("gris", indicator, row, "IMACEC sin historia suficiente", "No hay suficientes meses para variación anual.", "var_12m_pct")
        last2 = p["var_12m_pct"].tail(2)
        last3 = p["var_12m_pct"].tail(3)
        if len(last2) == 2 and (last2 < 0).all():
            return signal("rojo", indicator, row, "Actividad en contracción", "Variación anual negativa por dos meses consecutivos.", "var_12m_pct")
        if len(last3) == 3 and last3.is_monotonic_decreasing:
            return signal("amarillo", indicator, row, "Actividad desacelera", "La variación anual desacelera por tres meses.", "var_12m_pct")
        return signal("verde", indicator, row, "Actividad sin alerta fuerte", f"Variación anual: {yoy:.2f}%.", "var_12m_pct")

    if rule == "desempleo":
        r = rules["desempleo"]
        if pd.isna(yoy_pp):
            return signal("gris", indicator, row, "Desempleo sin comparable anual", "No hay dato suficiente para comparación 12 meses.", "var_12m_pp")
        if yoy_pp > r["red_yoy_pp"]:
            return signal("rojo", indicator, row, "Desempleo sube fuerte", f"Sube {yoy_pp:.2f} pp en 12 meses.", "var_12m_pp")
        if yoy_pp > r["yellow_yoy_pp"]:
            return signal("amarillo", indicator, row, "Desempleo al alza", f"Sube {yoy_pp:.2f} pp en 12 meses.", "var_12m_pp")
        return signal("verde", indicator, row, "Mercado laboral estable", f"Cambio 12 meses: {yoy_pp:.2f} pp.", "var_12m_pp")

    if rule == "ipsa":
        ma50, ma200 = row.get("ma_50"), row.get("ma_200")
        if pd.isna(ma50) or pd.isna(ma200):
            return signal("gris", indicator, row, "IPSA sin medias suficientes", "No hay historial suficiente para medias móviles 50/200.", "ma_50/ma_200")
        if value < ma200:
            return signal("rojo", indicator, row, "IPSA bajo media 200 días", "Señal técnica de debilidad relevante.", "ma_200")
        if value < ma50:
            return signal("amarillo", indicator, row, "IPSA bajo media 50 días", "Señal técnica de corto plazo débil.", "ma_50")
        return signal("verde", indicator, row, "IPSA sobre medias relevantes", "Señal técnica favorable bajo medias 50/200.", "ma_50/ma_200")

    if rule in {"curva", "curva_uf"}:
        if sid.startswith("pendiente") and value < 0:
            return signal("rojo", indicator, row, "Curva invertida", f"Pendiente en {value:.2f} pp.", "valor")
        if pd.notna(row.get("var_abs")) and abs(row.get("var_abs")) > 0.35:
            return signal("amarillo", indicator, row, "Movimiento relevante de tasas", f"Cambio último dato: {row.get('var_abs'):.2f} pp.", "var_abs")
        return signal("verde", indicator, row, "Curva sin alerta crítica", "No se gatillan umbrales de alerta.", "valor")

    return signal("verde", indicator, row, "Sin alerta bajo regla genérica", "Indicador disponible sin umbral específico gatillado.", "valor")


def generate_all_signals(indicators: list[dict], df: pd.DataFrame) -> pd.DataFrame:
    rows = [generate_signal(ind, df) for ind in indicators]
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["severidad", "categoria", "indicador"], ascending=[False, True, True]).reset_index(drop=True)
    return out


def market_state(signals: pd.DataFrame) -> tuple[str, str]:
    if signals.empty:
        return "sin datos", "No hay suficientes indicadores para evaluar estado general."
    red = int((signals["estado"] == "rojo").sum())
    yellow = int((signals["estado"] == "amarillo").sum())
    if red >= 3:
        return "riesgo alto", "Hay varias alertas rojas activas en el tablero."
    if red >= 1 or yellow >= 4:
        return "atención", "Existen focos de presión que requieren seguimiento."
    if yellow >= 1:
        return "neutral", "El mercado presenta señales mixtas, sin alerta sistémica."
    return "favorable", "Las señales principales se mantienen estables o favorables."


def automatic_reading(signals: pd.DataFrame) -> list[str]:
    if signals.empty:
        return ["No hay datos suficientes para generar lectura automática."]
    top = signals[signals["estado"].isin(["rojo", "amarillo"])].head(5)
    if top.empty:
        return ["Mercado local sin alertas relevantes bajo las reglas configuradas."]
    bullets = []
    for _, row in top.iterrows():
        bullets.append(f"{row['indicador']}: {row['mensaje']} — {row['explicacion']}")
    return bullets[:5]
