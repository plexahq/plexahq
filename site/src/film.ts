import "./styles.css";
import gsap from "gsap";
import { createPlexus, VIEWS, type View } from "./scene/plexus";

/**
 * The X launch video, as a page: a fixed GSAP timeline drives the particle scene and the
 * captions. scripts/film.cjs runs it under a fake clock and captures it frame by frame,
 * so the result is smooth at any render speed. Dev server only (not in the site build).
 */

declare global {
  interface Window {
    filmReady?: boolean;
    filmDuration?: number;
    filmStart?: () => void;
  }
}

const $ = (id: string) => document.getElementById(id)!;
const wide = innerWidth / innerHeight > 1.3;
const k = wide ? 1 : 1.55; // squarer frames: bigger formations

// every formation centred, a little above the captions, no text mask
const views: View[] = VIEWS.map((v) => ({ ...v }));
const place = (i: number, o: Partial<View>) => (views[i] = { ...views[i]!, x: 0, mask: 0, ...o, scale: (o.scale ?? views[i]!.scale) * k });
place(14, { y: 0.1, scale: 0.72, spin: 0, opacity: 1 }); // logo
place(0, { y: 0.15, scale: 0.9, graph: 1, labels: 1, opacity: 1 }); // plexus sphere
place(5, { y: 0.16, scale: 1.08, rotX: 0.62, graph: 2, labels: 1, opacity: 0.95 }); // cross-chain ring, tilted open
place(6, { y: 0.15, scale: 0.86, opacity: 1 }); // verifier shield
place(8, { y: 0.14, scale: 0.98, opacity: 1 }); // candles
place(7, { y: 0.15, scale: 0.88, opacity: 0.95 }); // Zero orbits
place(13, { y: 0.14, scale: 0.6, spin: 0, opacity: 1 }); // closing logo

const wordsHtml = (text: string) =>
  text
    .split(" ")
    .map((w) => `<span class="w"><span>${w}</span></span>`)
    .join(" ");

/**
 * A caption: kicker, then two lines whose words rise in; it leaves by lifting and blurring away.
 * Each caption gets its own elements up front, because GSAP resolves its targets when the
 * timeline is built.
 */
function caption(tl: gsap.core.Timeline, at: number, hold: number, kicker: string, l1: string, l2: string) {
  const cap = document.createElement("div");
  cap.className = "film-cap";
  cap.innerHTML = `<p class="fc-k">${kicker}</p><p class="fc-l">${wordsHtml(l1)}</p><p class="fc-l sig">${wordsHtml(l2)}</p>`;
  document.body.appendChild(cap);
  const [line1, line2] = cap.querySelectorAll(".fc-l");
  tl.fromTo(cap.querySelector(".fc-k"), { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.6, ease: "power2.out" }, at);
  tl.fromTo(line1!.querySelectorAll(".w > span"), { y: 0, yPercent: 110 }, { yPercent: 0, duration: 0.9, ease: "expo.out", stagger: 0.07 }, at + 0.12);
  tl.fromTo(line2!.querySelectorAll(".w > span"), { y: 0, yPercent: 110 }, { yPercent: 0, duration: 0.9, ease: "expo.out", stagger: 0.07 }, at + 0.32);
  tl.to(cap, { opacity: 0, y: -24, filter: "blur(10px)", duration: 0.55, ease: "power2.in" }, at + hold);
}

(async () => {
  await document.fonts.ready;
  const p = createPlexus($("gl") as HTMLCanvasElement, { count: 9000, reduced: false, labels: $("node-labels"), views });
  if (!p) throw new Error("WebGL unavailable");

  // real recent LayerZero routes for the pulses along the threads
  let routes: [string, string][] = [["ethereum", "base"], ["arbitrum", "ethereum"], ["bsc", "arbitrum"], ["base", "optimism"], ["ethereum", "avalanche"], ["polygon", "bsc"]];
  try {
    const live = (await (await fetch("/api/live?messages=40")).json()) as { messages: { from: string; to: string }[] };
    const real = live.messages.map((m) => [m.from, m.to] as [string, string]).filter(([a, b]) => a && b && a !== b);
    if (real.length >= 6) routes = real;
  } catch {
    // keep the fallback routes
  }

  p.prepareIntro(14, 0);
  p.start();

  const tl = gsap.timeline({ paused: true });
  // 1 · dust gathers into the logo, the name appears beneath it
  tl.call(() => void p.assemble(2.4), [], 0.25);
  tl.fromTo("#mark", { opacity: 0, letterSpacing: "0.8em" }, { opacity: 1, letterSpacing: "0.42em", duration: 1.4, ease: "expo.out" }, 1.7);
  tl.to("#mark", { opacity: 0, filter: "blur(8px)", duration: 0.5, ease: "power2.in" }, 3.55);
  // 2 · the logo bursts into the storm and becomes the network
  tl.call(() => void p.open(1.7), [], 3.7);
  tl.to(["#brand", "#date"], { opacity: 1, duration: 1, ease: "power2.out" }, 4.6);
  caption(tl, 5.0, 2.5, "Your AI × LayerZero", "Every chain.", "One conversation.");
  // pulses along the sphere and the ring while they're on screen
  for (let t = 5.0, i = 0; t < 11.4; t += 0.32, i++) {
    const [a, b] = routes[i % routes.length]!;
    tl.call(() => p.pulse(a, b, i % 5 !== 0), [], t);
  }
  // 3 · cross-chain ring
  tl.call(() => void p.morph(0, 5, 1.5), [], 7.7);
  caption(tl, 8.9, 2.4, "LayerZero", "Every message,", "followed hop by hop.");
  // 4 · verifier shield
  tl.call(() => void p.morph(5, 6, 1.5), [], 11.5);
  caption(tl, 12.7, 2.3, "Trust check", "Who guards the bridge?", "Just ask.");
  // 5 · candles
  tl.call(() => void p.morph(6, 8, 1.5), [], 15.2);
  caption(tl, 16.4, 2.3, "Markets", "Wall Street,", "on-chain.");
  // 6 · Zero orbits
  tl.call(() => void p.morph(8, 7, 1.5), [], 18.9);
  caption(tl, 20.1, 2.3, "Zero", "Built for Zero.", "Ready on day one.");
  // 7 · back into the logo, the name and the date
  tl.call(() => void p.morph(7, 13, 1.7), [], 22.6);
  tl.to(["#brand", "#date"], { opacity: 0, duration: 0.6 }, 22.8);
  $("end-name").innerHTML = wordsHtml("Plexa");
  tl.fromTo("#end-name .w > span", { y: 0, yPercent: 110 }, { yPercent: 0, duration: 1.1, ease: "expo.out" }, 23.65);
  tl.fromTo("#end-line", { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.9, ease: "power2.out" }, 24.2);
  tl.fromTo("#end-date", { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.9, ease: "power2.out" }, 24.7);
  tl.to({}, { duration: 2.6 }, 25.0); // hold the last frame

  window.filmDuration = tl.duration();
  window.filmStart = () => void tl.play(0);
  window.filmReady = true;
})();
