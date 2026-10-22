"use client";

import { useTranslations } from "next-intl";

export default function ErrorBoundary({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const t = useTranslations("errors");
  return (
    <div role="alert" className="mx-auto max-w-3xl px-4 py-20">
      <h1 className="text-3xl font-semibold">{t("errorTitle")}</h1>
      <p className="mt-3 text-muted-foreground">{t("errorBody")}</p>
      <button
        type="button"
        onClick={reset}
        className="mt-6 rounded-sm bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
      >
        {t("retry")}
      </button>
    </div>
  );
}
