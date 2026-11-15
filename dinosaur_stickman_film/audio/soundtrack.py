#!/usr/bin/env python3
"""Compose and mix the soundtrack: original score + sound design, synchronised to
the scene cues. Writes audio/soundtrack.wav (48 kHz, 16-bit stereo).

    python3 audio/soundtrack.py
"""
import math
import os
import sys

import numpy as np
from scipy.io import wavfile
from scipy.ndimage import maximum_filter1d, uniform_filter1d

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import scenes  # noqa: E402
from synth import *  # noqa: E402,F401,F403
import synth as S  # noqa: E402

CUE = scenes.cues()
TOTAL = scenes.total()
N = n_of(TOTAL + 1.0)


def C(name):
    return CUE[name]


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
        if s < 0:
            sig = sig[-s:]
            s = 0
            e = min(N, len(sig))
        self.x[s:e] += sig[: e - s] * gain


music, sfx, amb = Bus(), Bus(), Bus()


def chord(bus, t, notes, dur, amp=0.05, inst=strings, pan_spread=0.6, **kw):
    for i, m in enumerate(notes):
        pan = (i / max(1, len(notes) - 1) - 0.5) * pan_spread
        bus.add(t, inst(m, dur, amp=amp, **kw), pan=pan, width=0.3)


def melody(bus, t, notes, beat, inst=celesta, amp=0.1, pan=0.0, legato=1.0, **kw):
    """notes: [(midi or None, beats), ...]"""
    for m, b in notes:
        if m is not None:
            d = b * beat * legato
            if inst in (strings, brass, choir):
                bus.add(t, inst(m, d, amp=amp, **kw), pan=pan)
            else:
                bus.add(t, inst(m, max(d, 1.2), amp=amp, **kw), pan=pan)
        t += b * beat
    return t


# =============================================================== ACT 1
def act1():
    t0, t1 = 0.0, C("s02_something_wrong.start")
    # night ambience
    amb.add(0.0, crickets(11.5, 0.016) * env_ar(n_of(11.5), 2.5, 1.5), width=0.6)
    amb.add(0.0, wind(11.5, 0.05, 120, 700) * env_ar(n_of(11.5), 3, 1.5), width=0.7)
    amb.add(10.6, bp(pink(n_of(TOTAL)), 60, 400)[: n_of(46)] * 0.012, width=0.5)          # room tone
    amb.add(10.6, crickets(46, 0.004), width=0.6)
    # lullaby: pad + celesta
    prog = [[50, 57, 62, 64, 65], [46, 53, 58, 62, 69], [43, 50, 58, 62, 65], [45, 52, 57, 61, 64]]
    for i, ch in enumerate(prog * 2):
        t = 0.8 + i * 4.1
        if t > 26:
            break
        chord(music, t, ch, 4.6, amp=0.016, attack=1.6, release=2.0, bright=1500)
    lull = [(74, 1), (77, 1), (81, 2), (79, 1), (77, 1), (76, 2), (74, 1), (76, 1), (77, 1), (74, 1), (72, 2), (None, 2),
            (74, 1), (77, 1), (81, 2), (84, 1), (81, 1), (79, 2), (77, 1), (76, 1), (74, 4)]
    melody(music, 2.6, lull, 0.62, inst=celesta, amp=0.05, pan=0.2)
    sfx.add(C("s01_quiet_night.shift"), rustle(1.4, 0.05, 800, 4000, rate=8), pan=0.2)
    # something is wrong
    s2 = C("s02_something_wrong.start")
    music.add(s2 + 0.5, drone(26, 30, amp=0.05, attack=8, release=3, bright=300), width=0.4)
    for i, f in enumerate((1568, 1661, 2093, 2217)):
        n = n_of(22)
        tt_ = tt(n)
        glass = np.sin(2 * np.pi * f * tt_) * env_ar(n, 6, 4) * (0.5 + 0.5 * np.sin(2 * np.pi * (0.2 + 0.07 * i) * tt_))
        music.add(s2 + 2 + i * 1.5, glass * 0.006, pan=(i - 1.5) * 0.4)
    chord(music, s2 + 4.0, [51, 58, 63, 69], 7.0, amp=0.014, attack=3.0, release=2.0, bright=1200)
    s3 = C("s03_portal_opens.start")
    burst = C("s03_portal_opens.burst")

    def pw(tsec):
        a = s2 + 1.5 + tsec
        out = np.interp(a, [s2 + 1.5, burst - 0.5, burst + 0.2, C("s03_portal_opens.wind"), C("s04_enter_portal.tunnel"),
                            C("s04_enter_portal.silence")], [0.05, 0.6, 1.2, 1.5, 1.5, 1.5])
        return out
    hum = portal_hum(C("s04_enter_portal.silence") - (s2 + 1.5), 0.05, power=pw)
    hum *= env_ar(len(hum), 4.0, 0.05)
    sfx.add(s2 + 1.5, hum, width=0.5)
    sfx.add(C("s02_something_wrong.stir"), rustle(1.2, 0.05, 700, 3500, rate=10), pan=0.3)
    sfx.add(C("s02_something_wrong.eyes_full") + 0.3, heartbeat(0.25))
    sfx.add(C("s02_something_wrong.eyes_full") + 1.1, heartbeat(0.25))
    # portal opens
    sfx.add(burst - 1.0, riser(1.0, 0.12, 300, 2500))
    sfx.add(burst, boom(0.6, 70, 30, 2.5), width=0.4)
    music.add(burst, braam(26, 4.0, 0.12), width=0.5)
    music.add(burst, hp(noise(n_of(3.0)), 3000) * env_exp(n_of(3.0), 0.8) * 0.06, width=0.8)
    sfx.add(C("s03_portal_opens.sit_up"), rustle(0.9, 0.08, 600, 3500, rate=14), pan=0.3)
    sfx.add(C("s03_portal_opens.sit_up") + 0.1, breath(0.45, 0.05, True), pan=0.2)
    # eerie pulse + tremolo cluster
    beat = 60 / 96
    arp = [62, 63, 69, 70, 62, 63, 69, 74]
    t = C("s03_portal_opens.sit_up")
    k = 0
    while t < C("s04_enter_portal.tunnel"):
        u = (t - burst) / (C("s04_enter_portal.tunnel") - burst)
        music.add(t, pluck(arp[k % len(arp)] + 12, 0.4, amp=0.016 + 0.018 * u), pan=0.4 * math.sin(k))
        t += beat / 2
        k += 1
    for m in (50, 51, 57, 62, 63):
        music.add(burst + 1.5, strings(m, 17.5, amp=0.012, attack=6, release=2, bright=2500, trem=0.6), pan=(m - 56) / 14)
    for i, tt_ in enumerate((C("s03_portal_opens.out_of_bed") + 0.2, C("s03_portal_opens.steps"))):
        sfx.add(tt_, rustle(0.6, 0.05, 500, 3000, rate=8), pan=0.2)
    t = C("s03_portal_opens.steps")
    while t < C("s03_portal_opens.reach") - 0.1:
        sfx.add(t, step(0.035, "grass"), pan=-0.1)
        t += 0.42
    sfx.add(C("s03_portal_opens.spark"), zap(0.35), pan=-0.3)
    sfx.add(C("s03_portal_opens.spark"), boom(0.15, 120, 60, 0.4, 0.2))
    w = C("s03_portal_opens.wind")
    g = wind(C("s04_enter_portal.tunnel") - w, 0.22, 200, 2500, gust=0.6) * env_ar(n_of(C("s04_enter_portal.tunnel") - w), 0.8, 0.3)
    sfx.add(w, g, width=0.8, pan=-0.2)
    sfx.add(w + 0.3, rustle(3.5, 0.08, 1500, 8000, rate=30), pan=-0.3, width=0.5)     # papers
    for i in range(4):
        sfx.add(w + 0.6 + i * 0.55, thud(0.08, 1.4), pan=-0.2)                          # books
    sfx.add(C("s03_portal_opens.slip"), step(0.08, "grass"), pan=0.1)
    sfx.add(C("s03_portal_opens.breath_in"), breath(1.0, 0.09, True), pan=0.0)
    sfx.add(C("s03_portal_opens.breath_out"), breath(0.9, 0.08, False), pan=0.0)
    chord(music, C("s03_portal_opens.breath_in"), [46, 53, 58, 62, 64], 5.0, amp=0.02, attack=1.0, release=1.5, bright=2200)
    # the leap and the tunnel
    sfx.add(C("s04_enter_portal.crouch"), rustle(0.3, 0.04, 600, 3000), pan=0)
    sfx.add(C("s04_enter_portal.jump"), whoosh(1.2, 0.18, 400, 3000, 0.4), width=0.6)
    tun0, flash, sil = C("s04_enter_portal.tunnel"), C("s04_enter_portal.flash"), C("s04_enter_portal.silence")
    sfx.add(C("s04_enter_portal.into"), whoosh(1.6, 0.3, 200, 4000, 0.6), width=0.8)
    for i in range(10):
        tt_ = tun0 + i * 0.5
        sfx.add(tt_, whoosh(0.9, 0.08 + 0.01 * i, 300 + 80 * i, 3500, 0.5), pan=math.sin(i * 1.7) * 0.8)
    music.add(tun0 - 0.5, riser(sil - tun0 + 0.5, 0.18, 150, 2400), width=0.8)
    chord(music, tun0, [62, 69, 74, 78, 81], sil - tun0, amp=0.02, inst=choir, attack=2.0, release=0.05)
    sfx.add(flash - 0.2, hp(noise(n_of(sil - flash + 0.2)), 300) * fade_env(n_of(sil - flash + 0.2), [(0, 0), (sil - flash + 0.2, 0.25)]),
            width=0.8)


# =============================================================== ACT 2
def adventure_theme(t, beat, amp=1.0, variant=0):
    """D major: I - V - vi - IV with a rising horn theme."""
    prog = [[50, 57, 62, 66, 69], [45, 52, 57, 61, 64], [47, 54, 59, 62, 66], [43, 50, 55, 59, 62]]
    if variant:
        prog = [[43, 50, 55, 59, 62], [50, 57, 62, 66, 69], [45, 52, 57, 61, 64], [50, 57, 62, 66, 69]]
    for i, ch in enumerate(prog):
        chord(music, t + i * 4 * beat, ch, 4 * beat, amp=0.022 * amp, attack=0.6, release=1.2, bright=2600)
        music.add(t + i * 4 * beat, taiko(0.12 * amp, 0.9), pan=0)
        music.add(t + i * 4 * beat + 2 * beat, taiko(0.07 * amp, 1.1), pan=0.1)
    theme = [(62, 1), (66, 1), (69, 2), (71, 1), (69, 1), (66, 2), (64, 1), (66, 1), (67, 2), (69, 4), (None, 2)]
    if variant:
        theme = [(67, 1), (71, 1), (74, 2), (73, 1), (71, 1), (69, 2), (66, 1), (69, 1), (71, 2), (74, 4), (None, 2)]
    melody(music, t, theme, beat, inst=brass, amp=0.05 * amp, pan=-0.15, legato=0.95)
    melody(music, t + 2 * beat, [(m + 12 if m else None, b) for m, b in theme], beat, inst=strings, amp=0.012 * amp, pan=0.2)


def act2():
    s5 = C("s05_prehistoric_world.start")
    land = C("s05_prehistoric_world.land")
    sfx.add(s5 + 0.3, lp(noise(n_of(land - s5 - 0.3)), 900) * fade_env(n_of(land - s5 - 0.3), [(0, 0), (land - s5 - 0.6, 0.18), (land - s5 - 0.3, 0.3)]),
            width=0.8)
    sfx.add(land, thud(0.5, 0.9))
    sfx.add(land, rustle(1.4, 0.12, 900, 6000, rate=25), width=0.4)
    # forest ambience across Act 2 (+ valley)
    a0, a1 = land + 0.3, C("s11_second_attack.start")
    amb.add(a0, birds(a1 - a0, 0.03, 0.7, seed=3) * env_ar(n_of(a1 - a0), 2.5, 2.0), width=0.8, pan=0.2)
    amb.add(a0, wind(a1 - a0, 0.03, 200, 1200) * env_ar(n_of(a1 - a0), 2.5, 2.0), width=0.8)
    amb.add(a0, bp(pink(n_of(a1 - a0)), 3000, 8000) * 0.006 * env_ar(n_of(a1 - a0), 2.5, 2), width=0.8)   # insects
    sfx.add(C("s05_prehistoric_world.get_up"), rustle(1.5, 0.06, 700, 4000, rate=10), pan=0.1)
    # the reveal: adventure theme
    beat = 60 / 92
    t = C("s05_prehistoric_world.reveal")
    music.add(t - 1.5, cymbal_swell(1.5, 0.05), width=0.8)
    adventure_theme(t, beat, amp=1.0)
    adventure_theme(t + 16 * beat, beat, amp=0.85, variant=1)
    # the plant: celesta sparkle
    p = C("s05_prehistoric_world.plant")
    chord(music, p, [50, 57, 62, 66], 4.0, amp=0.014, attack=1.0, release=2.0, bright=1800)
    sfx.add(C("s05_prehistoric_world.touch"), celesta(86, 1.5, 0.05), pan=0.3)
    sfx.add(C("s05_prehistoric_world.touch") + 0.12, celesta(90, 1.5, 0.04), pan=0.3)
    sfx.add(C("s05_prehistoric_world.touch"), rustle(0.6, 0.04, 1500, 6000), pan=0.3)
    sfx.add(C("s05_prehistoric_world.grass"), rustle(1.2, 0.04, 2000, 7000, rate=20), pan=0.1)
    # S6: playful walk
    s6 = C("s06_first_dinosaurs.start")
    beat6 = 60 / 120
    walk_motif = [(62, 0.5), (66, 0.5), (69, 0.5), (66, 0.5), (64, 0.5), (67, 0.5), (71, 0.5), (67, 0.5)]
    t = s6
    while t < C("s06_first_dinosaurs.rustle"):
        t = melody(music, t, walk_motif, beat6, inst=pluck, amp=0.05, pan=0.2)
    chord(music, s6, [50, 57, 62], 4.0, amp=0.012, attack=0.5, release=1.0)
    t = s6
    while t < C("s06_first_dinosaurs.rustle") + 1.0:
        sfx.add(t, step(0.03, "grass"), pan=0)
        t += 0.5
    sfx.add(C("s06_first_dinosaurs.rustle"), rustle(2.2, 0.12, 600, 5000, rate=40), pan=0.4)
    sfx.add(C("s06_first_dinosaurs.pop"), rustle(0.5, 0.14, 600, 5000, rate=40), pan=0.4)
    sfx.add(C("s06_first_dinosaurs.jump_back"), pluck(74, 0.4, 0.06), pan=0)
    music.add(C("s06_first_dinosaurs.jump_back"), strings(74, 0.25, amp=0.03, attack=0.01, release=0.2, bright=4000))
    for k, tt_ in enumerate((0.8, 1.5, 2.6)):
        sfx.add(C("s06_first_dinosaurs.pop") + tt_, chirp(0.06, 2000 + 300 * k, 3200 + 200 * k, 0.15), pan=0.4)
    sfx.add(C("s06_first_dinosaurs.chirp"), chirp(0.09, 1800, 3600, 0.22), pan=0.4)
    sfx.add(C("s06_first_dinosaurs.chirp") + 0.25, chirp(0.07, 2400, 3900, 0.16), pan=0.4)
    curious = [(69, 1), (71, 1), (74, 2), (None, 1), (71, 1), (69, 2)]
    melody(music, C("s06_first_dinosaurs.pop") + 1.2, curious, 0.45, inst=celesta, amp=0.04, pan=0.1)
    sfx.add(C("s06_first_dinosaurs.run_off"), rustle(1.0, 0.1, 800, 5000, rate=30), pan=0.6)
    for k in range(6):
        sfx.add(C("s06_first_dinosaurs.run_off") + k * 0.13, step(0.03, "grass"), pan=0.6)
    sfx.add(C("s06_first_dinosaurs.relax"), breath(1.0, 0.05, False))
    # thumps approach
    th = [C("s06_first_dinosaurs.thump%d" % k) for k in range(1, 5)]
    for k, tt_ in enumerate(th):
        sfx.add(tt_, big_step(0.25 + 0.12 * k), width=0.3)
    music.add(th[0] - 0.2, drone(26, C("s07_trex.roar") - th[0] + 1.0, amp=0.05, attack=4, release=0.5, bright=250), width=0.4)
    sfx.add(C("s06_first_dinosaurs.birds"), rustle(1.5, 0.12, 1200, 7000, rate=60), width=0.8)
    sfx.add(C("s06_first_dinosaurs.birds"), birds(1.6, 0.12, 12, seed=8), width=0.9)
    sfx.add(C("s06_first_dinosaurs.turn") + 0.3, heartbeat(0.3))
    sfx.add(C("s06_first_dinosaurs.turn") + 1.1, heartbeat(0.3))
    # S7: the T-Rex
    import scenes.s07_trex as S7
    s7 = C("s07_trex.start")
    for tt_ in S7.STEPS:
        sfx.add(s7 + tt_, big_step(0.85), width=0.3)
        sfx.add(s7 + tt_, crack(0.12, 12, 0.3, seed=int(tt_ * 10)), pan=0.2)
    music.add(C("s07_trex.tilt"), braam(26, 4.5, 0.16), width=0.6)
    music.add(C("s07_trex.tilt") + 0.2, choir(50, 4.0, amp=0.03, attack=1.5, release=1.5, vowel="o"), width=0.5)
    for m in (74, 75):
        music.add(C("s07_trex.eye") - 0.3, strings(m, 2.4, amp=0.01, attack=1.0, release=0.4, bright=3500, trem=0.5), pan=(m - 74.5))
    sfx.add(C("s07_trex.snort"), lp(noise(n_of(0.8)), 1200) * env_exp(n_of(0.8), 0.25) * 0.25, width=0.4)
    r = C("s07_trex.roar")
    sfx.add(r, roar(2.5, 0.9, 1.0, seed=3), width=0.4)
    sfx.add(r + 0.05, roar(2.4, 0.5, 0.82, seed=5), width=0.6)
    sfx.add(r, boom(0.5, 55, 28, 2.0), width=0.3)
    music.add(r - 0.6, cymbal_swell(0.6, 0.06), width=0.8)
    music.add(r, braam(26, 3.5, 0.18), width=0.5)
    sil = C("s07_trex.silence")
    for k in range(4):
        sfx.add(sil + 0.2 + k * 0.62, heartbeat(0.35))
    sfx.add(sil + 0.5, breath(0.8, 0.04, True))
    sfx.add(sil + 1.6, lp(noise(n_of(1.0)), 600) * env_exp(n_of(1.0), 0.4) * 0.18, width=0.4)   # rex exhale
    lunge = C("s07_trex.lunge")
    sfx.add(lunge, roar(1.2, 0.8, 1.15, seed=9), width=0.4)
    sfx.add(lunge + 0.25, thud(0.4, 0.8))
    music.add(lunge, braam(26, 1.5, 0.15))


# =============================================================== chase music
def chase(t0, t1, bpm=140, amp=1.0, key=50, muffle=None):
    beat = 60 / bpm
    prog = [0, -4, -2, -5]       # Dm - Bb - C - A (roots relative)
    chords_ = {0: [0, 3, 7], -4: [0, 4, 7], -2: [0, 4, 7], -5: [0, 4, 7]}
    t = t0
    bar = 0
    out = Bus() if muffle else music
    while t < t1 - 0.05:
        root = key + prog[(bar // 2) % 4]
        fade = min(1.0, (t - t0) / 1.5) * min(1.0, (t1 - t) / 1.2)
        a = amp * fade
        for b in range(4):
            tb = t + b * beat
            if tb >= t1:
                break
            out.add(tb, taiko(0.16 * a, 1.0 if b % 2 == 0 else 1.25), pan=0)
            if b in (1, 3):
                out.add(tb, snare(0.05 * a), pan=0.15)
            out.add(tb + beat / 2, tom(0.06 * a, 1.4 if b % 2 else 1.1), pan=-0.2)
            for s16 in range(4):
                m = root + 12 + [0, 0, 7, 0, 3, 0, 7, 12][(b * 4 + s16) % 8]
                out.add(tb + s16 * beat / 4, strings(m, beat / 4 * 0.6, amp=0.012 * a, attack=0.005, release=0.06, bright=3200,
                                                      voices=3), pan=0.3 * math.sin(s16 + b))
        if bar % 2 == 0:
            for iv in chords_[prog[(bar // 2) % 4]]:
                out.add(t, brass(root + 12 + iv, beat * 1.6, amp=0.03 * a), pan=-0.2 + iv * 0.03)
            out.add(t, strings(root, beat * 8, amp=0.03 * a, attack=0.1, release=0.4, bright=900), pan=0)
        t += 4 * beat
        bar += 1
    if muffle:
        x = out.x
        x[:, 0] = lp(x[:, 0], muffle)
        x[:, 1] = lp(x[:, 1], muffle)
        music.x += x


def rex_steps(t0, t1, period=0.68, amp=0.6, skip=()):
    t = t0
    while t < t1:
        if not any(a <= t < b for a, b in skip):
            sfx.add(t, big_step(amp), width=0.3)
        t += period


# =============================================================== ACT 3
def act3():
    import scenes.s08_run as S8
    s8 = C("s08_run.start")
    run0 = C("s07_trex.run")
    chase(run0, C("s09_river.splash"), bpm=140, amp=1.0)
    rex_steps(run0 + 0.3, s8 + 23.0, 0.68, 0.55, skip=[(s8 + 5.5, s8 + 9.0)])
    # front shot: fast stomps
    t = s8 + 5.5
    while t < s8 + 9.0:
        sfx.add(t, big_step(0.6), width=0.3)
        t += 0.3125
    for th in S8.HIT_A:
        if th < 5.5:
            sfx.add(s8 + th, crack(0.4, 40, 0.5, seed=int(th * 7)), pan=-0.3, width=0.4)
            sfx.add(s8 + th, rustle(1.2, 0.15, 800, 6000, rate=50), pan=-0.3, width=0.5)
    for k, (lx, tj) in enumerate(S8.LOGS):
        sfx.add(s8 + tj - 0.3, whoosh(0.5, 0.06, 500, 2500), pan=0.2)
        sfx.add(s8 + tj + 0.3, step(0.08, "grass"), pan=0.2)
        sfx.add(s8 + S8.LOG_HIT[k], crack(0.5, 50, 0.4, seed=k + 11), pan=-0.2, width=0.4)
    sfx.add(s8 + S8.SLIDE_T0, rustle(0.8, 0.12, 300, 3000, rate=40), pan=0.1)
    sfx.add(s8 + S8.CRASH_T, crack(0.9, 120, 0.8, seed=21), width=0.6)
    sfx.add(s8 + S8.CRASH_T, boom(0.45, 70, 35, 1.2), width=0.4)
    sfx.add(s8 + S8.CRASH_T, rustle(2.0, 0.2, 600, 7000, rate=60), width=0.8)
    sfx.add(s8 + 17.6, roar(0.9, 0.6, 1.2, seed=12), width=0.3)
    sfx.add(s8 + 6.0, roar(1.8, 0.55, 1.05, seed=13), width=0.4)
    sfx.add(s8 + 20.8, roar(2.0, 0.4, 0.95, seed=14), width=0.6)
    # stickman footsteps & breath during the chase
    t = run0 + 0.4
    while t < C("s09_river.jump"):
        sfx.add(t, step(0.03, "grass"), pan=0.1)
        t += 0.24
    t = run0 + 1.0
    while t < C("s09_river.jump"):
        sfx.add(t, breath(0.3, 0.025, True), pan=0.05)
        sfx.add(t + 0.32, breath(0.3, 0.025, False), pan=0.05)
        t += 0.7
    # S9 river
    river0 = C("s09_river.start")
    amb.add(river0, bp(pink(n_of(21.5)), 200, 2500) * 0.035 * env_ar(n_of(21.5), 1.5, 1.5), width=0.8)
    sfx.add(C("s09_river.skid"), rustle(0.6, 0.1, 300, 3000, rate=30), pan=0)
    sfx.add(C("s09_river.roar_off"), roar(1.8, 0.35, 1.0, seed=15), pan=-0.6, width=0.4)
    sfx.add(C("s09_river.jump"), whoosh(0.7, 0.08, 400, 2500), pan=0.2)
    sfx.add(C("s09_river.splash"), splash(0.6, 1.4, seed=2), width=0.5)
    sfx.add(C("s09_river.splash"), boom(0.2, 90, 40, 0.6))
    music.add(C("s09_river.splash"), strings(50, 9.0, amp=0.02, attack=0.5, release=1.0, bright=1500, trem=0.7), pan=-0.2)
    music.add(C("s09_river.splash"), strings(57, 9.0, amp=0.016, attack=0.5, release=1.0, bright=1800, trem=0.7), pan=0.2)
    chase(C("s09_river.swim") + 0.5, C("s09_river.climb"), bpm=128, amp=0.55)
    t = C("s09_river.surface")
    while t < C("s09_river.climb") - 0.2:
        sfx.add(t, splash(0.08, 0.25, seed=int(t * 13)), pan=0.1)
        t += 1 / 2.6
    rex_steps(river0 + 6.6, river0 + 7.6, 0.34, 0.5)
    sfx.add(C("s09_river.rex_bank"), rustle(0.8, 0.12, 200, 2000, rate=40), pan=-0.4)
    sfx.add(C("s09_river.roar"), roar(1.6, 0.85, 1.0, seed=16), pan=-0.4, width=0.4)
    sfx.add(C("s09_river.roar"), boom(0.3, 55, 30, 1.2))
    import scenes.s09_river as S9
    walk = S9.D.REX["walk"]
    period = 1.0 / (150.0 * walk["duty"] / (walk["stride"] * S9.RS))
    t = C("s09_river.wade")
    while t < river0 + 15.5:
        sfx.add(t, splash(0.25, 0.7, seed=int(t * 3)), pan=-0.3)
        sfx.add(t, big_step(0.25), pan=-0.3)
        t += period / 2
    sfx.add(C("s09_river.climb"), splash(0.15, 0.5, seed=4), pan=0.3)
    sfx.add(C("s09_river.climb") + 0.8, step(0.08, "rock"), pan=0.3)
    sfx.add(C("s09_river.collapse") + 0.5, thud(0.25, 1.2), pan=0.3)
    t = C("s09_river.collapse") + 0.6
    while t < C("s09_river.get_up"):
        sfx.add(t, breath(0.45, 0.06, True), pan=0.2)
        sfx.add(t + 0.5, breath(0.5, 0.06, False), pan=0.2)
        t += 1.1
    sfx.add(C("s09_river.roar2"), roar(1.4, 0.7, 0.95, seed=17), pan=-0.5, width=0.5)
    music.add(C("s09_river.collapse"), drone(38, 5.5, amp=0.04, attack=1.0, release=2.0, bright=400), width=0.3)
    chase(C("s09_river.run"), C("s10_valley.start") + 1.0, bpm=140, amp=0.5)


def act3b():
    # S10 valley: wonder
    s10 = C("s10_valley.start")
    amb.add(s10, lp(noise(n_of(20.5)), 2500) * 0.012 * env_ar(n_of(20.5), 2, 2), width=0.8)       # distant waterfall
    beat = 60 / 76
    prog = [[50, 57, 62, 66, 69], [47, 54, 59, 62, 66], [43, 50, 55, 59, 62], [45, 52, 57, 61, 64]]
    t = C("s10_valley.reveal")
    for i, ch in enumerate(prog * 2):
        tt_ = t + i * 4 * beat
        if tt_ > C("s10_valley.lower"):
            break
        chord(music, tt_, ch, 4 * beat, amp=0.02, attack=1.2, release=1.8, bright=2200)
        chord(music, tt_, [ch[2] + 12, ch[4] + 12], 4 * beat, amp=0.012, inst=choir, attack=1.5, release=1.8)
    theme = [(66, 2), (69, 1), (74, 3), (73, 1), (71, 1), (69, 4), (66, 2), (67, 1), (69, 3), (62, 4)]
    melody(music, t + 4 * beat, theme, beat, inst=brass, amp=0.04, pan=-0.1, legato=0.98, bright=1800)
    for k, tt_ in enumerate((s10 + 3.0, s10 + 9.5)):
        n = n_of(2.4)
        call = lp(saw_f(np.interp(tt(n), [0, 1.2, 2.4], [95, 110, 80]), n), 600) * env_ar(n, 0.4, 1.0) * 0.06
        sfx.add(tt_, call, pan=0.5 - k, width=0.6)
    low = C("s10_valley.lower")
    music.add(low, strings(74, 3.0, amp=0.012, attack=0.8, release=1.0, bright=3000), pan=0.2)
    for k in range(4):
        sfx.add(C("s10_valley.freeze") + k * 0.75, heartbeat(0.22))
    sfx.add(C("s10_valley.snort"), lp(noise(n_of(1.0)), 900) * env_exp(n_of(1.0), 0.35) * 0.2, width=0.4)
    rel = C("s10_valley.turn_away")
    chord(music, rel + 0.6, [43, 50, 59, 62, 66], 3.5, amp=0.022, attack=1.0, release=1.5)
    sfx.add(rel + 0.6, breath(1.4, 0.05, False))
    chord(music, rel + 3.4, [50, 57, 62, 66, 69], 3.5, amp=0.02, attack=1.0, release=2.0)
    sfx.add(low + 0.6, lp(noise(n_of(2.0)), 300) * env_ar(n_of(2.0), 0.6, 1.0) * 0.12, width=0.3)   # huge body moving
    # S11 second attack
    r = C("s11_second_attack.roar")
    sfx.add(r, roar(2.4, 0.55, 0.95, seed=21), pan=-0.5, width=0.8)
    music.add(r, braam(26, 2.5, 0.14), width=0.6)
    sfx.add(r + 0.3, rustle(1.5, 0.08, 1500, 7000, rate=50), width=0.9)
    burst = C("s11_second_attack.burst")
    sfx.add(burst, crack(0.6, 80, 0.7, seed=31), pan=-0.5, width=0.5)
    sfx.add(burst + 0.1, roar(1.6, 0.8, 1.05, seed=22), pan=-0.4, width=0.4)
    n = n_of(2.4)
    call = lp(saw_f(np.interp(tt(n), [0, 0.4, 2.4], [120, 150, 90]), n), 700) * env_ar(n, 0.1, 1.2) * 0.07
    sfx.add(burst + 0.5, call, pan=0.6)
    rex_steps(burst, C("s11_second_attack.leap") - 0.3, 0.62, 0.55)
    chase(burst - 0.4, C("s11_second_attack.leap"), bpm=150, amp=1.0)
    t = burst + 2.0
    while t < C("s11_second_attack.leap"):
        sfx.add(t, step(0.04, "rock"), pan=0.1)
        t += 0.23
    leap = C("s11_second_attack.leap")
    sfx.add(leap, whoosh(0.6, 0.08, 500, 2500), pan=0.1)
    sfx.add(C("s11_second_attack.grab"), thud(0.3, 1.6))
    music.add(C("s11_second_attack.grab"), strings(75, 4.5, amp=0.016, attack=0.05, release=1.0, bright=4000, trem=0.6), pan=0.2)
    music.add(C("s11_second_attack.grab"), strings(74, 4.5, amp=0.016, attack=0.05, release=1.0, bright=4000, trem=0.6), pan=-0.2)
    music.add(C("s11_second_attack.grab"), drone(26, 4.5, amp=0.05, attack=0.2, release=1.0, bright=300))
    sfx.add(C("s11_second_attack.pebbles"), rocks(3.0, 0.08, density=4, seed=5), pan=0.1)
    sfx.add(C("s11_second_attack.reach"), breath(0.4, 0.06, True))
    sfx.add(C("s11_second_attack.pull"), breath(1.0, 0.08, False))
    sfx.add(C("s11_second_attack.over"), step(0.1, "rock"))
    music.add(C("s11_second_attack.over"), brass(62, 0.6, amp=0.04))
    sfx.add(C("s11_second_attack.roar2"), roar(1.2, 0.75, 1.0, seed=23), pan=-0.4, width=0.4)
    sfx.add(C("s11_second_attack.step"), big_step(0.7), width=0.3)
    chase(C("s11_second_attack.rex_edge"), C("s12_final_escape.inside"), bpm=150, amp=1.0)
    # S12 final escape
    s12 = C("s12_final_escape.start")
    rex_steps(s12, s12 + 2.0, 0.42, 0.55)
    sfx.add(C("s12_final_escape.ram"), boom(0.55, 70, 30, 1.6), width=0.5)
    sfx.add(C("s12_final_escape.ram"), rocks(1.0, 0.25, density=30, seed=7), width=0.5)
    sfx.add(C("s12_final_escape.ram") + 0.1, roar(1.5, 0.6, 1.1, seed=24), pan=-0.3)
    for k, tt_ in enumerate((C("s12_final_escape.snap1"), C("s12_final_escape.snap2"), C("s12_final_escape.snap2") + 0.55,
                             C("s12_final_escape.snap2") + 1.1, C("s12_final_escape.snap2") + 1.7)):
        sfx.add(tt_, thud(0.18, 1.8), pan=-0.4)
    chase(C("s12_final_escape.inside"), C("s12_final_escape.collapse"), bpm=150, amp=0.9, muffle=900)
    t = C("s12_final_escape.inside")
    while t < C("s12_final_escape.climb"):
        sfx.add(t, step(0.05, "rock"), pan=0.0)
        t += 0.27
    sfx.add(C("s12_final_escape.crack"), crack(0.3, 30, 0.6, seed=41), width=0.4)
    sfx.add(C("s12_final_escape.collapse"), boom(0.8, 60, 25, 3.0), width=0.5)
    sfx.add(C("s12_final_escape.collapse"), rocks(3.0, 0.45, density=40, seed=9), width=0.6)
    sfx.add(C("s12_final_escape.rumble"), rumble(4.0, 0.25) * env_ar(n_of(4.0), 0.1, 2.5), width=0.5)
    sfx.add(C("s12_final_escape.collapse") + 0.6, lp(roar(1.6, 0.5, 0.95, seed=25), 500), pan=-0.4)
    music.add(C("s12_final_escape.collapse"), braam(26, 3.0, 0.15))
    # the climb: tired strings
    cl = C("s12_final_escape.climb")
    chord(music, cl, [45, 52, 57, 60], 4.0, amp=0.016, attack=1.5, release=1.5, bright=1400)
    chord(music, cl + 4.0, [41, 48, 53, 57], 4.0, amp=0.018, attack=1.5, release=2.0, bright=1600)
    t = cl
    while t < C("s12_final_escape.top"):
        sfx.add(t, breath(0.5, 0.06, True), pan=0.1)
        sfx.add(t + 0.55, breath(0.55, 0.06, False), pan=0.1)
        t += 1.2
    t = cl + 0.2
    while t < C("s12_final_escape.top"):
        sfx.add(t, step(0.035, "rock"), pan=0.1)
        t += 0.55


# =============================================================== ACT 4
def act4():
    s13 = C("s13_beautiful_view.start")
    amb.add(s13, wind(34, 0.035, 150, 900, gust=0.5) * env_ar(n_of(34), 3, 3), width=0.8)
    amb.add(s13, birds(28, 0.012, 0.4, seed=11) * env_ar(n_of(28), 3, 3), width=0.8)
    beat = 60 / 66
    prog = [[48, 55, 60, 64, 67], [47, 55, 59, 62, 67], [45, 52, 57, 60, 64], [41, 48, 53, 57, 60]]
    t = C("s12_final_escape.top")
    music.add(t, cymbal_swell(1.5, 0.03), width=0.8)
    i = 0
    end = C("s14_sky_light.bright")
    while t < end:
        ch = prog[i % 4]
        d = min(4 * beat, end - t + 0.5)
        chord(music, t, ch, d, amp=0.022, attack=1.2, release=2.2, bright=2000)
        for k in range(8):
            tk = t + k * beat / 2
            if tk < end:
                music.add(tk, piano(ch[[2, 3, 4, 3, 2, 3, 4, 3][k]] + 12, 2.2, amp=0.035), pan=0.25)
        t += 4 * beat
        i += 1
    theme = [(76, 3), (74, 1), (72, 2), (74, 2), (76, 3), (79, 1), (77, 4), (None, 2), (72, 2), (71, 2), (69, 3), (71, 1), (72, 6)]
    melody(music, C("s13_beautiful_view.breath") + 0.5, theme, beat, inst=strings, amp=0.03, pan=-0.1, legato=1.0, bright=2600,
           attack=0.4, release=1.2)
    melody(music, C("s13_beautiful_view.behind") + 4 * beat, [(64, 6), (65, 2), (67, 8)], beat, inst=brass, amp=0.025, pan=0.2,
           bright=1500)
    sfx.add(C("s13_beautiful_view.sit"), rustle(0.5, 0.05, 400, 3000), pan=0.1)
    t = C("s13_beautiful_view.sit")
    while t < C("s13_beautiful_view.behind"):
        sfx.add(t, breath(0.4, 0.05, True), pan=0.1)
        sfx.add(t + 0.42, breath(0.45, 0.05, False), pan=0.1)
        t += 0.95
    sfx.add(C("s13_beautiful_view.exhale"), breath(2.2, 0.08, False), pan=0.0)
    # S14: darkening
    s14b = C("s14_sky_light.bright")
    music.add(C("s14_sky_light.light"), celesta(93, 2.5, 0.025), pan=0.5)
    music.add(C("s14_sky_light.notice"), celesta(92, 2.5, 0.02), pan=0.5)
    music.add(s14b, drone(26, C("s16_impact.impact") - s14b, amp=0.06, attack=5, release=0.1, bright=280), width=0.4)
    chord(music, s14b, [45, 52, 57, 60, 63], 6.0, amp=0.02, attack=2.0, release=2.0, bright=1400)
    chord(music, s14b + 6.0, [44, 51, 56, 59, 62], 5.0, amp=0.022, attack=1.5, release=1.5, bright=1600, trem=0.3)
    sfx.add(C("s14_sky_light.trail"), rumble(7, 0.08) * env_ar(n_of(7), 4, 1), width=0.5)
    sfx.add(C("s14_sky_light.stand"), rustle(0.6, 0.04, 500, 3000), pan=0.1)
    sfx.add(C("s14_sky_light.realize"), boom(0.25, 60, 30, 1.5))
    music.add(C("s14_sky_light.realize"), strings(62, 3.0, amp=0.02, attack=0.05, release=1.5, bright=3500, trem=0.5))
    music.add(C("s14_sky_light.realize"), strings(63, 3.0, amp=0.02, attack=0.05, release=1.5, bright=3500, trem=0.5))


# =============================================================== ACT 5
def act5():
    s15 = C("s15_asteroid.start")
    imp = C("s16_impact.impact")
    chord(music, s15, [38, 50, 51, 57, 62, 63], imp - s15, amp=0.016, inst=choir, attack=2.5, release=0.3, vowel="o")
    sfx.add(s15, rumble(imp - s15, 0.2) * fade_env(n_of(imp - s15), [(0, 0.2), (imp - s15 - 1, 1.0), (imp - s15, 1.0)]), width=0.6)
    n = n_of(imp - s15)
    whistle = np.sin(2 * np.pi * np.cumsum(np.geomspace(900, 160, n)) / SR) * fade_env(n, [(0, 0), (imp - s15, 0.03)])
    sfx.add(s15, whistle, width=0.3)
    for k, tt_ in enumerate((C("s15_asteroid.panic"), C("s15_asteroid.panic") + 1.4)):
        sfx.add(tt_, roar(1.2, 0.2, 1.3 + 0.2 * k, seed=40 + k), pan=-0.6 + 1.0 * k, width=0.6)
    sfx.add(C("s15_asteroid.panic"), birds(3.0, 0.08, 10, seed=12), width=0.9)
    sfx.add(C("s15_asteroid.panic"), rustle(3.0, 0.08, 1200, 7000, rate=60), width=0.9)
    rex_steps(C("s15_asteroid.panic"), C("s15_asteroid.cliff"), 0.31, 0.12)
    t = C("s15_asteroid.cliff")
    while t < imp:
        sfx.add(t, heartbeat(0.32))
        t += 0.55
    music.add(C("s15_asteroid.cliff"), braam(26, 3.0, 0.14), width=0.5)
    music.add(C("s15_asteroid.face"), braam(25, 3.0, 0.16), width=0.5)
    music.add(imp - 2.2, riser(2.2, 0.2, 100, 1500), width=0.8)
    sfx.add(C("s16_impact.entry"), lp(noise(n_of(imp - C("s16_impact.entry"))), 1500) *
            fade_env(n_of(imp - C("s16_impact.entry")), [(0, 0.05), (imp - C("s16_impact.entry"), 0.45)]), width=0.8)
    # impact
    sfx.add(imp, explosion(1.0, 8.0), width=0.5)
    sfx.add(imp + 0.03, boom(0.9, 45, 22, 4.0, 0.6), width=0.3)
    music.add(imp, braam(26, 6.0, 0.2), width=0.6)
    music.add(imp, choir(38, 6.0, amp=0.03, attack=0.05, release=3.0, vowel="a"), width=0.6)
    wv = C("s16_impact.wave_hits")
    sfx.add(wv - 0.8, wind(C("s16_impact.world") - wv + 0.8, 0.5, 80, 3000, gust=0.3) *
            fade_env(n_of(C("s16_impact.world") - wv + 0.8), [(0, 0), (1.5, 0.8), (C("s16_impact.world") - wv + 0.8, 1.0)]), width=0.8)
    sfx.add(wv, rocks(3.0, 0.3, density=30, seed=11), width=0.8)
    sfx.add(C("s16_impact.engulf"), boom(0.5, 50, 25, 2.0), width=0.5)
    w0 = C("s16_impact.world")
    end = C("s16_impact.silence")
    sfx.add(w0, rumble(end - w0, 0.45) * fade_env(n_of(end - w0), [(0, 1), (end - w0 - 1.0, 0.8), (end - w0 - 0.05, 0.0), (end - w0, 0)]),
            width=0.6)
    # final image: silence, wind, the closing note
    ash0 = C("s17_final_image.ashland")
    amb.add(ash0, wind(9.0, 0.03, 120, 600, gust=0.3) * env_ar(n_of(9.0), 2.0, 1.5), width=0.8)
    n = n_of(8.5)
    emb = bp(noise(n), 2000, 7000) * (RNG.random(n) < 0.002) * 2
    amb.add(ash0 + 0.5, emb * 0.05 * env_ar(n, 2, 2), width=0.8)
    music.add(ash0 + 1.0, drone(38, 9.0, amp=0.025, attack=3, release=3, bright=200), width=0.5)
    ti = C("s17_final_image.title")
    for m in (38, 45, 50, 57):
        music.add(ti, piano(m, 6.0, amp=0.07), pan=(m - 47) / 20)
    chord(music, ti, [50, 57, 62, 64, 65], 5.0, amp=0.02, attack=1.5, release=3.5, bright=1600)
    tg = C("s17_final_image.tagline")
    music.add(tg, celesta(86, 3.5, 0.03), pan=0.2)
    music.add(tg + 0.05, piano(74, 3.5, amp=0.04), pan=-0.1)
    chord(music, tg, [62, 69, 74], 2.6, amp=0.012, attack=1.2, release=0.6, bright=2000)


# =============================================================== mix
def level(x, target_db=-24.0, max_boost=5.0, min_gain=0.5, win=1.6):
    """Slow 'riding the fader' leveller: lifts quiet passages, tames loud ones."""
    p = uniform_filter1d((x ** 2).mean(1), size=n_of(win))
    rms = np.sqrt(np.maximum(p, 1e-12))
    g = np.clip(10 ** (target_db / 20) / rms, min_gain, max_boost)
    g = uniform_filter1d(g, size=n_of(win))
    return x * g[:, None]


def master():
    ir_m = reverb_ir(3.2, 2.6, seed=5, bright=5000)
    ir_s = reverb_ir(1.6, 1.2, seed=9, bright=7000)
    m = apply_reverb(music.x, wet=0.45, ir=ir_m)
    m = level(m, target_db=-25.0)
    s = apply_reverb(sfx.x, wet=0.18, ir=ir_s)
    a = amb.x
    mix = m * 1.0 + s * 1.0 + a * 1.7
    for ch in range(2):
        mix[:, ch] = hp(mix[:, ch], 22)
        mix[:, ch] = lp(mix[:, ch], 16500, order=4)
    # hard silence where the story asks for it
    for a0, a1 in ((C("s04_enter_portal.silence"), C("s05_prehistoric_world.fall")),
                   (C("s16_impact.silence"), C("s17_final_image.ashland") - 0.3)):
        i0, i1 = n_of(a0), n_of(a1)
        ramp = n_of(0.04)
        mix[i0:i0 + ramp] *= np.linspace(1, 0, ramp)[:, None]
        mix[i0 + ramp:i1] = 0
    # loudness: normalise RMS of the loud passages, then a smooth peak limiter
    blocks = (mix[: len(mix) // n_of(0.4) * n_of(0.4)] ** 2).mean(1).reshape(-1, n_of(0.4)).mean(1)
    gated = blocks[blocks > 10 ** (-50 / 10) * blocks.max()]
    rms = np.sqrt(gated.mean())
    mix *= 10 ** (-16.0 / 20) / max(rms, 1e-9)
    thr = 0.70
    env = maximum_filter1d(np.abs(mix).max(1), size=n_of(0.01))
    env = lp(env, 12, order=1)
    env = np.maximum(env, maximum_filter1d(np.abs(mix).max(1), size=n_of(0.002)))
    gain = np.minimum(1.0, thr / np.maximum(env, 1e-9))
    gain = -maximum_filter1d(-gain, size=n_of(0.01))
    mix *= gain[:, None]
    for ch in range(2):
        mix[:, ch] = lp(mix[:, ch], 17000, order=2)
    peak = np.abs(mix).max()
    if peak > 0.75:
        mix *= 0.75 / peak
    return mix


def main():
    out = os.path.join(ROOT, "audio", "soundtrack.wav")
    print("total", TOTAL, "s")
    act1()
    print("act 1")
    act2()
    print("act 2")
    act3()
    act3b()
    print("act 3")
    act4()
    print("act 4")
    act5()
    print("act 5")
    mix = master()
    mix = mix[: n_of(TOTAL)]
    wavfile.write(out, SR, (np.clip(mix, -1, 1) * 32767).astype(np.int16))
    print("wrote", out, mix.shape, "peak", float(np.abs(mix).max()))


if __name__ == "__main__":
    main()
