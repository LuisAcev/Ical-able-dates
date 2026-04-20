#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Logica de actualizacion de iCal para un listing individual o todos.

Reutiliza collect_available_dates y apply_manual_extra_availability de allin.py
y generate_ics_for_listing de ical_gen.py.
"""

import logging
import subprocess
import time
from datetime import datetime

logger = logging.getLogger(__name__)

from config import DATE_RANGE_START, DATE_RANGE_END
from allin import collect_available_dates, apply_manual_blocked_dates, apply_manual_available_override
from ical_gen import generate_ics_for_listing
from storage import load_listings, get_listing, update_timestamp, update_last_error


def _effective_start(listing):
    """Retorna la fecha de inicio efectiva para el iCal del listing.

    Si el listing tiene start_date configurado y es posterior a DATE_RANGE_START,
    usa esa fecha. De lo contrario usa el global DATE_RANGE_START.
    """
    raw = listing.get("start_date")
    if not raw:
        return DATE_RANGE_START
    try:
        candidate = datetime.strptime(raw, "%Y-%m-%d")
        return candidate if candidate > DATE_RANGE_START else DATE_RANGE_START
    except ValueError:
        return DATE_RANGE_START


def update_single_listing(listing_id):
    """
    Actualiza el iCal de un listing individual.
    Lee la configuracion (resort_codes, bedrooms) del JSON de storage.

    Returns:
        dict con resultado: {listing_id, dates_found, updated_at, error}
    """
    listing_id = str(listing_id)
    listing = get_listing(listing_id)

    if not listing:
        return {
            "listing_id": listing_id,
            "dates_found": 0,
            "updated_at": None,
            "error": f"Listing {listing_id} no encontrado en storage",
        }

    resort_codes = listing.get("resort_codes", [])
    bedrooms = listing.get("bedrooms", "0")

    if not resort_codes:
        return {
            "listing_id": listing_id,
            "dates_found": 0,
            "updated_at": None,
            "error": f"Listing {listing_id} no tiene resort_codes configurados",
        }

    # Construir bedroom_filter compatible con el scraper
    bedroom_filter = {listing_id: bedrooms}

    all_available = set()
    failed_codes = []

    for resort_code in resort_codes:
        for attempt in range(2):
            try:
                logger.info("Scraping %s for listing %s (attempt %d)...", resort_code, listing_id, attempt + 1)
                available = collect_available_dates(resort_code, listing_id, bedroom_filter)
                all_available.update(available)
                logger.info("%s: %d available dates found", resort_code, len(available))
                break
            except Exception as e:
                if attempt == 0:
                    logger.warning("Error scraping %s, retrying: %s", resort_code, e)
                else:
                    logger.error("Error scraping %s after 2 attempts: %s", resort_code, e)
                    failed_codes.append(resort_code)
        # Asegurar que Chrome murio antes de lanzar el siguiente resort code
        for name in ("chrome", "chromedriver"):
            try:
                subprocess.run(["pkill", "-9", "-f", name], capture_output=True)
            except Exception:
                pass
        time.sleep(5)

    all_failed = len(failed_codes) == len(resort_codes)

    if all_failed and failed_codes:
        error_msg = f"Scraping fallido para: {', '.join(failed_codes)}"
        update_last_error(listing_id, error_msg)
        logger.warning("Listing %s: todos los scrapers fallaron, iCal sin cambios.", listing_id)
        return {
            "listing_id": listing_id,
            "dates_found": 0,
            "updated_at": listing.get("last_updated"),
            "error": error_msg,
        }

    partial_error = f"Scraping fallido para: {', '.join(failed_codes)}" if failed_codes else None
    update_last_error(listing_id, partial_error)

    # Guardar fechas crudas del scraper para regeneracion futura sin re-scrapear
    from storage import upsert_listing
    fresh = get_listing(listing_id) or listing
    fresh["scraper_available_dates"] = sorted(all_available)
    upsert_listing(fresh)
    listing = fresh

    ical_start = _effective_start(listing)
    available_list = sorted(d for d in all_available if d >= ical_start.strftime("%Y-%m-%d"))
    available_sorted = apply_manual_blocked_dates(available_list, [tuple(r) for r in (listing.get("manual_dates") or [])])
    available_sorted = apply_manual_available_override(available_sorted, [tuple(r) for r in (listing.get("available_override_dates") or [])])
    generate_ics_for_listing(listing_id, available_sorted, DATE_RANGE_START, DATE_RANGE_END)
    ts = update_timestamp(listing_id)

    return {
        "listing_id": listing_id,
        "dates_found": len(available_sorted),
        "updated_at": ts,
        "error": None,
    }


def update_all_listings(progress_callback=None):
    """
    Actualiza el iCal de todos los listings registrados.

    Args:
        progress_callback: Funcion opcional (current, total, listing_id) para reportar progreso.

    Returns:
        Lista de resultados por listing.
    """
    listings = load_listings()
    results = []

    for i, listing in enumerate(listings):
        lid = listing["listing_id"]
        if progress_callback:
            progress_callback(i + 1, len(listings), lid)

        result = update_single_listing(lid)
        results.append(result)

    return results
