# Guía de mapeo de series BCCh para el monitor de derivados

El objetivo de esta etapa es reemplazar el auto-mapeo por un mapeo validado y estable.  
El archivo final productivo debe ser `config/series_map.csv`, con un `series_id` correcto para cada `logical_series`.

## 1. Generar candidatos

```bash
python scripts/04_generate_series_review.py --refresh-catalog --top 20
```

Esto descarga el catálogo BCCh por frecuencia desde la API BDE y genera:

```text
outputs/mapeo_series/series_candidates_review.csv
outputs/mapeo_series/series_candidates_best_summary.csv
```

## 2. Revisar candidatos

Abre `outputs/mapeo_series/series_candidates_review.csv` y valida manualmente una fila por `logical_series`.

Marca con `1` la columna `selected` en la serie correcta.

Criterios de validación:

1. La frecuencia debe calzar: `MONTHLY` o `DAILY`.
2. El título debe coincidir con el camino BDE esperado (`bde_path`).
3. Deben coincidir monto vigente vs monto transado.
4. Deben coincidir USD-CLP vs ME-ML.
5. Deben coincidir contraparte, instrumento o plazo según el gráfico.
6. Para SPC, evitar series UF, OIS, basis o tasas externas.
7. Para UF-CLP, evitar series de monedas o Swap Promedio Cámara.

## 3. Aplicar selección

```bash
python scripts/05_apply_review_selection.py
```

Esto genera:

```text
config/series_map_validado.csv
```

Cuando esté revisado, puedes reemplazar:

```bash
copy config\series_map_validado.csv config\series_map.csv
```

## 4. Correr la app sin auto-mapeo

En Streamlit, desactiva el auto-mapeo.  
Desde ese momento la app mensual usará solo el mapeo validado.

## Familias BDE principales

- D01: Derivados > Resumen > Bancos > Montos vigentes / Montos transados.
- D02: Derivados > Monedas > Bancos > Bancos mensual > USD-CLP.
- D03: Derivados > Monedas > Bancos diario/mensual + Spot USD-CLP + Total derivados + spot.
- D04: Derivados > Tasa de interés > Swap Promedio Cámara en pesos > Bancos mensual.
- D05: Derivados > Unidad de Fomento - Peso Chileno > Bancos mensual.
- D06: Se calcula a partir de las series ya validadas de D01-D05.
