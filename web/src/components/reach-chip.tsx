import { getTranslations } from "next-intl/server";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { CheckOut } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Locale } from "@/i18n/routing";

const TONE: Record<CheckOut["outcome"], string> = {
  reachable: "bg-reach",
  http_error: "bg-degraded",
  timeout: "bg-degraded",
  connection_error: "bg-blocked",
  tls_error: "bg-blocked",
  refused_by_policy: "bg-lattice-shut",
};

/** The latest reachability check; the tooltip says when and from where it ran. */
export async function ReachChip({
  check,
  locale,
  className,
}: {
  check: CheckOut | null | undefined;
  locale: Locale;
  className?: string;
}) {
  const t = await getTranslations({ locale, namespace: "status" });
  if (!check) {
    return (
      <span className={cn("inline-flex items-center gap-1.5 text-xs text-muted-foreground", className)}>
        <span aria-hidden className="size-2 rounded-full border border-teak/40" />
        {t("unchecked")}
      </span>
    );
  }
  const when = t("checkedFrom", {
    time: formatDateTime(check.checked_at, locale),
    region: check.region,
  });
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          tabIndex={0}
          className={cn(
            "inline-flex items-center gap-1.5 text-xs text-muted-foreground cursor-default rounded-sm",
            className,
          )}
        >
          <span aria-hidden className={cn("size-2 rounded-full", TONE[check.outcome])} />
          {t(check.outcome)}
          <span className="sr-only">. {when}</span>
        </span>
      </TooltipTrigger>
      <TooltipContent>{when}</TooltipContent>
    </Tooltip>
  );
}
