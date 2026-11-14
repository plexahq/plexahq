/**
 * Renders the X launch video (site/film.html) frame by frame under a fake clock, then encodes it.
 *
 *   npm run dev:http & npx vite --port 5173 &      # API + dev server (film.html is dev-only)
 *   node scripts/film.cjs out/plexa-16x9 1920 1080
 *   node scripts/film.cjs out/plexa-1x1 1080 1080
 *   node scripts/film.cjs out/stills 1920 1080 --stills
 *
 * Needs Playwright with Chromium and ffmpeg on the PATH. In the cloud sandbox, WebGL runs on SwiftShader.
 */
const { chromium } = require("playwright");
const { execFileSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const [out = "film-out", w = "1920", h = "1080", mode] = process.argv.slice(2);
const W = Number(w);
const H = Number(h);
const FPS = 30;
const URL = process.env.FILM_URL ?? "http://127.0.0.1:5173/film.html";

(async () => {
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  page.on("pageerror", (e) => console.error("page error:", e.message));
  await page.clock.install({ time: new Date("2026-11-14T12:00:00Z") });
  await page.goto(URL);
  // boot: imports, fonts and the live routes resolve in real time; timers need the fake clock to move
  for (let i = 0; i < 400; i++) {
    if (await page.evaluate(() => window.filmReady === true)) break;
    await page.clock.runFor(50);
    await page.waitForTimeout(40);
  }
  if (!(await page.evaluate(() => window.filmReady === true))) throw new Error("film page never became ready");
  // from here on, time only moves when we say so (otherwise it keeps flowing in real time)
  const now = await page.evaluate(() => Date.now());
  await page.clock.pauseAt(now + 200);
  const duration = await page.evaluate(() => {
    window.filmStart();
    return window.filmDuration;
  });

  if (mode === "--stills") {
    let t = 0;
    for (const at of [1.4, 3.6, 5.2, 6.2, 9.4, 14.3, 18.2, 22.1, 26.5]) {
      await page.clock.runFor(Math.round((at - t) * 1000));
      t = at;
      await page.screenshot({ path: path.join(out, `still-${String(at).replace(".", "_")}.jpg`), type: "jpeg", quality: 90 });
    }
  } else {
    const frames = Math.ceil(duration * FPS);
    const t0 = Date.now();
    for (let f = 0; f < frames; f++) {
      await page.clock.runFor(Math.round(((f + 1) * 1000) / FPS) - Math.round((f * 1000) / FPS));
      await page.screenshot({ path: path.join(out, `f${String(f).padStart(4, "0")}.jpg`), type: "jpeg", quality: 93 });
      if (f % 60 === 0) console.log(`frame ${f}/${frames} · ${Math.round((Date.now() - t0) / 1000)}s`);
    }
    const mp4 = `${out}.mp4`;
    execFileSync("ffmpeg", ["-v", "error", "-y", "-framerate", String(FPS), "-i", path.join(out, "f%04d.jpg"), "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", mp4]);
    console.log("wrote", mp4);
  }
  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
