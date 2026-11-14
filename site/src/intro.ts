import type { Chapters } from "./motion";
import { revealHero } from "./motion";
import type { LiveFeed } from "./live";
import type { Plexus } from "./scene/plexus";

/**
 * Shared opening for the home page and the teaser. The loader's mark draws itself while the
 * 3D scene loads; then the stardust gathers into the logo, the logo bursts, and the storm
 * settles into the hero as the page opens. Any scroll, tap or key skips ahead.
 */

const INTRO_LOGO = 14; // the intro view in scene/plexus.ts VIEWS
const SKIP_EVENTS = ["wheel", "touchstart", "keydown", "pointerdown"];
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export interface SceneOptions {
  chapters: Chapters;
  reduced: boolean;
  /** Chapter index → scene formation index, when a page's chapters don't follow the home order. */
  map?: number[];
  /** Live LayerZero messages pulse along the hero's threads. */
  feed?: LiveFeed;
  onReady?: (plexus: Plexus) => void;
}

export function startScene(o: SceneOptions): Promise<Plexus | null> {
  const $ = (id: string) => document.getElementById(id)!;
  const narrow = innerWidth < 900;
  const map = (i: number) => o.map?.[i] ?? i;
  const t0 = performance.now();
  let plexus: Plexus | null = null;
  let opened = false;
  o.chapters.lenis?.stop();

  const skip = () => {
    if (performance.now() - t0 > 400) openPage();
  };
  for (const ev of SKIP_EVENTS) addEventListener(ev, skip, { passive: true });

  function openPage() {
    if (opened) return;
    opened = true;
    for (const ev of SKIP_EVENTS) removeEventListener(ev, skip);
    document.body.classList.remove("is-loading");
    o.chapters.lenis?.start();
    if (plexus && !o.reduced) {
      void plexus.open(1.6);
      setTimeout(() => revealHero(o.reduced), 620);
    } else {
      plexus?.intro();
      revealHero(o.reduced);
    }
  }

  return (async () => {
    await document.fonts.ready;
    try {
      const { createPlexus } = await import("./scene/plexus");
      plexus = createPlexus($("gl") as HTMLCanvasElement, { count: narrow ? 5200 : 9000, reduced: o.reduced, labels: $("node-labels") });
      if (plexus) {
        const p = plexus;
        // skipped before the scene was ready: just let the stardust settle into the hero
        if (opened) p.intro();
        else if (!o.reduced) p.prepareIntro(INTRO_LOGO, map(0));
        p.start();
        o.chapters.onTransition((a, c, t) => p.setTransition(map(a), map(c), t));
        if (o.feed) {
          // pulses: every fresh message, plus a slow replay so the network never sleeps
          o.feed.on((_, fresh) => fresh.slice(0, 8).forEach((m, k) => setTimeout(() => p.pulse(m.from, m.to, m.status === "DELIVERED"), k * 420)));
          setInterval(() => {
            const list = o.feed?.last?.messages;
            if (!list?.length || document.hidden) return;
            const m = list[Math.floor(Math.random() * list.length)]!;
            p.pulse(m.from, m.to, m.status === "DELIVERED");
          }, 900);
        }
        o.onReady?.(p);
      } else {
        $("gl").style.display = "none";
      }
    } catch (e) {
      console.error("3D scene failed to load", e);
      $("gl").style.display = "none";
      plexus = null;
    }
    // give the mark a moment to draw itself
    await sleep(Math.max(0, 950 - (performance.now() - t0)));
    if (!opened) {
      if (plexus && !o.reduced) {
        document.body.classList.add("intro-assemble");
        await plexus.assemble(1.55);
        await sleep(220);
      }
      openPage();
    }
    return plexus;
  })();
}
