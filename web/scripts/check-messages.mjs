// Fails when web/messages/en.json and ar.json do not have the same keys, or when a
// message is empty (bilingual.md: every UI string exists in both languages).
import { readFileSync } from "node:fs";

function keys(value, prefix = "") {
  return Object.entries(value).flatMap(([key, child]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    if (typeof child === "object" && child !== null) return keys(child, path);
    if (typeof child !== "string" || child.trim() === "") return [`${path} (empty)`];
    return [path];
  });
}

const load = (locale) =>
  JSON.parse(readFileSync(new URL(`../messages/${locale}.json`, import.meta.url), "utf8"));
const en = new Set(keys(load("en")));
const ar = new Set(keys(load("ar")));
const problems = [
  ...[...en].filter((key) => !ar.has(key)).map((key) => `missing in ar: ${key}`),
  ...[...ar].filter((key) => !en.has(key)).map((key) => `missing in en: ${key}`),
  ...[...en, ...ar].filter((key) => key.endsWith("(empty)")),
];
if (problems.length > 0) {
  console.error(problems.join("\n"));
  process.exit(1);
}
console.log(`messages: ${en.size} keys in en and ar`);
