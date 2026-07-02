# Monitor Mercado Chile · v23 clean AFP style

Monitor financiero y macroeconómico de Chile construido en Python/Streamlit. La app usa principalmente la API BDE/SieteWS del Banco Central de Chile para consultar indicadores de tipo de cambio, inflación, tasas, actividad, mercado laboral, commodities, bolsa local, riesgo externo, fiscal y expectativas.

## Objetivo

Crear una herramienta ejecutiva, modular y escalable para revisar el estado del mercado chileno con:

- KPIs ejecutivos.
- Gráficos Plotly interactivos.
- Señales tipo semáforo.
- Calidad de datos por indicador.
- Descarga CSV/Excel.
- Catálogo centralizado de indicadores.
- Metodología transparente.

## Estructura del proyecto

```text
app.py
config/
  indicators.py
  settings.py
services/
  bcch_client.py
  cmf_client.py
  ine_client.py
  external_sources.py
components/
  kpi_cards.py
  charts.py
  tables.py
  alerts.py
utils/
  dates.py
  formatting.py
  transformations.py
  signals.py
  validation.py
data/
exports/
assets/
requirements.txt
README.md
```

## Seguridad

La versión actual usa **login manual SieteWS en pantalla**. Las credenciales:

- no están hardcodeadas;
- no se escriben en archivos;
- no se suben a GitHub;
- no se imprimen en pantalla ni logs;
- viven solo en `st.session_state` durante la sesión.

Existe un ejemplo de `secrets.toml` solo como referencia en `examples/secrets.toml.example`, sin credenciales reales:

```toml
[general]
BCCH_USER = "tu_usuario"
BCCH_PASS = "tu_password"
```

## Instalación local

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
streamlit run app.py
```

En macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Despliegue en Streamlit Cloud

1. Subir el repositorio a GitHub.
2. Verificar que `.streamlit/secrets.toml` no esté en el repo.
3. Crear app en Streamlit Cloud apuntando a `app.py`.
4. Ingresar credenciales manualmente en la pantalla inicial de la app.

## Fuentes de datos

Fuente principal:

- Banco Central de Chile, API BDE/SieteWS.

Fuentes preparadas para crecimiento futuro:

- CMF.
- INE directo.
- Fuentes externas para riesgo país, mercado global o crédito.

Cuando un indicador no tiene código confirmado o fuente implementada, queda explícito como `TODO` en `config/indicators.py`. No se inventan datos ni códigos.

## Indicadores disponibles inicialmente

Implementados vía SieteWS, entre otros:

- USD/CLP.
- Euro/CLP.
- MER, MER-5, MER-X.
- UF.
- UTM.
- IPC mensual.
- IPC anual.
- TPM.
- Tasa interbancaria.
- Curva nominal pesos.
- Curva UF.
- IMACEC total y componentes.
- PIB trimestral.
- Desempleo.
- Ocupados.
- Cobre, oro y plata.
- IPSA.
- Reservas internacionales.
- Treasury 10Y EE.UU.
- TPM EE.UU.
- Deuda pública / PIB.
- Expectativas EEE/EOF.

Pendientes explícitos:

- Tasas CMF de interés corriente y máxima convencional.
- Algunas tasas de crédito.
- Informalidad laboral directa.
- EMBI/CDS Chile.
- Balance fiscal y gasto público.
- Volumen transado bolsa local.

## Metodología de transformaciones

La app calcula:

- Variación contra dato anterior.
- Variación 7 días.
- Variación 30 días.
- Variación 3 meses.
- Variación 12 meses.
- Variación YTD.
- Media móvil 7, 30, 50 y 200 observaciones.
- Z-score 252 observaciones.
- Base 100.
- Tasa real ex post aproximada: TPM menos IPC anual.
- Pendiente curva nominal: 10Y - 2Y.
- Pendiente curva UF: 10Y - 2Y.

## Semáforos

Estados:

- Verde: estable/favorable bajo regla configurada.
- Amarillo: atención.
- Rojo: alerta.
- Gris: sin datos suficientes o fuente pendiente.

Las reglas están en `config/settings.py` y se aplican desde `utils/signals.py`.

## Calidad de datos

El módulo `utils/validation.py` revisa:

- Duplicados.
- Valores nulos.
- Saltos extremos.
- Última fecha disponible.
- Rezago de publicación.
- Estado de fuente.

## Roadmap

- Alertas por email.
- Alertas por Telegram/Teams.
- Base histórica local en Parquet.
- Comparación Chile vs LatAm.
- Integración con portafolio propio.
- Módulo de renta fija más profundo.
- Módulo bancario CMF.
- Módulo inmobiliario.
- API propia del monitor.
- Backtesting de señales.
- Dashboard ejecutivo exportable a PDF.

## Disclaimer

Esta herramienta es informativa y de apoyo analítico. No constituye recomendación de inversión ni reemplaza fuentes oficiales o validación profesional.


## Cambios v23

- Limpieza visual profunda: se elimina multiselect gigante y se usa navegación horizontal tipo Monitor AFP.
- Solo se cargan indicadores implementados con código confirmado; pendientes/TODO quedan fuera del dashboard.
- Se corrigen cards KPI para que no aparezca HTML crudo.
- Se corrige `StreamlitInvalidHeightError` en tablas.
- Se recupera el módulo de tasas con vistas de TPM, expectativas EEE/EOF, curva nominal, curva UF, interbancario y spreads.
- La pendiente 10Y-2Y se deja como spread técnico explicado, no como gráfico principal del resumen.


## Cambios v23.1

- Corrige error `NameError` producido por CSS dentro de `f-string`.
- Se escapan correctamente las llaves CSS.
- Se oculta el correo/usuario SieteWS en pantalla; solo se muestra sesión activa.


## Cambios v23.2

- Corrige error de `pandas.resample()` en Streamlit Cloud.
- Actualiza alias de frecuencia:
  - Mensual: `ME`
  - Trimestral: `QE`
  - Semanal: `W-SUN`
- Agrega fallback para que un error de remuestreo no bote toda la app.


## Cambios v23.3

- Corrige `NameError: generate_signals is not defined`.
- Agrega wrapper seguro `generate_signals()` en `app.py`.
- Si una regla de señal falla, se marca gris y la app continúa cargando.


## Cambios v24

- Revisión larga de estabilidad para Streamlit Cloud 1.58 / Python 3.14 / pandas 3.
- Se agregan `__init__.py` a `components`, `config`, `services` y `utils` para estabilizar imports.
- Se elimina el CSS dentro de `f-string`; ahora usa placeholders seguros para evitar `NameError: border`.
- Se corrige definitivamente `height nulo` en tablas.
- Se actualiza la app a `width="stretch"` donde corresponde.
- Se corrigen alias de remuestreo: `M -> ME`, `Q -> QE`.
- Se agrega fallback defensivo en filtros, remuestreo, transformaciones y señales.
- Se reemplaza `validate_dataset` por `build_health_table`, que sí existe en `utils.validation`.
- La app queda sin credenciales hardcodeadas y sin imprimir usuario/clave.


## Cambios v25

- Corrige la curva UF: se reemplazan series de licitación primaria BCU por tasas de mercado secundario de bonos en UF (BCU/BTU), códigos `F022.BUF.TIS.*.UF.Z.D`.
- Amplía curva UF a 1Y, 2Y, 5Y, 10Y, 20Y y 30Y cuando exista data.
- Los gráficos de línea ahora cortan la línea ante brechas largas de datos; ya no conectan visualmente enero 2022 con julio 2023 como si fuera una interpolación válida.
- Agrega tablas de cobertura para curva UF y spreads técnicos.


## Cambios v26

- Agrega auditoría explícita de brechas para spreads técnicos 10Y-2Y.
- Muestra componentes nominales 2Y y 10Y antes del spread.
- Muestra componentes UF 2Y y 10Y antes del spread.
- Agrega tabla de cobertura por serie.
- Agrega tabla de brechas mayores a 45 días.
- Agrega observaciones por año para detectar si el vacío viene de la pata base o del cálculo del spread.
- El cálculo de spread conserva fecha y valor de cada pata para auditoría.


## Cambios v28

- Reconstrucción desde la base estable `v38_deriv_menu_summary_report`, no desde la v27 reducida.
- La app usa ancho completo real (`max-width: 100%`).
- Se integra el proyecto de derivados completo bajo `derivatives_app/`, manteniendo:
  - `src/chart_registry.py`;
  - todos los módulos `src/charts/d01...`, `d02...`, `d04...`, `d05...`;
  - `config/series_map.csv`;
  - `config/monitor_mensual_links.csv`;
  - documentación y referencias no sensibles.
- No se copian `.env`, `.streamlit/secrets.toml`, `run_app.bat`, `__pycache__` ni credenciales.
- El cliente BCCh del módulo derivados fue saneado para no tener usuario/clave hardcodeados.
- El módulo derivados usa las mismas credenciales SieteWS activas del monitor principal.
- Si una serie SieteWS de derivados falla, el gráfico usa fallback a la ruta BDE oficial del proyecto de derivados.
- La sección Señales reemplaza el heatmap confuso por un resumen apilado por categoría y estado.
- El resumen vuelve a incluir PIB trimestral como card/gráfico.


## Cambios v29

- Se corrige el error de Cloud `ModuleNotFoundError: No module named 'src'`.
- El runtime del proyecto de derivados queda en `derivatives_src/` con imports propios, no como paquete genérico `src`.
- `components/derivatives_section.py` ya no bota toda la app si falta una carpeta; muestra error amigable en la pestaña Derivados.
- `app.py` tiene fallback defensivo si el módulo de derivados no está completo.
- `components/tables.py` usa `width="stretch"` y `height="content"`, compatible con Streamlit 1.58.
- Se mantiene `derivatives_app/config/` para mapas y metadatos del proyecto original de derivados.
- No hay credenciales hardcodeadas; las credenciales siguen viniendo de login manual/session state o secrets.


## Cambios v30

- Derivados ahora tiene navegación de 3 niveles: módulo, submenú y gráfico.
- Se homologa el tema visual de gráficos de derivados al tema oscuro CMF.
- Se elimina fondo blanco en el módulo Derivados.
- Se mantiene el proyecto de derivados completo bajo `derivatives_src/` y `derivatives_app/config/`.


## Cambios v31

- Se elimina el tercer desplegable de Derivados.
- Derivados ahora usa solo dos desplegables:
  1. módulo D01/D02/D04/D05;
  2. submenú A/B/C...
- Siempre se muestran todos los gráficos del submenú seleccionado.
- Se mantiene fondo oscuro CMF para los gráficos de derivados.


## Cambios v32

- Derivados usa menús horizontales tipo tabs en vez de desplegables.
- Se precargan todos los dataframes del módulo Derivados al entrar a la sección.
- La línea Total se fuerza a color cyan en gráficos oscuros.


## Cambios v33

- Derivados ya no muestra prefijos D01/D02/D04/D05 en el menú.
- El submenú ya no muestra letras A/B/C; solo títulos principales.
- Se mejora cache de derivados:
  - `cached_preload_all_derivative_frames()` usa `st.cache_data`;
  - cambiar entre módulo/vista no recalcula desde cero;
  - se recarga solo si cambia rango, mapa, usuario, versión o botón limpiar cache.
- Menús de Derivados se ven más parecidos a tabs: se ocultan los círculos de radio.
- La línea Total se mantiene visible en cyan sobre fondo oscuro.


## Cambios v34

- Se corrige y refuerza la precarga real de Derivados.
- Se agrega `cached_preload_all_derivative_frames()` con `st.cache_data`.
- El cambio de módulo/vista hace rerun visual de Streamlit, pero no recalcula ni consulta los dataframes si no cambió rango/mapa/usuario/clave/versión.
- La clave no se almacena ni se imprime: solo se usa un hash para invalidar cache si cambia.


## Cambios v35

- Corrige gráfico de PIB trimestral: ya no se corta la línea por brechas trimestrales.
- Refuerza cache de Derivados y elimina spinner interno de precarga en cambios de vista.
- Corrige `render_deriv_plotly()` para evitar recursión accidental.
- Homologa nombres del menú Derivados sin prefijos D01/D02/D04/D05.
- Agrega `Resumen derivados` con cards por:
  - Comparación de mercados;
  - FX USD/CLP;
  - SPC nominal;
  - UF/CLP.
- El resumen muestra último dato, variación mensual, estado verde/amarillo/rojo/gris y mensaje ejecutivo.


## Cambios v36

- Se conserva la navegación de Derivados como en la versión visual aprobada:
  - `1. Módulo`;
  - `2. Submenú`;
  - botones tipo tab;
  - etiquetas con D01/D02/D04/D05.
- El resumen ejecutivo de derivados queda debajo de la caja de vista actual, no encima del menú.
- Mantiene el fix del gráfico de PIB trimestral.
- Mantiene cache silencioso de derivados.


## Cambios v37

- El resumen de derivados ahora tiene su propia página interna:
  - `8.0 Resumen`;
  - `8.1 Derivados`.
- `8.0 Resumen` muestra solo cards/tabla ejecutiva de actividad.
- `8.1 Derivados` conserva la navegación aprobada:
  - `1. Módulo`;
  - `2. Submenú`;
  - etiquetas D01/D02/D04/D05;
  - todos los gráficos de la vista seleccionada.
- Se evita que el resumen quede mezclado encima del menú detallado.


## Cambios v38

- Corrige el CSS que ocultaba los textos de los botones/radios en Derivados.
- Mantiene la navegación aprobada:
  - `8.0 Resumen`;
  - `8.1 Derivados`;
  - `1. Módulo`;
  - `2. Submenú`;
  - etiquetas D01/D02/D04/D05.
- Reconstruye el Resumen de Derivados con la estructura del Informe Mensual:
  - I. Mercados de derivados;
  - II. Derivados y spot sobre tipos de cambio;
  - III. SPC nominal;
  - IV. UF-CLP.
- Agrega cards específicas para vigentes, transados, FX, spot, NDF, SPC y UF/CLP.
