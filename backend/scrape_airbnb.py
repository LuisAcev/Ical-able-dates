#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Obtiene detalles de un listing de Airbnb usando Selenium.
Hace login automatico con credenciales del .env (sin depender de perfil de Chrome).
"""

import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from config import AIRBNB_EMAIL, AIRBNB_PASSWORD

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
    profile_dir = r"C:\Users\lface\AppData\Local\Google\Chrome\AVI_Profile"
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


def _login_airbnb(driver):
    """Login en Airbnb con email y password del .env."""
    global _logged_in
    if _logged_in:
        return

    driver.get("https://www.airbnb.com/login")
    wait = WebDriverWait(driver, 15)

    # Click en "Continue with email"
    try:
        email_btn = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//button[contains(text(),'email') or contains(text(),'correo')]"
        )))
        email_btn.click()
    except TimeoutException:
        # Puede que ya este en el form de email
        pass

    time.sleep(1)

    # Ingresar email
    try:
        email_input = wait.until(EC.presence_of_element_located((
            By.CSS_SELECTOR,
            "input[type='email'], input[name='email'], input#email-login-email"
        )))
        email_input.clear()
        email_input.send_keys(AIRBNB_EMAIL)
    except TimeoutException:
        print("  [Airbnb] No se encontro campo de email")
        return

    time.sleep(0.5)

    # Click en Continue/Next
    try:
        continue_btn = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//button[contains(text(),'Continue') or contains(text(),'Continuar') or @type='submit']"
        )))
        continue_btn.click()
    except TimeoutException:
        pass

    time.sleep(2)

    # Ingresar password
    try:
        pw_input = wait.until(EC.presence_of_element_located((
            By.CSS_SELECTOR,
            "input[type='password']"
        )))
        pw_input.clear()
        pw_input.send_keys(AIRBNB_PASSWORD)
    except TimeoutException:
        print("  [Airbnb] No se encontro campo de password")
        return

    time.sleep(0.5)

    # Click en Log in
    try:
        login_btn = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//button[contains(text(),'Log in') or contains(text(),'Iniciar') or @type='submit']"
        )))
        login_btn.click()
    except TimeoutException:
        pass

    # Esperar a que cargue el dashboard o la pagina principal
    time.sleep(5)
    _logged_in = True
    print("  [Airbnb] Login exitoso")


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
    _login_airbnb(driver)

    url = f"https://www.airbnb.com/rooms/{listing_id}"
    driver.get(url)

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
        print(f"  [Airbnb] No se pudo obtener titulo: {e}")

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
        print(f"  [Airbnb] No se pudieron obtener detalles: {e}")

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
            print(f"  [Airbnb] No se pudo obtener precio: {e}")

    return result


if __name__ == "__main__":
    test_id = "1098594949186974730"
    try:
        details = fetch_listing_details(test_id)
        print(f"Detalles: {details}")
    finally:
        close_driver()
