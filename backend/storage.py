#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Persistencia JSON para listings y timestamps de actualizacion.
"""

import json
import os
import tempfile
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path(__file__).parent / "data"
LISTINGS_FILE = DATA_DIR / "listings_data.json"


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
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


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
    """Agrega o actualiza un listing."""
    listings = load_listings()
    listing_id = str(listing["listing_id"])
    for i, l in enumerate(listings):
        if str(l["listing_id"]) == listing_id:
            listings[i] = listing
            save_listings(listings)
            return
    listings.append(listing)
    save_listings(listings)


def update_timestamp(listing_id):
    """Actualiza el timestamp de ultima actualizacion de un listing."""
    listings = load_listings()
    listing_id = str(listing_id)
    now = datetime.now(timezone.utc).isoformat()
    for l in listings:
        if str(l["listing_id"]) == listing_id:
            l["last_updated"] = now
            save_listings(listings)
            return now
    return None


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
        lid = entry["listing_id"]
        if lid not in seen:
            seen[lid] = {
                "listing_id": lid,
                "resort_codes": [entry["resort_code"]],
                "bedrooms": PRIMARY_BEDROOM_FILTER.get(lid, "0"),
                "title": "",
                "sync_mode": "primary",
                "last_updated": None,
            }
        else:
            if entry["resort_code"] not in seen[lid]["resort_codes"]:
                seen[lid]["resort_codes"].append(entry["resort_code"])

    for entry in AVAILABILITY_ONLY_LISTINGS:
        lid = entry["listing_id"]
        if lid not in seen:
            seen[lid] = {
                "listing_id": lid,
                "resort_codes": [entry["resort_code"]],
                "bedrooms": SECONDARY_BEDROOM_FILTER.get(lid, "0"),
                "title": "",
                "sync_mode": "secondary",
                "last_updated": None,
            }
        else:
            if entry["resort_code"] not in seen[lid]["resort_codes"]:
                seen[lid]["resort_codes"].append(entry["resort_code"])

    listings = list(seen.values())
    save_listings(listings)
    return listings
