#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# allin.py
# Scraper de disponibilidad Interval World (seccion Getaways) -> generacion iCalendar (.ics)
#
# 1) LISTA PRINCIPAL: busca disponibilidad completa en Interval.
# 2) LISTA SECUNDARIA: busca disponibilidad adicional.
# 3) Genera archivos .ics por listing para sincronizacion con Airbnb via iCal import.
#
# Configuracion: .env | Listings: listings.py | iCal: ical_gen.py

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from datetime import datetime, timedelta
import logging
import time
import re

logger = logging.getLogger(__name__)

from config import (
    INTERVAL_USERNAME, INTERVAL_PASSWORD,
    get_date_range_start, get_date_range_end,
    SPEED_FACTOR, GETAWAY_NAV_TIMEOUT,
    MORE_DATES_PAUSE, MAX_MORE_DATES_CLICKS,
    DATE_INPUT_PAUSE, DATE_KEY_DELAY, DATE_INPUT_RETRIES,
    HEADLESS, WAIT_RESULTS_TIMEOUT,
)

_BROWSER_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--no-zygote",
    "--single-process",  # Run everything in one OS process — prevents fork() EAGAIN in containers
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--in-process-gpu",
    "--disable-features=NetworkService,IsolateOrigins,site-per-process",
    "--ozone-platform=headless",
    "--disable-software-rasterizer",
    "--blink-settings=imagesEnabled=false",
    "--js-flags=--max-old-space-size=192",
]

def apply_manual_blocked_dates(available_dates, manual_ranges):
    if not manual_ranges:
        return available_dates
    blocked_manual = set()
    for (start, end) in manual_ranges:
        try:
            cur = datetime.strptime(start, "%Y-%m-%d")
            end_dt = datetime.strptime(end, "%Y-%m-%d")
        except ValueError:
            continue
        while cur < end_dt:
            blocked_manual.add(cur.strftime("%Y-%m-%d"))
            cur += timedelta(days=1)
    result = [d for d in available_dates if d not in blocked_manual]
    removed = len(available_dates) - len(result)
    logger.info("Manual blocked dates: -%d dates removed from available.", removed)
    return result


def apply_manual_available_override(available_dates, override_ranges):
    if not override_ranges:
        return available_dates
    override_set = set()
    for (start, end) in override_ranges:
        try:
            cur = datetime.strptime(start, "%Y-%m-%d")
            end_dt = datetime.strptime(end, "%Y-%m-%d")
        except ValueError:
            continue
        while cur < end_dt:
            override_set.add(cur.strftime("%Y-%m-%d"))
            cur += timedelta(days=1)
    available_set = set(available_dates)
    added = len(override_set - available_set)
    logger.info("Manual available overrides: +%d dates added to available.", added)
    return sorted(available_set | override_set)


# ========== Playwright helpers ==========

def _js_click(el):
    el.evaluate("el => el.click()")


def _type_slow(el, text):
    el.type(text, delay=int(DATE_KEY_DELAY * 1000))


def _hard_clear(el):
    el.scroll_into_view_if_needed()
    try:
        el.click()
    except Exception:
        pass
    time.sleep(0.10)
    el.press("Control+a")
    el.press("Delete")
    el.press("Backspace")
    el.evaluate(
        "el => {"
        "  el.value = '';"
        "  el.dispatchEvent(new Event('input', {bubbles: true}));"
        "  el.dispatchEvent(new Event('change', {bubbles: true}));"
        "}"
    )
    time.sleep(0.05)


_UP = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_LO = "abcdefghijklmnopqrstuvwxyz"


def _lower_xp(expr="."):
    """Expresion XPath que normaliza y pasa a minusculas (XPath 1.0 no tiene lower-case())."""
    return f"translate(normalize-space({expr}),'{_UP}','{_LO}')"


# Pistas para ubicar los campos de fecha si el form de Getaways no usa los ids
# conocidos. 'ident' se busca en id/name; 'labels' en el texto visible previo.
_DATE_FIELD_HINTS = {
    "fromDate": {
        "ident": ("fromdate", "startdate", "earliest"),
        "labels": ("earliest travel date", "check-in"),
    },
    "toDate": {
        "ident": ("todate", "enddate", "latest"),
        "labels": ("latest travel date", "check-out"),
    },
}


def _resolve_date_input(ctx, field_id):
    """Ubica el input de fecha: primero por id conocido, luego por id/name y etiqueta."""
    el = ctx.query_selector(f"#{field_id}")
    if el is not None:
        return el

    hints = _DATE_FIELD_HINTS[field_id]
    for cand in ctx.query_selector_all("input"):
        try:
            ident = f"{cand.get_attribute('id') or ''} {cand.get_attribute('name') or ''}".lower()
        except Exception:
            continue
        if any(h in ident.replace(" ", "") for h in hints["ident"]):
            logger.warning("%s ubicado por id/name alterno: '%s'", field_id, ident.strip())
            return cand

    for text in hints["labels"]:
        el = ctx.query_selector(
            f"xpath=//*[contains({_lower_xp()},'{text}')]/following::input[1]"
        )
        if el is not None:
            logger.warning("%s ubicado por etiqueta '%s'", field_id, text)
            return el
    return None


def _has_search_form(ctx):
    """True si el contexto contiene el buscador (campo de resort + fecha inicial)."""
    try:
        if ctx.query_selector("#fromDate") and ctx.query_selector("#searchCriteria"):
            return True
        return bool(_resolve_date_input(ctx, "fromDate") and _find_resort_code_input(ctx))
    except Exception:
        return False


def get_search_frame(page):
    """Returns the Page or Frame that contains the search form, or None."""
    if _has_search_form(page):
        return page
    for frame in page.frames:
        if frame == page.main_frame:
            continue
        if _has_search_form(frame):
            return frame
    return None


def set_date_field(frame, field_id, date_str, fast=False):
    el = _resolve_date_input(frame, field_id)
    if el is None:
        logger.warning("set_date_field: #%s not found", field_id)
        return
    el.scroll_into_view_if_needed()
    time.sleep(DATE_INPUT_PAUSE)

    current = (el.get_attribute("value") or "").strip()
    if current == date_str:
        logger.debug("%s: already has %s, skipping.", field_id, date_str)
        return

    if fast:
        frame.evaluate(
            """([el, v]) => {
                el.removeAttribute('readonly');
                el.removeAttribute('disabled');
                el.focus();
                el.value = '';
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.value = v;
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
            }""",
            [el, date_str],
        )
        time.sleep(0.2)
        try:
            el.press("Tab")
        except Exception:
            pass
        return

    for attempt in range(1, DATE_INPUT_RETRIES + 1):
        _hard_clear(el)
        _type_slow(el, date_str)
        time.sleep(0.20)
        try:
            el.press("Tab")
        except Exception:
            pass
        time.sleep(DATE_INPUT_PAUSE)
        val = (el.get_attribute("value") or "").strip()
        if re.fullmatch(r"\d{2}/\d{2}/\d{4}", val) and val == date_str:
            return
        time.sleep(0.3)

    frame.evaluate(
        """([el, v]) => {
            el.value = v;
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
        }""",
        [el, date_str],
    )
    time.sleep(0.2)
    try:
        el.press("Tab")
    except Exception:
        pass


def dismiss_cookie_banner(page):
    try:
        page.wait_for_selector("#onetrust-accept-btn-handler", timeout=5000)
        page.click("#onetrust-accept-btn-handler")
        time.sleep(0.5)
    except PlaywrightTimeoutError:
        try:
            page.evaluate(
                "document.querySelectorAll('.onetrust-pc-dark-filter, #onetrust-banner-sdk')"
                ".forEach(e => e.remove());"
            )
        except Exception:
            pass


def login_and_go_home(page):
    page.goto("https://www.intervalworld.com/web/my/auth/loginPage", wait_until="domcontentloaded")
    dismiss_cookie_banner(page)
    page.wait_for_selector("[name='j_username']", timeout=25000)
    page.fill("[name='j_username']", INTERVAL_USERNAME)
    page.fill("[name='j_password']", INTERVAL_PASSWORD)
    page.wait_for_selector("#buttonlogin")
    page.click("#buttonlogin")
    page.wait_for_selector(
        "a.text_hide.dc-mega, #searchCriteria",
        timeout=int(25 * SPEED_FACTOR * 1000),
    )
    time.sleep(1.0 * SPEED_FACTOR)
    page.goto("https://www.intervalworld.com/web/cs?a=0", wait_until="domcontentloaded")
    time.sleep(1.0 * SPEED_FACTOR)


_GETAWAYS_LINK_XP = f"xpath=//a[{_lower_xp()}='getaways']"
_NAV_CLICK_TIMEOUT = 4000  # ms


def _wait_for_search_form(page, deadline):
    while time.time() < deadline:
        if get_search_frame(page) is not None:
            return True
        time.sleep(0.4)
    return False


def _log_form_candidates(page):
    """Diagnostico: vuelca los inputs de cada frame cuando no se reconoce el buscador."""
    for frame in page.frames:
        try:
            fields = frame.evaluate(
                """() => Array.from(document.querySelectorAll('input, select'))
                    .map(e => [e.tagName, e.id, e.name, e.type].join('|')).slice(0, 40)"""
            )
        except Exception:
            continue
        if fields:
            logger.warning("[diag] campos en %s: %s", frame.url, fields)


def go_to_getaways(page, timeout=GETAWAY_NAV_TIMEOUT):
    """Abre el buscador de Getaways desde el menu principal.

    El tab 'Getaways' despliega un submenu con 'Getaways' y 'ShortStay Getaways';
    el primero lleva al buscador que usamos aqui. Se navega por el menu porque
    Interval no expone una URL estable para esa pagina.
    """
    deadline = time.time() + timeout * SPEED_FACTOR
    tabs = page.query_selector_all(_GETAWAYS_LINK_XP)
    if tabs:
        try:
            tabs[0].hover(timeout=_NAV_CLICK_TIMEOUT)
            time.sleep(0.6 * SPEED_FACTOR)
        except Exception:
            pass

    # Tras el hover, el item del submenu queda de ultimo: se prueba primero.
    candidates = list(reversed(page.query_selector_all(_GETAWAYS_LINK_XP)))
    candidates += page.query_selector_all(
        f"xpath=//a[contains({_lower_xp('@href')},'getaway')]"
    )

    for el in candidates:
        # Timeout corto: los items del submenu pueden estar ocultos y el default
        # de la pagina (60s) dejaria colgado cada intento.
        try:
            el.scroll_into_view_if_needed(timeout=_NAV_CLICK_TIMEOUT)
            el.click(timeout=_NAV_CLICK_TIMEOUT)
        except Exception:
            try:
                _js_click(el)
            except Exception:
                continue
        if _wait_for_search_form(page, min(deadline, time.time() + 8 * SPEED_FACTOR)):
            logger.info("Getaways abierto. url=%s", page.url)
            return True
        if time.time() >= deadline:
            break

    logger.error("No se pudo abrir Getaways desde el menu. url=%s", page.url)
    return False


def _find_resort_code_input(ctx):
    """Input del codigo de resort: #searchCriteria, o el primer texto que no sea fecha."""
    el = ctx.query_selector("#searchCriteria")
    if el is not None:
        return el
    for cand in ctx.query_selector_all("input[type='text'], input:not([type])"):
        try:
            ident = f"{cand.get_attribute('id') or ''} {cand.get_attribute('name') or ''}".lower()
        except Exception:
            continue
        if "date" in ident:
            continue
        logger.warning("Codigo de resort: usando input alterno '%s'", ident.strip())
        return cand
    return None


def _check_resort_search_radio(frame):
    """Marca la opcion de busqueda por codigo de resort ('Resort Name, Code')."""
    radio = frame.query_selector("input[name='searchType'][value='ResortSearch']")
    if radio is None:
        for cand in frame.query_selector_all("input[type='radio']"):
            try:
                label = cand.evaluate(
                    "el => ((el.closest('label') || el.parentElement || {}).textContent || '')"
                )
            except Exception:
                continue
            if "resort" in label.lower():
                radio = cand
                break
    if radio is None:
        logger.warning("Radio de busqueda por resort no encontrado")
        return
    try:
        if not radio.is_checked():
            _js_click(radio)
    except Exception as e:
        logger.warning("No se pudo marcar el radio de resort: %s", e)


def fast_set_resort_code(frame, resort_code):
    _check_resort_search_radio(frame)

    field = _find_resort_code_input(frame)
    if not field:
        logger.warning("Campo de codigo de resort no encontrado")
        return

    frame.evaluate(
        """([el, v]) => {
            el.style.opacity = 1;
            el.removeAttribute('disabled');
            el.removeAttribute('readonly');
            el.focus();
            el.value = '';
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.value = v;
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
            if (el.blur) el.blur();
        }""",
        [field, resort_code],
    )

    if (field.get_attribute("value") or "").strip() != resort_code:
        try:
            field.click()
            field.press("Control+a")
            field.press("Delete")
            field.type(resort_code)
            field.press("Tab")
        except Exception:
            pass
    time.sleep(0.6 * SPEED_FACTOR)


def _apply_guests_modal(context, timeout=4000):
    """Si hay un modal de Guests visible, asegura 1 adulto y hace click en Apply.
    context puede ser Page o Frame. Retorna True si manejó el modal."""
    try:
        apply_btn = context.wait_for_selector(
            "button:has-text('Apply')", timeout=timeout, state="visible"
        )
        # El contador de adultos está entre los botones [-] y [+]
        plus_btns = context.query_selector_all("xpath=//button[normalize-space(text())='+']")
        if plus_btns:
            adults_n = context.evaluate(
                """(btn) => {
                    let el = btn.previousElementSibling;
                    while (el) {
                        const n = parseInt(el.textContent.trim());
                        if (!isNaN(n) && n >= 0) return n;
                        el = el.previousElementSibling;
                    }
                    return -1;
                }""",
                plus_btns[0],
            )
            logger.info("Guests modal open: adults_count=%s", adults_n)
            if adults_n <= 0:
                plus_btns[0].click()
                time.sleep(0.3)
                logger.info("Guests: clicked + for adults")
        apply_btn.click()
        logger.info("Guests modal Applied")
        time.sleep(0.5 * SPEED_FACTOR)
        return True
    except PlaywrightTimeoutError:
        return False


def _open_guests_dropdown(frame):
    """Intenta abrir el dropdown de Guests probando distintas estrategias de click.
    Retorna True si el modal aparecio, False si no."""
    # El contenedor conocido del widget de Guests
    container = frame.query_selector("#exchange_form_Number_of_guest")
    if not container:
        # Fallback: buscar por atributos genéricos
        for q in ["[id*='uest']", "[class*='uest']", "[id*='eople']", "[class*='eople']"]:
            container = frame.query_selector(q)
            if container:
                break

    if not container:
        logger.warning("Guests: widget container not found")
        return False

    container.scroll_into_view_if_needed()

    # Estrategia 1: click en el primer hijo clickeable dentro del contenedor
    trigger = container.query_selector("button, a, input, span, div")
    if trigger:
        logger.info("Guests: clicking inner trigger <%s>", trigger.evaluate("el => el.tagName"))
        trigger.click()
        time.sleep(1.0 * SPEED_FACTOR)
        if _apply_guests_modal(frame):
            return True

    # Estrategia 2: click directo en el contenedor
    logger.info("Guests: clicking container directly")
    container.click()
    time.sleep(1.0 * SPEED_FACTOR)
    if _apply_guests_modal(frame):
        return True

    # Estrategia 3: mousedown+mouseup+click via JS para widgets que escuchan mousedown
    logger.info("Guests: dispatching mousedown via JS")
    frame.evaluate(
        """(el) => {
            ['mousedown','mouseup','click'].forEach(evt =>
                el.dispatchEvent(new MouseEvent(evt, {bubbles: true, cancelable: true}))
            );
        }""",
        container,
    )
    time.sleep(1.0 * SPEED_FACTOR)
    return _apply_guests_modal(frame)


def _set_guests_select(frame):
    """Getaways trae los huespedes en un <select> ('2 Adults 0 Children' por defecto).
    Elige la opcion de 1 adulto sin ninos. Retorna True si la aplico."""
    for el in frame.query_selector_all("select"):
        try:
            options = frame.evaluate(
                "el => Array.from(el.options).map(o => o.textContent.trim())", el
            )
        except Exception:
            continue
        if not any("adult" in (o or "").lower() for o in options):
            continue
        for i, text in enumerate(options):
            low = (text or "").lower()
            if re.search(r"\b1\s*adult", low) and not re.search(r"[1-9]\s*child", low):
                el.select_option(index=i)
                logger.info("Guests select: '%s'", text)
                return True
        logger.warning("Guests select sin opcion de 1 adulto: %s", options)
        return False
    return False


def select_guests(frame):
    """Deja 1 adulto: por el <select> de Getaways o, si no existe, por el modal."""
    try:
        if _set_guests_select(frame):
            return
        if not _open_guests_dropdown(frame):
            logger.warning("Guests: modal did not open after all strategies")
    except Exception as e:
        logger.warning("Could not select guests: %s", e)


def robust_continue_search_form(page, max_retries=4):
    def get_btn(frame):
        btn = frame.query_selector("#exchange_form_continue_btn")
        if btn:
            return btn
        # input submit variants
        for val in ["Find Getaway", "Find Getaways", "Continue", "continue",
                    "Search", "search", "Continuar", "Buscar"]:
            b = frame.query_selector(f"input[type='submit'][value='{val}']")
            if b:
                return b
        # button element variants
        for txt in ["Find Getaway", "Continue", "Search", "Continuar", "Buscar"]:
            b = frame.query_selector(f"button:has-text('{txt}')")
            if b:
                return b
        return None

    for attempt in range(1, max_retries + 1):
        _apply_guests_modal(page, timeout=800)
        frame = get_search_frame(page)
        if frame is None:
            return True
        prev_url = page.url
        btn = get_btn(frame)
        if btn is not None:
            lbl = btn.get_attribute("value") or btn.text_content() or "?"
            logger.info("Continue btn found: '%s' (attempt %d)", lbl.strip(), attempt)
            btn.scroll_into_view_if_needed()
            try:
                btn.click()
            except Exception:
                _js_click(btn)
            time.sleep(0.7 * SPEED_FACTOR)
        else:
            logger.warning("Continue btn NOT found (attempt %d), using form.submit()", attempt)

        # Si el click abrio el modal de guests, manejarlo y reintentar
        if _apply_guests_modal(page, timeout=800):
            time.sleep(0.3)
            continue

        if page.url == prev_url:
            try:
                frame.evaluate("document.querySelector('form').submit()")
            except Exception:
                pass
        wait_until = time.time() + int(8 * SPEED_FACTOR) + attempt * 2
        while time.time() < wait_until:
            cur = page.url
            if cur != prev_url and get_search_frame(page) is None:
                time.sleep(0.6 * SPEED_FACTOR)
                return True
            time.sleep(0.3)
        logger.info("Continue attempt %d timeout. url=%s", attempt, page.url)
        time.sleep(0.5 * SPEED_FACTOR)
    return False


def locate_all_resort_blocks(page):
    all_blocks = []
    for frame in page.frames:
        try:
            blocks = frame.query_selector_all(".table_frame")
            all_blocks.extend(blocks)
        except Exception:
            pass
    return all_blocks


def find_resort_block_by_code(page, resort_code):
    blocks = locate_all_resort_blocks(page)
    target = resort_code.strip().upper()
    for block in blocks:
        try:
            for s in block.query_selector_all("xpath=.//strong"):
                if (s.text_content() or "").strip().upper() == target:
                    return block
        except Exception:
            continue
    return None


def click_more_dates_until_exhausted(page, resort_code, pause=MORE_DATES_PAUSE, max_clicks=MAX_MORE_DATES_CLICKS):
    clicks = 0
    while clicks < max_clicks:
        block = find_resort_block_by_code(page, resort_code)
        if not block:
            break
        more = None
        for sel in [
            "xpath=.//a[contains(translate(normalize-space(.),"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'more dates')]",
            "xpath=.//button[contains(translate(normalize-space(.),"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'more dates')]",
            "xpath=.//a[contains(translate(normalize-space(.),"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'see more dates')]",
            "xpath=.//button[contains(translate(normalize-space(.),"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'see more dates')]",
            "xpath=.//*[contains(@class,'see_more_btn')]//a",
            "xpath=.//*[contains(@class,'see_more_btn')]//button",
            "xpath=.//*[contains(@class,'see_more_btn')]//input",
        ]:
            els = block.query_selector_all(sel)
            if els:
                more = els[0]
                break
        if more is None:
            return clicks
        more.scroll_into_view_if_needed()
        try:
            more.click()
        except Exception:
            _js_click(more)
        time.sleep(pause)
        clicks += 1
    return clicks


# ------- Parser -------

def _collect_from_strong_rows(block, required_bedrooms):
    dates = set()
    range_start = get_date_range_start()
    range_end = get_date_range_end(range_start)
    strongs = block.query_selector_all("xpath=.//strong[contains(., ' - ')]")
    for st in strongs:
        txt = (st.text_content() or "").strip()
        if not txt or " - " not in txt:
            continue
        txt = " ".join(txt.split())
        start_str, end_str = [s.strip() for s in txt.split(" - ", 1)]
        try:
            start_date = datetime.strptime(start_str, "%b %d %Y")
            end_date = datetime.strptime(end_str, "%b %d %Y")
        except Exception:
            continue
        bd = None
        try:
            tr_js = st.evaluate_handle("el => el.closest('tr')")
            tr = tr_js.as_element()
            if tr:
                for sp in tr.query_selector_all("span#bedrooms"):
                    val = (sp.text_content() or "").strip()
                    if val.isdigit():
                        bd = val
                        break
                    if val.upper() in ("E", "S"):  # Efficiency/Studio = 0 bedrooms
                        bd = "0"
                        break
                if bd is None:
                    next_tr_js = tr.evaluate_handle("el => el.nextElementSibling")
                    next_tr = next_tr_js.as_element()
                    if next_tr:
                        for sp in next_tr.query_selector_all("span#bedrooms"):
                            val = (sp.text_content() or "").strip()
                            if val.isdigit():
                                bd = val
                                break
                            if val.upper() in ("E", "S"):
                                bd = "0"
                                break
        except Exception:
            pass
        if required_bedrooms and (bd is None or str(bd) != required_bedrooms):
            continue
        for i in range((end_date - start_date).days):
            d = start_date + timedelta(days=i)
            if range_start <= d <= range_end:
                dates.add(d.strftime("%Y-%m-%d"))
    return dates


def _collect_from_avail_divs(block, required_bedrooms):
    dates = set()
    range_start = get_date_range_start()
    range_end = get_date_range_end(range_start)
    rows = block.query_selector_all("div.avail_dates")
    for row in rows:
        date_range = (row.text_content() or "").strip()
        if " - " not in date_range:
            continue
        bd = None
        try:
            next_div_js = row.evaluate_handle("el => el.nextElementSibling")
            next_div = next_div_js.as_element()
            if next_div:
                bedroom_span = next_div.query_selector("span#bedrooms")
                if bedroom_span:
                    raw = (bedroom_span.text_content() or "").strip()
                    bd = "0" if raw.upper() in ("E", "S") else raw
        except Exception:
            pass
        if required_bedrooms and (bd is None or bd != required_bedrooms):
            continue
        try:
            start_str, end_str = [s.strip() for s in date_range.split(" - ", 1)]
            start_date = datetime.strptime(start_str, "%b %d %Y")
            end_date = datetime.strptime(end_str, "%b %d %Y")
        except Exception:
            continue
        for i in range((end_date - start_date).days):
            d = start_date + timedelta(days=i)
            if range_start <= d <= range_end:
                dates.add(d.strftime("%Y-%m-%d"))
    return dates


def parse_availability_from_block(block, listing_id, bedroom_filter):
    required = str(bedroom_filter.get(listing_id, "")).strip() if listing_id in bedroom_filter else None
    dates = set()
    dates |= _collect_from_strong_rows(block, required)
    dates |= _collect_from_avail_divs(block, required)
    return sorted(dates)


def wait_results_or_timeout(page, label=""):
    deadline = time.time() + int(WAIT_RESULTS_TIMEOUT * SPEED_FACTOR)
    while time.time() < deadline:
        for frame in page.frames:
            try:
                if frame.query_selector(".table_frame"):
                    time.sleep(0.8 * SPEED_FACTOR)
                    return True
                content = frame.evaluate(
                    "() => document.body ? document.body.innerHTML.toLowerCase() : ''"
                )
                if "no availability" in content:
                    time.sleep(0.8 * SPEED_FACTOR)
                    return True
            except Exception:
                pass
        time.sleep(0.5)
    logger.warning("No results appeared [%s] url=%s", label, page.url)
    return False


# ---------- Recoleccion ----------

def collect_available_dates(resort_code, listing_id, bedroom_filter):
    range_start = get_date_range_start()
    range_end = get_date_range_end(range_start)
    pw = sync_playwright().start()
    try:
        browser = pw.chromium.launch(headless=HEADLESS, args=_BROWSER_ARGS)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        page.set_default_timeout(60000)
        page.set_default_navigation_timeout(60000)
        page_ref = [page]
        try:
            logger.info("[1] Logging in...")
            login_and_go_home(page_ref[0])
            logger.info("[2] Logged in. url=%s", page_ref[0].url)

            if not go_to_getaways(page_ref[0]):
                _log_form_candidates(page_ref[0])
                raise Exception(
                    "No se pudo abrir el buscador de Getaways desde el menu principal"
                )

            frame = get_search_frame(page_ref[0]) or page_ref[0]
            logger.info("[3] Getaways form: %s", "page" if frame == page_ref[0] else "iframe")

            fast_set_resort_code(frame, resort_code)
            set_date_field(frame, "fromDate", range_start.strftime("%m/%d/%Y"), fast=True)
            set_date_field(frame, "toDate", range_end.strftime("%m/%d/%Y"), fast=False)
            select_guests(frame)
            logger.info("[4] Form filled. Clicking Find Getaway...")

            if not robust_continue_search_form(page_ref[0]):
                logger.warning("[5] No se pudo enviar el formulario. url=%s", page_ref[0].url)
            else:
                logger.info("[5] Busqueda enviada. url=%s", page_ref[0].url)

            if not wait_results_or_timeout(page_ref[0], "after-find-getaway"):
                return []
            logger.info("[6] Getaway results loaded. url=%s", page_ref[0].url)

            url_before_more = page_ref[0].url
            click_more_dates_until_exhausted(page_ref[0], resort_code, pause=MORE_DATES_PAUSE)
            # If "more dates" navigated to a new page, wait for it to fully render
            if page_ref[0].url != url_before_more:
                logger.info("[7] Navigated to %s after more-dates, waiting for results...", page_ref[0].url)
                wait_results_or_timeout(page_ref[0], "after-more-dates")
            block = find_resort_block_by_code(page_ref[0], resort_code)
            if not block:
                logger.error("[8] Resort block not found: %s. url=%s", resort_code, page_ref[0].url)
                return []
            logger.info("[8] Resort block %s found. Parsing...", resort_code)
            available_dates = parse_availability_from_block(block, listing_id, bedroom_filter)
            return list(sorted(set(available_dates)))
        finally:
            try:
                browser.close()
            except Exception as e:
                logger.warning("Error closing browser: %s", e)
    finally:
        try:
            pw.stop()
        except Exception:
            pass


