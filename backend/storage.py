#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Persistencia JSON para listings y timestamps de actualizacion.
"""

import json
import logging
import os
import tempfile
import threading
from pathlib import Path

logger = logging.getLogger(__name__)
from datetime import datetime, timezone

DATA_DIR = Path(__file__).parent / "data"
LISTINGS_FILE = DATA_DIR / "listings_data.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
_storage_lock = threading.Lock()


def _ensure_dir():
    DATA_DIR.mkdir(exist_ok=True)


def _atomic_write(filepath, data):
    """Escritura atomica: temp file + rename."""
    _ensure_dir()
    fd, tmp = tempfile.mkstemp(dir=DATA_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, str(filepath))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _read_json(filepath, default):
    if not filepath.exists():
        return default
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        logger.error("JSON corrupto en %s, usando default", filepath)
        return default


# ================== LISTINGS ==================

def load_listings():
    """Retorna lista de listings guardados."""
    return _read_json(LISTINGS_FILE, [])


def save_listings(listings):
    """Guarda la lista completa de listings."""
    _atomic_write(LISTINGS_FILE, listings)


def get_listing(listing_id):
    """Busca un listing por ID. Retorna None si no existe."""
    listing_id = str(listing_id)
    for l in load_listings():
        if str(l["listing_id"]) == listing_id:
            return l
    return None


def upsert_listing(listing):
    """Agrega o actualiza un listing (thread-safe)."""
    listing["listing_id"] = str(listing["listing_id"])
    with _storage_lock:
        listings = load_listings()
        listing_id = listing["listing_id"]
        for i, l in enumerate(listings):
            if str(l["listing_id"]) == listing_id:
                listings[i] = listing
                save_listings(listings)
                return
        listings.append(listing)
        save_listings(listings)


def delete_listing(listing_id):
    """Elimina un listing por ID (thread-safe). Retorna True si se elimino."""
    listing_id = str(listing_id)
    with _storage_lock:
        listings = load_listings()
        original_len = len(listings)
        listings = [l for l in listings if str(l["listing_id"]) != listing_id]
        if len(listings) < original_len:
            save_listings(listings)
            return True
        return False


def update_timestamp(listing_id):
    """Actualiza el timestamp de ultima actualizacion de un listing (thread-safe)."""
    with _storage_lock:
        listings = load_listings()
        listing_id = str(listing_id)
        now = datetime.now(timezone.utc).isoformat()
        for l in listings:
            if str(l["listing_id"]) == listing_id:
                l["last_updated"] = now
                save_listings(listings)
                return now
        return None


def update_last_error(listing_id, error_msg):
    """Guarda o limpia el ultimo error de scraping de un listing (thread-safe)."""
    with _storage_lock:
        listings = load_listings()
        listing_id = str(listing_id)
        for l in listings:
            if str(l["listing_id"]) == listing_id:
                l["last_error"] = error_msg
                save_listings(listings)
                return


# ================== SETTINGS ==================

def load_settings():
    """Retorna el dict de settings guardado."""
    return _read_json(SETTINGS_FILE, {})


def save_setting(key, value):
    """Guarda un setting individual (thread-safe)."""
    with _storage_lock:
        settings = load_settings()
        settings[key] = value
        _atomic_write(SETTINGS_FILE, settings)


def get_setting(key, default=None):
    """Obtiene un setting por key."""
    return load_settings().get(key, default)


# ================== MIGRATIONS ==================

def ensure_manual_dates_field():
    """Agrega manual_dates=[] a listings existentes que no tengan el campo."""
    with _storage_lock:
        listings = load_listings()
        changed = False
        for l in listings:
            if "manual_dates" not in l:
                l["manual_dates"] = []
                changed = True
        if changed:
            save_listings(listings)


def ensure_ical_enabled_field():
    """Agrega ical_enabled=True a listings existentes que no tengan el campo."""
    with _storage_lock:
        listings = load_listings()
        changed = False
        for l in listings:
            if "ical_enabled" not in l:
                l["ical_enabled"] = True
                changed = True
        if changed:
            save_listings(listings)


def ensure_address_state_fields():
    """Agrega address='' y state='' a listings existentes que no tengan los campos."""
    with _storage_lock:
        listings = load_listings()
        changed = False
        for l in listings:
            if "address" not in l:
                l["address"] = ""
                changed = True
            if "state" not in l:
                l["state"] = ""
                changed = True
        if changed:
            save_listings(listings)


def ensure_last_error_field():
    """Agrega last_error=None a listings existentes que no tengan el campo."""
    with _storage_lock:
        listings = load_listings()
        changed = False
        for l in listings:
            if "last_error" not in l:
                l["last_error"] = None
                changed = True
        if changed:
            save_listings(listings)


def ensure_start_date_field():
    """Agrega start_date=None a listings existentes que no tengan el campo."""
    with _storage_lock:
        listings = load_listings()
        changed = False
        for l in listings:
            if "start_date" not in l:
                l["start_date"] = None
                changed = True
        if changed:
            save_listings(listings)


def build_initial_listings():
    """
    Construye la lista inicial de listings a partir de listings.py
    si no existe data guardada. Solo se corre una vez.
    """
    if LISTINGS_FILE.exists():
        return load_listings()

    from listings import (
        PRIMARY_LISTINGS, PRIMARY_BEDROOM_FILTER,
        AVAILABILITY_ONLY_LISTINGS, SECONDARY_BEDROOM_FILTER,
    )

    seen = {}
    for entry in PRIMARY_LISTINGS:
        lid = str(entry["listing_id"])
        if lid not in seen:
            seen[lid] = {
                "listing_id": lid,
                "resort_codes": [entry["resort_code"]],
                "bedrooms": PRIMARY_BEDROOM_FILTER.get(lid, "0"),
                "title": "",
                "sync_mode": "primary",
                "last_updated": None,
                "ical_enabled": True,
            }
        else:
            if entry["resort_code"] not in seen[lid]["resort_codes"]:
                seen[lid]["resort_codes"].append(entry["resort_code"])

    for entry in AVAILABILITY_ONLY_LISTINGS:
        lid = str(entry["listing_id"])
        if lid not in seen:
            seen[lid] = {
                "listing_id": lid,
                "resort_codes": [entry["resort_code"]],
                "bedrooms": SECONDARY_BEDROOM_FILTER.get(lid, "0"),
                "title": "",
                "sync_mode": "secondary",
                "last_updated": None,
                "ical_enabled": True,
            }
        else:
            if entry["resort_code"] not in seen[lid]["resort_codes"]:
                seen[lid]["resort_codes"].append(entry["resort_code"])

    listings = list(seen.values())
    save_listings(listings)
    return listings
