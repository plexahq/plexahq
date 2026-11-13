/**
 * Particle formations, one per chapter, in a local frame centred on the origin
 * (roughly radius 3). Each generator fills `out` (length = count * 3).
 */

export type Vec3 = [number, number, number];

/** Deterministic PRNG so formations are stable between reloads. */
export function rng(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export interface ChainNode {
  key: string;
  label: string;
  sub: string;
  zero?: boolean;
}

/** Labelled nodes of the plexus. Unknown chains from the live feed map onto satellites. */
export const CHAIN_NODES: ChainNode[] = [
  { key: "zero", label: "Zero · Atlas", sub: "mainnet nov 30", zero: true },
  { key: "ethereum", label: "Ethereum", sub: "eid 30101" },
  { key: "base", label: "Base", sub: "eid 30184" },
  { key: "arbitrum", label: "Arbitrum", sub: "eid 30110" },
  { key: "optimism", label: "Optimism", sub: "eid 30111" },
  { key: "hyperliquid", label: "HyperEVM", sub: "eid 30367" },
  { key: "bsc", label: "BNB Chain", sub: "eid 30102" },
  { key: "solana", label: "Solana", sub: "eid 30168" },
  { key: "tron", label: "Tron", sub: "eid 30420" },
  { key: "polygon", label: "Polygon", sub: "eid 30109" },
  { key: "avalanche", label: "Avalanche", sub: "eid 30106" },
];
export const SATELLITES = 14;

function fib(i: number, n: number, r: number): Vec3 {
  const y = 1 - (i / (n - 1)) * 2;
  const rad = Math.sqrt(1 - y * y);
  const th = Math.PI * (3 - Math.sqrt(5)) * i;
  return [Math.cos(th) * rad * r, y * r, Math.sin(th) * rad * r];
}

/** Node positions on a sphere (hero) and on a tilted ring (cross-chain chapter). */
export function nodeLayouts(): { sphere: Vec3[]; ring: Vec3[] } {
  const total = CHAIN_NODES.length + SATELLITES;
  const sphere: Vec3[] = [];
  const ring: Vec3[] = [];
  const order = [0, 3, 6, 1, 8, 4, 10, 2, 7, 5, 9];
  for (let i = 0; i < total; i++) {
    const labelled = i < CHAIN_NODES.length;
    const k = labelled ? order[i]! * 2 + 1 : (i - CHAIN_NODES.length) * 1.71 + 0.4;
    const p = fib(Math.floor(k * 1.07) % 25, 25, labelled ? 2.45 : 2.9);
    sphere.push(labelled ? p : [p[0] * 1.08, p[1] * 1.08, p[2] * 1.08]);
    const a = (i / total) * Math.PI * 2 + 0.3;
    const r = labelled ? 2.75 : 3.25;
    const tilt = 0.42;
    const x = Math.cos(a) * r;
    const z = Math.sin(a) * r;
    ring.push([x, z * Math.sin(tilt) * 0.55 + (labelled ? 0 : 0.18), z * Math.cos(tilt)]);
  }
  return { sphere, ring };
}

function bez(a: Vec3, b: Vec3, c: Vec3, t: number): Vec3 {
  const u = 1 - t;
  return [u * u * a[0] + 2 * u * t * b[0] + t * t * c[0], u * u * a[1] + 2 * u * t * b[1] + t * t * c[1], u * u * a[2] + 2 * u * t * b[2] + t * t * c[2]];
}

/** Control point that bows a hub-to-node thread outward. */
export function bow(p: Vec3, amount = 0.35): Vec3 {
  return [p[0] * 0.5 + p[1] * amount * 0.3, p[1] * 0.5 + amount, p[2] * 0.5 - p[0] * amount * 0.2];
}

function put(out: Float32Array, i: number, p: Vec3) {
  out[i * 3] = p[0];
  out[i * 3 + 1] = p[1];
  out[i * 3 + 2] = p[2];
}

function jitter(r: () => number, s: number): Vec3 {
  return [(r() - 0.5) * s, (r() - 0.5) * s, (r() - 0.5) * s];
}

function add(a: Vec3, b: Vec3): Vec3 {
  return [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
}

type Gen = (out: Float32Array, n: number, r: () => number) => void;

const plexus: Gen = (out, n, r) => {
  const { sphere } = nodeLayouts();
  const hub: Vec3 = [0, 0, 0];
  for (let i = 0; i < n; i++) {
    const u = r();
    if (u < 0.5) {
      const node = sphere[Math.floor(r() * sphere.length)]!;
      const t = Math.pow(r(), 0.8);
      put(out, i, add(bez(hub, bow(node), node, t), jitter(r, 0.08 + t * 0.06)));
    } else if (u < 0.82) {
      put(out, i, add(fib(Math.floor(r() * 2400), 2400, 2.95), jitter(r, 0.12)));
    } else if (u < 0.9) {
      const a = r() * Math.PI * 2;
      const rad = Math.pow(r(), 2) * 0.55;
      put(out, i, [Math.cos(a) * rad, (r() - 0.5) * 0.5, Math.sin(a) * rad]);
    } else {
      put(out, i, add([0, 0, 0], jitter(r, 9)));
    }
  }
};

const stat: Gen = (out, n, r) => {
  const clumps: Vec3[] = Array.from({ length: 9 }, () => [(r() - 0.5) * 6, (r() - 0.5) * 4.2, (r() - 0.5) * 3]);
  for (let i = 0; i < n; i++) {
    if (r() < 0.55) put(out, i, add(clumps[Math.floor(r() * clumps.length)]!, jitter(r, 1.1)));
    else put(out, i, [(r() - 0.5) * 8, (r() - 0.5) * 5.5, (r() - 0.5) * 4]);
  }
};

const converge: Gen = (out, n, r) => {
  const core: Vec3 = [2.1, 0, 0];
  const rings: Vec3[] = [-2, -1, 0, 1, 2].map((k) => [-2.6 + Math.abs(k) * 0.45, k * 1.05, -Math.abs(k) * 0.3]);
  for (let i = 0; i < n; i++) {
    const u = r();
    const ring = rings[Math.floor(r() * rings.length)]!;
    if (u < 0.36) {
      const a = r() * Math.PI * 2;
      const rad = 0.42 + (r() - 0.5) * 0.06;
      put(out, i, add(ring, [Math.cos(a) * rad * 0.35, Math.sin(a) * rad, Math.cos(a) * rad]));
    } else if (u < 0.86) {
      const t = r();
      const mid: Vec3 = [ring[0] * 0.2 + 0.6, ring[1] * 0.35, ring[2] * 0.4];
      put(out, i, add(bez(ring, mid, core, t), jitter(r, 0.06 + (1 - t) * 0.08)));
    } else {
      put(out, i, add(core, jitter(r, 0.5 * Math.pow(r(), 1.5))));
    }
  }
};

const blocks: Gen = (out, n, r) => {
  const cubes = 9;
  for (let i = 0; i < n; i++) {
    const c = Math.floor(r() * cubes);
    const t = c / (cubes - 1);
    const center: Vec3 = [-3.6 + t * 7.2, -1.2 + t * 1.6 + Math.sin(c * 1.3) * 0.25, -1.5 - t * 1.2];
    const s = 0.62 - t * 0.12;
    if (r() < 0.82) {
      // cube edges
      const axis = Math.floor(r() * 3);
      const a = r() < 0.5 ? -s : s;
      const b = r() < 0.5 ? -s : s;
      const v = (r() * 2 - 1) * s;
      const p: Vec3 = axis === 0 ? [v, a, b] : axis === 1 ? [a, v, b] : [a, b, v];
      put(out, i, add(center, add(p, jitter(r, 0.025))));
    } else {
      // chain links between blocks
      const nxt: Vec3 = [center[0] + 0.9, center[1] + 0.2, center[2] - 0.15];
      const k = r();
      put(out, i, [center[0] + s + (nxt[0] - center[0] - 2 * s) * k, center[1] + (nxt[1] - center[1]) * k, center[2] + (nxt[2] - center[2]) * k]);
    }
  }
};

const scanner: Gen = (out, n, r) => {
  for (let i = 0; i < n; i++) {
    const u = r();
    const a = r() * Math.PI * 2;
    if (u < 0.45) {
      const R = 2.5 + (r() - 0.5) * 0.12;
      put(out, i, [Math.cos(a) * 0.15 * (r() - 0.5), Math.sin(a) * R, Math.cos(a) * R]);
    } else if (u < 0.65) {
      const R = 1.9 + (r() - 0.5) * 0.08;
      put(out, i, [(r() - 0.5) * 0.08, Math.sin(a) * R, Math.cos(a) * R]);
    } else if (u < 0.88) {
      // packets streaming through the gate along x
      const x = (r() - 0.5) * 8;
      const lane = Math.floor(r() * 5) - 2;
      put(out, i, [x, lane * 0.32 + (r() - 0.5) * 0.04, (r() - 0.5) * 0.12]);
    } else {
      const rad = Math.sqrt(r()) * 2.4;
      put(out, i, [(r() - 0.5) * 0.04, Math.sin(a) * rad, Math.cos(a) * rad]);
    }
  }
};

const ringGraph: Gen = (out, n, r) => {
  const { ring } = nodeLayouts();
  const hub: Vec3 = [0, 0, 0];
  for (let i = 0; i < n; i++) {
    const u = r();
    if (u < 0.4) {
      const a = r() * Math.PI * 2;
      const R = 2.75 + (r() - 0.5) * 0.1;
      const z = Math.sin(a) * R;
      put(out, i, [Math.cos(a) * R, z * Math.sin(0.42) * 0.55, z * Math.cos(0.42)]);
    } else if (u < 0.8) {
      const node = ring[Math.floor(r() * ring.length)]!;
      const t = r();
      put(out, i, add(bez(hub, [node[0] * 0.5, node[1] * 0.5 + 0.6, node[2] * 0.5], node, t), jitter(r, 0.05)));
    } else {
      const a = r() * Math.PI * 2;
      const rad = Math.sqrt(r()) * 2.6;
      const z = Math.sin(a) * rad;
      put(out, i, add([Math.cos(a) * rad, z * Math.sin(0.42) * 0.55 - 0.05, z * Math.cos(0.42)], jitter(r, 0.04)));
    }
  }
};

const orbits: Gen = (out, n, r) => {
  const radii = [1.5, 2.45, 3.4, 4.5];
  for (let i = 0; i < n; i++) {
    const u = r();
    const a = r() * Math.PI * 2;
    if (u < 0.86) {
      const k = Math.floor(r() * radii.length);
      const R = radii[k]! + (r() - 0.5) * (k === 3 ? 0.3 : 0.05);
      const tilt = 1.08;
      const z = Math.sin(a) * R;
      put(out, i, [Math.cos(a) * R, z * Math.cos(tilt), z * Math.sin(tilt)]);
    } else {
      const rad = Math.pow(r(), 3) * 0.6;
      const t = r() * Math.PI;
      put(out, i, [Math.cos(a) * Math.sin(t) * rad, Math.cos(t) * rad, Math.sin(a) * Math.sin(t) * rad]);
    }
  }
};

/** A message at the centre, signed off by a ring of DVNs, inside a hexagonal shield. */
const quorum: Gen = (out, n, r) => {
  const k = 7;
  const nodes: Vec3[] = Array.from({ length: k }, (_, i) => {
    const a = (i / k) * Math.PI * 2 + 0.3;
    return [Math.cos(a) * 2.1, Math.sin(a) * 2.1, Math.sin(a * 2) * 0.35];
  });
  const hex: Vec3[] = [0, 1, 2, 3, 4, 5].map((i) => {
    const a = (i / 6) * Math.PI * 2 + Math.PI / 6;
    return [Math.cos(a) * 3.15, Math.sin(a) * 3.15, 0];
  });
  const ball = (c: Vec3, radius: number, pow: number): Vec3 => {
    const a = r() * Math.PI * 2;
    const t = Math.acos(2 * r() - 1);
    const rad = Math.pow(r(), pow) * radius;
    return [c[0] + Math.sin(t) * Math.cos(a) * rad, c[1] + Math.sin(t) * Math.sin(a) * rad, c[2] + Math.cos(t) * rad];
  };
  for (let i = 0; i < n; i++) {
    const u = r();
    if (u < 0.24) {
      put(out, i, ball(nodes[Math.floor(r() * k)]!, 0.3, 0.45));
    } else if (u < 0.54) {
      // signatures flowing from each verifier into the message
      const p = nodes[Math.floor(r() * k)]!;
      const c: Vec3 = [p[0] * 0.45 - p[1] * 0.2, p[1] * 0.45 + p[0] * 0.2, 0.45];
      put(out, i, add(bez(p, c, [0, 0, 0], r()), jitter(r, 0.04)));
    } else if (u < 0.66) {
      put(out, i, ball([0, 0, 0], 0.46, 0.6));
    } else if (u < 0.95) {
      const e = Math.floor(r() * 6);
      const A = hex[e]!;
      const B = hex[(e + 1) % 6]!;
      const t = r();
      put(out, i, add([A[0] + (B[0] - A[0]) * t, A[1] + (B[1] - A[1]) * t, (r() - 0.5) * 0.12], jitter(r, 0.03)));
    } else {
      put(out, i, jitter(r, 8));
    }
  }
};

/** A rising candlestick chart with a moving average and grid: markets, on-chain. */
const candles: Gen = (out, n, r) => {
  const N = 26;
  const pr = rng(77);
  const cs: { x: number; o: number; c: number; h: number; l: number }[] = [];
  let p = 0;
  for (let i = 0; i < N; i++) {
    const o = p;
    const c = o + (pr() - 0.36) * 0.75;
    cs.push({ x: -4.6 + (i / (N - 1)) * 9.2, o, c, h: Math.max(o, c) + pr() * 0.32, l: Math.min(o, c) - pr() * 0.32 });
    p = c;
  }
  const lo = Math.min(...cs.map((c) => c.l));
  const hi = Math.max(...cs.map((c) => c.h));
  const ny = (y: number) => -2.1 + ((y - lo) / (hi - lo)) * 4.2;
  const w = 0.12;
  for (let i = 0; i < n; i++) {
    const u = r();
    const c = cs[Math.floor(r() * N)]!;
    if (u < 0.58) {
      const y0 = ny(Math.min(c.o, c.c));
      const y1 = Math.max(ny(Math.max(c.o, c.c)), y0 + 0.06);
      const edge = r() < 0.45;
      const x = edge ? c.x + (r() < 0.5 ? -w : w) : c.x + (r() * 2 - 1) * w;
      put(out, i, [x, y0 + (y1 - y0) * r(), (r() - 0.5) * 0.14]);
    } else if (u < 0.74) {
      put(out, i, [c.x + (r() - 0.5) * 0.015, ny(c.l) + (ny(c.h) - ny(c.l)) * r(), (r() - 0.5) * 0.04]);
    } else if (u < 0.88) {
      const t = r() * (N - 1);
      const k = Math.floor(t);
      const f = t - k;
      const a = cs[k]!;
      const b = cs[Math.min(N - 1, k + 1)]!;
      const ya = ny((a.o + a.c) / 2);
      const yb = ny((b.o + b.c) / 2);
      put(out, i, add([a.x + (b.x - a.x) * f, ya + (yb - ya) * f + 0.42, 0.12], jitter(r, 0.025)));
    } else if (u < 0.97) {
      const row = Math.floor(r() * 5);
      put(out, i, [-5 + r() * 10, -2.1 + row * 1.05, -0.7]);
    } else {
      put(out, i, jitter(r, 8));
    }
  }
};

const lattice: Gen = (out, n, r) => {
  // icosahedron edges + vertex clusters
  const t = (1 + Math.sqrt(5)) / 2;
  const raw: Vec3[] = [[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t], [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]];
  const s = 2.2 / Math.hypot(1, t);
  const v = raw.map((p) => [p[0] * s, p[1] * s, p[2] * s] as Vec3);
  const edges: [number, number][] = [];
  for (let a = 0; a < v.length; a++)
    for (let b = a + 1; b < v.length; b++) {
      const d = Math.hypot(v[a]![0] - v[b]![0], v[a]![1] - v[b]![1], v[a]![2] - v[b]![2]);
      if (d < 2.4 * s + 0.01) edges.push([a, b]);
    }
  for (let i = 0; i < n; i++) {
    const u = r();
    if (u < 0.7) {
      const [a, b] = edges[Math.floor(r() * edges.length)]!;
      const k = r();
      const p: Vec3 = [v[a]![0] + (v[b]![0] - v[a]![0]) * k, v[a]![1] + (v[b]![1] - v[a]![1]) * k, v[a]![2] + (v[b]![2] - v[a]![2]) * k];
      put(out, i, add(p, jitter(r, 0.03)));
    } else if (u < 0.85) {
      put(out, i, add(v[Math.floor(r() * v.length)]!, jitter(r, 0.16)));
    } else {
      put(out, i, add(fib(Math.floor(r() * 900), 900, 3.1), jitter(r, 0.05)));
    }
  }
};

const wall: Gen = (out, n, r) => {
  const cols = 80;
  const rows = Math.ceil(n / cols);
  for (let i = 0; i < n; i++) {
    const c = i % cols;
    const w = Math.floor(i / cols);
    const x = (c / (cols - 1) - 0.5) * 13;
    const y = (w / Math.max(1, rows - 1) - 0.5) * 7.5;
    put(out, i, [x, y, -3.4 + Math.sin(x * 0.6) * 0.4 + Math.cos(y * 0.8) * 0.3 + (r() - 0.5) * 0.03]);
  }
};

const helix: Gen = (out, n, r) => {
  for (let i = 0; i < n; i++) {
    const u = r();
    const y = (r() - 0.5) * 6.4;
    const a = y * 1.35;
    const R = 1.35;
    if (u < 0.72) {
      const strand = r() < 0.5 ? 0 : Math.PI;
      put(out, i, add([Math.cos(a + strand) * R, y, Math.sin(a + strand) * R], jitter(r, 0.07)));
    } else if (u < 0.92) {
      const step = Math.round(y / 0.4) * 0.4;
      const aa = step * 1.35;
      const k = r() * 2 - 1;
      put(out, i, [Math.cos(aa) * R * k, step, Math.sin(aa) * R * k]);
    } else {
      put(out, i, add([0, y, 0], jitter(r, 3.2)));
    }
  }
};

const galaxy: Gen = (out, n, r) => {
  for (let i = 0; i < n; i++) {
    const arm = Math.floor(r() * 3);
    const d = Math.pow(r(), 0.7) * 3.6;
    const a = d * 1.3 + (arm * Math.PI * 2) / 3 + (r() - 0.5) * (0.5 + d * 0.06);
    put(out, i, [Math.cos(a) * d, (r() - 0.5) * 0.18 * (4 - d), Math.sin(a) * d]);
  }
};

const logo: Gen = (out, n, r) => {
  const ends: Vec3[] = [0, 60, 120, 180, 240, 300].map((deg) => {
    const a = ((deg - 90) * Math.PI) / 180;
    return [Math.cos(a) * 2.5, -Math.sin(a) * 2.5, 0];
  });
  for (let i = 0; i < n; i++) {
    const u = r();
    if (u < 0.16) {
      const a = r() * Math.PI * 2;
      const rad = Math.sqrt(r()) * 0.62;
      put(out, i, [Math.cos(a) * rad, Math.sin(a) * rad, (r() - 0.5) * 0.1]);
    } else if (u < 0.62) {
      const e = ends[Math.floor(r() * 6)]!;
      const k = 0.3 + r() * 0.62;
      put(out, i, add([e[0] * k, e[1] * k, 0], jitter(r, 0.05)));
    } else if (u < 0.86) {
      const e = ends[Math.floor(r() * 6)]!;
      const a = r() * Math.PI * 2;
      const rad = Math.sqrt(r()) * 0.3;
      put(out, i, [e[0] + Math.cos(a) * rad, e[1] + Math.sin(a) * rad, (r() - 0.5) * 0.06]);
    } else {
      const a = r() * Math.PI * 2;
      const R = 3.6 + Math.pow(r(), 2) * 2.5;
      put(out, i, [Math.cos(a) * R, Math.sin(a) * R, (r() - 0.5) * 1.2]);
    }
  }
};

/** Formation generator per chapter index (0..13). */
export const FORMATIONS: Gen[] = [plexus, stat, converge, blocks, scanner, ringGraph, quorum, orbits, candles, lattice, wall, helix, galaxy, logo];

/** Accent indices: which particles take the signal colour, per chapter. */
export const ACCENT_RATIO = [0.14, 0.04, 0.22, 0.1, 0.18, 0.14, 0.2, 0.32, 0.16, 0.12, 0.05, 0.2, 0.12, 0.36];
