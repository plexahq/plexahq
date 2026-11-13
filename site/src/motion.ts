import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";

gsap.registerPlugin(ScrollTrigger);

/** Wraps every word of an element in .split-line > span, keeping inline elements (em, b) and <br>. */
export function splitWords(el: HTMLElement) {
  const walk = (node: Node) => {
    for (const child of [...node.childNodes]) {
      if (child.nodeType === Node.TEXT_NODE) {
        const parts = (child.textContent ?? "").split(/(\s+)/);
        const frag = document.createDocumentFragment();
        for (const part of parts) {
          if (!part) continue;
          if (/^\s+$/.test(part)) frag.appendChild(document.createTextNode(" "));
          else {
            const outer = document.createElement("span");
            outer.className = "split-line";
            outer.style.display = "inline-block";
            const inner = document.createElement("span");
            inner.textContent = part;
            outer.appendChild(inner);
            frag.appendChild(outer);
          }
        }
        child.replaceWith(frag);
      } else if (child.nodeType === Node.ELEMENT_NODE && (child as Element).tagName !== "BR") {
        walk(child);
      }
    }
  };
  walk(el);
}

const GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789·/#%&*+=<>";

/** Decodes a label from random glyphs into its text, left to right. */
export function scramble(el: HTMLElement, duration = 900) {
  const final = el.textContent ?? "";
  const start = performance.now();
  const step = (now: number) => {
    const p = Math.min(1, (now - start) / duration);
    const fixed = Math.floor(final.length * p);
    let out = final.slice(0, fixed);
    for (let i = fixed; i < final.length; i++) out += final[i] === " " ? " " : GLYPHS[Math.floor(Math.random() * GLYPHS.length)];
    el.textContent = out;
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

export interface Chapters {
  onChange(fn: (i: number, name: string) => void): void;
  onTransition(fn: (a: number, c: number, t: number) => void): void;
  scrollTo(target: string | HTMLElement): void;
  lenis: Lenis | null;
}

export function initMotion(reduced: boolean, onVelocity: (v: number) => void): Chapters {
  const lenis = reduced ? null : new Lenis({ lerp: 0.09, wheelMultiplier: 0.95 });
  if (lenis) {
    lenis.on("scroll", (e: Lenis) => {
      ScrollTrigger.update();
      onVelocity(e.velocity);
    });
    gsap.ticker.add((t) => lenis.raf(t * 1000));
    gsap.ticker.lagSmoothing(0);
  } else {
    document.documentElement.classList.add("reduced");
  }

  // headings: split into words now, animate when they enter
  document.querySelectorAll<HTMLElement>("[data-split]").forEach((el) => {
    splitWords(el);
    if (reduced) return;
    const words = el.querySelectorAll(".split-line > span");
    const isHero = !!el.closest("#hero");
    if (isHero) return; // the hero plays after the loader (see revealHero)
    gsap.to(words, {
      y: 0,
      duration: 1.15,
      ease: "expo.out",
      stagger: 0.045,
      scrollTrigger: { trigger: el, start: "top 86%", once: true },
    });
  });

  if (!reduced) {
    document.querySelectorAll<HTMLElement>(".kicker").forEach((el) =>
      ScrollTrigger.create({ trigger: el, start: "top 88%", once: true, onEnter: () => scramble(el) }),
    );
    ScrollTrigger.batch("[data-reveal]:not(#hero [data-reveal])", {
      start: "top 90%",
      once: true,
      onEnter: (els) => gsap.to(els, { opacity: 1, y: 0, duration: 1.1, ease: "expo.out", stagger: 0.08, overwrite: true }),
    });
  }

  // nav hides on the way down, returns on the way up
  const nav = document.getElementById("nav")!;
  let lastY = 0;
  const onScroll = () => {
    const y = window.scrollY;
    nav.classList.toggle("is-hidden", y > 200 && y > lastY + 2);
    if (y < lastY - 2 || y < 200) nav.classList.remove("is-hidden");
    lastY = y;
  };
  window.addEventListener("scroll", onScroll, { passive: true });

  const scrollTo = (target: string | HTMLElement) => {
    const el = typeof target === "string" ? document.querySelector<HTMLElement>(target) : target;
    if (!el) return;
    if (lenis) lenis.scrollTo(el, { offset: 0, duration: 1.6 });
    else el.scrollIntoView();
  };
  // in-page links (#x, and /#x while on the home page) glide instead of jumping
  const onHome = location.pathname === "/" || location.pathname.endsWith("/index.html");
  document.querySelectorAll<HTMLAnchorElement>('a[href^="#"], a[href^="/#"]').forEach((a) =>
    a.addEventListener("click", (e) => {
      const href = a.getAttribute("href")!;
      const id = href.startsWith("/#") ? (onHome ? href.slice(1) : "") : href;
      if (id.length < 2 || !document.querySelector(id)) return;
      e.preventDefault();
      document.dispatchEvent(new CustomEvent("plexa:navigate"));
      scrollTo(id);
    }),
  );

  // chapters (home page only): HUD, rail, scroll-scrubbed scene transitions
  const sections = [...document.querySelectorAll<HTMLElement>("[data-chapter]")];
  const listeners: ((i: number, name: string) => void)[] = [];
  const tListeners: ((a: number, c: number, t: number) => void)[] = [];
  let lastT: [number, number, number] = [0, 1, 0];
  let active = -1;
  const rail = document.getElementById("rail");
  if (sections.length && rail) {
    const hudNum = document.getElementById("hud-num")!;
    const hudName = document.getElementById("hud-name")!;
    const hudBar = document.getElementById("hud-bar")!;
    rail.innerHTML = sections.map((s, i) => `<button type="button" aria-label="${s.dataset.name}" data-go="${i}"><i></i></button>`).join("");
    const dots = [...rail.querySelectorAll("button")];
    dots.forEach((d, i) => d.addEventListener("click", () => scrollTo(sections[i]!)));
    const setActive = (i: number) => {
      if (i === active) return;
      active = i;
      const name = sections[i]!.dataset.name ?? "";
      hudNum.textContent = String(i).padStart(2, "0");
      hudName.textContent = name;
      dots.forEach((d, k) => d.classList.toggle("on", k === i));
      document.body.classList.toggle("hero-active", i === 0);
      for (const fn of listeners) fn(i, name);
    };
    sections.forEach((s, i) =>
      ScrollTrigger.create({ trigger: s, start: "top 55%", end: "bottom 55%", onToggle: (self) => self.isActive && setActive(i) }),
    );
    // As section k rises from the bottom of the screen to near the top, the scene travels
    // from formation k-1, through the full-screen storm, into formation k.
    const emitT = (a: number, c: number, t: number) => {
      lastT = [a, c, t];
      for (const fn of tListeners) fn(a, c, t);
    };
    sections.forEach((s, k) => {
      if (k === 0) return;
      ScrollTrigger.create({
        trigger: s,
        start: "top bottom",
        end: "top 22%",
        onUpdate: (self) => emitT(k - 1, k, self.progress),
        onLeave: () => emitT(k - 1, k, 1),
        onLeaveBack: () => emitT(k - 1, k, 0),
      });
    });
    let state: [number, number, number] = [0, 1, 0];
    sections.forEach((s, k) => {
      const top = s.getBoundingClientRect().top;
      if (k > 0 && top < innerHeight) state = [k - 1, k, Math.min(1, (innerHeight - top) / (innerHeight * 0.78))];
    });
    emitT(...state);
    ScrollTrigger.create({ start: 0, end: "max", onUpdate: (self) => gsap.set(hudBar, { scaleX: self.progress }) });
    setActive(0);
  }

  return {
    onTransition(fn) {
      tListeners.push(fn);
      fn(...lastT);
    },
    onChange(fn) {
      listeners.push(fn);
      if (active >= 0) fn(active, sections[active]?.dataset.name ?? "");
    },
    scrollTo,
    lenis,
  };
}

/** Hero entrance after the loader lifts. */
export function revealHero(reduced: boolean) {
  const words = document.querySelectorAll("#hero [data-split] .split-line > span");
  const items = document.querySelectorAll("#hero [data-reveal]");
  if (reduced) return;
  const tl = gsap.timeline({ delay: 0.15 });
  tl.to(words, { y: 0, duration: 1.4, ease: "expo.out", stagger: 0.07 })
    .to(items, { opacity: 1, y: 0, duration: 1.2, ease: "expo.out", stagger: 0.1 }, "-=1.0")
    .fromTo(".nav", { yPercent: -100 }, { yPercent: 0, y: 0, duration: 1, ease: "expo.out", clearProps: "transform" }, "-=1.2");
}

/** Fire `fn` once when `el` first scrolls into view. */
export function whenVisible(el: HTMLElement, fn: () => void, start = "top 70%") {
  ScrollTrigger.create({ trigger: el, start, once: true, onEnter: fn });
}
