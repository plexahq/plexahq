# Plexa: project notes

Plexa is an MCP gateway that connects AI clients (Claude, Claude Code, ChatGPT, Cursor, VS Code) to LayerZero's **Zero** chain, EVM chains and LayerZero cross-chain messaging. Twelve tools, all read-only. Live at https://plexahq.vercel.app (MCP endpoint `/mcp`). Repo `plexahq/plexahq` is public, default branch `main`.

The owner writes in Turkish; reply in Turkish. Website copy is English.

## Context
- Zero mainnet: **2026-11-30** (date only, UTC midnight assumed). Zones: ATLAS (trading, lzATLAS), Interop (general EVM), Payments (announced). Chain IDs and RPCs not public yet. Enable with `PLEXA_RPC_ZERO_ATLAS` / `PLEXA_RPC_ZERO_INTEROP`.
- LayerZero metadata lists `zeroatlas-*` / `zerointerop-*`. The testnet entries use chain ID 1337 and Hardhat/Anvil default addresses, so they look like internal devnets. Do not hard-code them.
- Design references were teseralab.com and fungolabs.org. Use them for inspiration only, never copy their colours, fonts or imagery.

## Layout
- `src/`: the server.
  - `chains.ts`: chain registry and env overrides.
  - `tools/evm.ts`, `tools/layerzero.ts`: the tools.
  - `layerzero.ts`: Scan API and metadata clients.
  - `sourcify.ts`, `abi.ts`.
  - `live.ts`: snapshot behind `/api/live`.
  - `web.ts`: shared Request→Response handlers for `/mcp`, `/health` and `/api/live?messages=1..50`.
  - `http.ts`: Node server. `stdio.ts`: local entry.
- `api/*.js`: Vercel functions that import `../dist/web.js`.
- `site/`: Vite multi-page site, built into `site-dist/`.
  - Pages: `index.html` (home, 12 chapters `data-chapter` 0–11), plus `product`, `docs`, `stats`, `company`, `contact`.
  - `partials/nav.html` and `partials/footer.html` are inlined with `<!--#include name-->` by a plugin in `vite.config.ts`.
  - Clean URLs: `cleanUrls` in `vercel.json`, plus a dev/preview middleware.
  - `src/main.ts`: home bootstrap. `src/page.ts`: sub-pages, with a `SCENES` map giving each page a hero and an ambient formation.
  - `src/motion.ts`: Lenis, GSAP ScrollTrigger, word splitting, reveals, kicker scramble, chapter HUD and rail. It emits scroll-scrubbed transitions as `(a, c, t)`.
  - `src/nav.ts`: mobile menu.
  - `src/demos.ts`: connect tabs, read demo, simulate console, LayerZero track timeline, countdown, tools grid.
  - `src/live.ts`: `LiveFeed` that polls `/api/live`. `src/mcp.ts`: `callTool` client. `src/pages/*`: docs, stats and contact logic.
  - `src/scene/formations.ts`: 12 particle formations, indexed by chapter, plus `CHAIN_NODES`.
  - `src/scene/plexus.ts`: Three.js points shader.
    - Each particle has 3 targets: formation A, a full-screen "storm" and formation C. `uT` runs 0..1, with the storm at 0.5.
    - `VIEWS` places each formation: scale > 1.3 means a full-screen backdrop, otherwise it sits in the free right column.
    - Graph overlay (nodes, threads, live pulses) shows for views with `graph` 1 (sphere) or 2 (ring).
- Design tokens:
  - Colours: background `#0A0B0E`, signal orange `#FF5B1F`, verified teal `#2FD3B5`.
  - Fonts: Familjen Grotesk and Fragment Mono, via @fontsource.

## Commands
- `npm run build`: tsc builds the server into `dist/`, then vite builds the site into `site-dist/`.
- `npm run typecheck`: checks both server and site.
- `npm test`: unit tests (`vitest.config.ts`). `npm run test:live`: tests against real chains.
- Dev: `npm run dev:http` (API on :3000) and `npm run dev:site` (:5173, proxies `/mcp` and `/api`).
- In the cloud sandbox:
  - Node's `fetch` needs `NODE_USE_ENV_PROXY=1` (live tests and the local server).
  - For WebGL screenshots, launch Playwright Chromium with `--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader`.
  - For external sites, pass `proxy: { server: process.env.HTTPS_PROXY }`.

## Deploy
- Vercel project `plexahq` (team `mocadeneme`, Hobby plan) is Git-linked. Pushes to `main` deploy to production automatically. Preview URLs require Vercel login; `plexahq.vercel.app` is public.
- Workflow the owner approved: work on a branch, verify (typecheck, tests, screenshots), then fast-forward `main` and check production.
- Hobby is for non-commercial use only, so upgrade to Pro before launch. Public RPCs are rate-limited, so add our own RPC keys (Alchemy, Chainstack) as env vars when traffic grows.

## Open items
- Contact: no email or X handle yet. Enable GitHub private vulnerability reporting.
- No Open Graph image. Custom domain comes later (Vercel → Settings → Domains).
- Product roadmap: signing page, OFT bridging quotes, OApp DVN/security review, lzATLAS market data, agent wallets with limits.
- Merged branches that can be deleted: `claude/mcp-core`, `site/v1`, `site/v2`.

## Conventions
- Keep every tool read-only. Copy must be honest: no made-up data, and mark unknowns (e.g. Zero chain IDs "tba").
- Not affiliated with LayerZero Labs; the footer says so.
