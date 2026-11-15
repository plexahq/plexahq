#!/usr/bin/env python3
"""Character model sheets (stickman turnaround/poses, T-Rex, small dinosaur,
sauropod, pterosaur) rendered from the same rigs used in the film."""
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import skia  # noqa: E402

from engine.core import W, H, paint, c4, text_centered, lin  # noqa: E402
from engine import stickman as sm  # noqa: E402
from engine import dino as D  # noqa: E402

OUT = os.path.join(ROOT, "assets", "model_sheets")


def canvas():
    s = skia.Surface(W, H)
    c = s.getCanvas()
    c.drawRect(skia.Rect(0, 0, W, H), paint(shader=lin((0, 0), (0, H), [(0, "#f1ece0"), (1, "#ddd4c0")])))
    return s, c


def label(c, s, x, y, size=26):
    text_centered(c, s, x, y, size, (0.2, 0.18, 0.16), face="inter")


def stickman_sheet():
    s, c = canvas()
    label(c, "THE STICKMAN  -  MODEL SHEET", W / 2, 70, 40)
    gy = 470
    poses = [
        ("neutral", sm.stand(x=0, y=0, s=3.0, f=1, face=1.0)),
        ("front", sm.stand(x=0, y=0, s=3.0, f=1, face=0.0)),
        ("looking back", sm.stand(x=0, y=0, s=3.0, f=1, face=-1.0, head=-0.1)),
        ("afraid", sm.tremble(sm.stand(x=0, y=0, s=3.0, f=1, face=1.0, eye_s=1.7, torso=-0.2, sh_n=1.9, el_n=1.6, sh_f=1.6, el_f=1.8), 0.3)),
        ("sneak", sm.gait(0.3, 0, 0, 3.0, 1, "sneak")),
        ("exhausted", sm.gait(0.6, 0, 0, 3.0, 1, "tired")),
    ]
    for i, (name, p) in enumerate(poses):
        x = 190 + i * 310
        p.x = x
        if name not in ("sneak", "exhausted"):
            sm.settle(p, gy)
        else:
            p = sm.gait(0.3 if name == "sneak" else 0.6, x, gy, 3.0, 1, "sneak" if name == "sneak" else "tired")
        sm.draw(c, p, shadow_y=gy)
        label(c, name, x, gy + 60)
    gy2 = 950
    for i in range(8):
        x = 140 + i * 230
        p = sm.gait(i / 8, x, gy2, 2.6, 1, "sprint")
        p.eye_s = 1.5
        sm.draw(c, p, shadow_y=gy2)
    label(c, "sprint cycle (8 frames, IK feet, no sliding)", W / 2, gy2 + 70)
    s.makeImageSnapshot().save(os.path.join(OUT, "stickman.png"))


def dino_sheet():
    s, c = canvas()
    label(c, "CREATURES  -  MODEL SHEET", W / 2, 70, 40)
    rex = D.Theropod(D.REX)
    rex.draw(c, dict(x=420, gy=520, s=0.9, f=1, t=0.2))
    label(c, "T-Rex: idle", 520, 570)
    rex.draw(c, dict(x=1260, gy=520, s=0.9, f=1, t=0.2, jaw=0.8, neck_up=0.45, head_pitch=-0.05, pitch=-0.05))
    label(c, "T-Rex: roar", 1360, 570)
    small = D.Theropod(D.SMALL)
    small.draw(c, dict(x=260, gy=950, s=2.4, f=1, t=0.2, neck_up=0.6))
    label(c, "small theropod", 300, 1000)
    D.rex_front(c, 760, 960, 0.75, 0.15, jaw=0.6)
    label(c, "T-Rex: front (charge)", 760, 1000)
    D.Sauropod().draw(c, dict(x=1170, gy=950, s=0.5, f=1, t=0.0, moving=False))
    label(c, "sauropod", 1300, 1000)
    D.ptero(c, 1720, 760, 2.4, 0.2)
    label(c, "pterosaur", 1700, 860)
    s.makeImageSnapshot().save(os.path.join(OUT, "creatures.png"))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    stickman_sheet()
    dino_sheet()
    print("wrote", OUT)
