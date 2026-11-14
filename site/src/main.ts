import "./styles.css";
import { initConnect, initCountdown, initRead, initSimulate, initStocks, initTools, initTrack, initTrust, initZro } from "./demos";
import { bindFeed, LiveFeed, ZERO_AT_DEFAULT } from "./live";
import { startScene } from "./intro";
import { initMotion, whenVisible } from "./motion";
import { initNav } from "./nav";
import type { Plexus } from "./scene/plexus";

const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
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

// Intro and 3D scene (see intro.ts); everything above works without WebGL.
void startScene({ chapters, reduced, feed, onReady: (p) => (plexus = p) });
