import gsap from "gsap";
import * as THREE from "three";
import { ACCENT_RATIO, CHAIN_NODES, FORMATIONS, SATELLITES, bow, nodeLayouts, rng, type Vec3 } from "./formations";

/**
 * Where and how each formation sits on screen. x/y are fractions of the visible width/height.
 * "side" views sit in the free right column; "full" views (scale > 1.3) fill the screen behind content.
 */
/** mask: where text sits, so particles dim there (0 none, 1 left column, 2 centre). */
export interface View { x: number; y: number; scale: number; spin: number; rotX: number; rotY: number; noise: number; opacity: number; graph: 0 | 1 | 2; labels: number; mask: number }
const V = (x: number, y: number, scale: number, spin: number, rotX: number, rotY: number, noise: number, opacity: number, graph: 0 | 1 | 2 = 0, labels = 0, mask = 1): View => ({ x, y, scale, spin, rotX, rotY, noise, opacity, graph, labels, mask });
export const VIEWS: View[] = [
  V(0.22, 0.0, 1.0, 0.05, 0.18, 0, 0, 1, 1, 1), // 0 hero: plexus, side
  V(0.02, 0.0, 1.75, 0.012, 0, 0, 0.14, 0.6), // 1 gap: static, full
  V(0.04, 0.0, 1.55, 0, 0.05, -0.25, 0, 0.62), // 2 connect: convergence, full
  V(0.0, -0.02, 1.45, 0, 0.12, -0.3, 0, 0.55), // 3 read: blocks, full
  V(0.04, 0.0, 1.7, 0, 0.05, 0.8, 0, 0.55), // 4 simulate: scanner, full
  V(0.02, 0.04, 1.65, 0.025, 0.2, 0, 0, 0.78, 2, 0), // 5 cross-chain: ring graph, full
  V(0.05, 0.0, 1.45, 0.02, 0.15, -0.2, 0, 0.6), // 6 trust check: quorum, full
  V(0.0, -0.02, 1.12, 0.04, 0, 0, 0, 0.85, 0, 0, 2), // 7 zero: orbits, centre
  V(0.02, -0.02, 1.4, 0, 0.1, -0.22, 0, 0.82), // 8 markets: candles, full
  V(0.23, 0.1, 0.95, 0.08, 0.3, 0, 0, 0.95), // 9 security: lattice, side
  V(0.0, 0.0, 1.0, 0, 0, 0, 0.01, 0.55), // 10 tools: wall, full
  V(0.24, 0.0, 0.95, 0.12, 0.1, 0, 0, 0.95), // 11 roadmap: helix, side
  V(0.05, -0.05, 1.7, 0.04, 0.95, 0, 0, 0.45), // 12 faq: galaxy, full
  V(0.0, 0.17, 0.68, 0, 0, 0, 0, 1, 0, 0, 2), // 13 final: logo, centre
];

const INK = new THREE.Color("#ECEAE4");
const SIG = new THREE.Color("#FF5B1F");
const OK = new THREE.Color("#2FD3B5");
const DIM = new THREE.Color("#5A5F68");

const pointsVert = /* glsl */ `
  attribute vec3 aA; attribute vec3 aC; attribute vec3 aF; attribute float aSeed;
  uniform mat4 uMA, uMC;
  uniform float uT, uIntro, uTime, uSize, uPixelRatio, uMouseStrength, uBoost;
  uniform float uNoiseA, uNoiseC, uAccA, uAccC, uOpA, uOpC, uFloodOp, uMaskA, uMaskC, uMaskStrength;
  uniform vec3 uMouse;
  varying float vSeed; varying float vAlpha; varying float vAccent;

  float ease(float x) { x = clamp(x, 0.0, 1.0); return x * x * (3.0 - 2.0 * x); }

  // How much text sits at this screen position: 1 left column, 2 centred copy, 3 everywhere (phones).
  float maskOf(float type, vec2 ndc) {
    if (type < 0.5) return 0.0;
    if (type < 1.5) return smoothstep(0.12, -0.32, ndc.x);
    if (type < 2.5) return 1.0 - smoothstep(0.2, 0.75, length(vec2(ndc.x * 0.85, ndc.y * 1.25)));
    return 1.0;
  }

  // The full-screen "storm" between formations: a disk of stardust that swirls with scroll.
  vec3 storm(vec3 f, float s) {
    float tw = (uT - 0.5) * 1.6 * (0.35 + 0.65 * s) + uTime * 0.02;
    float c = cos(tw), sn = sin(tw);
    vec3 p = vec3(c * f.x - sn * f.y, sn * f.x + c * f.y, f.z);
    p += vec3(sin(p.y * 0.45 + uTime * 0.7 + s * 6.0), cos(p.x * 0.35 + uTime * 0.55 + s * 4.0), sin(uTime * 0.4 + s * 9.0)) * 0.35;
    return p;
  }

  void main() {
    float s = aSeed;
    vec3 pa = (uMA * vec4(aA, 1.0)).xyz;
    vec3 pc = (uMC * vec4(aC, 1.0)).xyz;
    vec3 pf = storm(aF, s);
    float t1 = ease((uT * 2.0 - s * 0.4) / 0.6);
    float t2 = ease(((uT - 0.5) * 2.0 - s * 0.4) / 0.6);
    vec3 p = mix(mix(pa, pf, t1), pc, t2);
    // opening: the storm condenses into the first formation
    float ti = ease((uIntro * 1.4 - s * 0.4));
    p = mix(storm(aF * 1.25, s), p, ti);
    float flood = max(t1 * (1.0 - t2), 1.0 - ti);
    float noise = mix(uNoiseA, uNoiseC, t2) + uBoost;
    p += vec3(sin(uTime * 0.55 + s * 12.0), cos(uTime * 0.45 + s * 9.0), sin(uTime * 0.35 + s * 7.0)) * (0.022 + noise);
    vec3 dm = p - uMouse; float dist = length(dm);
    p += normalize(dm + vec3(1e-4)) * smoothstep(1.6, 0.0, dist) * uMouseStrength;
    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    gl_Position = projectionMatrix * mv;
    gl_PointSize = uSize * (0.55 + s * 0.95) * (1.0 + flood * 0.35) * uPixelRatio * (11.0 / max(1.0, -mv.z));
    vSeed = s;
    float acc = mix(mix(uAccA, uAccC, t2), 0.26, flood);
    vAccent = step(1.0 - acc, fract(s * 7.13));
    vAlpha = smoothstep(28.0, 6.5, -mv.z) * mix(mix(uOpA, uOpC, t2), uFloodOp, flood);
    vec2 ndc = gl_Position.xy / gl_Position.w;
    vAlpha *= 1.0 - uMaskStrength * mix(maskOf(uMaskA, ndc), maskOf(uMaskC, ndc), t2);
  }`;
const pointsFrag = /* glsl */ `
  uniform vec3 uInk; uniform vec3 uSig;
  varying float vSeed; varying float vAlpha; varying float vAccent;
  void main() {
    vec2 c = gl_PointCoord - 0.5; float r = length(c);
    if (r > 0.5) discard;
    float a = pow(smoothstep(0.5, 0.0, r), 1.5);
    gl_FragColor = vec4(mix(uInk, uSig, vAccent), a * vAlpha * (0.32 + vSeed * 0.68) * (1.0 + vAccent * 0.6));
  }`;

const glowVert = /* glsl */ `
  attribute float aSize; attribute vec3 aColor; attribute float aAlpha;
  uniform float uPixelRatio, uScale;
  varying vec3 vColor; varying float vAlpha;
  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    gl_Position = projectionMatrix * mv;
    gl_PointSize = aSize * uScale * uPixelRatio * (11.0 / max(1.0, -mv.z));
    vColor = aColor; vAlpha = aAlpha;
  }`;
const glowFrag = /* glsl */ `
  uniform float uOpacity;
  varying vec3 vColor; varying float vAlpha;
  void main() {
    vec2 c = gl_PointCoord - 0.5; float r = length(c);
    if (r > 0.5) discard;
    float core = smoothstep(0.16, 0.0, r);
    float halo = pow(smoothstep(0.5, 0.0, r), 2.4) * 0.55;
    gl_FragColor = vec4(vColor * (1.0 + core), (core + halo) * vAlpha * uOpacity);
  }`;

interface Pulse { a: number; b: number; t0: number; dur: number; color: THREE.Color }
export interface PlexusOptions { count: number; reduced: boolean; labels: HTMLElement; views?: View[] }

const ease = (x: number) => {
  const c = Math.min(1, Math.max(0, x));
  return c * c * (3 - 2 * c);
};

export class Plexus {
  private renderer: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
  private points: THREE.Points;
  private mat: THREE.ShaderMaterial;
  private aA: THREE.BufferAttribute;
  private aC: THREE.BufferAttribute;
  private aF: THREE.BufferAttribute;
  private cache = new Map<number, Float32Array>();
  private views: View[];
  private pair: [number, number] = [-1, -1];
  private tCur = 0;
  private target = { a: 0, c: 1, t: 0 };
  private graphGroup = new THREE.Group();
  private graphView = -1;
  private graphOpacity = 0;
  private labelFactor = 0;
  private layouts = nodeLayouts();
  private nodePos: Vec3[];
  private threadGeo: THREE.BufferGeometry;
  private threadMat: THREE.LineBasicMaterial;
  private nodeGeo: THREE.BufferGeometry;
  private nodeMat: THREE.ShaderMaterial;
  private pulseGeo: THREE.BufferGeometry;
  private pulseMat: THREE.ShaderMaterial;
  private pulses: Pulse[] = [];
  private labelEls: HTMLElement[] = [];
  private mouse = new THREE.Vector3(99, 99, 0);
  private mouseTarget = new THREE.Vector3(99, 99, 0);
  private pointerNdc = new THREE.Vector2(0, 0);
  private running = false;
  private last = performance.now();
  private time = 0;
  private boost = 0;
  private viewW = 1;
  private viewH = 1;
  private readonly n: number;
  private readonly trail = 8;
  private readonly maxPulses = 48;
  private readonly MA = new THREE.Matrix4();
  private readonly MC = new THREE.Matrix4();
  private readonly tmp = { p: new THREE.Vector3(), q: new THREE.Quaternion(), s: new THREE.Vector3(), e: new THREE.Euler() };

  constructor(private canvas: HTMLCanvasElement, private opts: PlexusOptions) {
    this.n = opts.count;
    this.views = opts.views ?? VIEWS;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: false, powerPreference: "high-performance" });
    this.renderer.setClearColor("#0A0B0E", 1);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.6));
    this.camera.position.set(0, 0, 11);

    const seeds = new Float32Array(this.n).map(rng(7));
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(this.n * 3), 3));
    this.aA = new THREE.BufferAttribute(new Float32Array(this.n * 3), 3);
    this.aC = new THREE.BufferAttribute(new Float32Array(this.n * 3), 3);
    this.aF = new THREE.BufferAttribute(new Float32Array(this.n * 3), 3);
    geo.setAttribute("aA", this.aA);
    geo.setAttribute("aC", this.aC);
    geo.setAttribute("aF", this.aF);
    geo.setAttribute("aSeed", new THREE.BufferAttribute(seeds, 1));
    geo.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 80);
    this.mat = new THREE.ShaderMaterial({
      vertexShader: pointsVert,
      fragmentShader: pointsFrag,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      uniforms: {
        uMA: { value: this.MA }, uMC: { value: this.MC },
        uT: { value: 0 }, uIntro: { value: opts.reduced ? 1 : 0 }, uTime: { value: 0 }, uSize: { value: 3.2 },
        uPixelRatio: { value: this.renderer.getPixelRatio() }, uMouseStrength: { value: opts.reduced ? 0 : 0.42 }, uBoost: { value: 0 },
        uNoiseA: { value: 0 }, uNoiseC: { value: 0 }, uAccA: { value: 0.14 }, uAccC: { value: 0.14 }, uOpA: { value: 1 }, uOpC: { value: 1 },
        uFloodOp: { value: 0.95 }, uMaskA: { value: 1 }, uMaskC: { value: 1 }, uMaskStrength: { value: 0.8 }, uMouse: { value: this.mouse }, uInk: { value: INK }, uSig: { value: SIG },
      },
    });
    this.points = new THREE.Points(geo, this.mat);
    this.points.frustumCulled = false;
    this.scene.add(this.points);

    // --- graph overlay (hero sphere and cross-chain ring)
    this.graphGroup.matrixAutoUpdate = false;
    this.scene.add(this.graphGroup);
    this.nodePos = this.layouts.sphere.map((p) => [...p] as Vec3);
    this.threadGeo = new THREE.BufferGeometry();
    this.threadGeo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(this.nodePos.length * 22 * 2 * 3), 3));
    this.threadMat = new THREE.LineBasicMaterial({ color: "#7d838d", transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending });
    const threads = new THREE.LineSegments(this.threadGeo, this.threadMat);
    threads.frustumCulled = false;
    this.graphGroup.add(threads);

    const nn = this.nodePos.length + 1;
    this.nodeGeo = new THREE.BufferGeometry();
    this.nodeGeo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(nn * 3), 3));
    const sizes = new Float32Array(nn);
    const colors = new Float32Array(nn * 3);
    const alphas = new Float32Array(nn);
    for (let i = 0; i < nn; i++) {
      const hub = i === nn - 1;
      const labelled = i < CHAIN_NODES.length;
      const zero = labelled && CHAIN_NODES[i]!.zero;
      sizes[i] = hub ? 34 : zero ? 26 : labelled ? 16 : 8;
      (hub || zero ? SIG : labelled ? INK : DIM).toArray(colors, i * 3);
      alphas[i] = hub ? 1 : labelled ? 0.95 : 0.6;
    }
    this.nodeGeo.setAttribute("aSize", new THREE.BufferAttribute(sizes, 1));
    this.nodeGeo.setAttribute("aColor", new THREE.BufferAttribute(colors, 3));
    this.nodeGeo.setAttribute("aAlpha", new THREE.BufferAttribute(alphas, 1));
    this.nodeMat = this.glowMaterial();
    const nodes = new THREE.Points(this.nodeGeo, this.nodeMat);
    nodes.frustumCulled = false;
    this.graphGroup.add(nodes);

    const np = this.maxPulses * this.trail;
    this.pulseGeo = new THREE.BufferGeometry();
    this.pulseGeo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(np * 3), 3));
    this.pulseGeo.setAttribute("aSize", new THREE.BufferAttribute(new Float32Array(np), 1));
    this.pulseGeo.setAttribute("aColor", new THREE.BufferAttribute(new Float32Array(np * 3), 3));
    this.pulseGeo.setAttribute("aAlpha", new THREE.BufferAttribute(new Float32Array(np), 1));
    this.pulseMat = this.glowMaterial();
    const pulses = new THREE.Points(this.pulseGeo, this.pulseMat);
    pulses.frustumCulled = false;
    this.graphGroup.add(pulses);

    this.labelEls = CHAIN_NODES.map((c) => {
      const el = document.createElement("div");
      el.className = `node-label${c.zero ? " is-zero" : ""}`;
      el.innerHTML = `${c.label}<small>${c.sub}</small>`;
      el.style.opacity = "0";
      opts.labels.appendChild(el);
      return el;
    });

    this.resize();
    this.updateThreads(0);
    window.addEventListener("resize", () => this.resize());
    window.addEventListener("pointermove", (e) => {
      if (e.pointerType === "touch") return;
      this.pointerNdc.set((e.clientX / innerWidth) * 2 - 1, -(e.clientY / innerHeight) * 2 + 1);
      this.projectMouse();
    });
    document.addEventListener("visibilitychange", () => (document.hidden ? this.stop() : this.start()));
  }

  private glowMaterial() {
    return new THREE.ShaderMaterial({
      vertexShader: glowVert,
      fragmentShader: glowFrag,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      uniforms: { uPixelRatio: { value: this.renderer.getPixelRatio() }, uScale: { value: 1 }, uOpacity: { value: 0 } },
    });
  }

  private formation(i: number): Float32Array {
    let f = this.cache.get(i);
    if (!f) {
      f = new Float32Array(this.n * 3);
      FORMATIONS[i]!(f, this.n, rng(101 + i * 17));
      this.cache.set(i, f);
    }
    return f;
  }

  /** The storm: a disk of stardust large enough to cover the viewport at any rotation, at many depths. */
  private buildStorm() {
    const r = rng(999);
    const f = this.aF.array as Float32Array;
    const tanHalf = Math.tan(THREE.MathUtils.degToRad(this.camera.fov / 2));
    for (let i = 0; i < this.n; i++) {
      const z = -8 + Math.pow(r(), 0.7) * 15.5;
      const halfH = tanHalf * (11 - z);
      const R = Math.hypot(halfH, halfH * this.camera.aspect) * 1.08;
      let x: number, y: number;
      if (r() < 0.48) {
        const a = r() * Math.PI * 2;
        const d = Math.sqrt(r()) * R;
        x = Math.cos(a) * d;
        y = Math.sin(a) * d;
      } else {
        // a few luminous bands sweeping across the screen
        const band = Math.floor(r() * 4);
        const t = r() * 2 - 1;
        x = t * R;
        y = Math.sin(t * 2.6 + band * 1.7) * halfH * 0.5 + (band - 1.5) * halfH * 0.32 + (r() - 0.5) * (0.25 + Math.abs(t) * 0.5);
      }
      f[i * 3] = x;
      f[i * 3 + 1] = y;
      f[i * 3 + 2] = z;
    }
    this.aF.needsUpdate = true;
  }

  private isNarrow() {
    return innerWidth / innerHeight < 0.95 || innerWidth < 900;
  }

  private resize() {
    const w = innerWidth;
    const h = innerHeight;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.viewH = 2 * this.camera.position.z * Math.tan(THREE.MathUtils.degToRad(this.camera.fov / 2));
    this.viewW = this.viewH * this.camera.aspect;
    const s = Math.min(h / 900, w / 1000) * (this.isNarrow() ? 1.15 : 1);
    this.mat.uniforms.uSize!.value = 3.2 * Math.max(0.7, s);
    for (const m of [this.nodeMat, this.pulseMat]) m.uniforms.uScale!.value = Math.max(0.7, s);
    this.buildStorm();
  }

  /** World transform of a view at the current time (spin included). */
  private viewMatrix(i: number, out: THREE.Matrix4) {
    const v = this.views[i]!;
    const narrow = this.isNarrow();
    const full = v.scale > 1.3;
    const fit = Math.min(1, (this.viewW / 15.5) * (narrow ? 1.5 : 1));
    const s = v.scale * fit * (narrow ? (full ? 0.9 : 0.7) : 1);
    const { p, q, e } = this.tmp;
    p.set(narrow ? 0 : v.x * this.viewW, v.y * this.viewH + (narrow && !full ? 0.4 : 0), 0);
    q.setFromEuler(e.set(v.rotX, v.rotY + this.time * (this.opts.reduced ? 0 : v.spin), 0, "XYZ"));
    out.compose(p, q, this.tmp.s.set(s, s, s));
  }

  /**
   * Scroll-driven morph from view a to view c. t = 0 shows a, t = 0.5 is the full-screen storm, t = 1 shows c.
   * The scene follows this target at a capped speed (see advance), so fast scrolling never strobes.
   */
  setTransition(a: number, c: number, t: number) {
    this.target = { a, c, t: this.opts.reduced ? (t < 0.5 ? 0 : 1) : t };
    if (this.pair[0] < 0) {
      this.applyPair(a, c);
      this.tCur = this.target.t;
    }
  }

  private applyPair(a: number, c: number) {
    if (a === this.pair[0] && c === this.pair[1]) return;
    this.pair = [a, c];
    (this.aA.array as Float32Array).set(this.formation(a));
    (this.aC.array as Float32Array).set(this.formation(c));
    this.aA.needsUpdate = this.aC.needsUpdate = true;
    const u = this.mat.uniforms;
    const va = this.views[a]!;
    const vc = this.views[c]!;
    const narrow = this.isNarrow();
    u.uNoiseA!.value = va.noise;
    u.uNoiseC!.value = vc.noise;
    u.uAccA!.value = ACCENT_RATIO[a];
    u.uAccC!.value = ACCENT_RATIO[c];
    u.uOpA!.value = va.opacity * (narrow ? 0.62 : 1);
    u.uOpC!.value = vc.opacity * (narrow ? 0.62 : 1);
    u.uMaskA!.value = narrow ? 3 : va.mask;
    u.uMaskC!.value = narrow ? 3 : vc.mask;
    u.uMaskStrength!.value = narrow ? 0.72 : 0.8;
  }

  /**
   * Moves the morph toward the scroll target at no more than ~1.4 units/s (a full morph takes at least ~0.7s).
   * Switching to a different pair happens either at a shared endpoint (seamless) or inside the storm,
   * which is identical for every pair, so skipping several chapters at once morphs straight to the last one.
   */
  private advance(dt: number) {
    const T = this.target;
    const max = 1.4 * dt;
    const stepTo = (goal: number, linear = false) => {
      const d = goal - this.tCur;
      const want = linear ? d : d * Math.min(1, dt * 6);
      this.tCur += Math.max(-max, Math.min(max, want));
    };
    if (this.opts.reduced) {
      this.applyPair(T.a, T.c);
      this.tCur = T.t;
      return;
    }
    const [a, c] = this.pair;
    if (T.a === a && T.c === c) return stepTo(T.t);
    const shown = this.tCur < 0.004 ? a : this.tCur > 0.996 ? c : -1;
    if (shown >= 0 && (T.a === shown || T.c === shown)) {
      this.applyPair(T.a, T.c);
      this.tCur = T.a === shown ? 0 : 1;
      return stepTo(T.t);
    }
    if (Math.abs(this.tCur - 0.5) < 0.015) {
      this.applyPair(T.a, T.c);
      this.tCur = 0.5;
      return stepTo(T.t);
    }
    stepTo(0.5, true);
  }

  /** Hold a single view (sub-pages). */
  setStatic(i: number) {
    this.setTransition(i, i, 0);
  }

  /** Opening: the storm condenses into the first view. */
  intro() {
    if (this.opts.reduced) return;
    this.mat.uniforms.uIntro!.value = 0;
    gsap.to(this.mat.uniforms.uIntro!, { value: 1, duration: 3.4, ease: "power2.out" });
  }

  /** Scroll velocity briefly agitates the field. */
  setVelocity(v: number) {
    this.boost = Math.min(0.05, Math.abs(v) * 0.002);
  }

  private nodeIndex(chain: string): number {
    const i = CHAIN_NODES.findIndex((c) => c.key === chain || (c.key === "hyperliquid" && chain === "hyperevm"));
    if (i >= 0) return i;
    let h = 0;
    for (const ch of chain) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
    return CHAIN_NODES.length + (h % SATELLITES);
  }

  /** Send a light pulse from one chain to another through the Plexa hub. */
  pulse(from: string, to: string, delivered: boolean) {
    if (this.graphOpacity < 0.02) return;
    if (this.pulses.length >= this.maxPulses) this.pulses.shift();
    this.pulses.push({ a: this.nodeIndex(from), b: this.nodeIndex(to), t0: this.time, dur: 2.6 + Math.random() * 1.2, color: delivered ? OK : SIG });
  }

  private thread(i: number, s: number, out: Vec3, layout: number): Vec3 {
    const p = this.nodePos[i]!;
    const cs = bow(p);
    const cr: Vec3 = [p[0] * 0.5, p[1] * 0.5 + 0.6, p[2] * 0.5];
    const c: Vec3 = [cs[0] + (cr[0] - cs[0]) * layout, cs[1] + (cr[1] - cs[1]) * layout, cs[2] + (cr[2] - cs[2]) * layout];
    const u = 1 - s;
    out[0] = 2 * u * s * c[0] + s * s * p[0];
    out[1] = 2 * u * s * c[1] + s * s * p[1];
    out[2] = 2 * u * s * c[2] + s * s * p[2];
    return out;
  }

  private layout = 0;
  private updateThreads(layout: number) {
    this.layout = layout;
    const { sphere, ring } = this.layouts;
    for (let i = 0; i < this.nodePos.length; i++)
      for (let c = 0; c < 3; c++) this.nodePos[i]![c] = sphere[i]![c]! + (ring[i]![c]! - sphere[i]![c]!) * layout;
    const pos = this.threadGeo.getAttribute("position") as THREE.BufferAttribute;
    const a: Vec3 = [0, 0, 0];
    const b: Vec3 = [0, 0, 0];
    let k = 0;
    for (let i = 0; i < this.nodePos.length; i++)
      for (let s = 0; s < 22; s++) {
        this.thread(i, s / 22, a, layout);
        this.thread(i, (s + 1) / 22, b, layout);
        pos.setXYZ(k++, a[0], a[1], a[2]);
        pos.setXYZ(k++, b[0], b[1], b[2]);
      }
    pos.needsUpdate = true;
    const np = this.nodeGeo.getAttribute("position") as THREE.BufferAttribute;
    this.nodePos.forEach((p, i) => np.setXYZ(i, p[0], p[1], p[2]));
    np.setXYZ(this.nodePos.length, 0, 0, 0);
    np.needsUpdate = true;
  }

  private projectMouse() {
    const ray = new THREE.Raycaster();
    ray.setFromCamera(this.pointerNdc, this.camera);
    const hit = new THREE.Vector3();
    if (ray.ray.intersectPlane(new THREE.Plane(new THREE.Vector3(0, 0, 1), 0), hit)) this.mouseTarget.copy(hit);
  }

  private updateGraph() {
    const [a, c] = this.pair;
    const t = this.tCur;
    const wA = this.views[a]?.graph ? 1 - ease(t * 2) : 0;
    const wC = this.views[c]?.graph ? ease(t * 2 - 1) : 0;
    const useA = wA >= wC;
    const view = useA ? a : c;
    this.graphOpacity = Math.max(wA, wC) * (this.opts.reduced ? 1 : Math.min(1, this.mat.uniforms.uIntro!.value * 1.5));
    if (this.graphOpacity < 0.01) return;
    this.graphGroup.matrix.copy(useA ? this.MA : this.MC);
    this.graphGroup.matrixWorldNeedsUpdate = true;
    const layout = this.views[view]!.graph === 2 ? 1 : 0;
    if (view !== this.graphView || layout !== this.layout) this.updateThreads(layout);
    this.graphView = view;
    this.labelFactor = this.isNarrow() ? 0 : this.views[view]!.labels;
  }

  private updatePulses(time: number) {
    const pos = this.pulseGeo.getAttribute("position") as THREE.BufferAttribute;
    const size = this.pulseGeo.getAttribute("aSize") as THREE.BufferAttribute;
    const col = this.pulseGeo.getAttribute("aColor") as THREE.BufferAttribute;
    const alpha = this.pulseGeo.getAttribute("aAlpha") as THREE.BufferAttribute;
    const p: Vec3 = [0, 0, 0];
    this.pulses = this.pulses.filter((q) => time - q.t0 < q.dur);
    let k = 0;
    for (const q of this.pulses) {
      const head = (time - q.t0) / q.dur;
      for (let j = 0; j < this.trail; j++) {
        const t = Math.max(0, head - j * 0.018);
        if (t < 0.5) this.thread(q.a, 1 - t * 2, p, this.layout);
        else this.thread(q.b, t * 2 - 1, p, this.layout);
        pos.setXYZ(k, p[0], p[1], p[2]);
        size.setX(k, j === 0 ? 20 : 11 - j);
        col.setXYZ(k, q.color.r, q.color.g, q.color.b);
        alpha.setX(k, (1 - j / this.trail) * Math.min(1, (1 - head) * 6, head * 12));
        k++;
      }
    }
    for (; k < this.maxPulses * this.trail; k++) alpha.setX(k, 0);
    pos.needsUpdate = size.needsUpdate = col.needsUpdate = alpha.needsUpdate = true;
  }

  private updateLabels() {
    const o = this.graphOpacity * this.labelFactor;
    const v = new THREE.Vector3();
    const cam = new THREE.Vector3();
    this.labelEls.forEach((el, i) => {
      if (o < 0.02) {
        if (el.style.opacity !== "0") el.style.opacity = "0";
        return;
      }
      const p = this.nodePos[i]!;
      v.set(p[0], p[1], p[2]).applyMatrix4(this.graphGroup.matrix);
      cam.copy(v).applyMatrix4(this.camera.matrixWorldInverse);
      v.project(this.camera);
      const depth = THREE.MathUtils.clamp((-cam.z - 8) / 6, 0, 1);
      el.style.transform = `translate3d(${(v.x * 0.5 + 0.5) * innerWidth + 14}px, ${(-v.y * 0.5 + 0.5) * innerHeight - 8}px, 0)`;
      el.style.opacity = String(o * (1 - depth * 0.85));
    });
  }

  private frame = () => {
    if (!this.running) return;
    const now = performance.now();
    const dt = Math.min((now - this.last) / 1000, 0.05);
    this.last = now;
    this.time += dt;
    this.advance(dt);
    const u = this.mat.uniforms;
    u.uT!.value = this.tCur;
    u.uTime!.value = this.time;
    this.viewMatrix(Math.max(0, this.pair[0]), this.MA);
    this.viewMatrix(Math.max(0, this.pair[1]), this.MC);
    this.mouse.lerp(this.mouseTarget, 0.08);
    this.boost *= 0.92;
    u.uBoost!.value = this.boost;
    // a gentle push-in while the storm fills the screen
    const storm = Math.sin(Math.PI * Math.min(1, Math.max(0, this.tCur)));
    this.camera.position.x += (this.pointerNdc.x * 0.35 - this.camera.position.x) * 0.03;
    this.camera.position.y += (this.pointerNdc.y * 0.22 - this.camera.position.y) * 0.03;
    this.camera.position.z = 11 - storm * 1.1;
    this.camera.lookAt(0, 0, 0);
    this.updateGraph();
    this.threadMat.opacity = this.graphOpacity * 0.22;
    this.nodeMat.uniforms.uOpacity!.value = this.graphOpacity;
    this.pulseMat.uniforms.uOpacity!.value = this.graphOpacity;
    if (this.graphOpacity > 0.01) this.updatePulses(this.time);
    this.renderer.render(this.scene, this.camera);
    this.updateLabels();
    requestAnimationFrame(this.frame);
  };

  start() {
    if (this.running) return;
    this.running = true;
    this.last = performance.now();
    requestAnimationFrame(this.frame);
  }

  stop() {
    this.running = false;
  }
}

export function createPlexus(canvas: HTMLCanvasElement, opts: PlexusOptions): Plexus | null {
  try {
    const test = document.createElement("canvas");
    if (!(test.getContext("webgl2") || test.getContext("webgl"))) return null;
    return new Plexus(canvas, opts);
  } catch {
    return null;
  }
}
