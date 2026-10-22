import type { Metadata } from "next";
import { hasLocale } from "next-intl";
import { getTranslations } from "next-intl/server";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { ApiRow } from "@/components/api-row";
import { Pagination } from "@/components/pagination";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { Skeleton } from "@/components/ui/skeleton";
import { Link } from "@/i18n/navigation";
import { routing, type Locale } from "@/i18n/routing";
import { ACCESS_LEVELS, api, type AccessLevel } from "@/lib/api";
import { pick } from "@/lib/format";

const PAGE_SIZE = 20;
const AUTH = ["none", "api_key", "bearer", "oauth2", "basic", "mtls", "jwt", "undisclosed"] as const;

export async function generateMetadata({ params }: PageProps<"/[locale]/apis">): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "directory" });
  return { title: t("title"), description: t("lede") };
}

type Search = Awaited<PageProps<"/[locale]/apis">["searchParams"]>;

function one(value: Search[string]): string | undefined {
  const first = Array.isArray(value) ? value[0] : value;
  return first?.trim() || undefined;
}

export default async function ApisPage({ params, searchParams }: PageProps<"/[locale]/apis">) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  const t = await getTranslations({ locale, namespace: "directory" });
  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-2xl font-semibold">{t("title")}</h1>
      <p className="mt-2 max-w-[65ch] text-muted-foreground">{t("lede")}</p>
      <Suspense fallback={<Skeleton className="mt-6 h-96 w-full" />}>
        <Directory locale={locale} searchParams={searchParams} />
      </Suspense>
    </div>
  );
}

async function Directory({
  locale,
  searchParams,
}: {
  locale: Locale;
  searchParams: PageProps<"/[locale]/apis">["searchParams"];
}) {
  const t = await getTranslations({ locale });
  const search = await searchParams;
  const q = one(search.q);
  const sector = one(search.sector);
  const accessValue = one(search.access);
  const access = ACCESS_LEVELS.includes(accessValue as AccessLevel) ? (accessValue as AccessLevel) : undefined;
  const authValue = one(search.auth);
  const auth = AUTH.includes(authValue as (typeof AUTH)[number]) ? authValue : undefined;
  const invocable = one(search.invocable) === "true" ? true : undefined;
  const page = Math.max(1, Number.parseInt(one(search.page) ?? "1", 10) || 1);

  const [sectors, results] = await Promise.all([
    api.sectors(),
    api.apis({ q, sector, access, auth, invocable, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }),
  ]);
  const filtered = Boolean(q || sector || access || auth || invocable);
  const query = { q, sector, access, auth, invocable: invocable ? "true" : undefined };

  return (
    <div className="mt-6 grid gap-8 lg:grid-cols-[15rem_minmax(0,1fr)] [&>*]:min-w-0">
      <form method="get" action={`/${locale}/apis`} aria-label={t("directory.filters")} className="space-y-4 self-start">
        <div className="space-y-1.5">
          <label htmlFor="f-q" className="text-sm font-medium">
            {t("nav.searchLabel")}
          </label>
          <input
            id="f-q"
            name="q"
            type="search"
            defaultValue={q}
            maxLength={200}
            className="h-8 w-full rounded-sm border border-input bg-card px-2.5 text-sm focus-visible:border-ring"
          />
        </div>
        <Field id="f-sector" label={t("directory.sector")}>
          <NativeSelect id="f-sector" name="sector" defaultValue={sector ?? ""} className="w-full">
            <NativeSelectOption value="">{t("directory.any")}</NativeSelectOption>
            {sectors
              .filter((item) => item.api_count > 0)
              .map((item) => (
                <NativeSelectOption key={item.slug} value={item.slug}>
                  {pick(item.name, locale)} ({item.api_count})
                </NativeSelectOption>
              ))}
          </NativeSelect>
        </Field>
        <Field id="f-access" label={t("directory.access")}>
          <NativeSelect id="f-access" name="access" defaultValue={access ?? ""} className="w-full">
            <NativeSelectOption value="">{t("directory.any")}</NativeSelectOption>
            {ACCESS_LEVELS.map((level) => (
              <NativeSelectOption key={level} value={level}>
                {t(`access.${level}`)}
              </NativeSelectOption>
            ))}
          </NativeSelect>
        </Field>
        <Field id="f-auth" label={t("directory.auth")}>
          <NativeSelect id="f-auth" name="auth" defaultValue={auth ?? ""} className="w-full">
            <NativeSelectOption value="">{t("directory.any")}</NativeSelectOption>
            {AUTH.map((scheme) => (
              <NativeSelectOption key={scheme} value={scheme}>
                {t(`auth.${scheme}`)}
              </NativeSelectOption>
            ))}
          </NativeSelect>
        </Field>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            name="invocable"
            value="true"
            defaultChecked={invocable}
            className="size-4 accent-[var(--primary)]"
          />
          {t("directory.invocable")}
        </label>
        <div className="flex items-center gap-3">
          <button type="submit" className="h-8 rounded-sm bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90">
            {t("directory.apply")}
          </button>
          {filtered ? (
            <Link href="/apis" className="text-sm text-muted-foreground hover:text-foreground hover:underline">
              {t("directory.clear")}
            </Link>
          ) : null}
        </div>
      </form>

      <section aria-live="polite" aria-labelledby="results-count">
        <p id="results-count" className="mb-3 text-sm text-muted-foreground">
          {t("directory.results", { count: results.total })}
          {q ? ` ${t("directory.query", { query: q })}` : ""}
        </p>
        {results.items.length === 0 ? (
          <div className="border-y border-teak/25 py-10">
            <p className="font-medium">{t("directory.empty")}</p>
            <p className="mt-1 text-sm text-muted-foreground">{t("directory.emptyHint")}</p>
          </div>
        ) : (
          <ul className="border-y border-teak/25 bg-background">
            {results.items.map((item) => (
              <ApiRow key={item.slug} api={item} locale={locale} litAccess={access} />
            ))}
          </ul>
        )}
        <Pagination
          locale={locale}
          pathname="/apis"
          query={query}
          page={page}
          pages={Math.max(1, Math.ceil(results.total / PAGE_SIZE))}
        />
      </section>
    </div>
  );
}

function Field({ id, label, children }: { id: string; label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      {children}
    </div>
  );
}
