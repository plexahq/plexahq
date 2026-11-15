#!/usr/bin/env python3
"""Render THE LAST DAY OF THE DINOSAURS.

  python3 scripts/render.py stills 12 30.5 61      # PNG stills at those seconds
  python3 scripts/render.py sheet --every 2         # contact sheets for review
  python3 scripts/render.py video --start 0 --end 20 --scale 0.5 --out renders/test.mp4
  python3 scripts/render.py film                    # full film -> renders/video.mp4 (no audio)

Frames are drawn with Skia on the CPU, piped as raw BGRA into FFmpeg. The film is
split into chunks rendered by a process pool; chunks are concatenated losslessly.
"""
import argparse
import math
import os
import subprocess
import sys
import time
from multiprocessing import get_context

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import skia  # noqa: E402

from engine.core import W, H, FPS  # noqa: E402
import scenes  # noqa: E402


def draw_frame(frame, scale=1.0):
    w, h = int(W * scale), int(H * scale)
    surf = skia.Surface(w, h)
    c = surf.getCanvas()
    c.clear(skia.ColorBLACK)
    c.save()
    c.scale(scale, scale)
    scenes.render_at(c, frame / FPS, frame)
    c.restore()
    return surf


def _chunk(args):
    f0, f1, scale, path, crf = args
    w, h = int(W * scale), int(H * scale)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{w}x{h}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p", path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    for f in range(f0, f1):
        surf = draw_frame(f, scale)
        arr = surf.toarray()
        p.stdin.write(arr.tobytes())
    p.stdin.close()
    p.wait()
    return f0, f1, time.time() - t0


def video(start, end, scale, out, workers=4, chunk_s=6.0, crf=10):
    f_start, f_end = int(round(start * FPS)), int(round(end * FPS))
    seg_dir = os.path.join(os.path.dirname(os.path.abspath(out)), "segments_" + os.path.splitext(os.path.basename(out))[0])
    os.makedirs(seg_dir, exist_ok=True)
    step = int(chunk_s * FPS)
    jobs = []
    for i, f0 in enumerate(range(f_start, f_end, step)):
        f1 = min(f_end, f0 + step)
        jobs.append((f0, f1, scale, os.path.join(seg_dir, f"seg_{f0:06d}.mp4"), crf))
    # heavy chunks first keeps the pool busy
    t0 = time.time()
    done = 0
    ctx = get_context("fork")
    with ctx.Pool(workers) as pool:
        for f0, f1, dt in pool.imap_unordered(_chunk, jobs):
            done += f1 - f0
            el = time.time() - t0
            print(f"  frames {f0}-{f1} in {dt:.1f}s ({(f1 - f0) / dt:.2f} fps) | {done}/{f_end - f_start} | "
                  f"elapsed {el / 60:.1f} min", flush=True)
    lst = os.path.join(seg_dir, "list.txt")
    with open(lst, "w") as fh:
        for j in jobs:
            fh.write(f"file '{os.path.abspath(j[3])}'\n")
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out])
    print("wrote", out, f"in {(time.time() - t0) / 60:.1f} min")


def stills(times, scale, outdir):
    os.makedirs(outdir, exist_ok=True)
    for t in times:
        f = int(round(t * FPS))
        s = draw_frame(f, scale)
        path = os.path.join(outdir, f"still_{t:07.2f}.png")
        s.makeImageSnapshot().save(path)
        print(path)


def sheet(every, scale, outdir, start=0.0, end=None, cols=4, rows=4):
    os.makedirs(outdir, exist_ok=True)
    end = end or scenes.total()
    times = []
    t = start
    while t < end:
        times.append(t)
        t += every
    tw, th = int(W * scale), int(H * scale)
    per = cols * rows
    font = skia.Font(skia.Typeface("DejaVu Sans Mono"), 14)
    for k in range(0, len(times), per):
        surf = skia.Surface(tw * cols, th * rows)
        c = surf.getCanvas()
        c.clear(skia.ColorBLACK)
        for i, tt in enumerate(times[k:k + per]):
            img = draw_frame(int(round(tt * FPS)), scale).makeImageSnapshot()
            x, y = (i % cols) * tw, (i // cols) * th
            c.drawImage(img, x, y)
            p = skia.Paint(Color=skia.ColorWHITE)
            c.drawRect(skia.Rect(x, y, x + 70, y + 20), skia.Paint(Color=skia.ColorSetARGB(160, 0, 0, 0)))
            c.drawString(f"{tt:6.1f}", x + 4, y + 15, font, p)
        path = os.path.join(outdir, f"sheet_{times[k]:07.1f}.png")
        surf.makeImageSnapshot().save(path)
        print(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["stills", "sheet", "video", "film", "info"])
    ap.add_argument("times", nargs="*", type=float)
    ap.add_argument("--scale", type=float, default=None)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=None)
    ap.add_argument("--every", type=float, default=2.0)
    ap.add_argument("--out", default=None)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--crf", type=int, default=10)
    a = ap.parse_args()
    if a.mode == "info":
        for m, s, e in scenes.timeline():
            print(f"{m.__name__:32s} {s:7.2f} -> {e:7.2f}  ({e - s:5.2f}s)")
        print("total", scenes.total())
        return
    if a.mode == "stills":
        stills(a.times, a.scale or 0.5, a.out or os.path.join(ROOT, "renders", "stills"))
    elif a.mode == "sheet":
        sheet(a.every, a.scale or 0.25, a.out or os.path.join(ROOT, "renders", "sheets"), a.start, a.end)
    elif a.mode == "video":
        video(a.start, a.end or scenes.total(), a.scale or 0.5, a.out or os.path.join(ROOT, "renders", "preview.mp4"),
              a.workers, crf=a.crf)
    elif a.mode == "film":
        video(0.0, scenes.total(), a.scale or 1.0, a.out or os.path.join(ROOT, "renders", "video.mp4"), a.workers, crf=a.crf)


if __name__ == "__main__":
    main()
