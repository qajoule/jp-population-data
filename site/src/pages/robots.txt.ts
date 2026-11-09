// robots.txt. Everything is allowed. Cloudflare may prepend its own managed block; this file stands alone,
// writes no "Disallow: /" for "*" and no Content-signal line (see seoworkspace/common/README.md, section 9).
import type { APIRoute } from "astro";

export const GET: APIRoute = ({ site }) => {
  const sitemap = new URL("sitemap.xml", site).href;
  return new Response(`User-agent: *\nDisallow:\n\nSitemap: ${sitemap}\n`, {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
};
