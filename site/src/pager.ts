import gsap from "gsap";

/**
 * Page-by-page home: instead of scrolling the document, each chapter is a full-screen page
 * that dissolves into the particle storm while the next one is drawn by the particles and
 * then materialises in place. Chapters taller than the screen scroll inside themselves first.
 */

export interface PageParticles {
  /** The incoming page is laid out (transparent): sample it and start drawing it after `delay` seconds. */
  assemble(section: HTMLElement, delay: number): void;
  /** The real page is fading in: hand the particles back to the scene. */
  release(): void;
}

export interface PagerOptions {
  sections: HTMLElement[];
  nav: HTMLElement;
  /** Chapter HUD and rail. */
  onActive: (i: number) => void;
  /** Scene transition target (formation a → c at t). */
  emit: (a: number, c: number, t: number) => void;
  scramble: (el: HTMLElement) => void;
}

const DRAW_AT = 0.3;
const SHOW_AT = 1.02;
const SETTLE = 0.3;

/** True when the event target (up to the page) can still scroll in this direction. */
function canScroll(from: EventTarget | null, page: HTMLElement, dy: number): boolean {
  // over the nav, rail or HUD (outside the page) the wheel still means the page
  let el: Element | null = from instanceof Element && page.contains(from) ? from : page;
  while (el) {
    if (el instanceof HTMLElement && el.scrollHeight > el.clientHeight + 1) {
      const oy = el === page ? "auto" : getComputedStyle(el).overflowY;
      if (oy === "auto" || oy === "scroll") {
        if (dy > 0 && el.scrollTop + el.clientHeight < el.scrollHeight - 2) return true;
        if (dy < 0 && el.scrollTop > 1) return true;
      }
    }
    if (el === page) break;
    el = el.parentElement;
  }
  return false;
}

export class Pager {
  index = 0;
  private busy = false;
  private particles: PageParticles | null = null;
  private entered = new Set<number>([0]);
  private hooks = new Map<number, (() => void)[]>();
  private wheelAcc = 0;
  private lastWheel = 0;
  /** After a page turn or an inner scroll, wait for the gesture's inertia to die before turning again. */
  private guard = false;

  constructor(private o: PagerOptions) {
    o.sections.forEach((s, i) => s.classList.toggle("is-active", i === 0));
    window.addEventListener("wheel", this.onWheel, { passive: false });
    window.addEventListener("keydown", this.onKey);
    // inside a long page the nav hides on the way down and returns on the way up
    o.sections.forEach((s) => {
      let last = 0;
      let up = 0;
      s.addEventListener(
        "scroll",
        () => {
          const y = s.scrollTop;
          const dy = y - last;
          last = y;
          if (y < 60) {
            up = 0;
            o.nav.classList.remove("is-hidden");
          } else if (dy > 0) {
            up = 0;
            if (y > 120) o.nav.classList.add("is-hidden");
          } else if (dy < 0) {
            up -= dy;
            if (up > 24) o.nav.classList.remove("is-hidden");
          }
        },
        { passive: true },
      );
    });
  }

  setParticles(p: PageParticles | null) {
    this.particles = p;
  }

  get page(): HTMLElement {
    return this.o.sections[this.index]!;
  }

  indexOf(target: Element): number {
    return this.o.sections.findIndex((s) => s === target || s.contains(target));
  }

  /** Run `fn` once, the first time the page holding `el` has fully appeared. */
  whenEntered(el: Element, fn: () => void) {
    const i = this.indexOf(el);
    if (i < 0 || this.entered.has(i)) return void fn();
    const list = this.hooks.get(i) ?? [];
    list.push(fn);
    this.hooks.set(i, list);
  }

  private blocked(): boolean {
    const b = document.body.classList;
    return b.contains("is-loading") || b.contains("menu-open");
  }

  go(to: number): boolean {
    const n = this.o.sections.length;
    to = Math.max(0, Math.min(n - 1, to));
    if (to === this.index || this.busy) return false;
    const from = this.index;
    const dir = to > from ? 1 : -1;
    const out = this.o.sections[from]!;
    const inc = this.o.sections[to]!;
    this.busy = true;
    this.index = to;
    this.wheelAcc = 0;
    this.o.onActive(to);
    this.o.nav.classList.remove("is-hidden");
    // the scene travels to page `to`'s formation through the storm
    if (dir > 0) this.o.emit(to - 1, to, 1);
    else this.o.emit(to, to + 1, 0);

    // the outgoing page dissolves into the storm
    gsap.killTweensOf(out);
    gsap.to(out, {
      opacity: 0,
      filter: "blur(12px)",
      scale: 0.985,
      duration: 0.42,
      ease: "power2.in",
      onComplete: () => {
        out.classList.remove("is-active");
        gsap.set(out, { clearProps: "opacity,filter,transform" });
      },
    });

    // the incoming page is laid out invisibly, at its top (or its end, coming back up)
    gsap.killTweensOf(inc);
    gsap.set(inc, { opacity: 0, filter: "none", scale: 1 });
    inc.classList.add("is-active");
    inc.scrollTop = dir > 0 ? 0 : inc.scrollHeight;
    gsap.set(inc.querySelectorAll("[data-reveal]"), { opacity: 0 });

    const p = this.particles;
    const showAt = p ? SHOW_AT : 0.32;
    if (p) p.assemble(inc, DRAW_AT);
    gsap.delayedCall(showAt, () => {
      this.materialize(inc);
      p?.release();
    });
    gsap.delayedCall(showAt + SETTLE, () => {
      this.busy = false;
      this.guard = true;
      if (!this.entered.has(to)) {
        this.entered.add(to);
        const list = this.hooks.get(to);
        this.hooks.delete(to);
        list?.forEach((fn) => fn());
      }
    });
    return true;
  }

  /** The real page appears exactly where the particles drew it. */
  private materialize(page: HTMLElement) {
    gsap.fromTo(page, { opacity: 0, filter: "blur(6px)" }, { opacity: 1, filter: "blur(0px)", duration: 0.55, ease: "power2.out", clearProps: "filter" });
    gsap.to(page.querySelectorAll("[data-reveal]"), { opacity: 1, duration: 0.6, ease: "power2.out", stagger: 0.035 });
    const kicker = page.querySelector<HTMLElement>(".kicker");
    if (kicker) this.o.scramble(kicker);
  }

  private onWheel = (e: WheelEvent) => {
    if (e.ctrlKey) return; // pinch zoom
    const now = performance.now();
    const gap = now - this.lastWheel;
    this.lastWheel = now;
    if (this.blocked()) return;
    if (this.busy) {
      e.preventDefault();
      return;
    }
    const dy = e.deltaY * (e.deltaMode === 1 ? 32 : e.deltaMode === 2 ? innerHeight : 1);
    if (Math.abs(dy) < 1) return;
    if (canScroll(e.target, this.page, dy)) {
      // reading inside a long page; reaching its end mid-gesture must not turn the page
      this.guard = true;
      this.wheelAcc = 0;
      if (!(e.target instanceof Node && this.page.contains(e.target))) {
        // the browser won't scroll the page for a wheel over the nav or rail, so do it here
        e.preventDefault();
        this.page.scrollTop += dy;
      }
      return;
    }
    e.preventDefault();
    if (this.guard && gap < 180) return;
    this.guard = false;
    this.wheelAcc += dy;
    if (Math.abs(this.wheelAcc) >= 40) this.go(this.index + Math.sign(this.wheelAcc));
  };

  private onKey = (e: KeyboardEvent) => {
    if (this.blocked() || e.metaKey || e.ctrlKey || e.altKey) return;
    const t = e.target as HTMLElement | null;
    if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;
    // space on a focused button or summary presses it
    if (e.key === " " && t && /^(BUTTON|SUMMARY|A)$/.test(t.tagName)) return;
    const page = this.page;
    const down = e.key === "ArrowDown" || e.key === "PageDown" || (e.key === " " && !e.shiftKey);
    const up = e.key === "ArrowUp" || e.key === "PageUp" || (e.key === " " && e.shiftKey);
    if (down || up) {
      e.preventDefault();
      if (this.busy) return;
      const dy = down ? 1 : -1;
      if (canScroll(page, page, dy)) {
        const step = e.key.startsWith("Arrow") ? 120 : page.clientHeight * 0.85;
        page.scrollBy({ top: dy * step, behavior: "smooth" });
      } else this.go(this.index + dy);
    } else if (e.key === "Home") {
      e.preventDefault();
      this.go(0);
    } else if (e.key === "End") {
      e.preventDefault();
      this.go(this.o.sections.length - 1);
    }
  };
}
