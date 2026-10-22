import { ArrowRightIcon, SearchIcon } from "lucide-react";
import { hasLocale } from "next-intl";
import { getTranslations } from "next-intl/server";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { AccessLattice } from "@/components/access-lattice";
import { CodeBlock } from "@/components/code-examples";
import { Skeleton } from "@/components/ui/skeleton";
import { Link } from "@/i18n/navigation";
import { routing, type Locale } from "@/i18n/routing";
import { ACCESS_LEVELS, api, publicApiUrl } from "@/lib/api";
import { formatNumber, pick } from "@/lib/format";

const EXAMPLES = {
  en: ["national address", "e-invoicing", "inflation", "open banking", "Riyadh metro"],
  ar: ["العنوان الوطني", "الفوترة الإلكترونية", "التضخم", "المصرفية المفتوحة", "مترو الرياض"],
} as const;

export default async function HomePage({ params }: PageProps<"/[locale]">) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  const t = await getTranslations({ locale });
  return (
    <>
      <section className="border-b border-teak/20">
        <div className="mx-auto max-w-6xl px-4 pb-10 pt-12 md:pt-16">
          <h1 className="max-w-[20ch] text-3xl font-semibold leading-tight tracking-tight text-balance md:text-5xl">
            {t("home.heading")}
          </h1>
          <p className="mt-4 max-w-[62ch] text-base text-muted-foreground md:text-lg">{t("home.lede")}</p>
          <form action={`/${locale}/search`} method="get" role="search" className="mt-8 max-w-3xl">
            <label htmlFor="home-search" className="sr-only">
              {t("nav.searchLabel")}
            </label>
            <div className="flex items-stretch rounded-sm border border-teak/40 bg-card focus-within:border-ring focus-within:ring-2 focus-within:ring-ring/30">
              <SearchIcon aria-hidden className="ms-3 size-5 self-center text-muted-foreground" />
              <input
                id="home-search"
                name="q"
                type="search"
                required
                maxLength={200}
                placeholder={t("nav.searchPlaceholder")}
                className="min-w-0 flex-1 bg-transparent px-3 py-3 text-base outline-none placeholder:text-muted-foreground"
              />
              <button
                type="submit"
                className="m-1 rounded-sm bg-primary px-5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
              >
                {t("home.searchButton")}
              </button>
            </div>
          </form>
          <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 text-sm">
            <span className="text-muted-foreground">{t("home.examples")}</span>
            {EXAMPLES[locale].map((example) => (
              <Link
                key={example}
                href={{ pathname: "/search", query: { q: example } }}
                className="rounded-sm border border-teak/25 px-2 py-0.5 hover:border-primary hover:text-primary"
              >
                {example}
              </Link>
            ))}
          </div>
          <div className="mt-8 flex flex-wrap items-center justify-between gap-4 border-t border-teak/15 pt-4 text-sm">
            <Suspense fallback={<Skeleton className="h-5 w-72" />}>
              <Counts locale={locale} />
            </Suspense>
            <LatticeLegend locale={locale} />
          </div>
        </div>
      </section>

      <section aria-labelledby="sectors" className="mx-auto max-w-6xl px-4 py-10">
        <div className="mb-4 flex items-end justify-between gap-4">
          <h2 id="sectors" className="text-xl font-semibold">
            {t("home.sectorsTitle")}
          </h2>
          <Link href="/apis" className="inline-flex items-center gap-1 text-sm text-primary hover:underline">
            {t("home.browseAll")}
            <ArrowRightIcon aria-hidden className="size-4 rtl:rotate-180" />
          </Link>
        </div>
        <Suspense fallback={<Skeleton className="h-64 w-full" />}>
          <SectorIndex locale={locale} />
        </Suspense>
      </section>

      <section className="mx-auto grid max-w-6xl gap-10 px-4 py-6 md:grid-cols-2 [&>*]:min-w-0">
        <div aria-labelledby="invocable">
          <h2 id="invocable" className="text-xl font-semibold">
            {t("home.invocableTitle")}
          </h2>
          <p className="mt-2 text-sm text-muted-foreground max-w-[60ch]">{t("home.invocableLede")}</p>
          <Suspense fallback={<Skeleton className="mt-4 h-24 w-full" />}>
            <Invocable locale={locale} />
          </Suspense>
          <h2 className="mt-10 text-xl font-semibold">{t("home.datasetsTitle")}</h2>
          <Suspense fallback={<Skeleton className="mt-2 h-5 w-80" />}>
            <DatasetsTeaser locale={locale} />
          </Suspense>
        </div>
        <div aria-labelledby="agents" className="rounded-sm border border-teak/25 bg-card p-5">
          <h2 id="agents" className="text-xl font-semibold">
            {t("home.agentsTitle")}
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">{t("home.agentsLede")}</p>
          <div className="mt-4">
            <CodeBlock
              code={`claude mcp add --transport http saudi-api ${publicApiUrl()}/mcp`}
              wrap
              copy={t("api.copy")}
              copied={t("api.copied")}
            />
          </div>
          <Link
            href="/agents"
            className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
          >
            {t("home.agentsCta")}
            <ArrowRightIcon aria-hidden className="size-4 rtl:rotate-180" />
          </Link>
        </div>
      </section>
    </>
  );
}

async function Counts({ locale }: { locale: Locale }) {
  const t = await getTranslations({ locale, namespace: "home" });
  const stats = await api.stats();
  return (
    <p className="font-medium tabular-nums">
      {t("counts", {
        apis: formatNumber(stats.apis, locale),
        providers: formatNumber(stats.providers, locale),
        datasets: formatNumber(stats.datasets, locale),
      })}
    </p>
  );
}

async function LatticeLegend({ locale }: { locale: Locale }) {
  const t = await getTranslations({ locale, namespace: "access" });
  return (
    <figure className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground">
      <figcaption className="sr-only">{t("legend")}</figcaption>
      {ACCESS_LEVELS.map((level, index) => (
        <span key={level} className="inline-flex items-center gap-1.5">
          <AccessLattice level={level} label={t("lattice", { level: t(level), position: index + 1 })} />
          <span aria-hidden>{t(level)}</span>
        </span>
      ))}
    </figure>
  );
}

async function SectorIndex({ locale }: { locale: Locale }) {
  const t = await getTranslations({ locale, namespace: "directory" });
  const sectors = (await api.sectors()).filter((sector) => sector.api_count > 0);
  return (
    <ul className="grid border-t border-teak/25 sm:grid-cols-2 sm:gap-x-8">
      {sectors.map((sector) => (
        <li key={sector.slug} className="min-w-0 border-b border-teak/15">
          <Link
            href={{ pathname: "/apis", query: { sector: sector.slug } }}
            className="group flex items-baseline justify-between gap-4 py-3 hover:text-primary"
          >
            <span className="min-w-0 flex-1">
              <span className="block font-medium group-hover:underline">{pick(sector.name, locale)}</span>
              <span className="block truncate text-sm text-muted-foreground">
                {pick(sector.description, locale)}
              </span>
            </span>
            <span className="shrink-0 text-sm tabular-nums text-muted-foreground">
              {t("results", { count: sector.api_count })}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

async function Invocable({ locale }: { locale: Locale }) {
  const page = await api.apis({ invocable: true, limit: 10 });
  return (
    <ul className="mt-4 divide-y divide-teak/15 border-y border-teak/25">
      {page.items.map((item) => (
        <li key={item.slug}>
          <Link href={`/apis/${item.slug}`} className="flex items-baseline justify-between gap-4 py-3 hover:text-primary">
            <span className="font-medium hover:underline">{pick(item.name, locale)}</span>
            <span className="text-sm text-muted-foreground">{pick(item.provider.name, locale)}</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

async function DatasetsTeaser({ locale }: { locale: Locale }) {
  const t = await getTranslations({ locale, namespace: "home" });
  const stats = await api.stats();
  return (
    <>
      <p className="mt-2 text-sm text-muted-foreground max-w-[60ch]">
        {t("datasetsLede", { count: formatNumber(stats.datasets, locale) })}
      </p>
      <Link
        href="/datasets"
        className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
      >
        {t("datasetsCta")}
        <ArrowRightIcon aria-hidden className="size-4 rtl:rotate-180" />
      </Link>
    </>
  );
}
