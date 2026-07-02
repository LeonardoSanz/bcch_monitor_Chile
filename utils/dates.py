from __future__ import annotations

from datetime import date
import pandas as pd
from dateutil.relativedelta import relativedelta

from config.settings import MAX_START


def preset_to_dates(preset: str, today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    if preset == "1M":
        return today - relativedelta(months=1), today
    if preset == "3M":
        return today - relativedelta(months=3), today
    if preset == "6M":
        return today - relativedelta(months=6), today
    if preset == "YTD":
        return date(today.year, 1, 1), today
    if preset == "1Y":
        return today - relativedelta(years=1), today
    if preset == "3Y":
        return today - relativedelta(years=3), today
    if preset == "5Y":
        return today - relativedelta(years=5), today
    if preset == "Máximo":
        return MAX_START, today
    return today - relativedelta(years=3), today


def to_bcch_date(value: date | str | pd.Timestamp) -> str:
    return pd.to_datetime(value).strftime("%Y-%m-%d")
