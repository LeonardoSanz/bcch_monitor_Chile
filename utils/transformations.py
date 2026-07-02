from __future__ import annotations

import numpy as np
import pandas as pd


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out["fecha"] = pd.to_datetime(out["fecha"])
    out["year"] = out["fecha"].dt.year
    out["month"] = out["fecha"].dt.month
    out["quarter"] = out["fecha"].dt.to_period("Q").astype(str)
    return out


def add_transformations(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega variaciones, medias móviles, z-score y base 100 por serie."""
    if df.empty:
        return df
    out = df.copy()
    out["fecha"] = pd.to_datetime(out["fecha"])
    out["valor"] = pd.to_numeric(out["valor"], errors="coerce")
    out = out.dropna(subset=["fecha", "valor", "serie_id"]).sort_values(["serie_id", "fecha"])
    g = out.groupby("serie_id", group_keys=False)
    out["var_abs"] = g["valor"].diff()
    out["var_pct"] = g["valor"].pct_change() * 100
    out["var_7d_pct"] = g["valor"].pct_change(7) * 100
    out["var_30d_pct"] = g["valor"].pct_change(30) * 100
    out["var_3m_pct"] = g["valor"].pct_change(3) * 100
    out["var_12m_pct"] = g["valor"].pct_change(12) * 100
    out["var_12m_pp"] = g["valor"].diff(12)
    out["ma_7"] = g["valor"].transform(lambda s: s.rolling(7, min_periods=3).mean())
    out["ma_30"] = g["valor"].transform(lambda s: s.rolling(30, min_periods=10).mean())
    out["ma_50"] = g["valor"].transform(lambda s: s.rolling(50, min_periods=20).mean())
    out["ma_200"] = g["valor"].transform(lambda s: s.rolling(200, min_periods=60).mean())
    first = g["valor"].transform("first")
    out["base_100"] = np.where(first != 0, out["valor"] / first * 100, np.nan)
    mean_252 = g["valor"].transform(lambda s: s.rolling(252, min_periods=30).mean())
    std_252 = g["valor"].transform(lambda s: s.rolling(252, min_periods=30).std())
    out["zscore_252"] = (out["valor"] - mean_252) / std_252
    out["_year_tmp"] = out["fecha"].dt.year
    first_ytd = out.groupby(["serie_id", "_year_tmp"])["valor"].transform("first")
    out["ytd_pct"] = (out["valor"] / first_ytd - 1) * 100
    out = out.drop(columns=["_year_tmp"])
    return out.sort_values(["serie_id", "fecha"]).reset_index(drop=True)


def latest_by_indicator(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    return df.sort_values("fecha").groupby("serie_id", as_index=False).tail(1).reset_index(drop=True)


def resample_data(df: pd.DataFrame, frequency: str) -> pd.DataFrame:
    """Remuestrea series con alias compatibles con pandas 3.x.

    Alias seguros:
    - Mensual / M -> ME
    - Trimestral / Q -> QE
    - Semanal -> W-SUN

    Si alguna serie no puede remuestrearse, se conserva su versión original para
    que el dashboard no se caiga completo.
    """
    if df is None or df.empty or frequency in {None, "", "Original"}:
        return df if df is not None else pd.DataFrame()

    rule = {
        "Diaria": "D",
        "D": "D",
        "Semanal": "W-SUN",
        "W": "W-SUN",
        "W-SUN": "W-SUN",
        "Mensual": "ME",
        "M": "ME",
        "ME": "ME",
        "Trimestral": "QE",
        "Q": "QE",
        "QE": "QE",
    }.get(str(frequency), None)

    if not rule or "serie_id" not in df.columns:
        return df

    frames = []
    for sid, part in df.groupby("serie_id", dropna=False):
        p = part.copy()
        p["fecha"] = pd.to_datetime(p["fecha"], errors="coerce")
        p["valor"] = pd.to_numeric(p["valor"], errors="coerce")
        p = p.dropna(subset=["fecha", "valor"]).sort_values("fecha")
        if p.empty:
            continue

        try:
            numeric = p.set_index("fecha")["valor"].resample(rule).last().dropna().to_frame("valor")
        except Exception:
            frames.append(p)
            continue

        if numeric.empty:
            continue

        meta_cols = [c for c in p.columns if c not in ["fecha", "valor"]]
        last_meta = p.iloc[-1][meta_cols].to_dict()
        for k, v in last_meta.items():
            numeric[k] = v

        numeric["serie_id"] = sid
        frames.append(numeric.reset_index())

    return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame(columns=df.columns)



def make_spread(df: pd.DataFrame, long_id: str, short_id: str, new_id: str, name: str, category: str, unit: str = "pp") -> pd.DataFrame:
    """Calcula spread 10Y-2Y sin inventar datos y conserva auditoría de patas."""
    if df is None or df.empty:
        return pd.DataFrame()

    a = df[df["serie_id"].eq(long_id)][["fecha", "valor"]].copy().rename(columns={"valor": "long"})
    b = df[df["serie_id"].eq(short_id)][["fecha", "valor"]].copy().rename(columns={"valor": "short"})

    if a.empty or b.empty:
        return pd.DataFrame()

    a["fecha"] = pd.to_datetime(a["fecha"], errors="coerce")
    b["fecha"] = pd.to_datetime(b["fecha"], errors="coerce")
    a = a.dropna(subset=["fecha", "long"]).sort_values("fecha")
    b = b.dropna(subset=["fecha", "short"]).sort_values("fecha")
    a["long_fecha"] = a["fecha"]
    b["short_fecha"] = b["fecha"]

    merged = pd.merge_asof(
        a,
        b,
        on="fecha",
        direction="nearest",
        tolerance=pd.Timedelta("10D"),
    )
    merged = merged.dropna(subset=["long", "short"])

    if merged.empty:
        return pd.DataFrame()

    merged["desfase_dias"] = (merged["long_fecha"] - merged["short_fecha"]).abs().dt.days
    out = pd.DataFrame({
        "fecha": merged["fecha"],
        "valor": merged["long"] - merged["short"],
        "serie_id": new_id,
        "nombre_indicador": name,
        "categoria": category,
        "frecuencia": "D",
        "unidad": unit,
        "fuente": "Derivado",
        "fecha_actualizacion": pd.Timestamp.utcnow().isoformat(),
        "estado_fuente": "OK",
        "code": None,
        "spread_long_id": long_id,
        "spread_short_id": short_id,
        "spread_long_valor": merged["long"],
        "spread_short_valor": merged["short"],
        "spread_long_fecha": merged["long_fecha"],
        "spread_short_fecha": merged["short_fecha"],
        "spread_desfase_dias": merged["desfase_dias"],
    })
    return out


def build_derived_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Construye tasa real y pendientes de curva cuando existen las series base."""
    frames = [df]
    if not df.empty:
        # TPM menos IPC anual, usando último dato cercano de inflación.
        tpm = df[df["serie_id"].eq("tpm")][["fecha", "valor"]].rename(columns={"valor": "tpm"}).sort_values("fecha")
        ipc = df[df["serie_id"].eq("ipc_anual")][["fecha", "valor"]].rename(columns={"valor": "ipc"}).sort_values("fecha")
        if not tpm.empty and not ipc.empty:
            merged = pd.merge_asof(tpm, ipc, on="fecha", direction="backward", tolerance=pd.Timedelta("70D")).dropna()
            if not merged.empty:
                real = pd.DataFrame({
                    "fecha": merged["fecha"], "valor": merged["tpm"] - merged["ipc"],
                    "serie_id": "tasa_real_ex_post", "nombre_indicador": "Tasa real ex post aprox.",
                    "categoria": "Inflación y reajustes", "frecuencia": "D", "unidad": "pp", "fuente": "Derivado",
                    "fecha_actualizacion": pd.Timestamp.utcnow().isoformat(), "estado_fuente": "OK", "code": None,
                })
                frames.append(real)
        for long_id, short_id, new_id, name in [
            ("bcp_10y", "bcp_2y", "pendiente_nominal", "Pendiente curva nominal 10Y-2Y"),
            ("bcu_10y", "bcu_2y", "pendiente_uf", "Pendiente curva UF 10Y-2Y"),
        ]:
            spread = make_spread(df, long_id, short_id, new_id, name, "Tasas y renta fija")
            if not spread.empty:
                frames.append(spread)
    return pd.concat(frames, ignore_index=True, sort=False) if frames else df
