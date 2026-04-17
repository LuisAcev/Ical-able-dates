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
import re
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
            ranges.append((datetime.strptime(start, "%Y-%m-%d").strftime("%Y%m%d"), prev.replace("-", "")))
            start = d
            prev = d

    ranges.append((datetime.strptime(start, "%Y-%m-%d").strftime("%Y%m%d"), prev.replace("-", "")))

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

    # Validar listing_id para evitar path traversal
    if not re.match(r'^\d{1,25}$', str(listing_id)):
        raise ValueError(f"listing_id invalido: {listing_id}")

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
    logger.info("%s.ics generated (%d blocked ranges)", listing_id, event_count)
    return target_path


def parse_ics_file(listing_id, output_dir=None):
    """
    Lee un archivo .ics existente y retorna el set de fechas bloqueadas.

    Returns:
        set de strings "YYYY-MM-DD" con las fechas bloqueadas,
        o set vacio si el archivo no existe.
    """
    if output_dir is None:
        output_dir = ICS_OUTPUT_DIR

    ics_path = os.path.join(output_dir, f"{listing_id}.ics")
    if not os.path.exists(ics_path):
        return set()

    blocked = set()
    with open(ics_path, "r", encoding="utf-8") as f:
        dtstart = None
        for line in f:
            line = line.strip()
            if line.startswith("DTSTART;VALUE=DATE:") and ":" in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    dtstart = parts[1].strip()
            elif line.startswith("DTEND;VALUE=DATE:") and dtstart and ":" in line:
                parts = line.split(":", 1)
                if len(parts) < 2:
                    continue
                dtend = parts[1].strip()
                try:
                    start = datetime.strptime(dtstart, "%Y%m%d")
                    end = datetime.strptime(dtend, "%Y%m%d")
                    cur = start
                    while cur <= end:
                        blocked.add(cur.strftime("%Y-%m-%d"))
                        cur += timedelta(days=1)
                except ValueError:
                    pass
                dtstart = None
    return blocked
