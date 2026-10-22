import { hasLocale } from "next-intl";
import { getRequestConfig } from "next-intl/server";
import * as rootParams from "next/root-params";
import { routing } from "./routing";

// The locale passed explicitly (getTranslations({ locale })) or the [locale] root param.
// That segment matches any value, so an unknown one is replaced with a valid locale here
// and the root layout answers 404 (next-intl, "Configuration").
export default getRequestConfig(async ({ locale }) => {
  const requested = locale ?? (await rootParams.locale());
  const resolved = hasLocale(routing.locales, requested) ? requested : routing.defaultLocale;
  return {
    locale: resolved,
    messages: (await import(`../../messages/${resolved}.json`)).default,
  };
});
