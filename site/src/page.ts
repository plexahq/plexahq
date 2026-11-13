import "./styles.css";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { initConnect } from "./demos";
import { LiveFeed } from "./live";
import { initMotion } from "./motion";
import { initNav } from "./nav";
import type { Plexus, View } from "./scene/plexus";

/**
 * Sub-pages (product, docs, stats, company, contact): shared nav, motion and an ambient scene.
 * Each page names a hero formation and an ambient one; scrolling past the hero morphs between them.
 */
const page = document.body.dataset.page ?? "";
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const narrow = innerWidth < 900;

const SCENES: Record<string, { hero: number; ambient: number; tweak?: (v: View[]) => void }> = {
  product: { hero: 0, ambient: 10 },
  docs: { hero: 8, ambient: 8, tweak: (v) => (v[8] = { ...v[8]!, opacity: 0.3 }) },
  stats: { hero: 0, ambient: 10, tweak: (v) => (v[10] = { ...v[10]!, opacity: 0.35 }) },
  company: { hero: 7, ambient: 10 },
  contact: { hero: 10, ambient: 10, tweak: (v) => (v[10] = { ...v[10]!, opacity: 0.5 }) },
};

initNav();
initConnect();
let plexus: Plexus | null = null;
initMotion(reduced, (v) => plexus?.setVelocity(v));

const needsFeed = page === "stats" || page === "product";
const feed = needsFeed ? new LiveFeed(page === "stats" ? "/api/live?messages=50" : "/api/live") : null;

if (page === "docs") void import("./pages/docs").then((m) => m.initDocs());
if (page === "stats" && feed) void import("./pages/stats").then((m) => m.initStats(feed));
if (page === "contact") void import("./pages/contact").then((m) => m.initContact());
feed?.start();

(async () => {
  const cfg = SCENES[page];
  if (!cfg) return;
  try {
    const { createPlexus, VIEWS } = await import("./scene/plexus");
    const views = VIEWS.map((v) => ({ ...v }));
    cfg.tweak?.(views);
    plexus = createPlexus(document.getElementById("gl") as HTMLCanvasElement, {
      count: narrow ? 2800 : 7000,
      reduced,
      labels: document.getElementById("node-labels")!,
      views,
    });
    if (!plexus) {
      document.getElementById("gl")!.style.display = "none";
      return;
    }
    plexus.setTransition(cfg.hero, cfg.ambient, 0);
    plexus.start();
    plexus.intro();
    const hero = document.querySelector<HTMLElement>(".page-hero");
    if (hero && cfg.hero !== cfg.ambient) {
      ScrollTrigger.create({
        trigger: hero,
        start: "top top",
        end: "bottom top",
        onUpdate: (self) => plexus?.setTransition(cfg.hero, cfg.ambient, self.progress),
      });
    }
    if (feed) {
      feed.on((_s, fresh) => fresh.slice(0, 8).forEach((m, k) => setTimeout(() => plexus?.pulse(m.from, m.to, m.status === "DELIVERED"), k * 420)));
      setInterval(() => {
        const list = feed.last?.messages;
        if (!list?.length || document.hidden) return;
        const m = list[Math.floor(Math.random() * list.length)]!;
        plexus?.pulse(m.from, m.to, m.status === "DELIVERED");
      }, 900);
    }
  } catch (e) {
    console.error("3D scene failed to load", e);
    document.getElementById("gl")!.style.display = "none";
  }
})();
