import type { Metadata } from "next";
import { hasLocale } from "next-intl";
import { getTranslations } from "next-intl/server";
import { notFound } from "next/navigation";

import { routing } from "@/i18n/routing";

const SOURCE_URL = "https://github.com/malsabbagh05/saudi-api";

export async function generateMetadata({ params }: PageProps<"/[locale]/about">): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "about" });
  return { title: t("title"), description: t("lede") };
}

export default async function AboutPage({ params }: PageProps<"/[locale]/about">) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  const t = await getTranslations({ locale, namespace: "about" });
  const sections = [
    ["evidenceTitle", "evidenceBody"],
    ["policyTitle", "policyBody"],
    ["independentTitle", "independentBody"],
    ["contributeTitle", "contributeBody"],
  ] as const;
  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="text-3xl font-semibold tracking-tight">{t("title")}</h1>
      <p className="mt-3 text-lg text-muted-foreground">{t("lede")}</p>
      {sections.map(([title, body]) => (
        <section key={title} className="mt-10">
          <h2 className="text-xl font-semibold">{t(title)}</h2>
          <p className="mt-2 max-w-[70ch]">{t(body)}</p>
        </section>
      ))}
      <p className="mt-10">
        <a href={SOURCE_URL} rel="noopener noreferrer" className="text-primary hover:underline">
          {t("source")}
        </a>
      </p>
    </div>
  );
}
