#!/usr/bin/env python3
"""Soundtrack for the 3D test: character reactions (gasp, whimper, scream, panting),
footsteps synced to the gait, T-Rex steps/snort/roar, forest ambience and music."""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "audio"))

import numpy as np  # noqa: E402
from scipy.io import wavfile  # noqa: E402
from scipy.ndimage import maximum_filter1d  # noqa: E402

from synth import *  # noqa: E402,F401,F403
import test_scene as T  # noqa: E402

DUR = T.DURATION
N = n_of(DUR + 0.5)


class Bus:
    def __init__(self):
        self.x = np.zeros((N, 2))

    def add(self, t, sig, gain=1.0, pan=0.0, width=0.0):
        if sig.ndim == 1:
            sig = stereo(sig, pan, width)
        s = n_of(t)
        if s >= N:
            return
        e = min(N, s + len(sig))
        self.x[s:e] += sig[: e - s] * gain


voice_bus, sfx, amb, music = Bus(), Bus(), Bus(), Bus()


def contacts(mover, t0, t1):
    out, last = [], None
    t = t0
    while t < t1:
        k = int(mover.phase(t) * 2)
        if last is not None and k > last:
            out.append(t)
        last = k
        t += 1 / 480
    return out


def main():
    C = T.CUES
    # ---- ambience: birds and insects until the first thump, then a held breath of silence
    calm = n_of(C["thump1"] + 0.3)
    amb.add(0, birds(C["thump1"] + 0.3, 0.06, 3.0, seed=4) * env_ar(calm, 0.8, 0.3), width=0.8)
    amb.add(0, bp(pink(N), 3000, 8000)[:calm] * 0.008 * env_ar(calm, 1.0, 0.3), width=0.8)
    amb.add(0, wind(DUR, 0.05, 150, 900), width=0.8)
    # ---- music
    for m in (50, 57, 62, 66):
        music.add(0.2, strings(m, 5.0, amp=0.03, attack=1.2, release=0.4, bright=2200), pan=(m - 58) / 20)
    for i, m in enumerate((74, 78, 81, 78, 76, 74)):
        music.add(0.8 + i * 0.6, celesta(m, 1.6, 0.05), pan=0.3)
    music.add(C["thump1"], drone(26, C["run"] - C["thump1"], amp=0.07, attack=1.5, release=0.3, bright=260), width=0.4)
    for m in (62, 63):
        music.add(C["turn"], strings(m, C["run"] - C["turn"], amp=0.02, attack=1.0, release=0.2, bright=3500, trem=0.6),
                  pan=m - 62.5)
    music.add(7.15, braam(26, 3.0, 0.2), width=0.6)
    music.add(C["roar"] - 0.5, cymbal_swell(0.5, 0.08), width=0.8)
    music.add(C["roar"], braam(26, 2.5, 0.22), width=0.6)
    beat = 60 / 150
    t = C["run"]
    b = 0
    while t < DUR:
        music.add(t, taiko(0.22 if b % 2 == 0 else 0.15, 1.0 if b % 2 == 0 else 1.25))
        music.add(t + beat / 2, tom(0.08, 1.3), pan=-0.2)
        for s16 in range(4):
            mm = 50 + [12, 12, 19, 12][s16]
            music.add(t + s16 * beat / 4, strings(mm, beat / 4 * 0.6, amp=0.02, attack=0.005, release=0.06, bright=3200, voices=3),
                      pan=0.3)
        if b % 4 == 0:
            for iv in (0, 3, 7):
                music.add(t, brass(62 + iv, beat * 1.5, amp=0.04), pan=-0.2)
        t += beat
        b += 1
    # ---- the explorer's voice and body
    for t in contacts(T.WALK, 0.05, 4.25):
        sfx.add(t, step(0.06, "grass"), pan=-0.1)
    for t in contacts(T.RUN, 10.3, DUR):
        sfx.add(t, step(0.11, "grass"), pan=0.0)
    voice_bus.add(C["ooh"], ooh(0.95, 0.32), pan=-0.1)
    sfx.add(4.25, rustle(0.6, 0.04, 600, 4000), pan=0)
    voice_bus.add(C["gasp"], gasp(0.55))
    voice_bus.add(6.55, whimper(0.8, 0.22))
    for k, tt_ in enumerate((7.45, 7.95, 8.4)):
        voice_bus.add(tt_, shaky_breath(0.45, 0.2, inhale=k % 2 == 0))
    voice_bus.add(9.15, voice([(0, 480), (0.4, 430)], 0.45, "e", breath=0.5, vib=(9, 0.05), attack=0.03, release=0.2) * 0.18)
    voice_bus.add(C["scream"], scream(1.25, 0.62))
    voice_bus.add(C["pant"], pant(DUR - C["pant"], 3.6, 0.32))
    # ---- earth shakes and birds flee
    for tt_, a in ((C["thump1"], 0.55), (C["thump2"], 0.7)):
        sfx.add(tt_, big_step(a), width=0.3)
        sfx.add(tt_ + 0.05, rustle(1.0, 0.06, 1500, 7000, rate=30), width=0.8)
    sfx.add(C["thump1"] + 0.15, birds(1.4, 0.12, 14, seed=9), width=0.9)
    sfx.add(C["thump1"] + 0.1, rustle(1.4, 0.12, 1200, 7000, rate=60), width=0.9)
    # ---- the T-Rex
    for tt_ in T.rex_steps():
        sfx.add(tt_, big_step(0.85 if tt_ < 10 else 0.75), width=0.3)
        sfx.add(tt_, crack(0.1, 10, 0.25, seed=int(tt_ * 13)), pan=-0.2)
    sfx.add(7.15, crack(0.4, 60, 0.8, seed=3), pan=-0.2, width=0.5)
    sfx.add(7.2, rustle(1.5, 0.12, 500, 5000, rate=50), pan=-0.2, width=0.6)
    sfx.add(8.4, lp(noise(n_of(0.9)), 700) * env_exp(n_of(0.9), 0.35) * 0.25, width=0.4)
    sfx.add(C["roar"], roar(1.3, 0.95, 1.0, seed=3), width=0.4)
    sfx.add(C["roar"] + 0.04, roar(1.25, 0.5, 0.82, seed=5), width=0.6)
    sfx.add(C["roar"], boom(0.45, 55, 28, 1.6), width=0.3)
    sfx.add(10.5, roar(0.9, 0.55, 1.15, seed=9), width=0.4)
    sfx.add(12.0, roar(0.6, 0.5, 1.2, seed=11), width=0.4)
    # ---- mix
    ir = reverb_ir(1.8, 1.3, seed=5, bright=6000)
    m = apply_reverb(music.x, wet=0.4, ir=ir)
    v = apply_reverb(voice_bus.x, wet=0.12, ir=ir)
    s = apply_reverb(sfx.x, wet=0.15, ir=ir)
    mix = m * 1.0 + v * 1.0 + s * 1.0 + amb.x * 1.6
    for ch in range(2):
        mix[:, ch] = lp(hp(mix[:, ch], 22), 16500, order=4)
    mix = mix[: n_of(DUR)]
    rms = np.sqrt(np.mean(mix ** 2))
    mix *= 10 ** (-17 / 20) / max(rms, 1e-9)
    env = maximum_filter1d(np.abs(mix).max(1), size=n_of(0.01))
    gain = np.minimum(1.0, 0.7 / np.maximum(lp(env, 12, order=1), 1e-9))
    gain = -maximum_filter1d(-gain, size=n_of(0.01))
    mix *= gain[:, None]
    end = n_of(0.25)
    mix[-end:] *= np.linspace(1, 0, end)[:, None]
    mix *= 0.75 / max(np.abs(mix).max(), 1e-9) if np.abs(mix).max() > 0.75 else 1.0
    out = os.path.join(HERE, "test_audio.wav")
    wavfile.write(out, SR, (np.clip(mix, -1, 1) * 32767).astype(np.int16))
    print("wrote", out, mix.shape)


if __name__ == "__main__":
    main()
