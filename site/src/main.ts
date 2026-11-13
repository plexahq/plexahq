import "./styles.css";
import { initConnect, initCountdown, initRead, initSimulate, initTools, initTrack } from "./demos";
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
