#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Servidor FastAPI para servir archivos iCalendar (.ics)
y API REST para el dashboard de listings.

Uso:
    uvicorn ical_server:app --host 0.0.0.0 --port 8085
    o directamente:
    python ical_server.py
"""

import os
import threading
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from config import ICS_OUTPUT_DIR, ICAL_SERVER_HOST, ICAL_SERVER_PORT
from storage import (
    load_listings, upsert_listing, update_timestamp,
    build_initial_listings, get_listing,
)

app = FastAPI(title="AVI iCalendar Server")

# CORS para el frontend (Vite dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Estado global de actualizacion
_update_lock = threading.Lock()
_update_status = {
    "updating": False,
    "current_listing": None,
    "progress": 0,
    "total": 0,
    "error": None,
}


# ================== MODELOS ==================

class ListingRegister(BaseModel):
    """Solo necesita el ID de Airbnb. String para evitar perdida de precision en JS."""
    listing_id: str

class ListingCreate(BaseModel):
    listing_id: str
    title: str = ""
    resort_codes: list[str] = []
    bedrooms: str = "0"
    sync_mode: str = "primary"


# ================== STARTUP ==================

@app.on_event("startup")
def startup():
    """Inicializa la data de listings si no existe."""
    build_initial_listings()


# ================== ICAL ENDPOINTS (existentes) ==================

@app.get("/", response_class=HTMLResponse)
def list_calendars():
    """Lista todos los .ics disponibles con links clickeables."""
    ics_dir = Path(ICS_OUTPUT_DIR)
    if not ics_dir.exists():
        return HTMLResponse("<h2>No hay calendarios generados todavia.</h2>")

    files = sorted(ics_dir.glob("*.ics"))
    if not files:
        return HTMLResponse("<h2>No hay calendarios generados todavia.</h2>")

    rows = "\n".join(
        f'<li><a href="/ical/{f.name}">{f.name}</a></li>'
        for f in files
    )
    return HTMLResponse(
        f"<h2>Calendarios iCal disponibles ({len(files)})</h2><ul>{rows}</ul>"
    )


@app.get("/ical/{filename}")
def serve_ics(filename: str):
    """Sirve un archivo .ics con el Content-Type correcto para Airbnb."""
    if not filename.endswith(".ics"):
        raise HTTPException(status_code=400, detail="Solo se sirven archivos .ics")

    file_path = (Path(ICS_OUTPUT_DIR) / filename).resolve()

    if not str(file_path).startswith(str(Path(ICS_OUTPUT_DIR).resolve())):
        raise HTTPException(status_code=403, detail="Acceso denegado")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Calendario {filename} no encontrado")

    return FileResponse(
        path=str(file_path),
        media_type="text/calendar; charset=utf-8",
        filename=filename,
    )


@app.get("/health")
def health_check():
    ics_dir = Path(ICS_OUTPUT_DIR)
    count = len(list(ics_dir.glob("*.ics"))) if ics_dir.exists() else 0
    return {"status": "ok", "calendars_count": count}


# ================== API ENDPOINTS ==================

@app.get("/api/listings")
def api_get_listings():
    """Retorna todos los listings con sus detalles y timestamps."""
    listings = load_listings()
    # Agregar info de si existe el .ics
    for l in listings:
        ics_path = Path(ICS_OUTPUT_DIR) / f"{l['listing_id']}.ics"
        l["has_ical"] = ics_path.exists()
    return {"listings": listings}


@app.post("/api/listings")
def api_register_listing(data: ListingRegister):
    """
    Registra un listing nuevo. Solo recibe el ID de Airbnb.
    Selenium navega a Airbnb y extrae titulo, habitaciones, precio, huespedes.
    """
    # Scraping de datos desde Airbnb
    from scrape_airbnb import fetch_listing_details, close_driver
    try:
        details = fetch_listing_details(data.listing_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener datos de Airbnb: {e}")
    finally:
        close_driver()

    existing = get_listing(data.listing_id)
    if existing:
        # Actualizar datos de Airbnb sin perder resort_codes, sync_mode, etc.
        existing["title"] = details.get("title", "") or existing.get("title", "")
        existing["bedrooms"] = str(details.get("bedrooms", 0)) or existing.get("bedrooms", "0")
        existing["guests"] = details.get("guests", 0) or existing.get("guests", 0)
        existing["price_per_night"] = details.get("price_per_night", 0) or existing.get("price_per_night", 0)
        upsert_listing(existing)
        return {"message": "Listing actualizado con datos de Airbnb", "listing": existing}

    listing = {
        "listing_id": data.listing_id,
        "title": details.get("title", ""),
        "bedrooms": str(details.get("bedrooms", 0)),
        "guests": details.get("guests", 0),
        "price_per_night": details.get("price_per_night", 0),
        "resort_codes": [],
        "sync_mode": "primary",
        "last_updated": None,
    }
    upsert_listing(listing)
    return {"message": "Listing registrado", "listing": listing}


@app.put("/api/listings/{listing_id}")
def api_update_listing_data(listing_id: int, data: ListingCreate):
    """Actualiza los datos de un listing (titulo, resort_codes, etc)."""
    existing = get_listing(listing_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Listing no encontrado")

    existing["title"] = data.title or existing.get("title", "")
    existing["resort_codes"] = data.resort_codes or existing.get("resort_codes", [])
    existing["bedrooms"] = data.bedrooms or existing.get("bedrooms", "0")
    existing["sync_mode"] = data.sync_mode or existing.get("sync_mode", "primary")
    upsert_listing(existing)
    return {"message": "Listing actualizado", "listing": existing}


def _run_update_single(listing_id):
    """Background task: actualiza iCal de un listing."""
    global _update_status
    with _update_lock:
        if _update_status["updating"]:
            return
        _update_status.update(
            updating=True, current_listing=listing_id,
            progress=0, total=1, error=None,
        )

    try:
        from updater import update_single_listing
        result = update_single_listing(listing_id)
        _update_status["error"] = result.get("error")
    except Exception as e:
        _update_status["error"] = str(e)
    finally:
        _update_status.update(updating=False, current_listing=None, progress=1)


def _run_update_all():
    """Background task: actualiza iCal de todos los listings."""
    global _update_status
    with _update_lock:
        if _update_status["updating"]:
            return
        listings = load_listings()
        _update_status.update(
            updating=True, current_listing=None,
            progress=0, total=len(listings), error=None,
        )

    try:
        from updater import update_single_listing
        for i, listing in enumerate(listings):
            lid = listing["listing_id"]
            _update_status.update(current_listing=lid, progress=i + 1)
            try:
                update_single_listing(lid)
            except Exception as e:
                print(f"  [Server] Error updating {lid}: {e}")
    except Exception as e:
        _update_status["error"] = str(e)
    finally:
        _update_status.update(updating=False, current_listing=None)


@app.post("/api/listings/{listing_id}/update", status_code=202)
def api_update_single(listing_id: int, background_tasks: BackgroundTasks):
    """Lanza actualizacion de iCal de un listing en background."""
    if _update_status["updating"]:
        raise HTTPException(status_code=409, detail="Ya hay una actualizacion en progreso")

    existing = get_listing(listing_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Listing no encontrado")

    background_tasks.add_task(_run_update_single, listing_id)
    return {"message": f"Actualizacion de {listing_id} iniciada"}


@app.post("/api/update-all", status_code=202)
def api_update_all(background_tasks: BackgroundTasks):
    """Lanza actualizacion de iCal de TODOS los listings en background."""
    if _update_status["updating"]:
        raise HTTPException(status_code=409, detail="Ya hay una actualizacion en progreso")

    background_tasks.add_task(_run_update_all)
    return {"message": "Actualizacion masiva iniciada"}


@app.get("/api/status")
def api_status():
    """Estado actual de actualizacion."""
    return _update_status


# ================== MAIN ==================

if __name__ == "__main__":
    os.makedirs(ICS_OUTPUT_DIR, exist_ok=True)
    uvicorn.run(
        "ical_server:app",
        host=ICAL_SERVER_HOST,
        port=ICAL_SERVER_PORT,
        reload=False,
    )
