#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Logica de actualizacion de iCal para un listing individual o todos.

Reutiliza collect_available_dates, apply_manual_blocked_dates y apply_manual_available_override
de allin.py, y generate_ics_for_listing de ical_gen.py.
"""

import json
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime

logger = logging.getLogger(__name__)

from config import get_date_range_start, get_date_range_end, CHROME_KILL_SLEEP
from allin import apply_manual_blocked_dates, apply_manual_available_override
from ical_gen import generate_ics_for_listing
from storage import load_listings, get_listing, update_timestamp, update_last_error, upsert_listing

# Timeout por resort code: 3 minutos. Configurable via env var.
_SCRAPE_TIMEOUT = int(os.getenv("SCRAPE_TIMEOUT_SECONDS", "180"))
_WORKER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraper_worker.py")


def kill_chrome_zombies(sleep_seconds: float = 0):
    """Mata procesos Chrome/chromedriver huerfanos. Compartido con ical_server."""
    for name in ("chrome", "chromedriver"):
        try:
            subprocess.run(["pkill", "-9", "-f", name], capture_output=True)
        except Exception:
            pass
    if sleep_seconds > 0:
        time.sleep(sleep_seconds)


def _scrape_in_process(resort_code, listing_id, bedroom_filter):
    """
    Ejecuta collect_available_dates en un subprocess aislado con timeout duro.

    Usa start_new_session=True para que Chrome quede en el mismo grupo de procesos
    que el worker. Si el timeout expira, mata el grupo entero (worker + Chrome)
    con SIGKILL antes de lanzar TimeoutError.
    """
    payload = json.dumps({
        "resort_code": resort_code,
        "listing_id": listing_id,
        "bedroom_filter": bedroom_filter,
    }).encode()

    proc = subprocess.Popen(
        [sys.executable, _WORKER_SCRIPT],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )

    try:
        stdout, stderr = proc.communicate(input=payload, timeout=_SCRAPE_TIMEOUT)
    except subprocess.TimeoutExpired:
        # Mata el grupo de procesos completo (worker + Chrome hijos)
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            proc.kill()
        proc.wait()
        raise TimeoutError(
            f"Scraping {resort_code} excedio {_SCRAPE_TIMEOUT}s — proceso terminado"
        )

    # Reenviar logs del worker al logger del padre
    if stderr:
        level = logging.WARNING if proc.returncode != 0 else logging.DEBUG
        for line in stderr.decode(errors="replace").splitlines():
            if line.strip():
                logger.log(level, "[worker] %s", line)

    if proc.returncode != 0:
        last_error = (stderr.decode(errors="replace").strip().splitlines() or ["error desconocido"])[-1]
        raise Exception(f"Worker fallo (exit {proc.returncode}): {last_error}")

    return json.loads(stdout.decode())


def _effective_start(listing, range_start):
    raw = listing.get("start_date")
    if not raw:
        return range_start
    try:
        candidate = datetime.strptime(raw, "%Y-%m-%d")
        return candidate if candidate > range_start else range_start
    except ValueError:
        return range_start


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

    bedroom_filter = {listing_id: bedrooms}

    all_available = set()
    failed_codes = []

    for i, resort_code in enumerate(resort_codes):
        for attempt in range(2):
            try:
                logger.info("Scraping %s for listing %s (attempt %d)...", resort_code, listing_id, attempt + 1)
                available = _scrape_in_process(resort_code, listing_id, bedroom_filter)
                all_available.update(available)
                logger.info("%s: %d available dates found", resort_code, len(available))
                break
            except Exception as e:
                if attempt == 0:
                    logger.warning("Error scraping %s, retrying: %s", resort_code, e)
                    kill_chrome_zombies(sleep_seconds=5)
                else:
                    logger.error("Error scraping %s after 2 attempts: %s", resort_code, e)
                    failed_codes.append(resort_code)

        # Entre resort codes: asegurar que Chrome murio antes de lanzar el siguiente
        if i < len(resort_codes) - 1:
            kill_chrome_zombies(sleep_seconds=5)

    all_failed = len(failed_codes) == len(resort_codes)

    if all_failed:
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

    fresh = get_listing(listing_id) or listing
    fresh["scraper_available_dates"] = sorted(all_available)
    upsert_listing(fresh)
    listing = fresh

    range_start = get_date_range_start()
    range_end = get_date_range_end(range_start)
    ical_start = _effective_start(listing, range_start)
    available_list = sorted(d for d in all_available if d >= ical_start.strftime("%Y-%m-%d"))
    available_sorted = apply_manual_blocked_dates(available_list, [tuple(r) for r in (listing.get("manual_dates") or [])])
    available_sorted = apply_manual_available_override(available_sorted, [tuple(r) for r in (listing.get("available_override_dates") or [])])
    generate_ics_for_listing(listing_id, available_sorted, range_start, range_end)
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

        if not listing.get("ical_enabled", True):
            continue

        result = update_single_listing(lid)
        results.append(result)

    return results
