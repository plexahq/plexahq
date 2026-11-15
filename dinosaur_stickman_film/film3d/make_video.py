#!/usr/bin/env python3
"""Encode film3d/frames/*.png + film3d/test_audio.wav into final/test_3d.mp4 (1080p24)."""
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def main():
    out = os.path.join(ROOT, "final", "test_3d.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", "24", "-i", os.path.join(HERE, "frames", "f_%05d.png"),
           "-i", os.path.join(HERE, "test_audio.wav"),
           "-vf", "scale=1920:1080:flags=lanczos,format=yuv420p",
           "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-tune", "film", "-profile:v", "high",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
           "-metadata", "title=The Last Day of the Dinosaurs - 3D test", out]
    subprocess.check_call(cmd)
    print("wrote", out, f"{os.path.getsize(out) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
