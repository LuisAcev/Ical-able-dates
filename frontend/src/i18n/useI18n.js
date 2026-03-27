import { useState, useEffect } from "react";
import { getLocale, setLocale, onLocaleChange, localeOptions } from "./index";

export const useI18n = () => {
  const [locale, setLocal] = useState(getLocale);

  useEffect(() => {
    return onLocaleChange(setLocal);
  }, []);

  const changeLocale = (code) => {
    setLocale(code);
  };

  return { locale, changeLocale, localeOptions };
};
