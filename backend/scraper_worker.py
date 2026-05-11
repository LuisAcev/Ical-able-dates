#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proceso hijo aislado para ejecutar collect_available_dates.

Lee un JSON de stdin con {resort_code, listing_id, bedroom_filter},
escribe el resultado como JSON en stdout.
Los logs de Playwright y allin.py van a stderr (capturado por el padre).
"""

import json
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stderr,
)

from allin import collect_available_dates

if __name__ == "__main__":
    try:
        raw = sys.stdin.read()
        if not raw:
            print("ERROR: no se recibio input del proceso padre", file=sys.stderr)
            sys.exit(1)
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: JSON invalido recibido del proceso padre: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        result = collect_available_dates(
            data["resort_code"],
            data["listing_id"],
            data["bedroom_filter"],
        )
        sys.stdout.write(json.dumps(result))
        sys.stdout.flush()
        sys.exit(0)
    except Exception:
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
