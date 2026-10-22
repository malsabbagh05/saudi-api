import type { Metadata } from "next";
import { hasLocale } from "next-intl";
import { getTranslations } from "next-intl/server";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { Link } from "@/i18n/navigation";
import { routing, type Locale } from "@/i18n/routing";
import { api } from "@/lib/api";
import { pick } from "@/lib/format";

export async function generateMetadata({ params }: PageProps<"/[locale]/search">): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "nav" });
  return { title: t("searchLabel"), robots: { index: false } };
}

export default async function SearchPage({ params, searchParams }: PageProps<"/[locale]/search">) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  const t = await getTranslations({ locale });
  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-2xl font-semibold">{t("nav.searchLabel")}</h1>
      <Suspense fallback={<Skeleton className="mt-6 h-64 w-full" />}>
        <Results locale={locale} searchParams={searchParams} />
      </Suspense>
    </div>
  );
}

async function Results({
  locale,
  searchParams,
}: {
  locale: Locale;
  searchParams: PageProps<"/[locale]/search">["searchParams"];
}) {
  const t = await getTranslations({ locale });
  const raw = (await searchParams).q;
  const q = (Array.isArray(raw) ? raw[0] : raw)?.trim() ?? "";
  const hits = q ? await api.search(q, 30) : [];
  return (
    <>
      <form action={`/${locale}/search`} method="get" role="search" className="mt-6 flex max-w-2xl gap-2">
        <label htmlFor="search-q" className="sr-only">
          {t("nav.searchLabel")}
        </label>
        <input
          id="search-q"
          name="q"
          type="search"
          defaultValue={q}
          maxLength={200}
          placeholder={t("nav.searchPlaceholder")}
          className="h-10 min-w-0 flex-1 rounded-sm border border-input bg-card px-3 placeholder:text-muted-foreground focus-visible:border-ring"
        />
        <button type="submit" className="rounded-sm bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90">
          {t("home.searchButton")}
        </button>
      </form>
      {q && hits.length === 0 ? (
        <div className="mt-8 border-y border-teak/25 py-8">
          <p className="font-medium">{t("directory.empty")}</p>
          <p className="mt-1 text-sm text-muted-foreground">{t("directory.emptyHint")}</p>
        </div>
      ) : null}
      {hits.length > 0 ? (
        <ol className="mt-6 divide-y divide-teak/15 border-y border-teak/25">
          {hits.map((hit) => {
            const href =
              hit.kind === "api" ? `/apis/${hit.api_slug}` : `/datasets/${hit.api_slug}/${hit.dataset_id}`;
            return (
              <li key={`${hit.kind}:${hit.api_slug}:${hit.dataset_id ?? ""}`} className="py-3">
                <Link href={href} className="group block">
                  <span className="flex flex-wrap items-baseline gap-x-2">
                    <span className="font-medium group-hover:text-primary group-hover:underline">
                      {pick(hit.name, locale)}
                    </span>
                    <span className="rounded-sm border border-teak/25 px-1.5 text-xs text-muted-foreground">
                      {hit.kind === "api" ? t("nav.apis") : t("nav.datasets")}
                    </span>
                  </span>
                  <span className="block text-sm text-muted-foreground line-clamp-1">{pick(hit.summary, locale)}</span>
                </Link>
              </li>
            );
          })}
        </ol>
      ) : null}
    </>
  );
}
