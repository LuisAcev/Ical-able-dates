#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# allin.py
# Scraper de disponibilidad Interval World -> generacion iCalendar (.ics)
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
    DATE_RANGE_START, DATE_RANGE_END,
    SPEED_FACTOR, VACATION_EXCHANGE_TIMEOUT, VACATION_EXCHANGE_PAUSE,
    MORE_DATES_PAUSE, MAX_MORE_DATES_CLICKS,
    DATE_INPUT_PAUSE, DATE_KEY_DELAY, DATE_INPUT_RETRIES,
    HEADLESS,
)
from ical_gen import generate_ics_for_listing
from listings import (
    PRIMARY_LISTINGS, PRIMARY_BEDROOM_FILTER,
    SECONDARY_BEDROOM_FILTER, AVAILABILITY_ONLY_LISTINGS,
    MANUAL_EXTRA_AVAIL,
)

_BROWSER_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--no-zygote",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--ozone-platform=headless",
    "--disable-software-rasterizer",
    "--blink-settings=imagesEnabled=false",
    "--js-flags=--max-old-space-size=192",
]

# ========= ORDEN ESPECIAL: primero 0 cuartos, luego 2 cuartos, luego resto =========
def sort_primary_listings_by_bedrooms(listings):
    def sort_key(prop):
        lid = prop["listing_id"]
        beds = PRIMARY_BEDROOM_FILTER.get(lid)
        if beds == "0":
            group = 0
        elif beds == "2":
            group = 1
        else:
            group = 2
        return (group, lid)
    return sorted(listings, key=sort_key)


def apply_manual_extra_availability(listing_id, available_dates, stored_manual_dates=None):
    if stored_manual_dates:
        ranges = stored_manual_dates
    else:
        ranges = MANUAL_EXTRA_AVAIL.get(str(listing_id)) or MANUAL_EXTRA_AVAIL.get(
            int(listing_id) if str(listing_id).isdigit() else listing_id
        )
    if not ranges:
        return available_dates

    dates_set = set(available_dates)
    before = len(dates_set)

    for start_str, end_str in ranges:
        try:
            sd = datetime.strptime(start_str, "%Y-%m-%d")
            ed = datetime.strptime(end_str, "%Y-%m-%d")
        except ValueError:
            continue
        cur = sd
        while cur < ed:
            if DATE_RANGE_START <= cur <= DATE_RANGE_END:
                dates_set.add(cur.strftime("%Y-%m-%d"))
            cur += timedelta(days=1)

    out = sorted(dates_set)
    added = len(out) - before
    logger.info("Manual extra availability for %s: +%d manual dates.", listing_id, added)
    return out


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


def get_exchange_frame(page):
    """Returns the Page or Frame that contains the exchange form, or None."""
    try:
        if page.query_selector("#fromDate") and page.query_selector("#searchCriteria"):
            return page
    except Exception:
        pass
    for frame in page.frames:
        if frame == page.main_frame:
            continue
        try:
            if frame.query_selector("#fromDate") and frame.query_selector("#searchCriteria"):
                return frame
        except Exception:
            pass
    return None


def set_date_field(frame, field_id, date_str, fast=False):
    el = frame.query_selector(f"#{field_id}")
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
            """([fid, v]) => {
                var el = document.getElementById(fid);
                el.removeAttribute('readonly');
                el.removeAttribute('disabled');
                el.focus();
                el.value = '';
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.value = v;
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
            }""",
            [field_id, date_str],
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
        """([fid, v]) => {
            var el = document.getElementById(fid);
            el.value = v;
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
        }""",
        [field_id, date_str],
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


def login_and_go_to_exchange(page):
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


def fast_set_resort_code(frame, resort_code):
    radio = frame.query_selector("input[name='searchType'][value='ResortSearch']")
    if radio and not radio.is_checked():
        _js_click(radio)

    field = frame.query_selector("#searchCriteria")
    if not field:
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


def _apply_guests_modal(context):
    """Si hay un modal de Guests visible, asegura 1 adulto y hace click en Apply.
    context puede ser Page o Frame. Retorna True si manejó el modal."""
    try:
        apply_btn = context.wait_for_selector(
            "button:has-text('Apply')", timeout=4000, state="visible"
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


def select_guests_in_exchange_form(frame):
    """Abre el widget de Guests haciendo click, luego aplica 1 adulto en el modal."""
    try:
        guest_el = None
        for q in ["[id*='uest']", "[class*='uest']", "[id*='eople']", "[class*='eople']",
                  "[id*='dult']", "[class*='dult']"]:
            guest_el = frame.query_selector(q)
            if guest_el:
                break

        if guest_el:
            guest_el.scroll_into_view_if_needed()
            guest_el.click()
            logger.info("Guests: clicked dropdown to open modal")
            time.sleep(1.0 * SPEED_FACTOR)
        else:
            logger.warning("Guests: no dropdown element found")

        if not _apply_guests_modal(frame):
            # Retry: segundo click en caso de que el primero no haya abierto el modal
            if guest_el:
                try:
                    guest_el.click()
                    time.sleep(1.0 * SPEED_FACTOR)
                except Exception:
                    pass
            if not _apply_guests_modal(frame):
                logger.warning("Guests: modal did not appear after 2 attempts")

    except Exception as e:
        logger.warning("Could not select guests: %s", e)


def robust_continue_in_exchange_form(page, max_retries=4):
    def get_btn(frame):
        btn = frame.query_selector("#exchange_form_continue_btn")
        if btn:
            return btn
        return frame.query_selector(
            "input[type='submit'][value='Continue'], input[type='submit'][value='continue']"
        )

    for attempt in range(1, max_retries + 1):
        _apply_guests_modal(page)
        frame = get_exchange_frame(page)
        if frame is None:
            return True
        prev_url = page.url
        btn = get_btn(frame)
        if btn is not None:
            btn.scroll_into_view_if_needed()
            try:
                btn.click()
            except Exception:
                _js_click(btn)
            time.sleep(0.7 * SPEED_FACTOR)

        # Si el click abrio el modal de guests, manejarlo y reintentar
        if _apply_guests_modal(page):
            time.sleep(0.3)
            continue

        if page.url == prev_url:
            try:
                frame.evaluate("document.querySelector('form').submit()")
            except Exception:
                pass
        wait_until = time.time() + int(8 * SPEED_FACTOR) + attempt * 2
        while time.time() < wait_until:
            if page.url != prev_url or get_exchange_frame(page) is None:
                time.sleep(0.6 * SPEED_FACTOR)
                return True
            time.sleep(0.3)
        time.sleep(0.5 * SPEED_FACTOR)
    return False


def click_any_unredeemed_vacation_exchange(page_ref, timeout=VACATION_EXCHANGE_TIMEOUT):
    page = page_ref[0]
    context = page.context
    end = time.time() + timeout * SPEED_FACTOR
    before_url = page.url
    before_page_ids = {id(p) for p in context.pages}

    xp = (
        "xpath=//tr[contains(@class,'unit_info')]"
        "[.//a[contains(@class,'pop_up') and contains("
        "translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')"
        ",'unredeemed deposit')]]"
    )

    while time.time() < end:
        rows = page.query_selector_all(xp)
        if not rows:
            page.evaluate("window.scrollBy(0, 600)")
            time.sleep(0.3 * SPEED_FACTOR)
            continue
        for row in rows:
            btn = None
            for sel in [
                "xpath=.//input[@type='image' and contains(@src,'vexchange')]",
                "xpath=.//a[contains(translate(normalize-space(.),"
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'vacation exchange')]",
                "xpath=.//button[contains(translate(normalize-space(.),"
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'vacation exchange')]",
            ]:
                els = row.query_selector_all(sel)
                if els:
                    btn = els[0]
                    break
            if not btn:
                continue
            btn.scroll_into_view_if_needed()
            try:
                btn.click()
            except Exception:
                _js_click(btn)
            time.sleep(VACATION_EXCHANGE_PAUSE * SPEED_FACTOR)
            new_pages = [p for p in context.pages if id(p) not in before_page_ids]
            if new_pages:
                new_page = new_pages[0]
                try:
                    new_page.wait_for_load_state("domcontentloaded", timeout=15000)
                except Exception:
                    pass
                page_ref[0] = new_page
                return True
            if page.url != before_url:
                return True
        page.evaluate("window.scrollBy(0, 800)")
        time.sleep(0.4 * SPEED_FACTOR)
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
                if bd is None:
                    next_tr_js = tr.evaluate_handle("el => el.nextElementSibling")
                    next_tr = next_tr_js.as_element()
                    if next_tr:
                        for sp in next_tr.query_selector_all("span#bedrooms"):
                            val = (sp.text_content() or "").strip()
                            if val.isdigit():
                                bd = val
                                break
        except Exception:
            pass
        if required_bedrooms and (bd is None or str(bd) != required_bedrooms):
            continue
        for i in range((end_date - start_date).days):
            d = start_date + timedelta(days=i)
            if DATE_RANGE_START <= d <= DATE_RANGE_END:
                dates.add(d.strftime("%Y-%m-%d"))
    return dates


def _collect_from_avail_divs(block, required_bedrooms):
    dates = set()
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
                    bd = (bedroom_span.text_content() or "").strip()
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
            if DATE_RANGE_START <= d <= DATE_RANGE_END:
                dates.add(d.strftime("%Y-%m-%d"))
    return dates


def parse_availability_from_block(block, listing_id, bedroom_filter):
    required = str(bedroom_filter.get(listing_id, "")).strip() if listing_id in bedroom_filter else None
    dates = set()
    dates |= _collect_from_strong_rows(block, required)
    dates |= _collect_from_avail_divs(block, required)
    return sorted(dates)


def wait_results_or_timeout(page, label=""):
    deadline = time.time() + int(20 * SPEED_FACTOR)
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
            login_and_go_to_exchange(page_ref[0])
            logger.info("[2] Logged in. url=%s", page_ref[0].url)

            frame = get_exchange_frame(page_ref[0]) or page_ref[0]
            logger.info("[3] Exchange frame: %s", "page" if frame == page_ref[0] else "iframe")

            fast_set_resort_code(frame, resort_code)
            set_date_field(frame, "fromDate", DATE_RANGE_START.strftime("%m/%d/%Y"), fast=True)
            set_date_field(frame, "toDate", DATE_RANGE_END.strftime("%m/%d/%Y"), fast=False)
            select_guests_in_exchange_form(frame)
            logger.info("[4] Form filled. Clicking Continue...")

            if not robust_continue_in_exchange_form(page_ref[0]):
                logger.error("[5] Could not click Continue. url=%s", page_ref[0].url)
                return []
            logger.info("[5] Continue OK. url=%s", page_ref[0].url)

            if not wait_results_or_timeout(page_ref[0], "after-continue"):
                return []
            logger.info("[6] Results page loaded. url=%s", page_ref[0].url)

            if not click_any_unredeemed_vacation_exchange(page_ref, timeout=VACATION_EXCHANGE_TIMEOUT):
                logger.error("[7] Could not click Vacation Exchange. url=%s", page_ref[0].url)
                return []
            logger.info("[7] Vacation Exchange clicked. url=%s", page_ref[0].url)

            if not wait_results_or_timeout(page_ref[0], "after-vexchange"):
                return []
            logger.info("[8] Exchange results loaded.")

            url_before_more = page_ref[0].url
            _ = click_more_dates_until_exhausted(page_ref[0], resort_code, pause=MORE_DATES_PAUSE)
            # If "more dates" navigated to a new page, wait for it to fully render
            if page_ref[0].url != url_before_more:
                logger.info("[8b] Navigated to %s after more-dates, waiting for results...", page_ref[0].url)
                wait_results_or_timeout(page_ref[0], "after-more-dates")
            block = find_resort_block_by_code(page_ref[0], resort_code)
            if not block:
                logger.error("[9] Resort block not found: %s. url=%s", resort_code, page_ref[0].url)
                return []
            logger.info("[9] Resort block %s found. Parsing...", resort_code)
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


# ================== MAIN ==================
def main():
    logger.info("Starting Interval World -> iCal scraper...")

    ordered_primary = sort_primary_listings_by_bedrooms(PRIMARY_LISTINGS)
    for prop in ordered_primary:
        logger.info("Scraping %s (Listing ID: %s)...", prop["resort_code"], prop["listing_id"])
        try:
            available = collect_available_dates(prop["resort_code"], prop["listing_id"], PRIMARY_BEDROOM_FILTER)
            available = apply_manual_extra_availability(prop["listing_id"], available)
            logger.info("%d available dates found.", len(available))
            generate_ics_for_listing(prop["listing_id"], available, DATE_RANGE_START, DATE_RANGE_END)
        except Exception as e:
            logger.exception("Error processing %s - %s: %s", prop["listing_id"], prop["resort_code"], e)

    for prop in AVAILABILITY_ONLY_LISTINGS:
        logger.info("Extra availability %s (Listing ID: %s)...", prop["resort_code"], prop["listing_id"])
        try:
            available = collect_available_dates(prop["resort_code"], prop["listing_id"], SECONDARY_BEDROOM_FILTER)
            available = apply_manual_extra_availability(prop["listing_id"], available)
            generate_ics_for_listing(prop["listing_id"], available, DATE_RANGE_START, DATE_RANGE_END)
            if available:
                logger.info("%d available dates.", len(available))
            else:
                logger.info("No availability.")
        except Exception as e:
            logger.exception("Error en %s (%s): %s", prop["listing_id"], prop["resort_code"], e)


if __name__ == "__main__":
    main()
