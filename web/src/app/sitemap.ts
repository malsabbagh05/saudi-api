import type { MetadataRoute } from "next";
import { connection } from "next/server";

import { routing } from "@/i18n/routing";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

type Slugs = { items: { slug: string }[] };

// Built per request from the API, so the sitemap follows the catalogue without a rebuild.
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  await connection();
  const pages = ["", "/apis", "/datasets", "/providers", "/agents", "/about"];
  let apis: string[] = [];
  let providers: string[] = [];
  try {
    const [apiPage, providerList] = await Promise.all([
      fetch(`${API_BASE_URL}/v1/apis?limit=100`, { cache: "no-store" }).then((r) => r.json() as Promise<Slugs>),
      fetch(`${API_BASE_URL}/v1/providers`, { cache: "no-store" }).then(
        (r) => r.json() as Promise<{ slug: string }[]>,
      ),
    ]);
    apis = apiPage.items.map((item) => `/apis/${item.slug}`);
    providers = providerList.map((item) => `/providers/${item.slug}`);
  } catch {
    // The static pages still make a valid sitemap while the API is down.
  }
  return [...pages, ...apis, ...providers].map((path) => ({
    url: `${SITE_URL}/${routing.defaultLocale}${path}`,
    alternates: {
      languages: Object.fromEntries(routing.locales.map((locale) => [locale, `${SITE_URL}/${locale}${path}`])),
    },
  }));
}
