import "server-only";

import { headers } from "next/headers";

import type { components } from "./api-schema";

// The REST API is the web directory's only data source (frontend.md). API_BASE_URL is a
// server-only setting; it never reaches the browser.
const BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

type Schemas = components["schemas"];
export type ApiSummary = Schemas["ApiSummary"];
export type ApiDetail = Schemas["ApiDetail"];
export type EndpointOut = Schemas["EndpointOut"];
export type SectorOut = Schemas["SectorOut"];
export type ProviderSummary = Schemas["ProviderSummary"];
export type ProviderOut = Schemas["ProviderOut"];
export type DatasetSummary = Schemas["DatasetSummary"];
export type DatasetDetail = Schemas["DatasetDetail"];
export type SearchHit = Schemas["SearchHit"];
export type StatsOut = Schemas["StatsOut"];
export type CheckOut = Schemas["CheckOut"];
export type Text = Schemas["Text"];
export type ApiPage = Schemas["Page_ApiSummary_"];
export type DatasetPage = Schemas["Page_DatasetSummary_"];

export type AccessLevel = "open" | "registration" | "approval" | "contract" | "restricted";
export const ACCESS_LEVELS: readonly AccessLevel[] = [
  "open",
  "registration",
  "approval",
  "contract",
  "restricted",
];

export class CatalogueUnavailable extends Error {
  constructor(readonly status: number | null) {
    super(`catalogue API unavailable (${status ?? "no response"})`);
  }
}

type Query = Record<string, string | number | boolean | undefined | null>;

async function get<T>(path: string, query?: Query): Promise<T | null> {
  const url = new URL(path, BASE_URL);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }
  // Carry the visitor's request ID to the API so one trace covers both services.
  const requestId = (await headers()).get("x-request-id");
  let response: Response;
  try {
    response = await fetch(url, {
      headers: { accept: "application/json", ...(requestId ? { "x-request-id": requestId } : {}) },
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
  } catch {
    throw new CatalogueUnavailable(null);
  }
  if (response.status === 404) return null;
  if (!response.ok) throw new CatalogueUnavailable(response.status);
  return (await response.json()) as T;
}

async function must<T>(path: string, query?: Query): Promise<T> {
  const value = await get<T>(path, query);
  if (value === null) throw new CatalogueUnavailable(404);
  return value;
}

export const api = {
  stats: () => must<StatsOut>("/v1/stats"),
  sectors: () => must<SectorOut[]>("/v1/sectors"),
  providers: () => must<ProviderSummary[]>("/v1/providers"),
  provider: (slug: string) => get<ProviderOut>(`/v1/providers/${encodeURIComponent(slug)}`),
  apis: (query: Query) => must<ApiPage>("/v1/apis", query),
  api: (slug: string) => get<ApiDetail>(`/v1/apis/${encodeURIComponent(slug)}`),
  datasets: (query: Query) => must<DatasetPage>("/v1/datasets", query),
  dataset: (apiSlug: string, id: string) =>
    get<DatasetDetail>(`/v1/datasets/${encodeURIComponent(apiSlug)}/${encodeURIComponent(id)}`),
  search: (q: string, limit = 20) => must<SearchHit[]>("/v1/search", { q, limit }),
};

/** The public origin of the API service, as visitors and agents should reach it. */
export function publicApiUrl(): string {
  return process.env.PUBLIC_API_URL ?? "http://localhost:8000";
}
