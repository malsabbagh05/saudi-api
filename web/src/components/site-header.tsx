import { SearchIcon } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { LocaleSwitch } from "@/components/locale-switch";
import { Link } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";

export async function SiteHeader({ locale }: { locale: Locale }) {
  const t = await getTranslations({ locale, namespace: "nav" });
  const links = [
    { href: "/apis", label: t("apis") },
    { href: "/datasets", label: t("datasets") },
    { href: "/providers", label: t("providers") },
    { href: "/agents", label: t("agents") },
    { href: "/about", label: t("about") },
  ] as const;
  return (
    <header className="border-b border-teak/25 bg-card">
      <a
        href="#content"
        className="sr-only focus:not-sr-only focus:absolute focus:start-4 focus:top-2 focus:z-50 focus:rounded-sm focus:bg-primary focus:px-3 focus:py-1.5 focus:text-primary-foreground"
      >
        {t("skip")}
      </a>
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-3 px-4 py-3">
        <Link href="/" className="flex items-center gap-2.5 font-semibold tracking-tight">
          <BrandMark />
          <span>{t("brand")}</span>
        </Link>
        <nav aria-label={t("primary")} className="order-3 w-full md:order-none md:w-auto">
          <ul className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
            {links.map((link) => (
              <li key={link.href}>
                <Link href={link.href} className="text-foreground/80 hover:text-foreground hover:underline">
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <div className="ms-auto flex items-center gap-3">
          <form action={`/${locale}/search`} method="get" role="search" className="relative hidden sm:block">
            <label htmlFor="header-search" className="sr-only">
              {t("searchLabel")}
            </label>
            <SearchIcon
              aria-hidden
              className="pointer-events-none absolute start-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            />
            <input
              id="header-search"
              name="q"
              type="search"
              maxLength={200}
              placeholder={t("searchPlaceholder")}
              className="h-8 w-56 rounded-sm border border-input bg-background ps-8 pe-2 text-sm placeholder:text-muted-foreground focus-visible:border-ring"
            />
          </form>
          <LocaleSwitch label={t("switchLanguage")} description={t("switchLanguageLabel")} />
        </div>
      </div>
    </header>
  );
}

/** The mark: one carved lattice aperture, the site's signature in miniature. */
function BrandMark() {
  return (
    <svg aria-hidden viewBox="0 0 24 24" className="size-6 shrink-0">
      <rect x="1" y="1" width="22" height="22" rx="2" className="fill-teak" />
      <rect x="7" y="7" width="10" height="10" transform="rotate(45 12 12)" className="fill-lattice-open" />
    </svg>
  );
}
