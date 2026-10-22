import { useTranslations } from "next-intl";

import { Link } from "@/i18n/navigation";

export default function NotFound() {
  const t = useTranslations("errors");
  return (
    <div className="mx-auto max-w-3xl px-4 py-20">
      <h1 className="text-3xl font-semibold">{t("notFoundTitle")}</h1>
      <p className="mt-3 text-muted-foreground">{t("notFoundBody")}</p>
      <Link href="/" className="mt-6 inline-block text-primary hover:underline">
        {t("home")}
      </Link>
    </div>
  );
}
