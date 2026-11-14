# Plexa: project notes

Plexa is an MCP gateway that connects AI clients (Claude, Claude Code, ChatGPT, Cursor, VS Code) to LayerZero's **Zero** chain, EVM chains and LayerZero cross-chain messaging. Sixteen tools, all read-only. Live at https://plexahq.vercel.app (MCP endpoint `/mcp`). Repo `plexahq/plexahq`, default branch `main`. It is public only because Vercel Hobby can't deploy private org repos; the owner wants the code private, so make it private once on Vercel Pro. The website must never link to GitHub or the source code.

The owner writes in Turkish; reply in Turkish. Website copy is English.

## Context
- Zero mainnet: **2026-11-30** (date only, UTC midnight assumed). Zones: ATLAS (trading, lzATLAS), Interop (general EVM), Payments (announced). Chain IDs and RPCs not public yet. Enable with `PLEXA_RPC_ZERO_ATLAS` / `PLEXA_RPC_ZERO_INTEROP`.
- LayerZero metadata lists `zeroatlas-*` / `zerointerop-*`. The testnet entries use chain ID 1337 and Hardhat/Anvil default addresses, so they look like internal devnets. Do not hard-code them.
- Design references were teseralab.com and fungolabs.org. Use them for inspiration only, never copy their colours, fonts or imagery.

## Layout
- `src/`: the server.
  - `chains.ts`: chain registry and env overrides. Mainnets: Ethereum, Arbitrum, Base, HyperEVM, BNB (`bnb`), OP, Polygon, Avalanche, plus Zero placeholders.
  - `tools/evm.ts`, `tools/layerzero.ts`, `tools/markets.ts`: the tools.
  - `lzsecurity.ts`: `lz_app_security` (peers, DVNs per pathway via EndpointV2 `getConfig`, owner/delegate, Safe detection, risk level).
  - `stocks.ts`: Ondo Global Markets token list (Ethereum + BNB), used by `stocks_lookup` / `stocks_portfolio`. `tools/markets.ts` also has `zro_overview` (ZRO OFT at the same address on 7 chains).
  - `layerzero.ts`: Scan API and metadata clients.
  - `sourcify.ts`, `abi.ts`.
  - `live.ts`: snapshot behind `/api/live`.
  - `web.ts`: shared Request→Response handlers for `/mcp`, `/health` and `/api/live?messages=1..50`.
  - `http.ts`: Node server. `stdio.ts`: local entry.
- `api/*.js`: Vercel functions that import `../dist/web.js`.
  - `api/contact.js`: contact form. Saves each message as private JSON in Vercel Blob store `plexa-contact` (`contact/YYYY-MM-DD/...`), via `BLOB_READ_WRITE_TOKEN`. Read them in Vercel → Storage.
- `site/`: Vite multi-page site, built into `site-dist/`.
  - Pages: `index.html` (home, 14 chapters `data-chapter` 0–13: …5 cross-chain, 6 trust check, 7 zero + ZRO panel, 8 markets, 9 security…), plus `product`, `docs`, `stats`, `company`, `contact`. Chapter index = formation index = `VIEWS` index; inserting a chapter means inserting in all three and updating `SCENES` in `page.ts`.
  - `partials/nav.html` and `partials/footer.html` are inlined with `<!--#include name-->` by a plugin in `vite.config.ts`.
  - Clean URLs: `cleanUrls` in `vercel.json`, plus a dev/preview middleware.
  - `src/main.ts`: home bootstrap. Intro: the loader's SVG mark draws itself while the scene loads; then the dust gathers into the particle logo (view/formation 14, not a chapter; `Plexus.prepareIntro` → `assemble` → `open`), the logo bursts through the storm into the hero and the page opens. Any scroll, tap or key skips it. Nav, HUD and rail stay hidden until then. `src/page.ts`: sub-pages, with a `SCENES` map giving each page a hero and an ambient formation.
  - `src/motion.ts`: Lenis, GSAP ScrollTrigger, word splitting, reveals, kicker scramble, chapter HUD and rail. It emits scroll-scrubbed transitions as `(a, c, t)`. A ResizeObserver refreshes ScrollTrigger when live demos change the page height.
    - Home chapters use `sceneCuts()`: each chapter's `.wrap` blocks are moved into a `.stage` that the scroll itself scrubs. It arrives tilted up from depth (blur only while moving), with its first-screen headline words and `[data-reveal]` items in the same timeline; it leaves by drifting up, swelling and dissolving into the particle storm. Nothing is time-locked, so it follows the scroll both ways. Any filter or opacity left on a stage at rest would kill the panels' backdrop blur, so rest states are cleared.
    - A page-turn mode (particles drawing the page's text) was tried and rejected by the owner: dotted text looked broken and waiting for a turn felt slow.
  - `src/nav.ts`: mobile menu.
  - `src/demos.ts`: connect tabs, read demo, simulate console, LayerZero track timeline, countdown, tools grid.
  - `src/live.ts`: `LiveFeed` that polls `/api/live`. `src/mcp.ts`: `callTool` client. `src/pages/*`: docs, stats and contact logic.
  - `src/scene/formations.ts`: 14 particle formations (incl. `quorum` shield and `candles` chart), indexed by chapter, plus `CHAIN_NODES`.
  - `src/scene/plexus.ts`: Three.js points shader.
    - Each particle has 3 targets: formation A, a full-screen "storm" and formation C. `uT` runs 0..1, with the storm at 0.5.
    - `VIEWS` places each formation: scale > 1.3 means a full-screen backdrop, otherwise it sits in the free right column.
    - Graph overlay (nodes, threads, live pulses) shows for views with `graph` 1 (sphere) or 2 (ring).
    - `mask` on each view dims particles behind text (1 left column, 2 centre; phones dim everywhere, lightly). Keep copy readable.
    - Phones (`isNarrow`): formations are sized to the screen width (`viewW / 6.2`), 5200 particles, opacity ×0.9, mask strength 0.42, lighter vignette. Earlier settings made them nearly invisible.
    - Scroll sets a target; `advance()` moves `tCur` at most ~1.4/s and switches formation pairs only at a shared endpoint or inside the storm, so fast scrolling shows one storm, not a strobe.
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
- Contact: no email or X handle yet; the form stores messages in Blob (no email notification yet).
- No Open Graph image. Custom domain comes later (Vercel → Settings → Domains).
- Product roadmap: ATLAS market data (read-only, once LayerZero publishes an interface), signing page, OFT bridging quotes.
- Out of scope by owner decision: anything with legal or licensing risk, e.g. trading or order preparation for tokenized stocks, agent trading mandates, licensed exchange price data. Stock tools show token supply and holdings only, never prices.
- Merged branches that can be deleted: `claude/mcp-core`, `site/v1`, `site/v2`.

## Conventions
- Keep every tool read-only. Copy must be honest: no made-up data, and mark unknowns (e.g. Zero chain IDs "tba").
- Not affiliated with LayerZero Labs; the footer says so.
