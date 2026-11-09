// sitemap.xml built from the static pages. No priority or changefreq (search engines ignore them);
// a page that sets "noindex" or is the 404 page is left out.
import type { APIRoute } from "astro";

const modules = import.meta.glob("./**/*.astro");

export const GET: APIRoute = ({ site }) => {
  const paths = Object.keys(modules)
    .map((file) => file.replace(/^\.\//, "/").replace(/index\.astro$/, "").replace(/\.astro$/, "/"))
    .filter((path) => !path.startsWith("/404") && !path.includes("["))
    .sort();
  const urls = paths.map((path) => `  <url>\n    <loc>${new URL(path, site).href}</loc>\n  </url>`).join("\n");
  const xml = `<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`;
  return new Response(xml, { headers: { "Content-Type": "application/xml; charset=utf-8" } });
};
