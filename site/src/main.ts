import gsap from "gsap";
import "./styles.css";
import { initConnect, initCountdown, initRead, initSimulate, initStocks, initTools, initTrack, initTrust, initZro } from "./demos";
import { bindFeed, LiveFeed, ZERO_AT_DEFAULT } from "./live";
import { initMotion, revealHero, whenVisible } from "./motion";
import { initNav } from "./nav";
import type { Plexus } from "./scene/plexus";

const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const narrow = innerWidth < 900;
const $ = (id: string) => document.getElementById(id)!;

// Content first: everything works without WebGL.
initNav();
initConnect();
initTools();
const read = initRead();
const sim = initSimulate();
const track = initTrack();
const trust = initTrust();
const zro = initZro();
const stocks = initStocks();

let plexus: Plexus | null = null;
const chapters = initMotion(reduced, (v) => plexus?.setVelocity(v));

const feed = new LiveFeed();
let autoTracked = false;
bindFeed(feed, $("feed-list"), $("blocks"), $("feed-meta"), (tx) => void track.track(tx));
initCountdown(() => feed.last?.zero.mainnetAt ?? ZERO_AT_DEFAULT);
feed.start();

// Auto-run each live demo once, the first time it scrolls into view.
whenVisible($("demo-read"), () => void read.run());
whenVisible($("console"), () => void sim.run());
whenVisible($("demo-trust"), () => void trust.run());
whenVisible($("zro-panel"), () => void zro.load(), "top bottom");
whenVisible($("demo-stocks"), () => void stocks.run());
whenVisible($("timeline"), () => {
  const pick = () => {
    const m = feed.last?.messages.find((x) => x.status === "DELIVERED") ?? feed.last?.messages[0];
    if (m?.sourceTx && !autoTracked) {
      autoTracked = true;
      void track.track(m.sourceTx);
    }
  };
  pick();
  if (!autoTracked) feed.on(() => pick());
}, "top bottom");

// Loader: count up while the 3D scene loads, then assemble the plexus.
const num = $("loader-num");
const bar = $("loader-bar");
let shown = 0;
let target = 30;
const loaderTick = () => {
  shown += (target - shown) * 0.12 + 0.4;
  if (shown > target) shown = target;
  num.textContent = String(Math.floor(shown)).padStart(3, "0");
  bar.style.transform = `scaleX(${shown / 100})`;
  if (shown < 100) requestAnimationFrame(loaderTick);
  else finish();
};
requestAnimationFrame(loaderTick);

let finished = false;
function finish() {
  if (finished) return;
  finished = true;
  setTimeout(() => {
    document.body.classList.remove("is-loading");
    plexus?.intro();
    revealHero(reduced);
    // arriving with a chapter link (e.g. /#connect from another page)
    if (chapters.paged && location.hash.length > 1) {
      const target = document.querySelector<HTMLElement>(location.hash);
      if (target) setTimeout(() => chapters.scrollTo(target), 900);
    }
  }, 180);
}

(async () => {
  await document.fonts.ready;
  target = 60;
  try {
    const { createPlexus } = await import("./scene/plexus");
    plexus = createPlexus($("gl") as HTMLCanvasElement, { count: narrow ? 3200 : 9000, reduced, labels: $("node-labels") });
    if (plexus) {
      plexus.start();
      chapters.onTransition((a, c, t) => plexus!.setTransition(a, c, t));
      if (chapters.paged) {
        // page turns: the particles draw the incoming page, then hand it to the real one
        const p = plexus;
        const { samplePage } = await import("./scene/glyphs");
        const glyph = { v: 0 };
        const apply = () => p.setGlyph(glyph.v);
        let tl: gsap.core.Timeline | null = null;
        chapters.setParticles({
          assemble(section, delay) {
            const points = samplePage(section, p.glyphBudget);
            tl?.kill();
            tl = gsap.timeline();
            if (glyph.v > 0.001) tl.to(glyph, { v: 0, duration: 0.2, ease: "power1.in", onUpdate: apply });
            tl.call(() => p.setGlyphs(points));
            tl.to(glyph, { v: 1, duration: 0.58, ease: "power3.out", onUpdate: apply }, `+=${delay}`);
          },
          release() {
            tl?.kill();
            tl = gsap.timeline().to(glyph, { v: 0, duration: 0.9, ease: "power2.in", onUpdate: apply });
          },
        });
      }
      // pulses: every fresh message, plus a slow replay so the network never sleeps
      feed.on((s, fresh) => fresh.slice(0, 8).forEach((m, k) => setTimeout(() => plexus?.pulse(m.from, m.to, m.status === "DELIVERED"), k * 420)));
      setInterval(() => {
        const list = feed.last?.messages;
        if (!list?.length || document.hidden) return;
        const m = list[Math.floor(Math.random() * list.length)]!;
        plexus?.pulse(m.from, m.to, m.status === "DELIVERED");
      }, 900);
    } else {
      $("gl").style.display = "none";
    }
  } catch (e) {
    console.error("3D scene failed to load", e);
    $("gl").style.display = "none";
  }
  target = 100;
})();
