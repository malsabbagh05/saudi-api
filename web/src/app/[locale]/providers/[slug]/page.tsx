import { ArrowUpRightIcon } from "lucide-react";
import type { Metadata } from "next";
import { hasLocale } from "next-intl";
import { getTranslations } from "next-intl/server";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { ApiRow } from "@/components/api-row";
import { Skeleton } from "@/components/ui/skeleton";
import { routing } from "@/i18n/routing";
import { api } from "@/lib/api";
import { pick } from "@/lib/format";

export async function generateMetadata({ params }: PageProps<"/[locale]/providers/[slug]">): Promise<Metadata> {
  const { locale, slug } = await params;
  if (!hasLocale(routing.locales, locale)) return {};
  const provider = await api.provider(slug);
  return provider ? { title: pick(provider.name, locale), description: pick(provider.description, locale) } : {};
}

export default function ProviderPage({ params }: PageProps<"/[locale]/providers/[slug]">) {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-6xl px-4 py-10">
          <Skeleton className="h-9 w-1/2" />
          <Skeleton className="mt-8 h-72 w-full" />
        </div>
      }
    >
      <Detail params={params} />
    </Suspense>
  );
}

async function Detail({ params }: { params: PageProps<"/[locale]/providers/[slug]">["params"] }) {
  const { locale, slug } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  const provider = await api.provider(slug);
  if (!provider) notFound();
  const t = await getTranslations({ locale });
  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-3xl font-semibold tracking-tight">{pick(provider.name, locale)}</h1>
      <p className="mt-1 text-muted-foreground">{t(`providers.${provider.kind}` as "providers.government")}</p>
      <p className="mt-3 max-w-[70ch]">{pick(provider.description, locale)}</p>
      <a
        href={provider.website_url}
        rel="noopener noreferrer"
        className="mt-3 inline-flex items-center gap-1 text-sm text-primary hover:underline"
      >
        {t("providers.website")}
        <ArrowUpRightIcon aria-hidden className="size-3.5 rtl:-scale-x-100" />
        <span className="sr-only">({t("common.external")})</span>
      </a>
      <h2 className="mt-10 mb-3 text-lg font-semibold">{t("providers.apis", { count: provider.apis.length })}</h2>
      <ul className="border-y border-teak/25">
        {provider.apis.map((item) => (
          <ApiRow key={item.slug} api={item} locale={locale} />
        ))}
      </ul>
    </div>
  );
}
