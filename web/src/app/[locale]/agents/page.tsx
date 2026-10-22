import type { Metadata } from "next";
import { hasLocale } from "next-intl";
import { getTranslations } from "next-intl/server";
import { notFound } from "next/navigation";

import { CodeBlock } from "@/components/code-examples";
import { routing } from "@/i18n/routing";
import { publicApiUrl } from "@/lib/api";

const TOOLS = [
  "search_catalog",
  "list_apis",
  "get_api",
  "list_sectors",
  "list_providers",
  "search_datasets",
  "get_dataset",
  "call_endpoint",
] as const;

export async function generateMetadata({ params }: PageProps<"/[locale]/agents">): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "agents" });
  return { title: t("title"), description: t("lede") };
}

export default async function AgentsPage({ params }: PageProps<"/[locale]/agents">) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  const t = await getTranslations({ locale });
  const base = publicApiUrl();
  const mcp = `${base}/mcp`;
  const copy = { copy: t("api.copy"), copied: t("api.copied") };
  const cursor = JSON.stringify({ mcpServers: { "saudi-api": { url: mcp } } }, null, 2);
  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-3xl font-semibold tracking-tight">{t("agents.title")}</h1>
      <p className="mt-3 max-w-[68ch] text-lg text-muted-foreground">{t("agents.lede")}</p>

      <section aria-labelledby="mcp" className="mt-10">
        <h2 id="mcp" className="text-xl font-semibold">
          {t("agents.mcpTitle")}
        </h2>
        <p className="mt-2">{t("agents.mcpLede")}</p>
        <div className="mt-3">
          <CodeBlock code={mcp} {...copy} wrap />
        </div>

        <div className="mt-8 grid gap-8 md:grid-cols-2 [&>*]:min-w-0">
          <div>
            <h3 className="font-semibold">{t("agents.claudeCode")}</h3>
            <div className="mt-2">
              <CodeBlock code={`claude mcp add --transport http saudi-api ${mcp}`} {...copy} wrap />
            </div>
          </div>
          <div>
            <h3 className="font-semibold">{t("agents.claudeDesktop")}</h3>
            <p className="mt-2 text-sm text-muted-foreground">{t("agents.claudeDesktopBody")}</p>
          </div>
          <div>
            <h3 className="font-semibold">{t("agents.chatgpt")}</h3>
            <p className="mt-2 text-sm text-muted-foreground">{t("agents.chatgptBody")}</p>
          </div>
          <div>
            <h3 className="font-semibold">{t("agents.cursor")}</h3>
            <p className="mt-2 text-sm text-muted-foreground">{t("agents.cursorBody")}</p>
            <div className="mt-2">
              <CodeBlock code={cursor} {...copy} />
            </div>
          </div>
        </div>
      </section>

      <section aria-labelledby="tools" className="mt-12">
        <h2 id="tools" className="text-xl font-semibold">
          {t("agents.toolsTitle")}
        </h2>
        <dl className="mt-3 divide-y divide-teak/15 border-y border-teak/25">
          {TOOLS.map((tool) => (
            <div key={tool} className="grid gap-1 py-2.5 sm:grid-cols-[12rem_minmax(0,1fr)] sm:gap-4">
              <dt>
                <code dir="ltr" className="text-sm font-semibold">
                  {tool}
                </code>
              </dt>
              <dd className="text-sm text-muted-foreground">{t(`tools.${tool}`)}</dd>
            </div>
          ))}
        </dl>
        <h3 className="mt-6 font-semibold">{t("agents.invokeTitle")}</h3>
        <p className="mt-2 max-w-[70ch] text-sm text-muted-foreground">{t("agents.invokeBody")}</p>
      </section>

      <section className="mt-12 grid gap-8 md:grid-cols-2 [&>*]:min-w-0">
        <div>
          <h2 className="text-xl font-semibold">{t("agents.restTitle")}</h2>
          <p className="mt-2 text-sm text-muted-foreground">{t("agents.restLede")}</p>
          <ul dir="ltr" className="mt-3 space-y-1 text-sm">
            <li>
              <a className="text-primary hover:underline" href={`${base}/docs`}>
                {base}/docs
              </a>
            </li>
            <li>
              <a className="text-primary hover:underline" href={`${base}/openapi.json`}>
                {base}/openapi.json
              </a>
            </li>
          </ul>
        </div>
        <div>
          <h2 className="text-xl font-semibold">{t("agents.llmsTitle")}</h2>
          <p className="mt-2 text-sm text-muted-foreground">{t("agents.llmsLede")}</p>
          <p dir="ltr" className="mt-3 text-sm">
            <a className="text-primary hover:underline" href={`${base}/llms.txt`}>
              {base}/llms.txt
            </a>
          </p>
        </div>
      </section>
    </div>
  );
}
