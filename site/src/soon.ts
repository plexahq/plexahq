import "./styles.css";
import { initCountdown } from "./demos";
import { startScene } from "./intro";
import { LiveFeed, ZERO_AT_DEFAULT } from "./live";
import { initMotion } from "./motion";
import { initNav } from "./nav";
import type { Plexus } from "./scene/plexus";

/**
 * Pre-launch teaser: a short page that says what Plexa is, with the stardust intro, until the
 * full site opens at Zero mainnet. Everything not open yet (docs, product, stats…) spins the
 * stardust into a vortex and says when it opens.
 */

/** The X profile for launch news. Empty until the account exists, which keeps the X buttons hidden. */
const X_URL = "";

/** Chapter → scene formation: plexus sphere, convergence, verifier shield, orbits, logo. */
const SCENE = [0, 2, 6, 7, 13];

const LABELS: Record<string, string> = {
  "/product": "Product",
  "/docs": "Docs",
  "/stats": "Live stats",
  "/company": "Company",
  "/contact": "Contact",
  "/#connect": "Connect your AI",
};

const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const $ = (id: string) => document.getElementById(id)!;

initNav();
let plexus: Plexus | null = null;
const chapters = initMotion(reduced, (v) => plexus?.setVelocity(v));
const feed = new LiveFeed();
feed.start();
initCountdown(() => feed.last?.zero.mainnetAt ?? ZERO_AT_DEFAULT);
void startScene({ chapters, reduced, map: SCENE, feed, onReady: (p) => (plexus = p) });

// X: shown only once there is an account to point at
document.querySelectorAll<HTMLAnchorElement>(".js-x").forEach((a) => {
  if (!X_URL) return;
  a.href = X_URL;
  a.target = "_blank";
  a.rel = "noopener";
  a.hidden = false;
});
document.querySelectorAll<HTMLElement>(".js-x-soon").forEach((el) => (el.hidden = Boolean(X_URL)));

// "Opens at Zero mainnet"
const veil = $("soon-veil");
let closeTimer = 0;

function untilLaunch(): string {
  const at = new Date(feed.last?.zero.mainnetAt ?? ZERO_AT_DEFAULT).getTime();
  const ms = Math.max(0, at - Date.now());
  if (ms === 0) return "Opening now";
  const d = Math.floor(ms / 86_400_000);
  const h = Math.floor(ms / 3_600_000) % 24;
  const parts = [d ? `${d} day${d === 1 ? "" : "s"}` : "", `${h} hour${h === 1 ? "" : "s"}`].filter(Boolean);
  return `In ${parts.join(" ")} · Nov 30, 2026`;
}

function showSoon(label: string) {
  clearTimeout(closeTimer);
  $("soon-k").textContent = label;
  $("soon-when").textContent = untilLaunch();
  veil.hidden = false;
  requestAnimationFrame(() => document.body.classList.add("soon-open"));
  plexus?.vortex(true);
  chapters.lenis?.stop();
  $("soon-close").focus({ preventScroll: true });
}

function hideSoon() {
  if (!document.body.classList.contains("soon-open")) return;
  document.body.classList.remove("soon-open");
  plexus?.vortex(false);
  chapters.lenis?.start();
  closeTimer = window.setTimeout(() => (veil.hidden = true), 700);
}

// capture phase: decide before the page's own link handling does
document.addEventListener(
  "click",
  (e) => {
    const a = (e.target as HTMLElement).closest<HTMLAnchorElement>("a[href]");
    if (!a) return;
    const href = a.getAttribute("href")!;
    const label = LABELS[href];
    if (label) {
      e.preventDefault();
      document.dispatchEvent(new CustomEvent("plexa:navigate"));
      showSoon(label);
    } else if (href === "/") {
      e.preventDefault();
      hideSoon();
      chapters.scrollTo("#hero");
    }
  },
  true,
);
$("soon-close").addEventListener("click", hideSoon);
veil.addEventListener("click", (e) => {
  if (!(e.target as HTMLElement).closest(".btn")) hideSoon();
});
document.addEventListener("keydown", (e) => e.key === "Escape" && hideSoon());
