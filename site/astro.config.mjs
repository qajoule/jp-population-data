import { defineConfig } from "astro/config";

export default defineConfig({
  output: "static",
  site: "https://jp-population-data.pages.dev",
  // The CSP is style-src 'self' with no hashes, so a stylesheet must never be inlined as <style>.
  // Astro inlines small stylesheets by default, which starts to happen when a second page splits the CSS.
  build: { inlineStylesheets: "never" },
});
