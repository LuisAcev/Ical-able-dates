#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generador de archivos iCalendar (.ics) para sincronizacion con Airbnb.

Airbnb interpreta cada VEVENT como un periodo BLOQUEADO.
Este modulo invierte las fechas disponibles para generar
eventos con los periodos NO disponibles.
"""

import logging
import os
import tempfile
from datetime import datetime, timedelta, timezone
from config import ICS_OUTPUT_DIR

logger = logging.getLogger(__name__)


def compute_blocked_ranges(available_dates, range_start, range_end):
    """
    Calcula rangos de fechas bloqueadas (no disponibles) dentro del rango dado.

    Args:
        available_dates: Lista de fechas disponibles en formato "YYYY-MM-DD".
        range_start: datetime del inicio del rango.
        range_end: datetime del fin del rango.

    Returns:
        Lista de tuplas (start_date, end_date_exclusive) en formato "YYYYMMDD".
        DTEND es exclusivo segun RFC 5545 para valores DATE.
    """
    available_set = set(available_dates)

    all_dates = [
        (range_start + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range((range_end - range_start).days + 1)
    ]

    blocked_dates = [d for d in all_dates if d not in available_set]

    if not blocked_dates:
        return []

    ranges = []
    start = blocked_dates[0]
    prev = blocked_dates[0]

    for d in blocked_dates[1:]:
        prev_dt = datetime.strptime(prev, "%Y-%m-%d")
        curr_dt = datetime.strptime(d, "%Y-%m-%d")
        if (curr_dt - prev_dt).days == 1:
            prev = d
        else:
            end_exclusive = (datetime.strptime(prev, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y%m%d")
            ranges.append((datetime.strptime(start, "%Y-%m-%d").strftime("%Y%m%d"), end_exclusive))
            start = d
            prev = d

    end_exclusive = (datetime.strptime(prev, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y%m%d")
    ranges.append((datetime.strptime(start, "%Y-%m-%d").strftime("%Y%m%d"), end_exclusive))

    return ranges


def generate_ics_content(listing_id, blocked_ranges):
    """
    Genera contenido iCalendar (RFC 5545) con VEVENTs para periodos bloqueados.

    Args:
        listing_id: ID del listing.
        blocked_ranges: Lista de tuplas (start_yyyymmdd, end_exclusive_yyyymmdd).

    Returns:
        String con contenido .ics valido (line endings CRLF).
    """
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AVI Interval Sync//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:AVI Listing {listing_id}",
    ]

    for start_date, end_date in blocked_ranges:
        lines.extend([
            "BEGIN:VEVENT",
            f"DTSTART;VALUE=DATE:{start_date}",
            f"DTEND;VALUE=DATE:{end_date}",
            f"UID:{listing_id}-{start_date}@avi-interval",
            f"DTSTAMP:{now}",
            "SUMMARY:Not Available",
            "STATUS:CONFIRMED",
            "TRANSP:OPAQUE",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")

    return "\r\n".join(lines) + "\r\n"


def generate_ics_for_listing(listing_id, available_dates, range_start, range_end, output_dir=None):
    """
    Genera y guarda el archivo .ics para un listing.

    Args:
        listing_id: ID del listing.
        available_dates: Lista de fechas disponibles "YYYY-MM-DD".
        range_start: datetime inicio del rango.
        range_end: datetime fin del rango.
        output_dir: Directorio de salida (default: config.ICS_OUTPUT_DIR).

    Returns:
        Path del archivo .ics generado.
    """
    if output_dir is None:
        output_dir = ICS_OUTPUT_DIR

    os.makedirs(output_dir, exist_ok=True)

    blocked_ranges = compute_blocked_ranges(available_dates, range_start, range_end)
    ics_content = generate_ics_content(listing_id, blocked_ranges)

    target_path = os.path.join(output_dir, f"{listing_id}.ics")

    # Escritura atomica: escribir a temporal y renombrar
    fd, tmp_path = tempfile.mkstemp(dir=output_dir, suffix=".ics.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(ics_content)
        os.replace(tmp_path, target_path)
    except Exception:
        # Limpiar archivo temporal si falla el rename
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    event_count = len(blocked_ranges)
    logger.info("%s.ics generado (%d bloqueos)", listing_id, event_count)
    return target_path
