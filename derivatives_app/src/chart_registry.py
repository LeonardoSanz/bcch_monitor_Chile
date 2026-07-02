from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd
import plotly.graph_objects as go

from src.io.bcch_api import BCCHClient
from src.series_registry import SeriesRegistry
from src.charts import (
    d01_resumen_stock,
    d01_resumen_flujo,
    d01_waterfall_variacion,
    d01_variacion_componentes,
    d02_der_spot_total,
    d02_der_spot_sector,
    d02_derivados_sector,
    d02_fx_instrumento,
    d02_fx_vigente_contraparte,
    d02_fx_variacion_apertura_sector,
    d02_fx_vigente_instrumento,
    d02_ndf_no_residentes_plazo,
    d02_ndf_variacion_plazo,
    d02_ndf_transados_plazo,
    d02_ndf_transados_variacion_plazo,
    d02_spot_sector,
    d02_spot_neto_sector,
    d02_spot_compra_usd,
    d02_spot_compras_ventas_variacion,
    d04_spc_nominal_sector,
    d04_spc_nominal_plazo,
    d04_spc_nominal_variacion_plazo,
    d04_spc_nominal_vigente_sector,
    d04_spc_nominal_vigente_plazo,
    d04_spc_nominal_vigente_variacion_plazo,
    d05_ufclp_forward_sector,
    d05_ufclp_swap_sector,
    d05_ufclp_forward_prices,
)


BuildDf = Callable[[BCCHClient | None, SeriesRegistry, str, str, bool], pd.DataFrame]
BuildFig = Callable[[pd.DataFrame], go.Figure]


@dataclass(frozen=True)
class ChartSpec:
    block: str
    title: str
    module_name: str
    build_dataframe: BuildDf
    build_figure: BuildFig
    chart_id: str | None = None


CHARTS: list[ChartSpec] = [
    ChartSpec("D01 - Comparación de mercados", "Stock por mercado", "d01_resumen_stock", d01_resumen_stock.build_dataframe, d01_resumen_stock.build_figure, d01_resumen_stock.CHART_ID),
    ChartSpec("D01 - Comparación de mercados", "Flujo transado por mercado", "d01_resumen_flujo", d01_resumen_flujo.build_dataframe, d01_resumen_flujo.build_figure, d01_resumen_flujo.CHART_ID),
    ChartSpec("D01 - Comparación de mercados", "Variación por mercado", "d01_waterfall_variacion", d01_waterfall_variacion.build_dataframe, d01_waterfall_variacion.build_figure, d01_waterfall_variacion.CHART_ID),
    ChartSpec("D01 - Comparación de mercados", "Descomposición de la variación", "d01_variacion_componentes", d01_variacion_componentes.build_dataframe, d01_variacion_componentes.build_figure, d01_variacion_componentes.CHART_ID),

    ChartSpec("D02-A - FX USD/CLP · Visión general", "Derivados + spot", "d02_der_spot_total", d02_der_spot_total.build_dataframe, d02_der_spot_total.build_figure, d02_der_spot_total.CHART_ID),
    ChartSpec("D02-A - FX USD/CLP · Visión general", "Derivados + spot por sector", "d02_der_spot_sector", d02_der_spot_sector.build_dataframe, d02_der_spot_sector.build_figure, d02_der_spot_sector.CHART_ID),
    ChartSpec("D02-B - Derivados · Montos transados", "Derivados por sector", "d02_derivados_sector", d02_derivados_sector.build_dataframe, d02_derivados_sector.build_figure, d02_derivados_sector.CHART_ID),
    ChartSpec("D02-B - Derivados · Montos transados", "Transados por instrumento", "d02_fx_instrumento", d02_fx_instrumento.build_dataframe, d02_fx_instrumento.build_figure, d02_fx_instrumento.CHART_ID),
    ChartSpec("D02-C - Derivados · Montos vigentes", "Vigentes por contraparte", "d02_fx_vigente_contraparte", d02_fx_vigente_contraparte.build_dataframe, d02_fx_vigente_contraparte.build_figure, d02_fx_vigente_contraparte.CHART_ID),
    ChartSpec("D02-C - Derivados · Montos vigentes", "Variación por apertura y sector", "d02_fx_variacion_apertura_sector", d02_fx_variacion_apertura_sector.build_dataframe, d02_fx_variacion_apertura_sector.build_figure, d02_fx_variacion_apertura_sector.CHART_ID),
    ChartSpec("D02-C - Derivados · Montos vigentes", "Vigentes por instrumento", "d02_fx_vigente_instrumento", d02_fx_vigente_instrumento.build_dataframe, d02_fx_vigente_instrumento.build_figure, d02_fx_vigente_instrumento.CHART_ID),
    ChartSpec("D02-D - NDF · Montos vigentes", "NDF vigentes netos por plazo", "d02_ndf_no_residentes_plazo", d02_ndf_no_residentes_plazo.build_dataframe, d02_ndf_no_residentes_plazo.build_figure, d02_ndf_no_residentes_plazo.CHART_ID),
    ChartSpec("D02-D - NDF · Montos vigentes", "Comparación NDF vigentes", "d02_ndf_variacion_plazo", d02_ndf_variacion_plazo.build_dataframe, d02_ndf_variacion_plazo.build_figure, d02_ndf_variacion_plazo.CHART_ID),
    ChartSpec("D02-E - NDF · Montos transados", "NDF transados netos por plazo", "d02_ndf_transados_plazo", d02_ndf_transados_plazo.build_dataframe, d02_ndf_transados_plazo.build_figure, d02_ndf_transados_plazo.CHART_ID),
    ChartSpec("D02-E - NDF · Montos transados", "Comparación NDF transados", "d02_ndf_transados_variacion_plazo", d02_ndf_transados_variacion_plazo.build_dataframe, d02_ndf_transados_variacion_plazo.build_figure, d02_ndf_transados_variacion_plazo.CHART_ID),
    ChartSpec("D02-F - Spot USD/CLP", "Spot por sector", "d02_spot_sector", d02_spot_sector.build_dataframe, d02_spot_sector.build_figure, d02_spot_sector.CHART_ID),
    ChartSpec("D02-F - Spot USD/CLP", "Comparación spot compras/ventas USD", "d02_spot_compras_ventas_variacion", d02_spot_compras_ventas_variacion.build_dataframe, d02_spot_compras_ventas_variacion.build_figure, d02_spot_compras_ventas_variacion.CHART_ID),

    ChartSpec("D04-A - SPC nominal · Montos transados", "SPC nominal transado por sector", "d04_spc_nominal_sector", d04_spc_nominal_sector.build_dataframe, d04_spc_nominal_sector.build_figure, d04_spc_nominal_sector.CHART_ID),
    ChartSpec("D04-A - SPC nominal · Montos transados", "SPC nominal transado por plazo contractual", "d04_spc_nominal_plazo", d04_spc_nominal_plazo.build_dataframe, d04_spc_nominal_plazo.build_figure, d04_spc_nominal_plazo.CHART_ID),
    ChartSpec("D04-A - SPC nominal · Montos transados", "Comparación SPC nominal por plazo", "d04_spc_nominal_variacion_plazo", d04_spc_nominal_variacion_plazo.build_dataframe, d04_spc_nominal_variacion_plazo.build_figure, d04_spc_nominal_variacion_plazo.CHART_ID),

    ChartSpec("D04-B - SPC nominal · Montos vigentes", "SPC nominal vigente por sector", "d04_spc_nominal_vigente_sector", d04_spc_nominal_vigente_sector.build_dataframe, d04_spc_nominal_vigente_sector.build_figure, d04_spc_nominal_vigente_sector.CHART_ID),
    ChartSpec("D04-B - SPC nominal · Montos vigentes", "SPC nominal vigente por plazo residual", "d04_spc_nominal_vigente_plazo", d04_spc_nominal_vigente_plazo.build_dataframe, d04_spc_nominal_vigente_plazo.build_figure, d04_spc_nominal_vigente_plazo.CHART_ID),
    ChartSpec("D04-B - SPC nominal · Montos vigentes", "Comparación SPC nominal vigente por plazo", "d04_spc_nominal_vigente_variacion_plazo", d04_spc_nominal_vigente_variacion_plazo.build_dataframe, d04_spc_nominal_vigente_variacion_plazo.build_figure, d04_spc_nominal_vigente_variacion_plazo.CHART_ID),

    ChartSpec("D05-A - UF/CLP · Transados por instrumento", "Forward UF/CLP por sector", "d05_ufclp_forward_sector", d05_ufclp_forward_sector.build_dataframe, d05_ufclp_forward_sector.build_figure, d05_ufclp_forward_sector.CHART_ID),
    ChartSpec("D05-A - UF/CLP · Transados por instrumento", "Swap UF/CLP por sector", "d05_ufclp_swap_sector", d05_ufclp_swap_sector.build_dataframe, d05_ufclp_swap_sector.build_figure, d05_ufclp_swap_sector.CHART_ID),
    ChartSpec("D05-B - UF/CLP · Precios forward", "Precios forward UF/CLP", "d05_ufclp_forward_prices", d05_ufclp_forward_prices.build_dataframe, d05_ufclp_forward_prices.build_figure, d05_ufclp_forward_prices.CHART_ID),
]


def blocks() -> list[str]:
    return list(dict.fromkeys(chart.block for chart in CHARTS))


def charts_for_block(block: str) -> list[ChartSpec]:
    return [chart for chart in CHARTS if chart.block == block]
