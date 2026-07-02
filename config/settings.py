from __future__ import annotations

from datetime import date

APP_NAME = "Monitor Mercado Chile"
APP_VERSION = "v38_deriv_menu_summary_report"
DEFAULT_START = date(2024, 1, 1)
MAX_START = date(2010, 1, 1)
CACHE_TTL_SECONDS = 60 * 60
BCCH_TIMEOUT_SECONDS = 25
BCCH_MAX_WORKERS = 6

COLORS = {
    "bg": "#041F5F",
    "panel": "#081B45",
    "panel_2": "#0A2A66",
    "text": "#F5F7FA",
    "muted": "#BFD1F5",
    "grid": "rgba(255,255,255,0.08)",
    "primary": "#8B3DFF",
    "cyan": "#58C7F3",
    "blue": "#3E7BFA",
    "green": "#22C55E",
    "yellow": "#FACC15",
    "red": "#FB7185",
    "gray": "#94A3B8",
}

SIGNAL_RULES = {
    "usdclp": {"yellow_30d_up": 2.0, "red_30d_up": 5.0},
    "copper": {"yellow_30d_down": -4.0, "red_30d_down": -8.0},
    "ipc": {"green_upper": 4.0, "yellow_upper": 5.0, "red_upper": 6.0},
    "tasa_real": {"yellow": 2.0, "red": 4.0},
    "imacec": {"red_consecutive_negative_yoy": 2, "yellow_slowdown_months": 3},
    "desempleo": {"yellow_yoy_pp": 0.5, "red_yoy_pp": 1.0},
    "ipsa": {"ma_short": 50, "ma_long": 200},
    "curva": {"yellow_30d_bp": 35.0, "red_30d_bp": 75.0, "inversion_threshold": 0.0},
}

RANGE_PRESETS = ["1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y", "Máximo", "Personalizado"]
FREQUENCIES = ["Original", "Diaria", "Semanal", "Mensual", "Trimestral"]
