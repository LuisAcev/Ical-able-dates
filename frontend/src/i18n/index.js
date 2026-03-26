import { es } from "./locales/es";
import { en } from "./locales/en";

const locales = { es, en };

const DEFAULT_LOCALE = "es";

export const t = locales[DEFAULT_LOCALE];
