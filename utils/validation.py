from __future__ import annotations

import pandas as pd


def validate_indicator_data(df: pd.DataFrame, expected_frequency: str = "") -> dict:
    if df.empty:
        return {"estado_calidad": "Sin datos", "duplicados": 0, "nulos": 0, "saltos_extremos": 0, "ultima_fecha": None, "observaciones": 0}
    data = df.copy()
    data["fecha"] = pd.to_datetime(data["fecha"])
    data["valor"] = pd.to_numeric(data["valor"], errors="coerce")
    duplicates = int(data.duplicated(["fecha", "serie_id"]).sum())
    nulls = int(data["valor"].isna().sum())
    pct = data.sort_values("fecha")["valor"].pct_change().abs() * 100
    jumps = int((pct > 25).sum())
    latest = data["fecha"].max()
    stale_days = (pd.Timestamp.today().normalize() - latest.normalize()).days if pd.notna(latest) else None
    estado = "OK"
    if nulls > 0 or duplicates > 0:
        estado = "Revisar"
    if jumps > 0:
        estado = "Saltos inusuales"
    if expected_frequency == "D" and stale_days is not None and stale_days > 10:
        estado = "Datos desactualizados"
    if expected_frequency == "M" and stale_days is not None and stale_days > 70:
        estado = "Datos desactualizados"
    return {
        "estado_calidad": estado,
        "duplicados": duplicates,
        "nulos": nulls,
        "saltos_extremos": jumps,
        "ultima_fecha": latest,
        "observaciones": len(data),
        "rezago_dias": stale_days,
    }


def build_health_table(df: pd.DataFrame, indicators: list[dict], diagnostics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ind in indicators:
        part = df[df["serie_id"].eq(ind["id"])] if not df.empty else pd.DataFrame()
        q = validate_indicator_data(part, ind.get("frequency", ""))
        diag = diagnostics[diagnostics["serie_id"].eq(ind["id"])] if diagnostics is not None and not diagnostics.empty else pd.DataFrame()
        source_state = diag["estado_fuente"].iloc[0] if not diag.empty and "estado_fuente" in diag else ("OK" if not part.empty else "Sin datos")
        rows.append({
            "serie_id": ind["id"],
            "indicador": ind["name"],
            "categoria": ind["category"],
            "fuente": ind.get("source", ""),
            "codigo": ind.get("code"),
            "estado_fuente": source_state,
            **q,
        })
    return pd.DataFrame(rows)
