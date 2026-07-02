# Guía de links y formato SIID

Este proyecto usa el archivo `config/monitor_mensual_links.csv` como puente entre los gráficos del Monitor Mensual SIID y los módulos Python.

## Qué contiene `monitor_mensual_links.csv`

- `chart_module`: módulo Python que genera el gráfico.
- `chart_id`: identificador lógico usado por `series_map.csv`.
- `sheet`: hoja del Excel fuente `BDE_DERIVADOS_MENSUAL.xlsx`.
- `excel_label`: nombre usado en el Excel para describir el gráfico.
- `bde_code`: código del cuadro BDE/SIETE.
- `bde_url`: link original al cuadro del Banco Central.
- `reference_image`: imagen embebida extraída del Excel.
- `usage_note`: descripción de cómo se usa la fuente.

## Cómo se usa en el proyecto

1. El auto-mapeo sigue activo y usa el catálogo `MONTHLY` del BCCh.
2. `catalog_matcher.py` ahora incorpora términos de `monitor_mensual_links.csv` para priorizar series cercanas a los cuadros correctos.
3. Los gráficos usan `src/charts/siid_style.py`, que aplica formato inspirado en el Monitor Mensual SIID: encabezado azul, unidad, grilla ligera, eje mensual y nota de fuente.

## Imágenes de referencia

Las imágenes originales extraídas del Excel están en:

```text
/docs/reference_images/
```

El archivo `contact_sheet.jpg` permite revisar rápidamente los 10 gráficos objetivo.

## Flujo recomendado

1. Ejecutar la app.
2. Revisar que `config/series_map_auto.csv` complete series razonables.
3. Validar visualmente los gráficos contra `/docs/reference_images/`.
4. Cuando una serie esté confirmada, copiar el `series_id` a `config/series_map.csv` para dejarlo fijo.
