import { getTranslations } from "next-intl/server";

import { publicApiUrl } from "@/lib/api";
import type { Locale } from "@/i18n/routing";

const SOURCE_URL = "https://github.com/malsabbagh05/saudi-api";

export async function SiteFooter({ locale }: { locale: Locale }) {
  const t = await getTranslations({ locale, namespace: "footer" });
  const api = publicApiUrl();
  return (
    <footer className="mt-16 border-t border-teak/25 bg-card">
      <div className="mx-auto flex max-w-6xl flex-wrap items-start justify-between gap-6 px-4 py-8 text-sm">
        <div className="space-y-1">
          <p className="font-medium">{t("tagline")}</p>
          <p className="text-muted-foreground">{t("independent")}</p>
        </div>
        <ul className="flex flex-wrap gap-x-5 gap-y-2 text-muted-foreground">
          <li>
            <a className="hover:text-foreground hover:underline" href={`${api}/docs`}>
              {t("restApi")}
            </a>
          </li>
          <li>
            <a className="hover:text-foreground hover:underline" href={`${api}/openapi.json`}>
              {t("openapi")}
            </a>
          </li>
          <li>
            <a className="hover:text-foreground hover:underline" href={`${api}/llms.txt`}>
              {t("llms")}
            </a>
          </li>
          <li>
            <a className="hover:text-foreground hover:underline" href={SOURCE_URL} rel="noopener noreferrer">
              {t("source")}
            </a>
          </li>
        </ul>
      </div>
    </footer>
  );
}
