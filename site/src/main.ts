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

// Intro: the mark draws itself while the 3D scene loads; then the stardust gathers into the
// logo, the logo bursts, and the storm settles into the hero as the page opens.
const INTRO_LOGO = 14; // the intro view in scene/plexus.ts VIEWS
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const t0 = performance.now();
let opened = false;
chapters.lenis?.stop();

const SKIP_EVENTS = ["wheel", "touchstart", "keydown", "pointerdown"];
// impatient visitors: any scroll, tap or key during the intro opens the page at once
const skip = () => {
  if (performance.now() - t0 > 400) openPage();
};
for (const ev of SKIP_EVENTS) addEventListener(ev, skip, { passive: true });

function openPage() {
  if (opened) return;
  opened = true;
  for (const ev of SKIP_EVENTS) removeEventListener(ev, skip);
  document.body.classList.remove("is-loading");
  chapters.lenis?.start();
  if (plexus && !reduced) {
    void plexus.open(1.6);
    setTimeout(() => revealHero(reduced), 620);
  } else {
    plexus?.intro();
    revealHero(reduced);
  }
}

(async () => {
  await document.fonts.ready;
  try {
    const { createPlexus } = await import("./scene/plexus");
    plexus = createPlexus($("gl") as HTMLCanvasElement, { count: narrow ? 5200 : 9000, reduced, labels: $("node-labels") });
    if (plexus) {
      // skipped before the scene was ready: just let the stardust settle into the hero
      if (opened) plexus.intro();
      else if (!reduced) plexus.prepareIntro(INTRO_LOGO, 0);
      plexus.start();
      chapters.onTransition((a, c, t) => plexus!.setTransition(a, c, t));
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
    plexus = null;
  }
  // give the mark a moment to draw itself
  await sleep(Math.max(0, 950 - (performance.now() - t0)));
  if (opened) return;
  if (plexus && !reduced) {
    document.body.classList.add("intro-assemble");
    await plexus.assemble(1.55);
    await sleep(220);
  }
  openPage();
})();
