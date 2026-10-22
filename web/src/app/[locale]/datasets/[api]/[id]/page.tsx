import { ArrowUpRightIcon } from "lucide-react";
import type { Metadata } from "next";
import { hasLocale } from "next-intl";
import { getTranslations } from "next-intl/server";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { CodeBlock } from "@/components/code-examples";
import { Skeleton } from "@/components/ui/skeleton";
import { Link } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";
import { api } from "@/lib/api";
import { formatDate, pick } from "@/lib/format";

export async function generateMetadata({ params }: PageProps<"/[locale]/datasets/[api]/[id]">): Promise<Metadata> {
  const { locale, api: apiSlug, id } = await params;
  if (!hasLocale(routing.locales, locale)) return {};
  const dataset = await api.dataset(apiSlug, id);
  return dataset ? { title: pick(dataset.name, locale) } : {};
}

export default function DatasetPage({ params }: PageProps<"/[locale]/datasets/[api]/[id]">) {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-6xl px-4 py-10">
          <Skeleton className="h-9 w-2/3" />
          <Skeleton className="mt-8 h-72 w-full" />
        </div>
      }
    >
      <Detail params={params} />
    </Suspense>
  );
}

async function Detail({ params }: { params: PageProps<"/[locale]/datasets/[api]/[id]">["params"] }) {
  const { locale, api: apiSlug, id } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  const [dataset, parent] = await Promise.all([api.dataset(apiSlug, id), api.api(apiSlug)]);
  if (!dataset) notFound();
  const t = await getTranslations({ locale });
  const args = JSON.stringify({ api_slug: apiSlug, endpoint_id: "query-cube", arguments: dataset.query }, null, 2);
  return (
    <article className="mx-auto max-w-6xl px-4 py-10">
      <header className="border-b border-teak/20 pb-6">
        <h1 className="text-3xl font-semibold leading-tight tracking-tight text-balance">
          {pick(dataset.name, locale)}
        </h1>
        <p className="mt-1 text-muted-foreground">
          {pick(dataset.topic, locale)}
          {pick(dataset.subtopic, locale) ? ` · ${pick(dataset.subtopic, locale)}` : ""}
        </p>
        <dl className="mt-4 flex flex-wrap gap-x-8 gap-y-2 text-sm">
          <div>
            <dt className="text-muted-foreground">{t("datasets.publisher")}</dt>
            <dd>
              {dataset.publisher.url ? (
                <a
                  href={dataset.publisher.url}
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-primary hover:underline"
                >
                  {pick(dataset.publisher.name, locale) || t("datasets.source")}
                  <ArrowUpRightIcon aria-hidden className="size-3.5 rtl:-scale-x-100" />
                </a>
              ) : (
                pick(dataset.publisher.name, locale)
              )}
            </dd>
          </div>
          {parent ? (
            <div>
              <dt className="text-muted-foreground">{t("api.provider")}</dt>
              <dd>
                <Link href={`/apis/${parent.slug}`} className="text-primary hover:underline">
                  {t("datasets.viewApi", { api: pick(parent.name, locale) })}
                </Link>
              </dd>
            </div>
          ) : null}
          <div>
            <dt className="text-muted-foreground">{t("datasets.refreshedLabel")}</dt>
            <dd>{formatDate(dataset.refreshed_at, locale)}</dd>
          </div>
        </dl>
      </header>

      <div className="mt-8 grid gap-10 lg:grid-cols-2 [&>*]:min-w-0">
        <section aria-labelledby="measures">
          <h2 id="measures" className="text-lg font-semibold">
            {t("datasets.measures")}
          </h2>
          <ul className="mt-3 divide-y divide-teak/15 border-y border-teak/25 text-sm">
            {dataset.measures.map((measure) => (
              <li key={measure.name} className="flex items-baseline justify-between gap-4 py-2">
                <span>{pick(measure.caption, locale)}</span>
                <code dir="ltr" className="text-xs text-muted-foreground">
                  {measure.name}
                </code>
              </li>
            ))}
          </ul>
          <h2 className="mt-8 text-lg font-semibold">{t("datasets.dimensions")}</h2>
          <ul className="mt-3 divide-y divide-teak/15 border-y border-teak/25 text-sm">
            {dataset.dimensions.map((dimension) => (
              <li key={dimension.name} className="py-2">
                <div className="flex items-baseline justify-between gap-4">
                  <span className="font-medium">
                    {pick(dimension.caption, locale)}
                    {dimension.required ? (
                      <span className="ms-2 rounded-sm bg-accent px-1.5 py-px text-[0.7rem] text-accent-foreground">
                        {t("datasets.required")}
                      </span>
                    ) : null}
                  </span>
                  <code dir="ltr" className="text-xs text-muted-foreground">
                    {dimension.name}
                  </code>
                </div>
                {dimension.levels.length > 0 ? (
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {t("datasets.levels")}:{" "}
                    <span dir="ltr">{dimension.levels.map((level) => level.name).join(", ")}</span>
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="query">
          <h2 id="query" className="text-lg font-semibold">
            {t("datasets.query")}
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">{t("datasets.queryLede")}</p>
          {dataset.query_url ? (
            <div className="mt-3">
              <CodeBlock code={`curl "${dataset.query_url}"`} copy={t("api.copy")} copied={t("api.copied")} wrap />
            </div>
          ) : null}
          <div className="mt-3">
            <CodeBlock code={`call_endpoint(${args})`} copy={t("api.copy")} copied={t("api.copied")} />
          </div>
        </section>
      </div>
    </article>
  );
}
