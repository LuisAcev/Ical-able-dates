import { es } from "./locales/es";
import { en } from "./locales/en";

const locales = { es, en };
const DATE_LOCALES = { es: "es-CO", en: "en-US" };
const STORAGE_KEY = "avi_locale";

let _locale = localStorage.getItem(STORAGE_KEY) || "es";
let _listeners = [];

function _notify() {
  _listeners.forEach((fn) => fn(_locale));
}

export function getLocale() {
  return _locale;
}

export function setLocale(locale) {
  if (!locales[locale]) return;
  _locale = locale;
  localStorage.setItem(STORAGE_KEY, locale);
  _notify();
}

export function onLocaleChange(fn) {
  _listeners.push(fn);
  return () => {
    _listeners = _listeners.filter((l) => l !== fn);
  };
}

export const localeOptions = [
  { code: "es", label: "ES" },
  { code: "en", label: "EN" },
];

// Getters seguros — siempre devuelven el idioma actual
export const getT = () => locales[_locale];
export const getDateLocale = () => DATE_LOCALES[_locale];

// Atajos para compatibilidad (Vite ES modules soporta live bindings)
export let t = locales[_locale];
export let dateLocale = DATE_LOCALES[_locale];

onLocaleChange((loc) => {
  t = locales[loc];
  dateLocale = DATE_LOCALES[loc];
});
