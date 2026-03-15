#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Logica de actualizacion de iCal para un listing individual o todos.

Reutiliza collect_available_dates y apply_manual_extra_availability de allin.py
y generate_ics_for_listing de ical_gen.py.
"""

import traceback
from datetime import datetime, timezone

from config import DATE_RANGE_START, DATE_RANGE_END
from listings import (
    PRIMARY_LISTINGS, PRIMARY_BEDROOM_FILTER,
    AVAILABILITY_ONLY_LISTINGS, SECONDARY_BEDROOM_FILTER,
    MANUAL_EXTRA_AVAIL,
)
from allin import collect_available_dates, apply_manual_extra_availability
from ical_gen import generate_ics_for_listing
from storage import load_listings, update_timestamp


def _get_listing_config(listing_id):
    """
    Busca la configuracion de un listing en PRIMARY y SECONDARY lists.
    Retorna lista de (resort_code, bedroom_filter_dict) para este listing.
    """
    lid = int(listing_id)
    entries = []

    for entry in PRIMARY_LISTINGS:
        if entry["listing_id"] == lid:
            entries.append((entry["resort_code"], PRIMARY_BEDROOM_FILTER))

    for entry in AVAILABILITY_ONLY_LISTINGS:
        if entry["listing_id"] == lid:
            entries.append((entry["resort_code"], SECONDARY_BEDROOM_FILTER))

    return entries


def update_single_listing(listing_id):
    """
    Actualiza el iCal de un listing individual.

    Returns:
        dict con resultado: {listing_id, dates_found, updated_at, error}
    """
    lid = int(listing_id)
    entries = _get_listing_config(lid)

    if not entries:
        return {
            "listing_id": lid,
            "dates_found": 0,
            "updated_at": None,
            "error": f"Listing {lid} no encontrado en configuracion",
        }

    all_available = set()

    for resort_code, bedroom_filter in entries:
        try:
            print(f"\n  [Updater] Scraping {resort_code} para listing {lid}...")
            available = collect_available_dates(resort_code, lid, bedroom_filter)
            available = apply_manual_extra_availability(lid, available)
            all_available.update(available)
            print(f"  [Updater] {resort_code}: {len(available)} dias disponibles")
        except Exception as e:
            print(f"  [Updater] Error scraping {resort_code}: {e}")
            traceback.print_exc()

    available_sorted = sorted(all_available)
    generate_ics_for_listing(lid, available_sorted, DATE_RANGE_START, DATE_RANGE_END)
    ts = update_timestamp(lid)

    return {
        "listing_id": lid,
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
