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
  const rise = { yPercent: 0, opacity: 1, filter: "blur(0px)", duration: 1.1, ease: "expo.out", stagger: 0.1 };
  tl.fromTo(cap.querySelector(".fc-k"), { opacity: 0, y: 12, letterSpacing: "0.5em" }, { opacity: 1, y: 0, letterSpacing: "0.24em", duration: 1, ease: "expo.out" }, at);
  tl.fromTo(line1!.querySelectorAll(".w > span"), { y: 0, yPercent: 105, opacity: 0, filter: "blur(12px)" }, rise, at + 0.15);
  tl.fromTo(line2!.querySelectorAll(".w > span"), { y: 0, yPercent: 105, opacity: 0, filter: "blur(12px)" }, rise, at + 0.4);
  tl.to(cap, { opacity: 0, y: -30, filter: "blur(14px)", duration: 0.8, ease: "power2.in" }, at + hold);
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

  const label = new URLSearchParams(location.search).get("label");
  if (label) {
    const el = document.createElement("div");
    el.textContent = label;
    el.style.cssText = "position:fixed;left:0;right:0;bottom:4vh;z-index:9;text-align:center;font:600 3.2vh 'Familjen Grotesk',sans-serif;color:#ff5b1f;letter-spacing:0.02em";
    document.body.appendChild(el);
  }
  p.prepareIntro(14, 0);
  p.start();

  p.push = 2.6; // dive deep into each storm
  const tl = gsap.timeline({ paused: true });

  // 1 · drifting dust gathers into the logo; the name settles beneath it
  tl.call(() => p.swirl(0.7), [], 0);
  tl.call(() => void p.assemble(2.4), [], 0.2);
  tl.call(() => p.swirl(0), [], 1.5);
  tl.fromTo("#mark", { opacity: 0, letterSpacing: "1em" }, { opacity: 1, letterSpacing: "0.42em", duration: 1.2, ease: "expo.out" }, 1.6);
  tl.to("#mark", { opacity: 0, filter: "blur(10px)", duration: 0.4, ease: "power2.in" }, 2.55);

  // 2 · the logo becomes the network; ?intro= picks how (previews), default "flow"
  const intro = new URLSearchParams(location.search).get("intro") ?? "flow";
  if (intro === "flow") {
    // no storm, no light: every particle arcs from the logo straight to its place in the network
    p.push = 1.2;
    tl.call(() => {
      p.setDirect(1);
      p.jump(14, 0, 0);
      void p.glide(1, 2.6);
    }, [], 2.7);
    tl.call(() => {
      p.setDirect(0);
      p.push = 2.6;
    }, [], 5.4);
  } else if (intro === "fly") {
    // the camera dives into the logo's core, stars rush past, and pulls back out of the network
    const cam = { z: 11 };
    const setCam = () => (p.camZ = cam.z);
    tl.to(cam, { z: 0.9, duration: 1.15, ease: "power3.in", onUpdate: setCam }, 2.65);
    tl.call(() => p.jump(14, 0, 1), [], 3.8);
    tl.to(cam, { z: 11, duration: 1.9, ease: "expo.out", onUpdate: setCam, onComplete: () => (p.camZ = null) }, 3.8);
  } else if (intro === "vortex") {
    // the earlier vortex, without the light
    tl.call(() => {
      p.swirl(3.2);
      void p.open(3.0);
    }, [], 2.75);
  } else {
    // big bang: collapse into a white-hot point, then explode with shockwave rings
    const pinch = { v: 0 };
    const setPinch = () => p.setPinch(pinch.v);
    tl.call(() => p.swirl(1.6), [], 2.6);
    tl.to(pinch, { v: 1, duration: 0.55, ease: "power3.in", onUpdate: setPinch }, 2.65);
    tl.fromTo("#core", { opacity: 0, scale: 0.15 }, { opacity: 1, scale: 0.55, duration: 0.5, ease: "power3.in" }, 2.7);
    tl.call(() => {
      p.jump(14, 0, 0.5);
      p.swirl(3.4);
      void p.glide(1, 2.4);
    }, [], 3.2);
    tl.to(pinch, { v: 0, duration: 0.9, ease: "expo.out", onUpdate: setPinch }, 3.2);
    tl.to("#core", { opacity: 0, scale: 1.8, duration: 0.45, ease: "power2.out" }, 3.2);
    tl.fromTo("#ring1", { opacity: 1, scale: 0.05 }, { opacity: 0, scale: 4.2, duration: 1.3, ease: "expo.out" }, 3.2);
    tl.fromTo("#ring2", { opacity: 0.9, scale: 0.05 }, { opacity: 0, scale: 3, duration: 1.5, ease: "expo.out" }, 3.34);
  }
  tl.call(() => p.swirl(0), [], 4.6);
  tl.to(["#brand", "#date"], { opacity: 1, duration: 1, ease: "power2.out" }, 5.2);
  caption(tl, 5.0, 3.0, "Your AI × LayerZero", "Every chain.", "One conversation.");
  for (let t = 4.8, i = 0; t < 8.6; t += 0.28, i++) {
    const [a, b] = routes[i % routes.length]!;
    tl.call(() => p.pulse(a, b, i % 5 !== 0), [], t);
  }

  // 3 · into the vortex again, out into Zero's orbits
  tl.call(() => {
    p.swirl(-2.8);
    void p.morph(0, 7, 3.0);
  }, [], 8.3);
  tl.call(() => p.swirl(0), [], 9.8);
  caption(tl, 10.7, 2.9, "Zero mainnet", "Built for Zero.", "Opens November 30.");

  // 4 · back into the logo, the name and the date
  tl.call(() => {
    p.swirl(3);
    void p.morph(7, 13, 3.0);
  }, [], 13.8);
  tl.call(() => p.swirl(0), [], 15.3);
  tl.to(["#brand", "#date"], { opacity: 0, duration: 0.7 }, 14.0);
  $("end-name").innerHTML = wordsHtml("Plexa");
  tl.fromTo("#end-name .w > span", { y: 0, yPercent: 105, filter: "blur(10px)" }, { yPercent: 0, filter: "blur(0px)", duration: 1.3, ease: "expo.out" }, 16.2);
  tl.fromTo("#end-line", { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.9, ease: "power2.out" }, 16.7);
  tl.fromTo("#end-date", { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.9, ease: "power2.out" }, 17.1);
  tl.to({}, { duration: 1.2 }, 18.0); // a short hold on the last frame

  window.filmDuration = tl.duration();
  window.filmStart = () => void tl.play(0);
  window.filmReady = true;
})();
