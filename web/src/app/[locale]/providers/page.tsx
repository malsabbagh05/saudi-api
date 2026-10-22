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

export async function generateMetadata({ params }: PageProps<"/[locale]/providers">): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "providers" });
  return { title: t("title"), description: t("lede") };
}

export default async function ProvidersPage({ params }: PageProps<"/[locale]/providers">) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  const t = await getTranslations({ locale, namespace: "providers" });
  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-2xl font-semibold">{t("title")}</h1>
      <p className="mt-2 max-w-[65ch] text-muted-foreground">{t("lede")}</p>
      <Suspense fallback={<Skeleton className="mt-6 h-96 w-full" />}>
        <List locale={locale} />
      </Suspense>
    </div>
  );
}

async function List({ locale }: { locale: Locale }) {
  const t = await getTranslations({ locale, namespace: "providers" });
  const providers = await api.providers();
  return (
    <ul className="mt-6 grid border-t border-teak/25 sm:grid-cols-2 sm:gap-x-8">
      {providers.map((provider) => (
        <li key={provider.slug} className="border-b border-teak/15">
          <Link href={`/providers/${provider.slug}`} className="group flex items-baseline justify-between gap-4 py-3">
            <span className="min-w-0 flex-1">
              <span className="block font-medium group-hover:text-primary group-hover:underline">
                {pick(provider.name, locale)}
              </span>
              <span className="block text-sm text-muted-foreground">
                {t(provider.kind as "government")}
              </span>
            </span>
            <span className="shrink-0 text-sm tabular-nums text-muted-foreground">
              {t("apis", { count: provider.api_count })}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
