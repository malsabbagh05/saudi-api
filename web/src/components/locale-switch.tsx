"use client";

import { useLocale } from "next-intl";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { Link, usePathname } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";

/** Switches language on the same page, keeping the query (search terms and filters). */
export function LocaleSwitch({ label, description }: { label: string; description: string }) {
  return (
    <Suspense fallback={<RootSwitch label={label} description={description} />}>
      <WithQuery label={label} description={description} />
    </Suspense>
  );
}

function WithQuery({ label, description }: { label: string; description: string }) {
  const query = useSearchParams().toString();
  return <Switch label={label} description={description} query={query} />;
}

function Switch({ label, description, query }: { label: string; description: string; query: string }) {
  const locale = useLocale() as Locale;
  const pathname = usePathname();
  const other: Locale = locale === "ar" ? "en" : "ar";
  return (
    <Link
      href={query ? `${pathname}?${query}` : pathname}
      locale={other}
      lang={other}
      hrefLang={other}
      aria-label={description}
      className="rounded-sm border border-teak/30 px-2.5 py-1 text-sm hover:bg-muted"
    >
      {label}
    </Link>
  );
}

/** While the path streams in (prerendering), link to the other locale's home page. */
function RootSwitch({ label, description }: { label: string; description: string }) {
  const locale = useLocale() as Locale;
  const other: Locale = locale === "ar" ? "en" : "ar";
  return (
    <Link
      href="/"
      locale={other}
      lang={other}
      hrefLang={other}
      aria-label={description}
      className="rounded-sm border border-teak/30 px-2.5 py-1 text-sm hover:bg-muted"
    >
      {label}
    </Link>
  );
}
