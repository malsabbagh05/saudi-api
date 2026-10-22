// Serves the production build the way the image does: Next.js standalone output with its
// static files beside it ("output: standalone" in the Next.js docs). Run `npm run build` first.
import { cpSync, existsSync } from "node:fs";
import { spawn } from "node:child_process";

const standalone = new URL("../.next/standalone/", import.meta.url);
if (!existsSync(new URL("server.js", standalone))) {
  console.error("No standalone build: run `npm run build` first.");
  process.exit(1);
}
cpSync(new URL("../.next/static/", import.meta.url), new URL(".next/static/", standalone), { recursive: true });
cpSync(new URL("../public/", import.meta.url), new URL("public/", standalone), { recursive: true });

const server = spawn(process.execPath, ["server.js"], {
  cwd: standalone,
  stdio: "inherit",
  env: { PORT: "3000", HOSTNAME: "127.0.0.1", ...process.env },
});
server.on("exit", (code) => process.exit(code ?? 0));
for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => server.kill(signal));
