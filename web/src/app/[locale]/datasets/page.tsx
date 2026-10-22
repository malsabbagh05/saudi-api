import type { Metadata } from "next";
import { hasLocale } from "next-intl";
import { getTranslations } from "next-intl/server";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { Pagination } from "@/components/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { Link } from "@/i18n/navigation";
import { routing, type Locale } from "@/i18n/routing";
import { api } from "@/lib/api";
import { pick } from "@/lib/format";

const PAGE_SIZE = 30;

export async function generateMetadata({ params }: PageProps<"/[locale]/datasets">): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "datasets" });
  return { title: t("title"), description: t("lede") };
}

export default async function DatasetsPage({ params, searchParams }: PageProps<"/[locale]/datasets">) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  const t = await getTranslations({ locale, namespace: "datasets" });
  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-2xl font-semibold">{t("title")}</h1>
      <p className="mt-2 max-w-[65ch] text-muted-foreground">{t("lede")}</p>
      <Suspense fallback={<Skeleton className="mt-6 h-96 w-full" />}>
        <List locale={locale} searchParams={searchParams} />
      </Suspense>
    </div>
  );
}

async function List({
  locale,
  searchParams,
}: {
  locale: Locale;
  searchParams: PageProps<"/[locale]/datasets">["searchParams"];
}) {
  const t = await getTranslations({ locale });
  const search = await searchParams;
  const first = (value: string | string[] | undefined) => (Array.isArray(value) ? value[0] : value)?.trim() || undefined;
  const q = first(search.q);
  const apiSlug = first(search.api);
  const page = Math.max(1, Number.parseInt(first(search.page) ?? "1", 10) || 1);
  const results = await api.datasets({ q, api: apiSlug, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE });
  return (
    <>
      <form method="get" action={`/${locale}/datasets`} role="search" className="mt-6 flex max-w-2xl gap-2">
        <label htmlFor="d-q" className="sr-only">
          {t("nav.searchLabel")}
        </label>
        <input
          id="d-q"
          name="q"
          type="search"
          defaultValue={q}
          maxLength={200}
          placeholder={t("nav.searchPlaceholder")}
          className="h-10 min-w-0 flex-1 rounded-sm border border-input bg-card px-3 placeholder:text-muted-foreground focus-visible:border-ring"
        />
        {apiSlug ? <input type="hidden" name="api" value={apiSlug} /> : null}
        <button type="submit" className="rounded-sm bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90">
          {t("home.searchButton")}
        </button>
      </form>
      <p className="mt-6 mb-3 text-sm text-muted-foreground" aria-live="polite">
        {t("datasets.results", { count: results.total })}
        {q ? ` ${t("directory.query", { query: q })}` : ""}
      </p>
      {results.items.length === 0 ? (
        <p className="border-y border-teak/25 py-10 font-medium">{t("datasets.empty")}</p>
      ) : (
        <ul className="divide-y divide-teak/15 border-y border-teak/25">
          {results.items.map((item) => (
            <li key={`${item.api_slug}:${item.id}`} className="grid gap-1 py-3 md:grid-cols-[minmax(0,1fr)_16rem] md:gap-6">
              <div className="min-w-0">
                <Link
                  href={`/datasets/${item.api_slug}/${item.id}`}
                  className="font-medium hover:text-primary hover:underline"
                >
                  {pick(item.name, locale)}
                </Link>
                <p className="text-sm text-muted-foreground">
                  {pick(item.topic, locale)}
                  {pick(item.subtopic, locale) ? ` · ${pick(item.subtopic, locale)}` : ""}
                </p>
              </div>
              <p className="text-sm text-muted-foreground md:text-end">{pick(item.publisher.name, locale)}</p>
            </li>
          ))}
        </ul>
      )}
      <Pagination
        locale={locale}
        pathname="/datasets"
        query={{ q, api: apiSlug }}
        page={page}
        pages={Math.max(1, Math.ceil(results.total / PAGE_SIZE))}
      />
    </>
  );
}
