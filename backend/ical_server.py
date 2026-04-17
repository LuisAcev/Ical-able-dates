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

import asyncio
import logging
import os
import re
import subprocess
import threading

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
import uvicorn

from config import ICS_OUTPUT_DIR, ICAL_SERVER_HOST, ICAL_SERVER_PORT, CORS_ORIGINS, ICAL_BASE_URL, DATE_RANGE_START, DATE_RANGE_END, AUTO_UPDATE_HOURS
from ical_gen import parse_ics_file, generate_ics_for_listing
from storage import (
    load_listings, upsert_listing, update_timestamp, delete_listing,
    build_initial_listings, get_listing, ensure_ical_enabled_field,
    ensure_manual_dates_field, ensure_address_state_fields, ensure_start_date_field,
    ensure_last_error_field, ensure_available_override_field, get_setting, save_setting,
)


async def _auto_update_loop():
    """Corre _run_update_all cada AUTO_UPDATE_HOURS horas."""
    # Espera 60s antes del primer ciclo para que el servidor este listo
    await asyncio.sleep(60)
    loop = asyncio.get_running_loop()
    while True:
        try:
            logger.info("Auto-update: starting scheduled update...")
            await asyncio.wait_for(
                loop.run_in_executor(None, _run_update_all),
                timeout=float(_TASK_TIMEOUT_SECONDS),
            )
            logger.info("Auto-update: completed. Next run in %d hours.", AUTO_UPDATE_HOURS)
        except asyncio.TimeoutError:
            logger.warning("Auto-update: timeout of %ds reached, releasing loop.", _TASK_TIMEOUT_SECONDS)
            _set_status(updating=False, current_listing=None, error="Timeout de actualizacion")
        except Exception as e:
            logger.exception("Auto-update: unexpected error, will retry in %dh: %s", AUTO_UPDATE_HOURS, e)
        await asyncio.sleep(AUTO_UPDATE_HOURS * 3600)


@asynccontextmanager
async def lifespan(_app):
    """Inicializa la data de listings si no existe."""
    _kill_chrome_zombies()
    os.makedirs(ICS_OUTPUT_DIR, exist_ok=True)
    build_initial_listings()
    ensure_ical_enabled_field()
    ensure_manual_dates_field()
    ensure_address_state_fields()
    ensure_start_date_field()
    ensure_last_error_field()
    ensure_available_override_field()
    task = asyncio.create_task(_auto_update_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="AVI iCalendar Server", lifespan=lifespan)

# CORS para el frontend (Vite dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
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

# Timeout de seguridad total: 4h cubre 85 listings con reintentos (~3min/listing worst case)
_TASK_TIMEOUT_SECONDS = 4 * 60 * 60
_active_timer = None

def _start_safety_timeout():
    """Inicia un timer que libera el estado updating si se excede el timeout."""
    def _timeout_handler():
        with _update_lock:
            if _update_status["updating"]:
                logger.warning("Safety timeout: update exceeded %ds", _TASK_TIMEOUT_SECONDS)
                _update_status.update(updating=False, current_listing=None, error="Update timeout")
    timer = threading.Timer(_TASK_TIMEOUT_SECONDS, _timeout_handler)
    timer.daemon = True
    timer.start()
    return timer


# ================== HELPERS ==================

_LISTING_ID_RE = re.compile(r'^\d{1,25}$')
_RESORT_CODE_RE = re.compile(r'^[A-Z0-9]{2,10}$')

def _validate_listing_id_param(listing_id: str):
    """Valida que el listing_id de un path param sea solo digitos."""
    if not _LISTING_ID_RE.match(listing_id):
        raise HTTPException(status_code=400, detail="listing_id invalido")


# ================== MODELOS ==================

class ListingRegister(BaseModel):
    """Solo necesita el ID de Airbnb. String para evitar perdida de precision en JS."""
    listing_id: str = Field(..., min_length=1, max_length=25, pattern=r'^\d+$')

def _check_resort_codes(v):
    """Validacion compartida de resort codes."""
    for code in v:
        if not _RESORT_CODE_RE.match(code.strip().upper()):
            raise ValueError(f'Resort code invalido: {code}')
    return v

class ListingCreate(BaseModel):
    listing_id: str = Field(default="", max_length=25)
    title: str = Field(default="", max_length=500)
    resort_codes: list[str] = []
    bedrooms: str = "0"
    sync_mode: str = "primary"
    address: str = Field(default="", max_length=500)
    state: str = Field(default="", max_length=100)

    @field_validator('resort_codes', mode='before')
    @classmethod
    def validate_resort_codes(cls, v):
        return _check_resort_codes(v)

class ListingManualCreate(BaseModel):
    """Creacion manual de listing con todos los campos requeridos."""
    listing_id: str = Field(..., min_length=1, max_length=25, pattern=r'^\d+$')
    title: str = Field(..., min_length=1, max_length=500)
    resort_codes: list[str] = Field(..., min_length=1)
    bedrooms: str
    address: str = Field(default="", max_length=500)
    state: str = Field(default="", max_length=100)

    @field_validator('resort_codes', mode='before')
    @classmethod
    def validate_resort_codes(cls, v):
        return _check_resort_codes(v)

class IcalToggle(BaseModel):
    ical_enabled: bool

class IcalBaseUrl(BaseModel):
    base_url: str

class ManualDatesUpdate(BaseModel):
    manual_dates: list[list[str]]
    available_override_dates: list[list[str]] = []
    start_date: str | None = None

    @field_validator('manual_dates', 'available_override_dates', mode='before')
    @classmethod
    def validate_dates(cls, v):
        for pair in v:
            if len(pair) != 2:
                raise ValueError('Cada rango debe tener [start, end]')
            from datetime import datetime as dt
            try:
                start = dt.strptime(pair[0], "%Y-%m-%d")
                end = dt.strptime(pair[1], "%Y-%m-%d")
            except ValueError:
                raise ValueError(f'Fecha invalida: {pair}')
            if start >= end:
                raise ValueError(f'start debe ser menor que end: {pair}')
        return v

    @field_validator('start_date', mode='before')
    @classmethod
    def validate_start_date(cls, v):
        if v is None or v == "":
            return None
        from datetime import datetime as dt
        try:
            dt.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f'start_date invalido: {v}. Formato esperado: YYYY-MM-DD')
        return v


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
    if not re.match(r'^[a-zA-Z0-9_\-]+\.ics$', filename):
        raise HTTPException(status_code=400, detail="Nombre de archivo invalido")

    file_path = (Path(ICS_OUTPUT_DIR) / filename).resolve()

    try:
        file_path.relative_to(Path(ICS_OUTPUT_DIR).resolve())
    except ValueError:
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
async def api_get_ical_base_url():
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
async def api_get_listings():
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
        logger.exception("Error scraping Airbnb for listing %s", data.listing_id)
        raise HTTPException(status_code=500, detail="Error al obtener datos de Airbnb")
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
        "address": data.address.strip(),
        "state": data.state.strip(),
        "last_updated": None,
        "ical_enabled": True,
    }
    upsert_listing(listing)
    return {"message": "Listing creado", "listing": listing}


@app.put("/api/listings/{listing_id}")
def api_update_listing_data(listing_id: str, data: ListingCreate):
    """Actualiza los datos de un listing (titulo, resort_codes, etc)."""
    _validate_listing_id_param(listing_id)
    existing = get_listing(listing_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Listing no encontrado")

    existing["title"] = data.title if data.title is not None else existing.get("title", "")
    existing["resort_codes"] = data.resort_codes if data.resort_codes is not None else existing.get("resort_codes", [])
    existing["bedrooms"] = data.bedrooms if data.bedrooms is not None else existing.get("bedrooms", "0")
    existing["sync_mode"] = data.sync_mode if data.sync_mode is not None else existing.get("sync_mode", "primary")
    existing["address"] = data.address.strip() if data.address is not None else existing.get("address", "")
    existing["state"] = data.state.strip() if data.state is not None else existing.get("state", "")
    upsert_listing(existing)
    return {"message": "Listing actualizado", "listing": existing}


@app.delete("/api/listings/{listing_id}")
def api_delete_listing(listing_id: str):
    """Elimina un listing del sistema."""
    _validate_listing_id_param(listing_id)
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
            logger.warning("Could not delete %s.ics", listing_id)

    return {"message": f"Listing {listing_id} eliminado"}


@app.patch("/api/listings/{listing_id}/toggle-ical")
def api_toggle_ical(listing_id: str, data: IcalToggle):
    """Activa o desactiva la actualizacion iCal de un listing."""
    _validate_listing_id_param(listing_id)
    existing = get_listing(listing_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Listing no encontrado")

    existing["ical_enabled"] = data.ical_enabled
    upsert_listing(existing)
    return {"message": "Estado iCal actualizado", "listing": existing}


@app.get("/api/listings/{listing_id}/dates")
async def api_get_listing_dates(listing_id: str):
    """Retorna fechas bloqueadas, disponibles y manuales para el calendario."""
    _validate_listing_id_param(listing_id)
    existing = get_listing(listing_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Listing no encontrado")

    blocked_dates = parse_ics_file(listing_id)
    range_start = DATE_RANGE_START.strftime("%Y-%m-%d")
    range_end = DATE_RANGE_END.strftime("%Y-%m-%d")

    from datetime import timedelta
    all_dates = set()
    cur = DATE_RANGE_START
    while cur <= DATE_RANGE_END:
        all_dates.add(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)

    available_dates = sorted(all_dates - blocked_dates)

    return {
        "range_start": range_start,
        "range_end": range_end,
        "blocked_dates": sorted(blocked_dates),
        "available_dates": available_dates,
        "manual_dates": existing.get("manual_dates", []),
        "available_override_dates": existing.get("available_override_dates", []),
        "start_date": existing.get("start_date") or None,
    }


@app.put("/api/listings/{listing_id}/manual-dates")
async def api_save_manual_dates(listing_id: str, data: ManualDatesUpdate):
    """Guarda rangos de fechas manuales para un listing."""
    _validate_listing_id_param(listing_id)
    existing = get_listing(listing_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Listing no encontrado")

    existing["manual_dates"] = data.manual_dates
    existing["available_override_dates"] = data.available_override_dates
    existing["start_date"] = data.start_date
    upsert_listing(existing)
    return {
        "message": "Fechas manuales guardadas",
        "manual_dates": data.manual_dates,
        "available_override_dates": data.available_override_dates,
        "start_date": data.start_date,
    }


@app.post("/api/listings/{listing_id}/regenerate-ical")
async def api_regenerate_ical(listing_id: str):
    """Regenera el .ics usando datos existentes + fechas manuales, sin re-scrapear."""
    _validate_listing_id_param(listing_id)
    existing = get_listing(listing_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Listing no encontrado")

    scraper_dates = existing.get("scraper_available_dates")
    if not scraper_dates:
        raise HTTPException(status_code=404, detail="No hay datos del scraper. Ejecuta una actualizacion primero.")

    available_dates = list(scraper_dates)

    from allin import apply_manual_blocked_dates, apply_manual_available_override
    manual = [tuple(r) for r in (existing.get("manual_dates") or [])]
    available_dates = apply_manual_blocked_dates(available_dates, manual)
    overrides = [tuple(r) for r in (existing.get("available_override_dates") or [])]
    available_dates = apply_manual_available_override(available_dates, overrides)

    # Aplicar start_date del listing si esta configurado
    from datetime import datetime as dt
    raw_start = existing.get("start_date")
    ical_start = DATE_RANGE_START
    if raw_start:
        try:
            candidate = dt.strptime(raw_start, "%Y-%m-%d")
            if candidate > DATE_RANGE_START:
                ical_start = candidate
        except ValueError:
            pass

    available_dates = [d for d in available_dates if d >= ical_start.strftime("%Y-%m-%d")]
    generate_ics_for_listing(listing_id, available_dates, DATE_RANGE_START, DATE_RANGE_END)
    ts = update_timestamp(listing_id)

    return {"message": f"iCal regenerado para {listing_id}", "updated_at": ts}


def _kill_chrome_zombies():
    """Mata procesos Chrome/chromedriver zombies antes de iniciar un run."""
    for name in ("chrome", "chromedriver"):
        try:
            subprocess.run(["pkill", "-f", name], capture_output=True)
        except Exception:
            pass


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

    global _active_timer
    _kill_chrome_zombies()
    timer = None
    try:
        timer = _start_safety_timeout()
        with _update_lock:
            _active_timer = timer
        from updater import update_single_listing
        result = update_single_listing(listing_id)
        _set_status(error=result.get("error"))
    except Exception as e:
        logger.exception("Error in update_single: %s", e)
        _set_status(error="Error interno al actualizar listing")
    finally:
        if timer is not None:
            timer.cancel()
        with _update_lock:
            _active_timer = None
        _set_status(updating=False, current_listing=None, progress=1)


def _run_update_all():
    """Background task: actualiza iCal de todos los listings."""
    global _active_timer
    with _update_lock:
        if _update_status["updating"]:
            return
        listings = load_listings()
        _update_status.update(
            updating=True, current_listing=None,
            progress=0, total=len(listings), error=None,
        )

    _kill_chrome_zombies()
    timer = None
    try:
        timer = _start_safety_timeout()
        with _update_lock:
            _active_timer = timer
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
        logger.exception("Error in update_all: %s", e)
        _set_status(error="Error interno en actualizacion masiva")
    finally:
        if timer is not None:
            timer.cancel()
        with _update_lock:
            _active_timer = None
        _set_status(updating=False, current_listing=None)


@app.post("/api/listings/{listing_id}/update", status_code=202)
def api_update_single(listing_id: str, background_tasks: BackgroundTasks):
    """Lanza actualizacion de iCal de un listing en background."""
    _validate_listing_id_param(listing_id)
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


@app.post("/api/update/cancel", status_code=200)
def api_cancel_update():
    """Cancela la actualizacion en curso y libera el estado."""
    global _active_timer
    with _update_lock:
        if not _update_status["updating"]:
            raise HTTPException(status_code=409, detail="No hay una actualizacion en curso")
        if _active_timer is not None:
            _active_timer.cancel()
            _active_timer = None
        _update_status.update(updating=False, current_listing=None, error="Cancelled by user")
    _kill_chrome_zombies()
    logger.info("Update cancelled by user.")
    return {"message": "Update cancelled"}


@app.get("/api/status")
async def api_status():
    """Estado actual de actualizacion."""
    with _update_lock:
        return dict(_update_status)


# ================== MAIN ==================

if __name__ == "__main__":
    os.makedirs(ICS_OUTPUT_DIR, exist_ok=True)
    uvicorn.run(
        "ical_server:app",
        host=ICAL_SERVER_HOST,
        port=ICAL_SERVER_PORT,
        reload=False,
    )
