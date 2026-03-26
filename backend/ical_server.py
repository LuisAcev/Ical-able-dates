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

import logging
import os
import threading

logger = logging.getLogger(__name__)
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from config import ICS_OUTPUT_DIR, ICAL_SERVER_HOST, ICAL_SERVER_PORT, CORS_ORIGINS, ICAL_BASE_URL
from storage import (
    load_listings, upsert_listing, update_timestamp, delete_listing,
    build_initial_listings, get_listing, ensure_ical_enabled_field,
    get_setting, save_setting,
)


@asynccontextmanager
async def lifespan(_app):
    """Inicializa la data de listings si no existe."""
    build_initial_listings()
    ensure_ical_enabled_field()
    yield


app = FastAPI(title="AVI iCalendar Server", lifespan=lifespan)

# CORS para el frontend (Vite dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
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

class ListingManualCreate(BaseModel):
    """Creacion manual de listing con todos los campos requeridos."""
    listing_id: str
    title: str
    resort_codes: list[str]
    bedrooms: str

class IcalToggle(BaseModel):
    ical_enabled: bool

class IcalBaseUrl(BaseModel):
    base_url: str


# ================== ICAL ENDPOINTS ==================

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

@app.get("/api/settings/ical-base-url")
def api_get_ical_base_url():
    """Retorna la URL base actual para iCal."""
    base_url = get_setting("ical_base_url", ICAL_BASE_URL)
    return {"base_url": base_url}


@app.put("/api/settings/ical-base-url")
def api_set_ical_base_url(data: IcalBaseUrl):
    """Cambia la URL base para iCal y la persiste en disco."""
    base = data.base_url.strip().rstrip("/")
    if base and not base.startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="La URL debe comenzar con http:// o https://")
    save_setting("ical_base_url", base)
    return {"message": "URL base actualizada", "base_url": base}


@app.get("/api/listings")
def api_get_listings():
    """Retorna todos los listings con sus detalles y timestamps."""
    base_url = get_setting("ical_base_url", ICAL_BASE_URL)
    listings = load_listings()
    for l in listings:
        ics_path = Path(ICS_OUTPUT_DIR) / f"{l['listing_id']}.ics"
        l["has_ical"] = ics_path.exists()
        l["ical_url"] = f"{base_url}/ical/{l['listing_id']}.ics" if base_url else ""
        l.pop("IcalURL", None)
    return {"listings": listings}


@app.post("/api/listings", status_code=201)
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
        existing["title"] = details.get("title") or existing.get("title", "")
        existing["bedrooms"] = str(details["bedrooms"]) if details.get("bedrooms") is not None else existing.get("bedrooms", "0")
        existing["guests"] = details["guests"] if details.get("guests") is not None else existing.get("guests", 0)
        existing["price_per_night"] = details["price_per_night"] if details.get("price_per_night") is not None else existing.get("price_per_night", 0)
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


@app.post("/api/listings/manual", status_code=201)
def api_create_listing_manual(data: ListingManualCreate):
    """Crea un listing manualmente con los datos proporcionados."""
    listing_id = str(data.listing_id).strip()
    if not listing_id:
        raise HTTPException(status_code=422, detail="listing_id es requerido")

    if get_listing(listing_id):
        raise HTTPException(status_code=409, detail=f"El listing {listing_id} ya existe")

    if not data.resort_codes:
        raise HTTPException(status_code=422, detail="Debe incluir al menos un resort code")

    listing = {
        "listing_id": listing_id,
        "title": data.title.strip(),
        "resort_codes": [code.strip().upper() for code in data.resort_codes],
        "bedrooms": data.bedrooms,
        "sync_mode": "primary",
        "last_updated": None,
        "ical_enabled": True,
    }
    upsert_listing(listing)
    return {"message": "Listing creado", "listing": listing}


@app.put("/api/listings/{listing_id}")
def api_update_listing_data(listing_id: str, data: ListingCreate):
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


@app.delete("/api/listings/{listing_id}")
def api_delete_listing(listing_id: str):
    """Elimina un listing del sistema."""
    existing = get_listing(listing_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Listing no encontrado")

    deleted = delete_listing(listing_id)
    if not deleted:
        raise HTTPException(status_code=500, detail="Error al eliminar el listing")

    # Eliminar el archivo .ics si existe
    ics_path = Path(ICS_OUTPUT_DIR) / f"{listing_id}.ics"
    if ics_path.exists():
        try:
            ics_path.unlink()
        except OSError:
            logger.warning("No se pudo eliminar %s.ics", listing_id)

    return {"message": f"Listing {listing_id} eliminado"}


@app.patch("/api/listings/{listing_id}/toggle-ical")
def api_toggle_ical(listing_id: str, data: IcalToggle):
    """Activa o desactiva la actualizacion iCal de un listing."""
    existing = get_listing(listing_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Listing no encontrado")

    existing["ical_enabled"] = data.ical_enabled
    upsert_listing(existing)
    return {"message": "Estado iCal actualizado", "listing": existing}


def _set_status(**kwargs):
    """Actualiza _update_status de forma thread-safe."""
    with _update_lock:
        _update_status.update(kwargs)


def _run_update_single(listing_id):
    """Background task: actualiza iCal de un listing."""
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
        _set_status(error=result.get("error"))
    except Exception as e:
        _set_status(error=str(e))
    finally:
        _set_status(updating=False, current_listing=None, progress=1)


def _run_update_all():
    """Background task: actualiza iCal de todos los listings."""
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
            _set_status(current_listing=lid, progress=i + 1)
            if not listing.get("ical_enabled", True):
                continue
            try:
                update_single_listing(lid)
            except Exception as e:
                logger.error("Error updating %s: %s", lid, e)
    except Exception as e:
        _set_status(error=str(e))
    finally:
        _set_status(updating=False, current_listing=None)


@app.post("/api/listings/{listing_id}/update", status_code=202)
def api_update_single(listing_id: str, background_tasks: BackgroundTasks):
    """Lanza actualizacion de iCal de un listing en background."""
    with _update_lock:
        if _update_status["updating"]:
            raise HTTPException(status_code=409, detail="Ya hay una actualizacion en progreso")

    existing = get_listing(listing_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Listing no encontrado")

    if not existing.get("ical_enabled", True):
        raise HTTPException(status_code=403, detail="La actualizacion iCal esta deshabilitada para este listing")

    background_tasks.add_task(_run_update_single, listing_id)
    return {"message": f"Actualizacion de {listing_id} iniciada"}


@app.post("/api/update-all", status_code=202)
def api_update_all(background_tasks: BackgroundTasks):
    """Lanza actualizacion de iCal de TODOS los listings en background."""
    with _update_lock:
        if _update_status["updating"]:
            raise HTTPException(status_code=409, detail="Ya hay una actualizacion en progreso")

    background_tasks.add_task(_run_update_all)
    return {"message": "Actualizacion masiva iniciada"}


@app.get("/api/status")
def api_status():
    """Estado actual de actualizacion."""
    with _update_lock:
        return dict(_update_status)


# ================== MAIN ==================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    os.makedirs(ICS_OUTPUT_DIR, exist_ok=True)
    uvicorn.run(
        "ical_server:app",
        host=ICAL_SERVER_HOST,
        port=ICAL_SERVER_PORT,
        reload=False,
    )
