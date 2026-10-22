import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { Link } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";

type Query = Record<string, string | undefined>;

export async function Pagination({
  locale,
  pathname,
  query,
  page,
  pages,
}: {
  locale: Locale;
  pathname: "/apis" | "/datasets";
  query: Query;
  page: number;
  pages: number;
}) {
  if (pages <= 1) return null;
  const t = await getTranslations({ locale, namespace: "directory" });
  const href = (target: number) => ({
    pathname,
    query: Object.fromEntries(
      Object.entries({ ...query, page: target > 1 ? String(target) : undefined }).filter(
        (entry): entry is [string, string] => entry[1] !== undefined,
      ),
    ),
  });
  return (
    <nav aria-label={t("page", { page, pages })} className="mt-6 flex items-center justify-between gap-4 text-sm">
      {page > 1 ? (
        <Link href={href(page - 1)} rel="prev" className="inline-flex items-center gap-1 hover:underline">
          <ChevronLeftIcon aria-hidden className="size-4 rtl:rotate-180" />
          {t("previous")}
        </Link>
      ) : (
        <span />
      )}
      <span className="tabular-nums text-muted-foreground">{t("page", { page, pages })}</span>
      {page < pages ? (
        <Link href={href(page + 1)} rel="next" className="inline-flex items-center gap-1 hover:underline">
          {t("next")}
          <ChevronRightIcon aria-hidden className="size-4 rtl:rotate-180" />
        </Link>
      ) : (
        <span />
      )}
    </nav>
  );
}
