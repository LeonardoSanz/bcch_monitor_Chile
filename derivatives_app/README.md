# Monitor Derivados BCCh - v18 D02 fixes

Versión mensual modular para la minuta interna de derivados bancarios.

## Cambios v18

- Corrige lectura numérica de BDE usando separador de miles `.` y decimal `,`.
  - Esto evita que `144.282` se lea como `144.282` en vez de `144282`.
  - Aplica a D01 y D02.
- Eje Y ahora muestra números completos sin notación compacta.
- Ajuste de encabezado CMF para títulos largos, evitando que se tape `Unidad: Millones de USD`.
- D02 gráfico 3 ahora usa la ruta correcta:
  - `DER_BM_SPC_02`: montos transados en derivados USD/CLP por sector de contraparte.
- D02 gráficos por instrumento y vigentes deberían mostrar la línea Total sobre las barras al corregirse la escala.

## Ejecutar

```bat
run_app.bat
```

o bien:

```bash
pip install -r requirements.txt
streamlit run app_streamlit.py
```


- v19: se corrige el cálculo de la línea Total para que refleje la suma de las barras visibles y se excluye la categoría agregada Residentes no bancos en gráficos por sector.


- v20: se corrige D02 gráfico 6 (variación de montos vigentes) calculando la diferencia mensual con un mes previo al rango para no perder el primer mes visible y mejorar el calce con la fuente BDE.


- v21: se reemplaza el antiguo D02 gráfico 6 por dos gráficos comparativos (comprador y vendedor) en la misma línea visual, con selección de mes base y mes comparación al estilo de D01.


- v22: se corrigen los filtros del bloque comprador/vendedor para DER_BM_PPC_02, aceptando filas donde el prefijo 'Monto vigente comprador/vendedor' viene en bde_series o en bde_parent.


- v23: se corrige comprador/vendedor leyendo el sector desde `bde_parent` y usando `bde_series` solo para identificar `Monto vigente comprador` / `Monto vigente vendedor` en `DER_BM_PPC_02`.

- v24: se reemplaza el bloque de variación comprador/vendedor por un bloque tipo D01: parámetros de comparación arriba, selector de apertura (Comprador/Vendedor/Neto), gráfico de variación por sector y ranking de contribución en la misma línea visual. La extracción se hace recorriendo la jerarquía visible de DER_BM_PPC_02.


- v25: se corrige el bloque D02 de variación por apertura asegurando columna `sector`, leyendo jerarquía por indentación y evitando KeyError cuando la extracción viene vacía.


- v26: ajustes estéticos en el bloque D02 variación por apertura: ejes X corregidos, fuente más abajo y márgenes/alineación mejorados.


- v29: bloque NDF corregido a 4 gráficos: vigentes netos + comparación usando DER_BD_PPC_04, y transados netos + comparación usando DER_BD_SPC_04. Se elimina lógica diaria/API para NDF.


- v30: corrección Spot USD/CLP por sector. La línea Total ahora usa el total oficial de SPT_USDCLP_S02 y se excluyen agregados al desagregar sectores para evitar duplicaciones.


- v31: ajuste visual en Spot por sector. Se robusteció la extracción del sector (serie + parent) y la línea total del gráfico se calcula desde las barras visibles para que quede alineada con el apilado.


- v32: Spot USD/CLP por sector corregido excluyendo el agregado `Residentes no bancos`. El gráfico suma solo sectores no duplicados: Interbancario, Fondos de Pensiones, Sector Real, Seguros, Corredores, AGF, Otros Sectores y No Residentes.


- v33: se agrega mapeo explícito para `Corredoras de bolsa y agencias de valores` dentro de `Corredores de Bolsa` en Spot USD/CLP.


- v34: se agrega comparador Spot Compras/Ventas USD por sector usando SPT_USDCLP_S02. Incluye solo Fondos de Pensiones, Sector Real, Cías. de Seguros, Corredores de Bolsa, AGF, Otros Sectores y No Residentes; excluye Interbancario y Residentes no bancos.


- v35: se eliminan los gráficos `Spot neto por sector` y `Spot compra USD`. El comparador Spot Compras/Ventas USD ahora lee SPT_USDCLP_S02 por orden visual de filas y no depende de `bde_parent`, corrigiendo la pérdida de datos.


- v36: pasada de orden y formato. D02 se separa en pestañas temáticas: visión general, derivados transados, derivados vigentes, NDF vigentes, NDF transados y Spot. Se compactan headers, se mejora lectura de unidad, se baja la fuente para no tapar eje X, se aumentan márgenes para etiquetas y se reposicionan cajas de variación fuera del área principal del gráfico.

- v37: ajustes finos de layout. Controles de comparación movidos a columna izquierda, fuente aún más abajo para despejar eje X y cajas de resumen/variación reubicadas dentro del canvas para que no se corten.


- v38: se corrige navegación. Las secciones D0X/sub-bloques pasan al panel izquierdo bajo las fechas; los parámetros de comparación vuelven a quedar arriba de cada gráfico comparativo.


- v39: corrección de headers de gráficos. El bloque morado ahora ajusta su altura según si el título ocupa 1, 2 o 3 líneas; la unidad queda separada y no se monta con el título.


- v40: prueba visual alternativa. Se eliminan los headers morados dentro de Plotly y los títulos/unidades pasan a tarjetas externas de Streamlit para evitar saltos de línea feos o textos montados.


- v41: se agrega D04-A SPC nominal · Montos transados usando DER_IR_SPC_07. Incluye gráficos por sector, por plazo contractual y comparador de variación por plazo con selección de compra/venta y meses.


- v42: se corrige el primer gráfico SPC nominal por sector. El filtro compra/venta ahora incluye `Total`, construido como Interbancario + Compra tasa variable + Venta tasa variable, mostrando No residentes, Interbancario y Residentes no bancos.


- v43: se agrega D04-B SPC nominal · Montos vigentes usando DER_POS_MVCP_01. Mantiene la misma lógica del bloque transado: sector, plazo residual y variación por plazo, con Total construido como Interbancario + Compra tasa variable + Venta tasa variable.


- v44: se corrige SPC nominal transado/vigente para reconocer `Compra tasa variable` y `Venta tasa variable` tanto en singular como plural. Esto recupera Compra/Venta en los parámetros y evita que el gráfico vigente por sector muestre solo Interbancario.


- v45: se agrega D05-A UF/CLP · Transados por instrumento y D05-B UF/CLP · Precios forward. En D05-A se separan Forward y Swap, con parámetro compartido de Compra UF, Venta UF, Neto y Total, y sectores Interbancario, No residentes y Residentes no bancos.


- v46: limpieza de navegación. Se eliminan del reporte los bloques antiguos `D04 - Tasas SPC CLP`, `D05 - UF/CLP inflación` y `D06 - Lectura de riesgos`. Se mantienen los nuevos bloques D04-A, D04-B, D05-A y D05-B.


- v47: se corrige parser D05-A UF/CLP. La lectura de DER_FX_MLML_02 ahora sigue la jerarquía real Forward/Swap → Interbancario/Sectores → No residentes/Residentes no bancos → Compras UF/Ventas UF/Neto. También se corrige la unidad del bloque transado a miles de UF.


- v48: se corrige D05-A UF/CLP para que Interbancario aparezca también en los gráficos de Compra UF, Venta UF y Neto. En Total se usan las filas agregadas del cuadro: Interbancario + No residentes + Residentes no bancos.


- v49: se corrige D05-B UF/CLP precios forward. El gráfico ahora usa doble eje Y: barras para montos transados forward 12 meses interbancario en miles de UF y línea para promedio de precios forward 12 meses interbancario en CLP.


- v50: se corrige error de D05-B `metric`. El dataframe final ahora conserva `metric` y `unit_metric` para separar barras de montos transados y línea de precio forward.


- v51: optimización de exportación Power BI. El botón global ahora descarga un `.xlsx` con una hoja `INDICE` y una hoja por cada gráfico del registro, en vez de un CSV consolidado del bloque visible. La generación queda cacheada por fechas, mapa de series y versión de app.


- v52: se rediseña la navegación lateral. Se reemplaza la lista de radio buttons por dos selectores jerárquicos: Mercado y Vista, reduciendo alto usado y evitando cortes visuales.
