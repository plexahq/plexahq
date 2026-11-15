#!/usr/bin/env python3
"""Mux the rendered picture with the soundtrack into the final MP4 and keep it
under GitHub's 100 MB file limit.

  python3 scripts/finalize.py [--crf 20] [--max-mb 95]

Input:  renders/video.mp4 (from scripts/render.py film), audio/soundtrack.wav
Output: final/final_dinosaur_adventure.mp4
"""
import argparse
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def duration(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path])
    return float(out.strip())


def encode(video, audio, out, crf=None, bitrate=None, passlog=None):
    base = ["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", audio, "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "slow", "-tune", "animation", "-profile:v", "high", "-level", "4.1",
            "-pix_fmt", "yuv420p", "-r", "24", "-g", "48", "-colorspace", "bt709", "-color_primaries", "bt709",
            "-color_trc", "bt709"]
    tail = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-shortest", "-movflags", "+faststart",
            "-metadata", "title=The Last Day of the Dinosaurs", out]
    if crf is not None:
        subprocess.check_call(base + ["-crf", str(crf), "-maxrate", "6M", "-bufsize", "12M"] + tail)
        return
    # two-pass to an exact size
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-c:v", "libx264", "-preset", "slow", "-tune", "animation",
                           "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", "24", "-g", "48", "-b:v", f"{bitrate}k", "-pass", "1",
                           "-passlogfile", passlog, "-an", "-f", "mp4", os.devnull])
    subprocess.check_call(base + ["-b:v", f"{bitrate}k", "-pass", "2", "-passlogfile", passlog] + tail)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=os.path.join(ROOT, "renders", "video.mp4"))
    ap.add_argument("--audio", default=os.path.join(ROOT, "audio", "soundtrack.wav"))
    ap.add_argument("--out", default=os.path.join(ROOT, "final", "final_dinosaur_adventure.mp4"))
    ap.add_argument("--crf", type=int, default=20)
    ap.add_argument("--max-mb", type=float, default=95.0)
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    encode(a.video, a.audio, a.out, crf=a.crf)
    mb = os.path.getsize(a.out) / 1e6
    print(f"crf {a.crf}: {mb:.1f} MB")
    if mb > a.max_mb:
        dur = duration(a.video)
        kbps = int((a.max_mb * 8e6 * 0.97) / dur / 1000) - 192
        print(f"too large; two-pass at {kbps} kb/s video")
        encode(a.video, a.audio, a.out, bitrate=kbps, passlog=os.path.join(ROOT, "renders", "x264pass"))
        print(f"two-pass: {os.path.getsize(a.out) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
