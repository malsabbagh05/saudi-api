import type { Locale } from "@/i18n/routing";

// Dates are shown in the Gregorian calendar with Western digits in both languages, so
// they read the same as the catalogue's ISO dates and the code beside them (bilingual.md).
function intlLocale(locale: Locale): string {
  return locale === "ar" ? "ar-SA-u-ca-gregory-nu-latn" : "en-GB";
}

export function formatDate(value: string, locale: Locale): string {
  return new Intl.DateTimeFormat(intlLocale(locale), {
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "Asia/Riyadh",
  }).format(new Date(value));
}

export function formatDateTime(value: string, locale: Locale): string {
  return new Intl.DateTimeFormat(intlLocale(locale), {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Riyadh",
    timeZoneName: "short",
  }).format(new Date(value));
}

export function formatNumber(value: number, locale: Locale): string {
  return new Intl.NumberFormat(intlLocale(locale)).format(value);
}

/** The text of a bilingual pair in the page's language. */
export function pick(text: { en: string; ar: string }, locale: Locale): string {
  return locale === "ar" ? text.ar : text.en;
}
