import gsap from "gsap";
import * as THREE from "three";
import { ACCENT_RATIO, CHAIN_NODES, FORMATIONS, SATELLITES, bow, nodeLayouts, rng, type Vec3 } from "./formations";

/** Where and how each chapter's formation sits on screen. x/y are fractions of the visible width/height. */
interface View { x: number; y: number; scale: number; spin: number; rotX: number; rotY: number; noise: number; opacity: number; graph: 0 | 1 | 2 }
const VIEWS: View[] = [
  { x: 0.22, y: 0.0, scale: 1.0, spin: 0.05, rotX: 0.18, rotY: 0, noise: 0, opacity: 1, graph: 1 },
  { x: 0.24, y: 0.0, scale: 1.0, spin: 0.015, rotX: 0, rotY: 0, noise: 0.16, opacity: 0.8, graph: 0 },
  { x: 0.12, y: 0.0, scale: 0.92, spin: 0, rotX: 0.05, rotY: -0.25, noise: 0, opacity: 0.8, graph: 0 },
  { x: 0.08, y: 0.06, scale: 1.0, spin: 0, rotX: 0.12, rotY: -0.35, noise: 0, opacity: 0.7, graph: 0 },
  { x: 0.16, y: 0.0, scale: 1.05, spin: 0, rotX: 0.05, rotY: 0.75, noise: 0, opacity: 0.8, graph: 0 },
  { x: 0.2, y: 0.14, scale: 1.0, spin: 0.03, rotX: 0.2, rotY: 0, noise: 0, opacity: 0.95, graph: 2 },
  { x: 0.0, y: -0.02, scale: 1.12, spin: 0.04, rotX: 0.0, rotY: 0, noise: 0, opacity: 0.85, graph: 0 },
  { x: 0.23, y: 0.1, scale: 0.95, spin: 0.08, rotX: 0.3, rotY: 0, noise: 0, opacity: 0.95, graph: 0 },
  { x: 0.0, y: 0.0, scale: 1.0, spin: 0, rotX: 0, rotY: 0, noise: 0.01, opacity: 0.55, graph: 0 },
  { x: 0.24, y: 0.0, scale: 0.95, spin: 0.12, rotX: 0.1, rotY: 0, noise: 0, opacity: 0.95, graph: 0 },
  { x: 0.24, y: -0.08, scale: 1.0, spin: 0.05, rotX: 0.95, rotY: 0, noise: 0, opacity: 0.55, graph: 0 },
  { x: 0.0, y: 0.17, scale: 0.68, spin: 0, rotX: 0, rotY: 0, noise: 0, opacity: 1, graph: 0 },
];

const INK = new THREE.Color("#ECEAE4");
const SIG = new THREE.Color("#FF5B1F");
const OK = new THREE.Color("#2FD3B5");
const DIM = new THREE.Color("#5A5F68");

const pointsVert = /* glsl */ `
  attribute vec3 aFrom; attribute vec3 aTo; attribute float aSeed;
  uniform float uMix, uTime, uSize, uPixelRatio, uNoise, uMouseStrength, uAccent;
  uniform vec3 uMouse;
  varying float vSeed; varying float vAlpha; varying float vAccent;
  void main() {
    float d = clamp((uMix - aSeed * 0.35) / 0.65, 0.0, 1.0);
    d = d * d * (3.0 - 2.0 * d);
    vec3 p = mix(aFrom, aTo, d);
    float mid = sin(d * 3.14159);
    p += vec3(sin(aSeed * 40.0 + uTime * 0.6), cos(aSeed * 31.0 + uTime * 0.5), sin(aSeed * 17.0 + uTime * 0.4)) * mid * 0.55;
    p += vec3(sin(uTime * 0.55 + aSeed * 12.0), cos(uTime * 0.45 + aSeed * 9.0), sin(uTime * 0.35 + aSeed * 7.0)) * (0.022 + uNoise);
    vec3 dm = p - uMouse; float dist = length(dm);
    p += normalize(dm + vec3(1e-4)) * smoothstep(1.5, 0.0, dist) * uMouseStrength;
    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    gl_Position = projectionMatrix * mv;
    gl_PointSize = uSize * (0.55 + aSeed * 0.95) * uPixelRatio * (11.0 / -mv.z);
    vSeed = aSeed;
    vAccent = step(1.0 - uAccent, fract(aSeed * 7.13));
    vAlpha = smoothstep(26.0, 7.0, -mv.z);
  }`;
const pointsFrag = /* glsl */ `
  uniform vec3 uInk; uniform vec3 uSig; uniform float uOpacity;
  varying float vSeed; varying float vAlpha; varying float vAccent;
  void main() {
    vec2 c = gl_PointCoord - 0.5; float r = length(c);
    if (r > 0.5) discard;
    float a = pow(smoothstep(0.5, 0.0, r), 1.5);
    vec3 col = mix(uInk, uSig, vAccent);
    gl_FragColor = vec4(col, a * uOpacity * vAlpha * (0.32 + vSeed * 0.68) * (1.0 + vAccent * 0.6));
  }`;

const glowVert = /* glsl */ `
  attribute float aSize; attribute vec3 aColor; attribute float aAlpha;
  uniform float uPixelRatio, uScale;
  varying vec3 vColor; varying float vAlpha;
  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    gl_Position = projectionMatrix * mv;
    gl_PointSize = aSize * uScale * uPixelRatio * (11.0 / -mv.z);
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

export interface PlexusOptions { count: number; reduced: boolean; labels: HTMLElement }

export class Plexus {
  private renderer: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
  private root = new THREE.Group();
  private spinner = new THREE.Group();
  private points: THREE.Points;
  private pointMat: THREE.ShaderMaterial;
  private from: Float32Array;
  private to: Float32Array;
  private seeds: Float32Array;
  private cache = new Map<number, Float32Array>();
  private chapter = -1;
  private spinSpeed = 0.05;
  private spinAngle = 0;
  private graph = { opacity: 0, layout: 0 };
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
  private last = performance.now();
  private elapsed = 0;
  private labelFactor = 1;
  private running = false;
  private velocityNoise = 0;
  private viewW = 1;
  private viewH = 1;
  private readonly n: number;
  private readonly trail = 8;
  private readonly maxPulses = 48;

  constructor(private canvas: HTMLCanvasElement, private opts: PlexusOptions) {
    this.n = opts.count;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: false, powerPreference: "high-performance" });
    this.renderer.setClearColor("#0A0B0E", 1);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.6));
    this.camera.position.set(0, 0, 11);
    this.scene.add(this.root);
    this.root.add(this.spinner);

    // --- particle field
    const r = rng(7);
    this.seeds = new Float32Array(this.n).map(() => r());
    this.from = new Float32Array(this.n * 3);
    for (let i = 0; i < this.n; i++) {
      const a = r() * Math.PI * 2;
      const b = Math.acos(2 * r() - 1);
      const R = 9 + r() * 9;
      this.from.set([Math.cos(a) * Math.sin(b) * R, Math.cos(b) * R, Math.sin(a) * Math.sin(b) * R - 4], i * 3);
    }
    this.to = this.formation(0);
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(this.n * 3), 3));
    geo.setAttribute("aFrom", new THREE.BufferAttribute(this.from, 3));
    geo.setAttribute("aTo", new THREE.BufferAttribute(this.to, 3));
    geo.setAttribute("aSeed", new THREE.BufferAttribute(this.seeds, 1));
    geo.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 50);
    this.pointMat = new THREE.ShaderMaterial({
      vertexShader: pointsVert,
      fragmentShader: pointsFrag,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      uniforms: {
        uMix: { value: 0 }, uTime: { value: 0 }, uSize: { value: 3.2 }, uPixelRatio: { value: this.renderer.getPixelRatio() },
        uNoise: { value: 0 }, uMouseStrength: { value: opts.reduced ? 0 : 0.42 }, uAccent: { value: ACCENT_RATIO[0] },
        uMouse: { value: this.mouse }, uInk: { value: INK }, uSig: { value: SIG }, uOpacity: { value: 1 },
      },
    });
    this.points = new THREE.Points(geo, this.pointMat);
    this.spinner.add(this.points);

    // --- graph: threads, nodes, pulses
    this.nodePos = this.layouts.sphere.map((p) => [...p] as Vec3);
    const segs = 22;
    this.threadGeo = new THREE.BufferGeometry();
    this.threadGeo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(this.nodePos.length * segs * 2 * 3), 3));
    this.threadMat = new THREE.LineBasicMaterial({ color: "#7d838d", transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending });
    const threads = new THREE.LineSegments(this.threadGeo, this.threadMat);
    threads.frustumCulled = false;
    this.spinner.add(threads);

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
    this.spinner.add(nodes);

    const np = this.maxPulses * this.trail;
    this.pulseGeo = new THREE.BufferGeometry();
    this.pulseGeo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(np * 3), 3));
    this.pulseGeo.setAttribute("aSize", new THREE.BufferAttribute(new Float32Array(np), 1));
    this.pulseGeo.setAttribute("aColor", new THREE.BufferAttribute(new Float32Array(np * 3), 3));
    this.pulseGeo.setAttribute("aAlpha", new THREE.BufferAttribute(new Float32Array(np), 1));
    this.pulseMat = this.glowMaterial();
    const pulses = new THREE.Points(this.pulseGeo, this.pulseMat);
    pulses.frustumCulled = false;
    this.spinner.add(pulses);

    // --- HTML labels for named nodes
    this.labelEls = CHAIN_NODES.map((c) => {
      const el = document.createElement("div");
      el.className = `node-label${c.zero ? " is-zero" : ""}`;
      el.innerHTML = `${c.label}<small>${c.sub}</small>`;
      el.style.opacity = "0";
      opts.labels.appendChild(el);
      return el;
    });

    this.resize();
    this.updateThreads();
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
    this.pointMat.uniforms.uSize!.value = 3.2 * Math.max(0.7, s);
    for (const m of [this.nodeMat, this.pulseMat]) m.uniforms.uScale!.value = Math.max(0.7, s);
    if (this.chapter >= 0) this.applyView(this.chapter, 0);
  }

  private applyView(i: number, duration: number) {
    const v = VIEWS[i]!;
    const narrow = this.isNarrow();
    const fit = Math.min(1, (this.viewW / 15.5) * (narrow ? 1.5 : 1));
    const target = {
      x: narrow ? 0 : v.x * this.viewW,
      y: v.y * this.viewH + (narrow ? 0.4 : 0),
      s: v.scale * fit * (narrow ? 0.7 : 1),
    };
    const ease = "power3.inOut";
    gsap.to(this.root.position, { x: target.x, y: target.y, duration, ease });
    gsap.to(this.root.scale, { x: target.s, y: target.s, z: target.s, duration, ease });
    gsap.to(this.root.rotation, { x: v.rotX, duration, ease });
    gsap.to(this, { spinSpeed: this.opts.reduced ? 0 : v.spin, duration, ease });
    gsap.to(this.pointMat.uniforms.uOpacity!, { value: v.opacity * (narrow ? 0.62 : 1), duration, ease });
    gsap.to(this.pointMat.uniforms.uNoise!, { value: v.noise, duration, ease });
    gsap.to(this.pointMat.uniforms.uAccent!, { value: ACCENT_RATIO[i], duration, ease });
    gsap.to(this, { labelFactor: narrow ? 0 : i === 5 ? 0.28 : 1, duration, ease });
    gsap.to(this.graph, { opacity: v.graph ? 1 : 0, duration: duration * (v.graph ? 1.2 : 0.5), ease });
    if (v.graph) gsap.to(this.graph, { layout: v.graph === 2 ? 1 : 0, duration, ease, onUpdate: () => this.updateThreads() });
    // rotY is an offset on top of the running spin: ease the accumulated angle toward it
    const base = Math.round(this.spinAngle / (Math.PI * 2)) * Math.PI * 2;
    gsap.to(this, { spinAngle: v.spin ? this.spinAngle : base + v.rotY, duration, ease });
  }

  /** Morph to chapter i. */
  setChapter(i: number) {
    if (i === this.chapter) return;
    const first = this.chapter < 0;
    this.chapter = i;
    if (!first) {
      // freeze the current (possibly mid-transition) positions as the new origin
      const mix = this.pointMat.uniforms.uMix!.value as number;
      for (let k = 0; k < this.n; k++) {
        let d = Math.min(1, Math.max(0, (mix - this.seeds[k]! * 0.35) / 0.65));
        d = d * d * (3 - 2 * d);
        for (let c = 0; c < 3; c++) this.from[k * 3 + c] = this.from[k * 3 + c]! + (this.to[k * 3 + c]! - this.from[k * 3 + c]!) * d;
      }
      this.to.set(this.formation(i));
      const g = this.points.geometry;
      (g.getAttribute("aFrom") as THREE.BufferAttribute).needsUpdate = true;
      (g.getAttribute("aTo") as THREE.BufferAttribute).needsUpdate = true;
      gsap.killTweensOf(this.pointMat.uniforms.uMix!);
      this.pointMat.uniforms.uMix!.value = 0;
      gsap.to(this.pointMat.uniforms.uMix!, { value: 1, duration: this.opts.reduced ? 0 : 2.4, ease: "power2.inOut" });
    }
    this.applyView(i, first ? 0 : 1.8);
  }

  /** Play the opening assembly from scattered stars into the plexus. */
  intro() {
    this.pointMat.uniforms.uMix!.value = 0;
    gsap.to(this.pointMat.uniforms.uMix!, { value: 1, duration: this.opts.reduced ? 0 : 3.2, ease: "power3.out" });
  }

  /** Scroll velocity briefly agitates the field. */
  setVelocity(v: number) {
    this.velocityNoise = Math.min(0.12, Math.abs(v) * 0.004);
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
    if (this.pulses.length >= this.maxPulses) this.pulses.shift();
    this.pulses.push({
      a: this.nodeIndex(from),
      b: this.nodeIndex(to),
      t0: this.elapsed,
      dur: 2.6 + Math.random() * 1.2,
      color: delivered ? OK : SIG,
    });
  }

  private thread(i: number, s: number, out: Vec3): Vec3 {
    const p = this.nodePos[i]!;
    const cs = bow(p);
    const cr: Vec3 = [p[0] * 0.5, p[1] * 0.5 + 0.6, p[2] * 0.5];
    const t = this.graph.layout;
    const c: Vec3 = [cs[0] + (cr[0] - cs[0]) * t, cs[1] + (cr[1] - cs[1]) * t, cs[2] + (cr[2] - cs[2]) * t];
    const u = 1 - s;
    out[0] = 2 * u * s * c[0] + s * s * p[0];
    out[1] = 2 * u * s * c[1] + s * s * p[1];
    out[2] = 2 * u * s * c[2] + s * s * p[2];
    return out;
  }

  private updateThreads() {
    const t = this.graph.layout;
    const { sphere, ring } = this.layouts;
    for (let i = 0; i < this.nodePos.length; i++)
      for (let c = 0; c < 3; c++) this.nodePos[i]![c] = sphere[i]![c]! + (ring[i]![c]! - sphere[i]![c]!) * t;
    const pos = this.threadGeo.getAttribute("position") as THREE.BufferAttribute;
    const segs = 22;
    const a: Vec3 = [0, 0, 0];
    const b: Vec3 = [0, 0, 0];
    let k = 0;
    for (let i = 0; i < this.nodePos.length; i++) {
      for (let s = 0; s < segs; s++) {
        this.thread(i, s / segs, a);
        this.thread(i, (s + 1) / segs, b);
        pos.setXYZ(k++, a[0], a[1], a[2]);
        pos.setXYZ(k++, b[0], b[1], b[2]);
      }
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
    ray.ray.intersectPlane(new THREE.Plane(new THREE.Vector3(0, 0, 1), 0), hit);
    this.mouseTarget.copy(hit);
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
        if (t < 0.5) this.thread(q.a, 1 - t * 2, p);
        else this.thread(q.b, t * 2 - 1, p);
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
    const o = this.graph.opacity * this.labelFactor;
    const v = new THREE.Vector3();
    const camSpace = new THREE.Vector3();
    this.labelEls.forEach((el, i) => {
      if (o < 0.02) {
        if (el.style.opacity !== "0") el.style.opacity = "0";
        return;
      }
      const p = this.nodePos[i]!;
      v.set(p[0], p[1], p[2]);
      this.spinner.localToWorld(v);
      camSpace.copy(v).applyMatrix4(this.camera.matrixWorldInverse);
      v.project(this.camera);
      const x = (v.x * 0.5 + 0.5) * innerWidth;
      const y = (-v.y * 0.5 + 0.5) * innerHeight;
      const depth = THREE.MathUtils.clamp((-camSpace.z - 8) / 6, 0, 1);
      el.style.transform = `translate3d(${x + 14}px, ${y - 8}px, 0)`;
      el.style.opacity = String(o * (1 - depth * 0.85));
    });
  }

  private frame = () => {
    if (!this.running) return;
    const now = performance.now();
    const dt = Math.min((now - this.last) / 1000, 0.05);
    this.last = now;
    this.elapsed += dt;
    const time = this.elapsed;
    this.spinAngle += this.spinSpeed * dt;
    this.spinner.rotation.y = this.spinAngle;
    this.mouse.lerp(this.mouseTarget, 0.08);
    const local = this.spinner.worldToLocal(this.mouse.clone());
    this.pointMat.uniforms.uMouse!.value = local;
    this.pointMat.uniforms.uTime!.value = time;
    this.velocityNoise *= 0.92;
    const baseNoise = VIEWS[Math.max(0, this.chapter)]!.noise;
    this.pointMat.uniforms.uNoise!.value += (baseNoise + this.velocityNoise - this.pointMat.uniforms.uNoise!.value) * 0.1;
    this.camera.position.x += (this.pointerNdc.x * 0.35 - this.camera.position.x) * 0.03;
    this.camera.position.y += (this.pointerNdc.y * 0.22 - this.camera.position.y) * 0.03;
    this.camera.lookAt(0, 0, 0);
    this.threadMat.opacity = this.graph.opacity * 0.22;
    this.nodeMat.uniforms.uOpacity!.value = this.graph.opacity;
    this.pulseMat.uniforms.uOpacity!.value = this.graph.opacity;
    if (this.graph.opacity > 0.01) this.updatePulses(time);
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
