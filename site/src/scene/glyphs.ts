/**
 * Turns what a page shows into points for the particles to settle on: every visible word,
 * drawn in its own font, plus the outlines of panels and buttons. Points are returned as
 * NDC x, y and a colour flag (0 ink, 1 signal orange), in screen order.
 */

const FRAMES = ".panel, .console, .zone, .tool, .pr, .group, .guess, .urlbox, .track, .scenario, .faq details, .road li, .btn, .countdown > div, .checks li";
const SKIP = "script, style, select, option, svg, input, textarea, .sr-only, [aria-hidden='true']";

function isSignal(color: string): boolean {
  const m = color.match(/\d+(\.\d+)?/g);
  if (!m) return false;
  const [r, g, b] = m.map(Number) as [number, number, number];
  return r > 200 && g < 140 && b < 90;
}

export function samplePage(section: HTMLElement, budget: number, step = 3): Float32Array {
  const W = Math.max(1, Math.round(innerWidth));
  const H = Math.max(1, Math.round(innerHeight));
  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) return new Float32Array(0);
  const visible = (r: DOMRect) => r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < H && r.right > 0 && r.left < W;

  // frames first, thin, so words drawn on top keep their shape
  ctx.lineWidth = 2;
  section.querySelectorAll<HTMLElement>(FRAMES).forEach((el) => {
    const r = el.getBoundingClientRect();
    if (!visible(r) || r.width < 24 || r.height < 16) return;
    ctx.strokeStyle = el.classList.contains("btn-sig") ? "#f00" : "#0f0";
    ctx.strokeRect(r.left + 1, r.top + 1, r.width - 2, r.height - 2);
  });

  // words, each drawn where the browser laid it out
  const range = document.createRange();
  const walker = document.createTreeWalker(section, NodeFilter.SHOW_TEXT);
  const styleCache = new Map<Element, CSSStyleDeclaration>();
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const text = node.textContent ?? "";
    if (!text.trim()) continue;
    const el = node.parentElement;
    if (!el || el.closest(SKIP)) continue;
    let cs = styleCache.get(el);
    if (!cs) {
      cs = getComputedStyle(el);
      styleCache.set(el, cs);
    }
    if (cs.visibility === "hidden" || cs.display === "none") continue;
    ctx.font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    (ctx as CanvasRenderingContext2D & { letterSpacing?: string }).letterSpacing = cs.letterSpacing === "normal" ? "0px" : cs.letterSpacing;
    ctx.fillStyle = isSignal(cs.color) ? "#f00" : "#0f0";
    const upper = cs.textTransform === "uppercase";
    const re = /\S+/g;
    for (let m = re.exec(text); m; m = re.exec(text)) {
      range.setStart(node, m.index);
      range.setEnd(node, m.index + m[0].length);
      const r = range.getBoundingClientRect();
      if (!visible(r)) continue;
      const word = upper ? m[0].toUpperCase() : m[0];
      const tm = ctx.measureText(word);
      const asc = tm.actualBoundingBoxAscent;
      const desc = tm.actualBoundingBoxDescent;
      ctx.fillText(word, r.left, r.top + (r.height - (asc + desc)) / 2 + asc);
    }
  }

  // sample on a staggered grid
  const data = ctx.getImageData(0, 0, W, H).data;
  const pts: number[] = [];
  for (let y = 0, row = 0; y < H; y += step, row++) {
    for (let x = row % 2 ? Math.floor(step / 2) : 0; x < W; x += step) {
      const i = (y * W + x) * 4;
      const r = data[i]!;
      const g = data[i + 1]!;
      if (r < 90 && g < 90) continue;
      pts.push(x, y, r > g ? 1 : 0);
    }
  }

  // too many points: keep an even random share of them
  let count = pts.length / 3;
  if (count > budget) {
    for (let k = 0; k < budget; k++) {
      const j = k + Math.floor(Math.random() * (count - k));
      for (let c = 0; c < 3; c++) [pts[k * 3 + c], pts[j * 3 + c]] = [pts[j * 3 + c]!, pts[k * 3 + c]!];
    }
    count = budget;
  }
  const out = new Float32Array(count * 3);
  for (let k = 0; k < count; k++) {
    out[k * 3] = (pts[k * 3]! / W) * 2 - 1;
    out[k * 3 + 1] = 1 - (pts[k * 3 + 1]! / H) * 2;
    out[k * 3 + 2] = pts[k * 3 + 2]!;
  }
  return out;
}
