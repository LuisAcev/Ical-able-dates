#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Logica de actualizacion de iCal para un listing individual o todos.

Reutiliza collect_available_dates y apply_manual_extra_availability de allin.py
y generate_ics_for_listing de ical_gen.py.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

from config import DATE_RANGE_START, DATE_RANGE_END
from allin import collect_available_dates, apply_manual_extra_availability
from ical_gen import generate_ics_for_listing
from storage import load_listings, get_listing, update_timestamp


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

    for resort_code in resort_codes:
        try:
            logger.info("Scraping %s para listing %s...", resort_code, listing_id)
            available = collect_available_dates(resort_code, listing_id, bedroom_filter)
            available = apply_manual_extra_availability(listing_id, available)
            all_available.update(available)
            logger.info("%s: %d dias disponibles", resort_code, len(available))
        except Exception as e:
            logger.exception("Error scraping %s: %s", resort_code, e)

    available_sorted = sorted(all_available)
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
