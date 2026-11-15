#!/usr/bin/env python3
"""Quality control for the final MP4.

Checks container/stream properties, duration against the timeline, black frames,
frozen frames, audio loudness/peaks and audio/video length match, decodes the
whole file to make sure it plays, and writes a frame contact sheet.

  python3 scripts/qc.py [final/final_dinosaur_adventure.mp4]
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "final", "final_dinosaur_adventure.mp4")
    report = {}
    probe = json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path]).stdout)
    v = [s for s in probe["streams"] if s["codec_type"] == "video"][0]
    a = [s for s in probe["streams"] if s["codec_type"] == "audio"][0]
    num, den = map(int, v["r_frame_rate"].split("/"))
    report["file_mb"] = round(int(probe["format"]["size"]) / 1e6, 2)
    report["duration_s"] = round(float(probe["format"]["duration"]), 3)
    report["video"] = dict(codec=v["codec_name"], profile=v.get("profile"), width=v["width"], height=v["height"],
                           fps=num / den, pix_fmt=v["pix_fmt"], frames=int(v.get("nb_frames", 0)),
                           duration=float(v["duration"]), aspect=round(v["width"] / v["height"], 4))
    report["audio"] = dict(codec=a["codec_name"], sample_rate=int(a["sample_rate"]), channels=a["channels"],
                           duration=float(a["duration"]))
    import scenes
    report["timeline_s"] = round(scenes.total(), 3)

    # decode everything once: errors, black frames, frozen frames
    r = run(["ffmpeg", "-v", "error", "-i", path, "-vf", "blackdetect=d=0.4:pix_th=0.06,freezedetect=n=0.0008:d=2.5",
             "-f", "null", "-"])
    dec = run(["ffmpeg", "-v", "info", "-i", path, "-vf", "blackdetect=d=0.4:pix_th=0.06,freezedetect=n=0.0008:d=2.5",
               "-an", "-f", "null", "-"])
    report["decode_errors"] = r.stderr.strip().splitlines()[:5]
    report["black_segments"] = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", dec.stderr)
    report["frozen_segments"] = re.findall(r"freeze_start: ([\d.]+)", dec.stderr)
    ld = run(["ffmpeg", "-nostats", "-i", path, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
    summ = ld[ld.rfind("Summary"):]
    m = re.search(r"I:\s+(-?[\d.]+) LUFS", summ)
    p = re.search(r"Peak:\s+(-?[\d.]+) dBFS", summ)
    l = re.search(r"LRA:\s+([\d.]+) LU", summ)
    report["loudness"] = dict(integrated_lufs=float(m.group(1)) if m else None, true_peak_dbfs=float(p.group(1)) if p else None,
                              lra=float(l.group(1)) if l else None)
    print(json.dumps(report, indent=2))
    ok = (report["video"]["width"] == 1920 and report["video"]["height"] == 1080 and abs(report["video"]["fps"] - 24) < 1e-6
          and report["duration_s"] >= 210 and not report["decode_errors"]
          and abs(report["audio"]["duration"] - report["video"]["duration"]) < 0.2)
    print("QC", "PASS" if ok else "CHECK")
    with open(os.path.join(ROOT, "renders", "qc_report.json"), "w") as fh:
        json.dump(report, fh, indent=2)
    # contact sheet: one frame every 6 seconds
    sheet = os.path.join(ROOT, "assets", "storyboard_from_final.jpg")
    run(["ffmpeg", "-y", "-v", "error", "-i", path, "-vf", "fps=1/6,scale=384:-1,tile=6x8:padding=4:margin=4", "-frames:v", "1",
         "-q:v", "3", sheet])
    print("contact sheet:", sheet)


if __name__ == "__main__":
    main()
