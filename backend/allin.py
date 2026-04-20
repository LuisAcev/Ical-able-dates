#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# interval_all.py
# Scraper de disponibilidad Interval World -> generacion iCalendar (.ics)
#
# 1) LISTA PRINCIPAL: busca disponibilidad completa en Interval.
# 2) LISTA SECUNDARIA: busca disponibilidad adicional.
# 3) Genera archivos .ics por listing para sincronizacion con Airbnb via iCal import.
#
# Configuracion: .env | Listings: listings.py | iCal: ical_gen.py

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException

from datetime import datetime, timedelta
import logging
import shutil
import subprocess
import threading
import time, re

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

USERNAME = INTERVAL_USERNAME
PASSWORD = INTERVAL_PASSWORD

# ========= ORDEN ESPECIAL: primero 0 cuartos, luego 2 cuartos, luego resto =========
def sort_primary_listings_by_bedrooms(listings):
    """
    Orden:
      1) Estudios (0 dormitorios)
      2) 2 dormitorios
      3) Lo demás (1, 3, etc.)
    """
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
    """
    Añade manualmente rangos de disponibilidad extra a la lista de available_dates
    usando la misma lógica que Interval (incluye start, excluye end).
    Si stored_manual_dates tiene datos, los usa. Si no, fallback a MANUAL_EXTRA_AVAIL.
    """
    if stored_manual_dates:
        ranges = stored_manual_dates
    else:
        # Fallback: buscar en dict hardcodeado con string e int keys
        ranges = MANUAL_EXTRA_AVAIL.get(str(listing_id)) or MANUAL_EXTRA_AVAIL.get(int(listing_id) if str(listing_id).isdigit() else listing_id)
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
    """Remove manually blocked date ranges from available dates."""
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
    removed = len(blocked_manual)
    logger.info("Manual blocked dates: -%d dates removed from available.", removed)
    return [d for d in available_dates if d not in blocked_manual]


def apply_manual_available_override(available_dates, override_ranges):
    """Force-add date ranges to available list, overriding scraper blocks."""
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

# Speed knobs cargados desde config.py via .env

# ========== Selenium helpers ==========
def js_click(driver, el):
    driver.execute_script("arguments[0].click();", el)

def _type_slow(el, text):
    for ch in text:
        el.send_keys(ch)
        time.sleep(DATE_KEY_DELAY)

def _hard_clear(driver, el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    try:
        el.click()
    except Exception:
        pass
    time.sleep(0.10)
    for _ in range(2):
        try:
            el.send_keys(Keys.CONTROL, "a")
        except Exception:
            el.send_keys(Keys.COMMAND, "a")
        el.send_keys(Keys.DELETE)
        el.send_keys(Keys.BACK_SPACE)
        time.sleep(0.05)
    driver.execute_script("arguments[0].value='';", el)
    driver.execute_script(
        "arguments[0].dispatchEvent(new Event('input',{bubbles:true}));"
        "arguments[0].dispatchEvent(new Event('change',{bubbles:true}));",
        el
    )
    time.sleep(0.05)

def set_date_field(driver, field_id, date_str, fast=False):
    """
    Si fast=True: pone la fecha directo con JS (más rápido, sin tipear).
    Si fast=False: usa el método tradicional con tipeo.
    """
    el = driver.find_element(By.ID, field_id)
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    time.sleep(DATE_INPUT_PAUSE)

    current = (el.get_attribute("value") or "").strip()
    if current == date_str:
        logger.debug("%s: ya tenia %s, se deja igual.", field_id, date_str)
        return

    if fast:
        driver.execute_script(
            "var el=arguments[0],v=arguments[1];"
            "el.removeAttribute('readonly');"
            "el.removeAttribute('disabled');"
            "el.focus();"
            "el.value='';"
            "el.dispatchEvent(new Event('input',{bubbles:true}));"
            "el.value=v;"
            "el.dispatchEvent(new Event('input',{bubbles:true}));"
            "el.dispatchEvent(new Event('change',{bubbles:true}));",
            el, date_str
        )
        time.sleep(0.2)
        try:
            el.send_keys(Keys.TAB)
        except Exception:
            pass
        return

    for attempt in range(1, DATE_INPUT_RETRIES + 1):
        _hard_clear(driver, el)
        _type_slow(el, date_str)
        time.sleep(0.20)
        try:
            el.send_keys(Keys.TAB)
        except Exception:
            pass
        time.sleep(DATE_INPUT_PAUSE)
        val = (el.get_attribute("value") or "").strip()
        if re.fullmatch(r"\d{2}/\d{2}/\d{4}", val) and val == date_str:
            return
        time.sleep(0.3)

    driver.execute_script(
        "var el=arguments[0],v=arguments[1];"
        "el.value=v;"
        "el.dispatchEvent(new Event('input',{bubbles:true}));"
        "el.dispatchEvent(new Event('change',{bubbles:true}));",
        el, date_str
    )
    time.sleep(0.2)
    try:
        el.send_keys(Keys.TAB)
    except Exception:
        pass

def create_driver():
    opts = Options()
    if HEADLESS:
        opts.add_argument("--headless=new")
        opts.add_argument("--window-size=1920,1080")
    else:
        opts.add_argument("--start-maximized")
    # Flags requeridos para correr Chrome en contenedores Docker/Railway
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-setuid-sandbox")
    opts.add_argument("--no-zygote")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-background-timer-throttling")
    opts.add_argument("--disable-renderer-backgrounding")
    opts.add_argument("--disable-backgrounding-occluded-windows")
    opts.add_argument("--disable-ipc-flooding-protection")
    opts.add_argument("--disable-crash-reporter")
    opts.add_argument("--disable-breakpad")
    opts.add_argument("--log-level=3")
    opts.add_argument("--blink-settings=imagesEnabled=false")
    opts.add_argument("--js-flags=--max-old-space-size=192")
    opts.add_argument("--disable-software-rasterizer")
    opts.add_argument("--disable-features=VizDisplayCompositor")
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])
    chromedriver_path = shutil.which("chromedriver") or "/usr/local/bin/chromedriver"
    service = Service(executable_path=chromedriver_path, log_output=subprocess.DEVNULL)
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(60)
    driver.set_script_timeout(30)
    return driver

def dismiss_cookie_banner(driver):
    try:
        btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
        )
        btn.click()
        time.sleep(0.5)
    except TimeoutException:
        driver.execute_script(
            "document.querySelectorAll('.onetrust-pc-dark-filter, #onetrust-banner-sdk')"
            ".forEach(e => e.remove());"
        )

def login_and_go_to_exchange(driver, wait):
    driver.get("https://www.intervalworld.com/web/my/auth/loginPage")
    dismiss_cookie_banner(driver)
    wait.until(EC.presence_of_element_located((By.NAME, "j_username"))).send_keys(USERNAME)
    driver.find_element(By.NAME, "j_password").send_keys(PASSWORD)
    wait.until(EC.element_to_be_clickable((By.ID, "buttonlogin"))).click()
    wait.until(EC.any_of(
        EC.presence_of_element_located((By.CSS_SELECTOR, "a.text_hide.dc-mega")),
        EC.presence_of_element_located((By.ID, "searchCriteria"))
    ))
    time.sleep(1.0 * SPEED_FACTOR)
    driver.get("https://www.intervalworld.com/web/cs?a=0")
    time.sleep(1.0 * SPEED_FACTOR)

def get_exchange_form(driver):
    driver.switch_to.default_content()
    forms = driver.find_elements(
        By.XPATH,
        "//form[.//input[@id='fromDate'] and .//input[@id='toDate'] and .//input[@id='searchCriteria']]"
    )
    if forms:
        return forms[0]
    for fr in driver.find_elements(By.TAG_NAME, "iframe"):
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(fr)
            forms = driver.find_elements(
                By.XPATH,
                "//form[.//input[@id='fromDate'] and .//input[@id='toDate'] and .//input[@id='searchCriteria']]"
            )
            if forms:
                return forms[0]
        except Exception:
            pass
    driver.switch_to.default_content()
    return None

def fast_set_resort_code(driver, resort_code):
    form = get_exchange_form(driver)
    if form:
        radios = form.find_elements(By.XPATH, ".//input[@name='searchType' and @value='ResortSearch']")
        if radios and not radios[0].is_selected():
            js_click(driver, radios[0])
        field = form.find_element(By.ID, "searchCriteria")
    else:
        radio = driver.find_element(By.CSS_SELECTOR, "input[name='searchType'][value='ResortSearch']")
        if not radio.is_selected():
            js_click(driver, radio)
        field = driver.find_element(By.ID, "searchCriteria")

    driver.execute_script(
        "const el=arguments[0],v=arguments[1];"
        "el.style.opacity=1;el.removeAttribute('disabled');el.removeAttribute('readonly');"
        "el.focus();el.value='';el.dispatchEvent(new Event('input',{bubbles:true}));"
        "el.value=v;el.dispatchEvent(new Event('input',{bubbles:true}));"
        "el.dispatchEvent(new Event('change',{bubbles:true}));if(el.blur)el.blur();",
        field, resort_code
    )
    if (field.get_attribute("value") or "").strip() != resort_code:
        try:
            field.click()
            try:
                field.send_keys(Keys.CONTROL, "a")
            except Exception:
                field.send_keys(Keys.COMMAND, "a")
            field.send_keys(Keys.DELETE)
            field.send_keys(resort_code)
            field.send_keys(Keys.TAB)
        except Exception:
            pass
    time.sleep(0.6 * SPEED_FACTOR)

def robust_continue_in_exchange_form(driver, wait, max_retries=3):
    def get_btn(form):
        btn = form.find_elements(By.XPATH, ".//input[@id='exchange_form_continue_btn']")
        if btn:
            return btn[0]
        btn = form.find_elements(
            By.XPATH,
            ".//input[@type='submit' and translate(@value,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='continue']"
        )
        return btn[0] if btn else None

    for attempt in range(1, max_retries + 1):
        form = get_exchange_form(driver)
        if form is None:
            return True
        prev_url = driver.current_url
        btn = get_btn(form)
        if btn is not None:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            try:
                btn.click()
            except Exception:
                try:
                    ActionChains(driver).move_to_element(btn).pause(0.05 * SPEED_FACTOR).click(btn).perform()
                except Exception:
                    js_click(driver, btn)
            time.sleep(0.7 * SPEED_FACTOR)
        if driver.current_url == prev_url:
            try:
                driver.execute_script("arguments[0].submit();", form)
            except Exception:
                pass
        try:
            WebDriverWait(driver, int(8 * SPEED_FACTOR) + attempt * 2).until(
                lambda d: d.current_url != prev_url or get_exchange_form(driver) is None
            )
            time.sleep(0.6 * SPEED_FACTOR)
            return True
        except TimeoutException:
            time.sleep(0.5 * SPEED_FACTOR)
    return False

def click_any_unredeemed_vacation_exchange(driver, timeout=VACATION_EXCHANGE_TIMEOUT):
    end = time.time() + timeout * SPEED_FACTOR
    xp_rows = ("//tr[contains(@class,'unit_info')][.//a[contains(@class,'pop_up') "
               "and contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'unredeemed deposit')]]")
    before_url = driver.current_url
    before_handles = set(driver.window_handles)
    while time.time() < end:
        rows = driver.find_elements(By.XPATH, xp_rows)
        if not rows:
            driver.execute_script("window.scrollBy(0, 600);")
            time.sleep(0.3 * SPEED_FACTOR)
            continue
        for row in rows:
            btn = None
            for xp in [
                ".//input[@type='image' and contains(@src,'vexchange')]",
                ".//a[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'vacation exchange')]",
                ".//button[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'vacation exchange')]"
            ]:
                els = row.find_elements(By.XPATH, xp)
                if els:
                    btn = els[0]
                    break
            if not btn:
                continue
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            try:
                btn.click()
            except Exception:
                js_click(driver, btn)
            time.sleep(VACATION_EXCHANGE_PAUSE * SPEED_FACTOR)
            new_handles = set(driver.window_handles) - before_handles
            if new_handles:
                driver.switch_to.window(list(new_handles)[0])
                return True
            if driver.current_url != before_url:
                return True
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(0.4 * SPEED_FACTOR)
    return False

def locate_all_resort_blocks(driver):
    driver.switch_to.default_content()
    blocks = driver.find_elements(By.CLASS_NAME, "table_frame")
    if blocks:
        return blocks
    for fr in driver.find_elements(By.TAG_NAME, "iframe"):
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(fr)
            blocks = driver.find_elements(By.CLASS_NAME, "table_frame")
            if blocks:
                return blocks
        except Exception:
            pass
    driver.switch_to.default_content()
    return []

def find_resort_block_by_code(driver, resort_code):
    blocks = locate_all_resort_blocks(driver)
    target = resort_code.strip().upper()
    for block in blocks:
        try:
            for s in block.find_elements(By.XPATH, ".//strong"):
                if (s.text or "").strip().upper() == target:
                    return block
        except Exception:
            continue
    return None

def click_more_dates_until_exhausted(driver, resort_code, pause=MORE_DATES_PAUSE, max_clicks=MAX_MORE_DATES_CLICKS):
    clicks = 0
    while clicks < max_clicks:
        block = find_resort_block_by_code(driver, resort_code)
        if not block:
            break

        more = None
        for xp in [
            ".//a[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'more dates')]",
            ".//button[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'more dates')]",
            ".//a[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'see more dates')]",
            ".//button[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'see more dates')]",
            ".//*[contains(@class,'see_more_btn')]//a",
            ".//*[contains(@class,'see_more_btn')]//button",
            ".//*[contains(@class,'see_more_btn')]//input"
        ]:
            els = block.find_elements(By.XPATH, xp)
            if els:
                more = els[0]
                break

        if more is None:
            return clicks

        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", more)
        try:
            more.click()
        except Exception:
            try:
                ActionChains(driver).move_to_element(more).pause(0.05).click(more).perform()
            except Exception:
                js_click(driver, more)

        time.sleep(pause)
        clicks += 1

    return clicks

# ------- Parser -------
def _collect_from_strong_rows(block, required_bedrooms):
    dates = set()
    strongs = block.find_elements(By.XPATH, ".//strong[contains(., ' - ')]")
    for st in strongs:
        txt = (st.text or "").strip()
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
            tr = st.find_element(By.XPATH, "ancestor::tr[1]")
            spans = tr.find_elements(By.XPATH, ".//span[@id='bedrooms']")
            for sp in spans:
                val = (sp.text or "").strip()
                if val.isdigit():
                    bd = val
                    break
            if bd is None:
                next_tr = tr.find_element(By.XPATH, "following-sibling::tr[1]")
                spans2 = next_tr.find_elements(By.XPATH, ".//span[@id='bedrooms']")
                for sp in spans2:
                    val = (sp.text or "").strip()
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
    rows = block.find_elements(By.XPATH, ".//div[@class='avail_dates']")
    for row in rows:
        date_range = (row.text or "").strip()
        if " - " not in date_range:
            continue
        try:
            next_div = row.find_element(By.XPATH, "following-sibling::div[1]")
        except Exception:
            continue
        try:
            bedroom_span = next_div.find_element(By.XPATH, ".//span[@id='bedrooms']")
            bd = (bedroom_span.text or "").strip()
        except Exception:
            bd = None
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

def wait_results_or_timeout(driver):
    try:
        WebDriverWait(driver, int(20 * SPEED_FACTOR)).until(EC.any_of(
            EC.presence_of_element_located((By.CLASS_NAME, "table_frame")),
            EC.presence_of_element_located((By.XPATH,
                "//*[contains(translate(normalize-space(.),"
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'no availability')]"
            ))
        ))
        time.sleep(0.8 * SPEED_FACTOR)
        return True
    except TimeoutException:
        logger.info("No results appeared - treating as NO AVAILABILITY for this period.")
        return False

# ---------- Recolección ----------
def collect_available_dates(resort_code, listing_id, bedroom_filter):
    driver = create_driver()
    wait = WebDriverWait(driver, int(25 * SPEED_FACTOR))
    try:
        login_and_go_to_exchange(driver, wait)
        fast_set_resort_code(driver, resort_code)

        # fromDate rápido (JS), toDate estándar
        set_date_field(driver, "fromDate", DATE_RANGE_START.strftime("%m/%d/%Y"), fast=True)
        set_date_field(driver, "toDate", DATE_RANGE_END.strftime("%m/%d/%Y"), fast=False)

        if not robust_continue_in_exchange_form(driver, wait, max_retries=3):
            logger.error("Could not click Continue")
            return []
        if not wait_results_or_timeout(driver):
            return []
        if not click_any_unredeemed_vacation_exchange(driver, timeout=VACATION_EXCHANGE_TIMEOUT):
            logger.error("Could not click Vacation Exchange (Unredeemed Deposit).")
            return []
        if not wait_results_or_timeout(driver):
            return []
        _ = click_more_dates_until_exhausted(driver, resort_code, pause=MORE_DATES_PAUSE)
        block = find_resort_block_by_code(driver, resort_code)
        if not block:
            logger.error("Resort block not found: %s", resort_code)
            return []
        logger.info("Resort block %s found. Parsing...", resort_code)
        available_dates = parse_availability_from_block(block, listing_id, bedroom_filter)
        return list(sorted(set(available_dates)))
    finally:
        def _quit_driver():
            try:
                driver.quit()
            except Exception as e:
                logger.warning("Error closing driver: %s", e)
        t = threading.Thread(target=_quit_driver, daemon=True)
        t.start()
        t.join(timeout=10)
        if t.is_alive():
            logger.warning("driver.quit() did not respond in 10s, force-killing Chrome")
            try:
                if hasattr(driver, 'service') and hasattr(driver.service, 'process') and driver.service.process:
                    driver.service.process.kill()
            except Exception:
                pass

# ================== MAIN ==================
def main():
    logger.info("Starting Interval World -> iCal scraper...")

    # 1) LISTA PRINCIPAL (ordenado: 0 dormitorios, luego 2, luego resto)
    ordered_primary = sort_primary_listings_by_bedrooms(PRIMARY_LISTINGS)
    for prop in ordered_primary:
        logger.info("Scraping %s (Listing ID: %s)...", prop["resort_code"], prop["listing_id"])
        try:
            available = collect_available_dates(prop["resort_code"], prop["listing_id"], PRIMARY_BEDROOM_FILTER)
            available = apply_manual_extra_availability(prop["listing_id"], available)
            logger.info("%d available dates found.", len(available))
            generate_ics_for_listing(prop["listing_id"], available, DATE_RANGE_START, DATE_RANGE_END)
        except Exception as e:
            logger.exception("Error processing %s - %s: %s", prop['listing_id'], prop['resort_code'], e)

    # 2) LISTA SECUNDARIA (solo disponibilidad adicional)
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
            logger.exception("Error en %s (%s): %s", prop['listing_id'], prop['resort_code'], e)

if __name__ == "__main__":
    main()
