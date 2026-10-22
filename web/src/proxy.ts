import createMiddleware from "next-intl/middleware";
import { routing } from "./i18n/routing";

export default createMiddleware(routing);

export const config = {
  // Every path except Next internals, files with an extension, and the metadata routes.
  matcher: "/((?!_next|_vercel|sitemap.xml|robots.txt|.*\..*).*)",
};
