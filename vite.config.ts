import { defineConfig } from "vite";

// The marketing site lives in site/ and builds to site-dist/ (Vercel's output directory).
// In development, /mcp and /api are proxied to a local Plexa server (npm run dev:http).
const API = process.env.PLEXA_API ?? "http://127.0.0.1:3000";

export default defineConfig({
  root: "site",
  publicDir: "public",
  build: {
    outDir: "../site-dist",
    emptyOutDir: true,
    target: "es2022",
    chunkSizeWarningLimit: 900,
  },
  server: {
    proxy: {
      "/mcp": { target: API, changeOrigin: true },
      "/api": { target: API, changeOrigin: true },
      "/health": { target: API, changeOrigin: true },
    },
  },
  preview: {
    proxy: {
      "/mcp": { target: API, changeOrigin: true },
      "/api": { target: API, changeOrigin: true },
      "/health": { target: API, changeOrigin: true },
    },
  },
});
