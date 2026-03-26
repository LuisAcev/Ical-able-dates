#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Obtiene detalles de un listing de Airbnb usando Selenium.
Hace login automatico con credenciales del .env (sin depender de perfil de Chrome).
"""

import logging
import re
import time
from selenium import webdriver

logger = logging.getLogger(__name__)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from config import AIRBNB_PROFILE_DIR

REQUEST_DELAY = 4

_driver = None
_logged_in = False


def get_driver():
    """Crea o reutiliza un driver de Chrome (perfil temporal)."""
    global _driver
    if _driver is not None:
        try:
            _driver.title
            return _driver
        except Exception:
            _driver = None

    # Perfil persistente separado para Selenium (no conflicta con Chrome abierto)
    profile_dir = AIRBNB_PROFILE_DIR
    options = Options()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--headless=new")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-blink-features=AutomationControlled")
    _driver = webdriver.Chrome(options=options)
    return _driver


def close_driver():
    global _driver, _logged_in
    if _driver:
        try:
            _driver.quit()
        except Exception:
            pass
        _driver = None
        _logged_in = False


def _ensure_logged_in(driver):
    """Verifica que la sesion de Airbnb este activa en el perfil AVI_Profile."""
    global _logged_in
    if _logged_in:
        return

    driver.get("https://www.airbnb.com.co/hosting/listings")
    time.sleep(4)

    if "/login" in driver.current_url:
        raise RuntimeError(
            "No hay sesion activa en Airbnb. "
            "Ejecuta 'python scrape_airbnb.py login' para hacer login manual."
        )

    _logged_in = True
    logger.info("Sesion activa OK")


def manual_login():
    """Abre Chrome visible (sin headless) para que el usuario haga login manualmente."""
    profile_dir = AIRBNB_PROFILE_DIR
    options = Options()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-blink-features=AutomationControlled")
    # SIN headless — Chrome visible
    driver = webdriver.Chrome(options=options)
    driver.get("https://www.airbnb.com.co/login")
    print("\n>>> Chrome abierto en la pagina de login de Airbnb.")
    print(">>> Haz login manualmente y luego presiona ENTER aqui...")
    input()
    print(f"URL actual: {driver.current_url}")
    if "/login" not in driver.current_url:
        print("Login exitoso! La sesion quedo guardada en AVI_Profile.")
    else:
        print("Parece que no se completo el login. Intenta de nuevo.")
    driver.quit()


def _extract_number(text):
    if not text:
        return None
    match = re.search(r'\d+', text.replace(',', '').replace('.', ''))
    return int(match.group()) if match else None


def fetch_listing_details(listing_id):
    """
    Navega a la pagina publica de un listing de Airbnb
    y extrae titulo, habitaciones, precio, huespedes.
    """
    driver = get_driver()
    _ensure_logged_in(driver)

    url = f"https://www.airbnb.com.co/rooms/{listing_id}"
    driver.get(url)
    time.sleep(REQUEST_DELAY)

    # Detectar pagina de error 404
    if "Ups" in driver.page_source or "error: 404" in driver.page_source or "No hemos podido encontrar" in driver.page_source:
        raise ValueError(f"Listing {listing_id} no encontrado en Airbnb (404)")

    result = {
        "title": "",
        "bedrooms": 0,
        "guests": 0,
        "price_per_night": 0,
    }

    wait = WebDriverWait(driver, 15)

    # 1. Titulo — el h1 principal
    try:
        h1 = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1")))
        result["title"] = h1.text.strip()
    except Exception as e:
        logger.warning("No se pudo obtener titulo: %s", e)

    # 2. Detalles (guests, bedrooms)
    try:
        details_el = wait.until(EC.presence_of_element_located((
            By.XPATH,
            "//*[contains(text(),'guest') or contains(text(),'Guest')]"
        )))
        details_text = details_el.text.lower()

        guests_match = re.search(r'(\d+)\s*guest', details_text)
        if guests_match:
            result["guests"] = int(guests_match.group(1))

        if 'studio' in details_text:
            result["bedrooms"] = 0
        else:
            bed_match = re.search(r'(\d+)\s*bedroom', details_text)
            if bed_match:
                result["bedrooms"] = int(bed_match.group(1))
    except Exception as e:
        logger.warning("No se pudieron obtener detalles: %s", e)

    # 3. Precio por noche
    try:
        price_el = driver.find_element(
            By.XPATH,
            "//*[contains(text(),'night') or contains(text(),'noche')]"
        )
        price_text = price_el.text
        price_match = re.search(r'[\$]\s*([\d,]+)', price_text)
        if price_match:
            result["price_per_night"] = int(price_match.group(1).replace(',', ''))
    except Exception:
        try:
            spans = driver.find_elements(By.CSS_SELECTOR, "span._tyxjp1")
            for span in spans:
                txt = span.text
                if '$' in txt:
                    result["price_per_night"] = _extract_number(txt) or 0
                    break
        except Exception as e:
            logger.warning("No se pudo obtener precio: %s", e)

    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "login":
        manual_login()
    else:
        test_id = sys.argv[1] if len(sys.argv) > 1 else "1098594949186974730"
        try:
            details = fetch_listing_details(test_id)
            print(f"Detalles: {details}")
        finally:
            close_driver()
