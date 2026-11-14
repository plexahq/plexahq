import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { defineConfig, type Plugin } from "vite";

// The website lives in site/ and builds to site-dist/ (Vercel's output directory).
// In development, /mcp and /api are proxied to a local Plexa server (npm run dev:http).
const API = process.env.PLEXA_API ?? "http://127.0.0.1:3000";
const SITE = fileURLToPath(new URL("./site/", import.meta.url));
export const PAGES = ["product", "docs", "stats", "company", "contact", "soon"];

/** Inlines shared markup: <!--#include nav--> → site/partials/nav.html */
function partials(): Plugin {
  return {
    name: "plexa-partials",
    transformIndexHtml: (html) =>
      html.replace(/<!--#include ([\w-]+)-->/g, (_, name: string) => readFileSync(`${SITE}partials/${name}.html`, "utf8")),
  };
}

/** /docs → /docs.html locally, like Vercel's cleanUrls in production. */
function cleanUrls(): Plugin {
  const rewrite = (req: { url?: string }, _res: unknown, next: () => void) => {
    const m = req.url?.match(new RegExp(`^/(${PAGES.join("|")})/?(\\?.*|#.*)?$`));
    if (m) req.url = `/${m[1]}.html${m[2] ?? ""}`;
    next();
  };
  return {
    name: "plexa-clean-urls",
    configureServer: (s) => void s.middlewares.use(rewrite),
    configurePreviewServer: (s) => void s.middlewares.use(rewrite),
  };
}

const proxy = {
  "/mcp": { target: API, changeOrigin: true },
  "/api": { target: API, changeOrigin: true },
  "/health": { target: API, changeOrigin: true },
};

export default defineConfig({
  root: "site",
  publicDir: "public",
  plugins: [partials(), cleanUrls()],
  build: {
    outDir: "../site-dist",
    emptyOutDir: true,
    target: "es2022",
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      input: Object.fromEntries([["index", `${SITE}index.html`], ...PAGES.map((p) => [p, `${SITE}${p}.html`])]),
    },
  },
  server: { proxy },
  preview: { proxy },
});
