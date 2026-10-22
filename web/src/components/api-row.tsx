import { getTranslations } from "next-intl/server";

import { AccessLattice, accessPosition } from "@/components/access-lattice";
import { ReachChip } from "@/components/reach-chip";
import { Link } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";
import type { AccessLevel, ApiSummary } from "@/lib/api";
import { pick } from "@/lib/format";

/**
 * One API as a dense row: what it is, who publishes it, and the facts a developer judges
 * first (access, authentication, endpoints, reachability), readable without opening it.
 */
export async function ApiRow({
  api,
  locale,
  litAccess,
}: {
  api: ApiSummary;
  locale: Locale;
  litAccess?: AccessLevel;
}) {
  const t = await getTranslations({ locale });
  const level = api.access.level as AccessLevel;
  return (
    <li className="group relative grid gap-x-6 gap-y-2 border-b border-border px-4 py-4 last:border-b-0 hover:bg-card md:grid-cols-[minmax(0,1fr)_15rem]">
      <div className="min-w-0">
        <h3 className="text-base font-medium leading-snug">
          <Link
            href={`/apis/${api.slug}`}
            className="after:absolute after:inset-0 hover:underline focus-visible:outline-none group-focus-within:underline"
          >
            {pick(api.name, locale)}
          </Link>
        </h3>
        <p className="text-sm text-muted-foreground">{pick(api.provider.name, locale)}</p>
        <p className="mt-1 line-clamp-2 text-sm text-foreground/85 max-w-[72ch]">
          {pick(api.summary, locale)}
        </p>
      </div>
      <dl className="relative z-[1] grid grid-cols-[auto_1fr] items-center gap-x-3 gap-y-1 text-xs self-start">
        <dt className="text-muted-foreground">{t("access.label")}</dt>
        <dd className="flex items-center gap-2">
          <AccessLattice
            level={level}
            lit={litAccess === level}
            label={t("access.lattice", { level: t(`access.${level}`), position: accessPosition(level) })}
          />
          <span aria-hidden>{t(`access.${level}`)}</span>
        </dd>
        <dt className="text-muted-foreground">{t("auth.label")}</dt>
        <dd>{api.access.auth.map((scheme) => t(`auth.${scheme}` as "auth.none")).join(" · ")}</dd>
        <dt className="text-muted-foreground">{t("api.endpoints")}</dt>
        <dd>
          {t("directory.endpoints", { count: api.endpoint_count })}
          {api.dataset_count > 0 ? ` · ${t("directory.datasets", { count: api.dataset_count })}` : ""}
        </dd>
        <dt className="text-muted-foreground">{t("api.status")}</dt>
        <dd className="flex items-center gap-2">
          <ReachChip check={api.check} locale={locale} />
          {api.agent_invocation ? (
            <span className="rounded-sm bg-accent px-1.5 py-px text-[0.7rem] font-medium text-accent-foreground">
              {t("api.invocable")}
            </span>
          ) : null}
        </dd>
      </dl>
    </li>
  );
}
