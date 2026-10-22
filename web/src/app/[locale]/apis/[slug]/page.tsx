import { ArrowUpRightIcon } from "lucide-react";
import type { Metadata } from "next";
import { hasLocale } from "next-intl";
import { getTranslations } from "next-intl/server";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { AccessLattice, accessPosition } from "@/components/access-lattice";
import { CodeBlock, CodeExamples } from "@/components/code-examples";
import { ReachChip } from "@/components/reach-chip";
import { Skeleton } from "@/components/ui/skeleton";
import { Link } from "@/i18n/navigation";
import { routing, type Locale } from "@/i18n/routing";
import { api, type AccessLevel, type ApiDetail, type EndpointOut } from "@/lib/api";
import { formatDate, pick } from "@/lib/format";

export async function generateMetadata({ params }: PageProps<"/[locale]/apis/[slug]">): Promise<Metadata> {
  const { locale, slug } = await params;
  if (!hasLocale(routing.locales, locale)) return {};
  const detail = await api.api(slug);
  if (!detail) return {};
  return { title: pick(detail.name, locale), description: pick(detail.summary, locale) };
}

export default function ApiPage({ params }: PageProps<"/[locale]/apis/[slug]">) {
  return (
    <Suspense fallback={<DetailSkeleton />}>
      <Detail params={params} />
    </Suspense>
  );
}

function DetailSkeleton() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <Skeleton className="h-9 w-2/3" />
      <Skeleton className="mt-4 h-5 w-1/2" />
      <Skeleton className="mt-8 h-72 w-full" />
    </div>
  );
}

async function Detail({ params }: { params: PageProps<"/[locale]/apis/[slug]">["params"] }) {
  const { locale, slug } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  const [detail, sectors] = await Promise.all([api.api(slug), api.sectors()]);
  if (!detail) notFound();
  const sectorNames = new Map(sectors.map((sector) => [sector.slug, pick(sector.name, locale)]));
  const t = await getTranslations({ locale });
  const other: Locale = locale === "ar" ? "en" : "ar";
  const level = detail.access.level as AccessLevel;

  return (
    <article className="mx-auto max-w-6xl px-4 py-10">
      <header className="border-b border-teak/20 pb-6">
        <h1 className="text-3xl font-semibold leading-tight tracking-tight text-balance">
          {pick(detail.name, locale)}
        </h1>
        <p className="mt-1 text-muted-foreground">
          <Link href={`/providers/${detail.provider.slug}`} className="text-foreground hover:underline">
            {pick(detail.provider.name, locale)}
          </Link>
          <span aria-hidden> · </span>
          <bdi lang={other}>{pick(detail.name, other)}</bdi>
        </p>
        <p className="mt-4 max-w-[70ch] text-lg">{pick(detail.summary, locale)}</p>
        <div className="mt-4 flex flex-wrap items-center gap-2 text-sm">
          {detail.sectors.map((sector) => (
            <Link
              key={sector}
              href={{ pathname: "/apis", query: { sector } }}
              className="rounded-sm border border-teak/25 px-2 py-0.5 hover:border-primary hover:text-primary"
            >
              {sectorNames.get(sector) ?? sector}
            </Link>
          ))}
          {detail.status !== "active" ? (
            <span className="rounded-sm bg-degraded/15 px-2 py-0.5 text-degraded">
              {t(detail.status === "deprecated" ? "api.deprecated" : "api.beta")}
            </span>
          ) : null}
        </div>
      </header>

      <div className="mt-8 grid gap-10 lg:grid-cols-[minmax(0,1fr)_22rem] [&>*]:min-w-0">
        <div className="min-w-0 space-y-10">
          {detail.status_note ? (
            <p className="rounded-sm border border-degraded/40 bg-degraded/10 p-3 text-sm">
              {pick(detail.status_note, locale)}
            </p>
          ) : null}
          <section aria-labelledby="about">
            <h2 id="about" className="text-lg font-semibold">
              {t("api.description")}
            </h2>
            <p className="mt-2 max-w-[72ch] whitespace-pre-line">{pick(detail.description, locale)}</p>
          </section>

          <section aria-labelledby="endpoints">
            <h2 id="endpoints" className="text-lg font-semibold">
              {t("api.endpoints")}
            </h2>
            {detail.endpoints.length === 0 ? (
              <p className="mt-2 text-muted-foreground">{t("api.noEndpoints")}</p>
            ) : (
              <ol className="mt-4 space-y-8">
                {detail.endpoints.map((endpoint) => (
                  <Endpoint key={endpoint.id} endpoint={endpoint} locale={locale} />
                ))}
              </ol>
            )}
          </section>

          {detail.spec && detail.spec.operation_count > 0 ? (
            <section aria-labelledby="spec">
              <h2 id="spec" className="text-lg font-semibold">
                {t("api.spec")}
              </h2>
              <details className="mt-3 rounded-sm border border-teak/25">
                <summary className="cursor-pointer px-4 py-2.5 text-sm">
                  {t("api.specFetched", {
                    count: detail.spec.operation_count,
                    date: detail.spec.fetched_at ? formatDate(detail.spec.fetched_at, locale) : "-",
                  })}
                </summary>
                <ul dir="ltr" className="divide-y divide-teak/15 border-t border-teak/25 text-sm">
                  {detail.spec.operations.map((operation) => (
                    <li key={`${operation.method} ${operation.path}`} className="flex gap-3 px-4 py-2">
                      <span className="w-14 shrink-0 font-mono text-xs font-semibold">{operation.method}</span>
                      <span className="min-w-0">
                        <code className="break-all text-xs">{operation.path}</code>
                        {operation.summary ? (
                          <span className="block text-xs text-muted-foreground">{operation.summary}</span>
                        ) : null}
                      </span>
                    </li>
                  ))}
                </ul>
              </details>
            </section>
          ) : null}

          {detail.dataset_count > 0 ? (
            <section aria-labelledby="datasets">
              <h2 id="datasets" className="text-lg font-semibold">
                {t("api.datasets")}
              </h2>
              <Link
                href={{ pathname: "/datasets", query: { api: detail.slug } }}
                className="mt-2 inline-block text-primary hover:underline"
              >
                {t("api.datasetsLink", { count: detail.dataset_count })}
              </Link>
            </section>
          ) : null}

          <section aria-labelledby="agents">
            <h2 id="agents" className="text-lg font-semibold">
              {t("api.useWithAgents")}
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">{t("api.useWithAgentsLede")}</p>
            <div className="mt-3">
              <CodeBlock
                code={`get_api({"slug": "${detail.slug}"})`}
                copy={t("api.copy")}
                copied={t("api.copied")}
              />
            </div>
          </section>
        </div>

        <aside className="space-y-6 self-start lg:sticky lg:top-6">
          <Facts detail={detail} level={level} locale={locale} />
        </aside>
      </div>
    </article>
  );
}

async function Facts({ detail, level, locale }: { detail: ApiDetail; level: AccessLevel; locale: Locale }) {
  const t = await getTranslations({ locale });
  return (
    <>
      <dl className="divide-y divide-teak/15 rounded-sm border border-teak/30 bg-card text-sm">
        <Fact label={t("access.label")}>
          <span className="flex items-center gap-2">
            <AccessLattice
              level={level}
              label={t("access.lattice", { level: t(`access.${level}`), position: accessPosition(level) })}
            />
            <span aria-hidden className="font-medium">
              {t(`access.${level}`)}
            </span>
          </span>
          {detail.access.notes ? (
            <span className="mt-1 block text-muted-foreground">{pick(detail.access.notes, locale)}</span>
          ) : null}
        </Fact>
        <Fact label={t("auth.label")}>
          {detail.access.auth.map((scheme) => t(`auth.${scheme}` as "auth.none")).join(" · ")}
          {detail.access.api_key ? (
            <code dir="ltr" className="mt-1 block text-xs text-muted-foreground">
              {detail.access.api_key.in}: {detail.access.api_key.name}
            </code>
          ) : null}
        </Fact>
        <Fact label={t("pricing.label")}>{t(`pricing.${detail.access.pricing}` as "pricing.free")}</Fact>
        {detail.formats.length > 0 ? (
          <Fact label={t("api.formats")}>
            <span dir="ltr">{detail.formats.map((format) => format.toUpperCase()).join(" · ")}</span>
          </Fact>
        ) : null}
        <Fact label={t("api.status")}>
          <ReachChip check={detail.check} locale={locale} />
        </Fact>
        {detail.base_urls.length > 0 ? (
          <Fact label={t("api.baseUrls")}>
            <ul className="space-y-1.5">
              {detail.base_urls.map((base) => (
                <li key={base.url}>
                  <span className="block text-xs text-muted-foreground">
                    {t(base.environment === "sandbox" ? "api.sandbox" : "api.production")}
                  </span>
                  <code dir="ltr" className="block break-all text-xs">
                    {base.url}
                  </code>
                </li>
              ))}
            </ul>
          </Fact>
        ) : null}
        <Fact label={t("api.agents")}>
          <span className="block">{t(detail.usage.agent_invocation ? "api.invocableYes" : "api.invocableNo")}</span>
          {detail.usage.agent_invocation && detail.usage.max_requests_per_minute ? (
            <span className="mt-1 block text-muted-foreground">
              {t("api.budget", { count: detail.usage.max_requests_per_minute })}
            </span>
          ) : null}
          {detail.usage.notes ? (
            <span className="mt-1 block text-muted-foreground">{pick(detail.usage.notes, locale)}</span>
          ) : null}
        </Fact>
      </dl>

      <nav aria-label={t("api.links")} className="rounded-sm border border-teak/30 bg-card p-4 text-sm">
        <ul className="space-y-2">
          <ExternalLink href={detail.documentation_url} label={t("api.documentation")} hint={t("common.external")} />
          {detail.signup_url ? (
            <ExternalLink href={detail.signup_url} label={t("api.signup")} hint={t("common.external")} />
          ) : null}
          {detail.terms_url ? (
            <ExternalLink href={detail.terms_url} label={t("api.terms")} hint={t("common.external")} />
          ) : null}
          {detail.openapi_url ? (
            <ExternalLink href={detail.openapi_url} label={t("api.openapi")} hint={t("common.external")} />
          ) : null}
        </ul>
      </nav>

      <section aria-labelledby="verification" className="rounded-sm border border-teak/30 bg-card p-4 text-sm">
        <h2 id="verification" className="font-semibold">
          {t("api.verification")}
        </h2>
        <p className="mt-1">
          {t("api.verifiedOn", { date: formatDate(detail.verification.checked_on, locale) })}{" "}
          <span className="text-muted-foreground">
            {t(detail.verification.method === "live_request" ? "api.live_request" : "api.official_documentation")}
          </span>
        </p>
        <h3 className="mt-3 text-xs font-medium text-muted-foreground">{t("api.evidence")}</h3>
        <ul dir="ltr" className="mt-1 space-y-1">
          {detail.verification.evidence.map((url) => (
            <li key={url}>
              <a href={url} rel="noopener noreferrer" className="break-all text-xs text-primary hover:underline">
                {url}
              </a>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[6.5rem_minmax(0,1fr)] gap-3 px-4 py-3">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0">{children}</dd>
    </div>
  );
}

function ExternalLink({ href, label, hint }: { href: string; label: string; hint: string }) {
  return (
    <li>
      <a href={href} rel="noopener noreferrer" className="inline-flex items-center gap-1 text-primary hover:underline">
        {label}
        <ArrowUpRightIcon aria-hidden className="size-3.5 rtl:-scale-x-100" />
        <span className="sr-only">({hint})</span>
      </a>
    </li>
  );
}

async function Endpoint({ endpoint, locale }: { endpoint: EndpointOut; locale: Locale }) {
  const t = await getTranslations({ locale });
  return (
    <li id={endpoint.id} className="scroll-mt-6">
      <div dir="ltr" className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="rounded-sm bg-teak px-1.5 py-0.5 font-mono text-xs font-semibold text-background">
          {endpoint.method}
        </span>
        <code className="break-all text-sm">{endpoint.path}</code>
      </div>
      <p className="mt-2">{pick(endpoint.summary, locale)}</p>
      {endpoint.parameters.length > 0 ? (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[32rem] border-collapse text-sm">
            <caption className="sr-only">{t("api.parameters")}</caption>
            <thead>
              <tr className="border-b border-teak/30 text-start text-xs text-muted-foreground">
                <th scope="col" className="py-1.5 pe-3 text-start font-medium">
                  {t("api.name")}
                </th>
                <th scope="col" className="py-1.5 pe-3 text-start font-medium">
                  {t("api.in")}
                </th>
                <th scope="col" className="py-1.5 pe-3 text-start font-medium">
                  {t("api.type")}
                </th>
                <th scope="col" className="py-1.5 text-start font-medium">
                  {t("api.example")}
                </th>
              </tr>
            </thead>
            <tbody>
              {endpoint.parameters.map((parameter) => (
                <tr key={`${parameter.in}:${parameter.name}`} className="border-b border-teak/15 align-top">
                  <td className="py-2 pe-3">
                    <code dir="ltr" className="text-xs font-semibold">
                      {parameter.name}
                    </code>
                    <span className="ms-2 text-xs text-muted-foreground">
                      {parameter.required ? t("api.required") : t("api.optional")}
                    </span>
                    <span className="mt-0.5 block text-xs text-muted-foreground">
                      {pick(parameter.description, locale)}
                    </span>
                    {parameter.allowed_values ? (
                      <span dir="ltr" className="mt-0.5 block text-xs text-muted-foreground">
                        {t("api.allowed")}: {parameter.allowed_values.join(", ")}
                      </span>
                    ) : null}
                  </td>
                  <td className="py-2 pe-3 text-xs">{parameter.in}</td>
                  <td className="py-2 pe-3 text-xs">{parameter.type}</td>
                  <td className="py-2">
                    {parameter.example ? (
                      <code dir="ltr" className="break-all text-xs">
                        {parameter.example}
                      </code>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {endpoint.examples.length > 0 ? (
        <div className="mt-4">
          <h3 className="sr-only">{t("api.examples")}</h3>
          <CodeExamples examples={endpoint.examples} copy={t("api.copy")} copied={t("api.copied")} />
        </div>
      ) : null}
      {endpoint.response_example ? (
        <details className="mt-3">
          <summary className="cursor-pointer text-sm text-muted-foreground">{t("api.responseExample")}</summary>
          <CodeBlock code={endpoint.response_example} copy={t("api.copy")} copied={t("api.copied")} />
        </details>
      ) : null}
    </li>
  );
}
