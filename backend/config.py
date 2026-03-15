#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


def _env(key, default=None):
    val = os.getenv(key, default)
    if val is None:
        raise RuntimeError(f"Variable de entorno requerida no encontrada: {key}")
    return val


# ================== INTERVAL WORLD ==================
INTERVAL_USERNAME = _env("INTERVAL_USERNAME")
INTERVAL_PASSWORD = _env("INTERVAL_PASSWORD")

# ================== HOSTAWAY API (opcional, legacy) ==================
HOSTAWAY_ACCOUNT_ID = _env("HOSTAWAY_ACCOUNT_ID", "")
HOSTAWAY_API_SECRET = _env("HOSTAWAY_API_SECRET", "")

# ================== DATES ==================
DATE_RANGE_DAYS = int(_env("DATE_RANGE_DAYS", "365"))
DATE_RANGE_START = datetime.today()
DATE_RANGE_END = DATE_RANGE_START + timedelta(days=DATE_RANGE_DAYS)

# ================== SCRAPER ==================
HEADLESS = _env("HEADLESS", "false").lower() == "true"

# ================== SCRAPER SPEED KNOBS ==================
SPEED_FACTOR = float(_env("SPEED_FACTOR", "0.9"))
VACATION_EXCHANGE_TIMEOUT = int(_env("VACATION_EXCHANGE_TIMEOUT", "20"))
VACATION_EXCHANGE_PAUSE = float(_env("VACATION_EXCHANGE_PAUSE", "0.5"))
MORE_DATES_PAUSE = float(_env("MORE_DATES_PAUSE", "0.8"))
MAX_MORE_DATES_CLICKS = int(_env("MAX_MORE_DATES_CLICKS", "8"))
DATE_INPUT_PAUSE = float(_env("DATE_INPUT_PAUSE", "0.4"))
DATE_KEY_DELAY = float(_env("DATE_KEY_DELAY", "0.02"))
DATE_INPUT_RETRIES = int(_env("DATE_INPUT_RETRIES", "2"))

# ================== AIRBNB ==================
AIRBNB_EMAIL = _env("AIRBNB_EMAIL", "")
AIRBNB_PASSWORD = _env("AIRBNB_PASSWORD", "")

# ================== ICAL SERVER ==================
ICAL_SERVER_HOST = _env("ICAL_SERVER_HOST", "0.0.0.0")
ICAL_SERVER_PORT = int(_env("ICAL_SERVER_PORT", "8085"))
ICS_OUTPUT_DIR = Path(__file__).parent / _env("ICS_OUTPUT_DIR", "ics_files")
