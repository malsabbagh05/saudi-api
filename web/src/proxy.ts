import createMiddleware from "next-intl/middleware";
import { routing } from "./i18n/routing";

export default createMiddleware(routing);

export const config = {
  // Every path except Next internals, files with an extension, and the metadata routes.
  // The dot is escaped twice: in a string literal "\." is only ".", which would exclude
  // every path of two or more characters (next-intl, "Proxy / middleware").
  matcher: "/((?!_next|_vercel|sitemap.xml|robots.txt|.*\\..*).*)",
};
