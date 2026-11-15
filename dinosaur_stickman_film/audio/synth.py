"""Small synthesis toolkit: oscillators, filters, envelopes, instruments and sound
effects. Everything is generated from numpy; no samples or external assets."""
import numpy as np
from scipy import signal

SR = 48000
RNG = np.random.default_rng(7)


def n_of(sec):
    return max(1, int(round(sec * SR)))


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def tt(n):
    return np.arange(n) / SR


# ----------------------------------------------------------------- filters
def _sos(kind, f, order=2):
    nyq = SR / 2
    if kind == "band":
        lo, hi = max(10, f[0]), min(nyq * 0.98, f[1])
        return signal.butter(order, [lo, hi], "bandpass", fs=SR, output="sos")
    return signal.butter(order, min(max(10, f), nyq * 0.98), kind, fs=SR, output="sos")


def lp(x, f, order=2):
    return signal.sosfilt(_sos("low", f, order), x)


def hp(x, f, order=2):
    return signal.sosfilt(_sos("high", f, order), x)


def bp(x, lo, hi, order=2):
    return signal.sosfilt(_sos("band", (lo, hi), order), x)


def sweep_filter(x, centers, width=0.6, kind="band"):
    """Time-varying band-pass by crossfading fixed filters along a centre-frequency curve."""
    n = len(x)
    cs = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(centers)), centers)
    bands = np.geomspace(max(40, cs.min()), cs.max() * 1.001, 8)
    out = np.zeros(n)
    outs = [bp(x, b * (1 - width / 2), b * (1 + width / 2)) for b in bands]
    lc = np.log(cs)
    lb = np.log(bands)
    for i, b in enumerate(bands):
        w = np.clip(1 - np.abs(lc - lb[i]) / (lb[1] - lb[0] + 1e-9), 0, 1)
        out += outs[i] * w
    return out


# ----------------------------------------------------------------- envelopes
def env_ar(n, a, r, curve=2.0):
    e = np.ones(n)
    na, nr = min(n, n_of(a)), min(n, n_of(r))
    if na > 0:
        e[:na] = np.linspace(0, 1, na) ** curve
    if nr > 0:
        e[-nr:] *= np.linspace(1, 0, nr) ** curve
    return e


def env_exp(n, decay, attack=0.002):
    t = tt(n)
    e = np.exp(-t / max(decay, 1e-4))
    na = n_of(attack)
    if na > 1:
        e[:na] *= np.linspace(0, 1, na)
    return e


def fade_env(n, pts):
    """Piecewise linear envelope from [(sec, value), ...]."""
    t = tt(n)
    xs, ys = zip(*pts)
    return np.interp(t, xs, ys)


# ----------------------------------------------------------------- oscillators
def saw_f(freq, n):
    """Saw with a frequency array or scalar (phase integrated)."""
    if np.isscalar(freq):
        ph = (freq * tt(n)) % 1.0
    else:
        ph = np.cumsum(freq) / SR % 1.0
    return 2 * ph - 1


def sine_f(freq, n, phase=0.0):
    if np.isscalar(freq):
        return np.sin(2 * np.pi * freq * tt(n) + phase)
    return np.sin(2 * np.pi * np.cumsum(freq) / SR + phase)


def noise(n):
    return RNG.standard_normal(n)


def pink(n):
    w = RNG.standard_normal(n)
    b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
    a = [1, -2.494956002, 2.017265875, -0.522189400]
    return signal.lfilter(b, a, w) * 3.0


def brown(n):
    x = np.cumsum(RNG.standard_normal(n))
    x = hp(x, 20)
    return x / (np.abs(x).max() + 1e-9)


def stereo(x, pan=0.0, width=0.0):
    """pan -1..1. width adds a short decorrelating delay on one side."""
    l = x * np.cos((pan + 1) * np.pi / 4)
    r = x * np.sin((pan + 1) * np.pi / 4)
    if width > 0:
        d = int(width * 0.012 * SR)
        r = np.concatenate([np.zeros(d), r[:-d]]) if d > 0 else r
    return np.stack([l, r], 1)


# ----------------------------------------------------------------- instruments
def strings(midi, dur, amp=0.1, attack=0.9, release=1.6, bright=2200, voices=5, vib=0.0045, trem=0.0):
    n = n_of(dur + release)
    t = tt(n)
    f = mtof(midi)
    out = np.zeros(n)
    for k in range(voices):
        det = 1 + (k - (voices - 1) / 2) * 0.0032
        fv = f * det * (1 + vib * np.sin(2 * np.pi * (5.1 + 0.3 * k) * t + k))
        out += saw_f(fv, n)
    out = lp(out / voices, bright)
    out = lp(out, bright * 1.6)
    e = env_ar(n, attack, release, 1.6)
    hold = n_of(dur)
    e[hold:] = e[hold:] * np.linspace(1, 0, n - hold) if n > hold else e[hold:]
    if trem > 0:
        e *= 1 - trem * (0.5 + 0.5 * np.sin(2 * np.pi * 11 * t))
    return out * e * amp


def brass(midi, dur, amp=0.1, attack=0.08, release=0.5, bright=2600):
    n = n_of(dur + release)
    t = tt(n)
    f = mtof(midi) * (1 + 0.003 * np.sin(2 * np.pi * 4.8 * t))
    raw = 0.6 * saw_f(f, n) + 0.4 * saw_f(f * 1.003, n)
    dark = lp(raw, 500)
    br = lp(raw, bright)
    fe = np.clip(tt(n) / max(attack * 3, 0.05), 0, 1) * np.exp(-tt(n) / (dur + 0.4) * 0.8)
    x = dark * (1 - fe) + br * fe
    e = env_ar(n, attack, release, 1.4)
    e[n_of(dur):] *= np.linspace(1, 0, n - n_of(dur)) if n > n_of(dur) else 1
    return np.tanh(x * 1.5) * e * amp


def piano(midi, dur=3.0, amp=0.15, bright=1.0):
    n = n_of(dur)
    t = tt(n)
    f = mtof(midi)
    out = np.zeros(n)
    for k in range(1, 9):
        fk = f * k * (1 + 0.0004 * k * k)
        if fk > SR / 2.2:
            break
        out += np.sin(2 * np.pi * fk * t) * (1 / k ** (1.4 / bright)) * np.exp(-t * (0.6 + 0.9 * k) * (220 / max(f, 60)) ** 0.3)
    hammer = bp(noise(n), 1000, 5000) * np.exp(-t * 80) * 0.05
    return (out * 0.5 + hammer) * env_ar(n, 0.003, 0.3) * amp


def celesta(midi, dur=2.5, amp=0.1):
    n = n_of(dur)
    t = tt(n)
    f = mtof(midi)
    x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 4.0 * t) * np.exp(-t * 6) + 0.15 * np.sin(2 * np.pi * f * 2.0 * t)
    return x * np.exp(-t * 1.6) * env_ar(n, 0.002, 0.2) * amp


def pluck(midi, dur=0.6, amp=0.1):
    n = n_of(dur)
    t = tt(n)
    f = mtof(midi)
    x = sum(np.sin(2 * np.pi * f * k * t) * np.exp(-t * (8 + 6 * k)) / k for k in range(1, 6))
    return x * env_ar(n, 0.002, 0.05) * amp


def choir(midi, dur, amp=0.08, attack=1.5, release=2.0, vowel="a"):
    n = n_of(dur + release)
    t = tt(n)
    out = np.zeros(n)
    for k in range(4):
        fv = mtof(midi) * (1 + (k - 1.5) * 0.004) * (1 + 0.006 * np.sin(2 * np.pi * (5 + 0.4 * k) * t + k))
        out += saw_f(fv, n)
    forms = {"a": [(700, 1.0), (1220, 0.6), (2600, 0.25)], "o": [(450, 1.0), (800, 0.5), (2830, 0.15)],
             "u": [(325, 1.0), (700, 0.3), (2530, 0.1)]}[vowel]
    y = sum(bp(out, f * 0.85, f * 1.15) * g for f, g in forms)
    e = env_ar(n, attack, release, 1.5)
    e[n_of(dur):] *= np.linspace(1, 0, n - n_of(dur)) if n > n_of(dur) else 1
    return y * e * amp


def drone(midi, dur, amp=0.1, attack=2.0, release=2.0, bright=600):
    n = n_of(dur)
    t = tt(n)
    f = mtof(midi)
    x = saw_f(f * (1 + 0.002 * np.sin(2 * np.pi * 0.1 * t)), n) + 0.7 * saw_f(f * 1.5 * 1.001, n) + 0.5 * np.sin(2 * np.pi * f / 2 * t)
    x = lp(x, bright)
    return x * env_ar(n, attack, release, 1.5) * amp


# ----------------------------------------------------------------- percussion
def taiko(amp=0.5, pitch=1.0, decay=0.5):
    n = n_of(decay * 3)
    t = tt(n)
    f = (55 + 70 * np.exp(-t * 25)) * pitch
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / decay)
    skin = bp(noise(n), 80, 900) * np.exp(-t * 30) * 0.6
    return np.tanh((body + skin) * 1.4) * amp


def tom(amp=0.3, pitch=1.0):
    n = n_of(0.6)
    t = tt(n)
    f = (110 + 80 * np.exp(-t * 30)) * pitch
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7) + bp(noise(n), 200, 2000) * np.exp(-t * 40) * 0.3) * amp


def snare(amp=0.2):
    n = n_of(0.3)
    t = tt(n)
    return (bp(noise(n), 1500, 7000) * np.exp(-t * 18) + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * 0.5) * amp


def hat(amp=0.08):
    n = n_of(0.08)
    return hp(noise(n), 7000) * np.exp(-tt(n) * 60) * amp


def cymbal_swell(dur, amp=0.15):
    n = n_of(dur)
    t = tt(n)
    return hp(noise(n), 4000) * (t / dur) ** 2.5 * amp


def boom(amp=0.8, f0=60, f1=28, decay=2.5, noise_amt=0.4):
    n = n_of(decay * 2.5)
    t = tt(n)
    f = f1 + (f0 - f1) * np.exp(-t * 6)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / decay)
    nz = lp(noise(n), 400) * np.exp(-t / (decay * 0.4)) * noise_amt
    return np.tanh((s + nz) * 1.6) * amp


def braam(midi=26, dur=3.5, amp=0.5):
    n = n_of(dur)
    t = tt(n)
    x = np.zeros(n)
    for m, g in ((midi, 1.0), (midi + 12, 0.7), (midi + 7, 0.5), (midi + 19, 0.3)):
        for d in (-0.004, 0.0, 0.004):
            x += saw_f(mtof(m) * (1 + d), n) * g
    cut = 200 + 1800 * np.clip(t / 0.4, 0, 1) * np.exp(-t / dur * 1.5)
    y = lp(x, 1600) * (cut / 2000) + lp(x, 300) * (1 - cut / 2000)
    e = env_ar(n, 0.05, dur * 0.7, 1.2)
    return np.tanh(y * 0.6) * e * amp


def riser(dur, amp=0.25, f0=200, f1=1800):
    n = n_of(dur)
    t = tt(n)
    u = t / dur
    nz = sweep_filter(noise(n), np.geomspace(f0 * 2, f1 * 3, 16), width=0.5)
    tone = np.sin(2 * np.pi * np.cumsum(f0 * (f1 / f0) ** u) / SR) * 0.3
    return (nz * 0.6 + tone) * u ** 2.2 * amp


def heartbeat(amp=0.5):
    n = n_of(0.7)
    t = tt(n)
    a = np.sin(2 * np.pi * 52 * t) * np.exp(-t * 18)
    t2 = np.clip(t - 0.22, 0, None)
    b = np.sin(2 * np.pi * 46 * t2) * np.exp(-t2 * 16) * (t > 0.22) * 0.75
    return lp(a + b, 200) * amp


# ----------------------------------------------------------------- sound effects
def wind(dur, amp=0.1, lo=150, hi=900, gust=0.4, seed=0):
    n = n_of(dur)
    t = tt(n)
    x = bp(pink(n), lo, hi)
    g = 1 + gust * (np.sin(2 * np.pi * 0.13 * t + seed) + 0.6 * np.sin(2 * np.pi * 0.31 * t + seed * 2))
    return x * g * amp


def crickets(dur, amp=0.02):
    n = n_of(dur)
    t = tt(n)
    out = np.zeros(n)
    for k, (f, rate, ph) in enumerate(((4300, 3.1, 0), (4700, 2.6, 1.3), (3900, 3.6, 2.1))):
        chirp = (np.sin(2 * np.pi * rate * t + ph) > 0.55).astype(float)
        chirp = lp(chirp, 60)
        out += np.sin(2 * np.pi * f * t) * chirp * (0.5 + 0.5 * np.sin(2 * np.pi * 40 * t))
    return out * amp


def birds(dur, amp=0.05, density=0.8, seed=1):
    n = n_of(dur)
    out = np.zeros(n)
    rng = np.random.default_rng(seed)
    k = int(dur * density)
    for i in range(k):
        st = rng.uniform(0, dur - 0.6)
        nn = n_of(rng.uniform(0.06, 0.18))
        t = tt(nn)
        f0, f1 = rng.uniform(2200, 4200), rng.uniform(2600, 5200)
        reps = rng.integers(1, 4)
        for r in range(reps):
            s = n_of(st + r * 0.15)
            if s + nn >= n:
                break
            f = np.linspace(f0, f1, nn) * (1 + 0.04 * np.sin(2 * np.pi * 30 * t))
            out[s:s + nn] += np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / t[-1]) * rng.uniform(0.3, 1.0)
    return out * amp


def whoosh(dur, amp=0.3, f0=300, f1=2500, peak=0.5):
    n = n_of(dur)
    t = tt(n) / dur
    x = sweep_filter(noise(n), np.geomspace(f0, f1, 12) if f1 > f0 else np.geomspace(f0, f1, 12), width=0.8)
    e = np.where(t < peak, (t / peak) ** 2, ((1 - t) / (1 - peak)) ** 1.5)
    return x * e * amp


def thud(amp=0.5, pitch=1.0):
    n = n_of(0.8)
    t = tt(n)
    f = (80 + 60 * np.exp(-t * 30)) * pitch
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9) + lp(noise(n), 900) * np.exp(-t * 25) * 0.6) * amp


def rustle(dur, amp=0.15, lo=1500, hi=7000, rate=18):
    n = n_of(dur)
    t = tt(n)
    gr = lp((RNG.random(n) < rate / SR * 40).astype(float), 300) * 4
    return bp(noise(n), lo, hi) * (0.3 + gr) * env_ar(n, 0.05, dur * 0.4) * amp


def step(amp=0.12, kind="grass"):
    n = n_of(0.12)
    t = tt(n)
    if kind == "rock":
        x = bp(noise(n), 800, 5000) * np.exp(-t * 60) + np.sin(2 * np.pi * 140 * t) * np.exp(-t * 50) * 0.5
    else:
        x = bp(noise(n), 400, 4000) * np.exp(-t * 35) + np.sin(2 * np.pi * 90 * t) * np.exp(-t * 40) * 0.4
    return x * amp


def big_step(amp=0.8):
    n = n_of(2.2)
    t = tt(n)
    f = 34 + 40 * np.exp(-t * 14)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.4)
    thump = lp(noise(n), 300) * np.exp(-t * 14)
    rattle = bp(noise(n), 1500, 6000) * np.exp(-t * 7) * (0.5 + 0.5 * np.sin(2 * np.pi * 23 * t)) * 0.12
    return np.tanh((sub * 1.2 + thump * 0.7 + rattle) * 1.3) * amp


def roar(dur=2.6, amp=0.8, pitch=1.0, seed=3):
    """Synthesised dinosaur roar: a rough, formant-filtered growl over noise and sub."""
    n = n_of(dur + 0.8)
    t = tt(n)
    rng = np.random.default_rng(seed)
    contour = np.interp(t, [0, 0.25, 0.7, dur * 0.8, dur + 0.8], [0.7, 1.05, 1.0, 0.8, 0.55])
    jitter = lp(rng.standard_normal(n), 8) * 4
    f0 = (62 + jitter) * contour * pitch
    rough = 1 + 0.35 * np.sin(2 * np.pi * (26 + 6 * np.sin(2 * np.pi * 0.7 * t)) * t)
    g = saw_f(f0 * rough, n) + 0.6 * saw_f(f0 * 2.01, n) + 0.4 * saw_f(f0 * 2.97, n)
    nz = noise(n) * (0.6 + 0.4 * np.sin(2 * np.pi * 31 * t))
    src = g * 0.7 + nz * 0.5
    open_ = np.interp(t, [0, 0.3, dur * 0.7, dur + 0.8], [0.3, 1.0, 0.9, 0.4])
    f1 = sweep_filter(src, 300 + 450 * open_[:: max(1, n // 64)], width=0.5)
    f2 = bp(src, 900, 1700) * 0.5
    f3 = bp(src, 2200, 3600) * 0.15
    sub = np.sin(2 * np.pi * np.cumsum(f0 * 0.5) / SR) * 0.6
    y = f1 + f2 + f3 + sub
    y = np.tanh(y * 2.2)
    y = lp(y, 5000)
    e = env_ar(n, 0.12, 0.9, 1.3)
    e *= np.interp(t, [0, dur, dur + 0.8], [1, 1, 0])
    return y * e * amp


def chirp(amp=0.2, f0=1800, f1=3200, dur=0.18):
    n = n_of(dur)
    t = tt(n)
    f = np.linspace(f0, f1, n) * (1 + 0.06 * np.sin(2 * np.pi * 45 * t))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / t[-1]) * amp


def crack(amp=0.6, n_clicks=40, dur=0.5, seed=1):
    """Branches breaking: a cluster of sharp clicks and a woody knock."""
    n = n_of(dur + 0.3)
    out = np.zeros(n)
    rng = np.random.default_rng(seed)
    for i in range(n_clicks):
        s = int(rng.uniform(0, dur) ** 1.5 / dur ** 0.5 * SR)
        ln = n_of(rng.uniform(0.002, 0.01))
        if s + ln < n:
            out[s:s + ln] += rng.standard_normal(ln) * np.exp(-np.arange(ln) / (ln / 3)) * rng.uniform(0.3, 1)
    out = hp(out, 600) + bp(out, 200, 1200) * 0.8
    t = tt(n)
    knock = np.sin(2 * np.pi * 180 * t) * np.exp(-t * 20) * 0.6
    return (out + knock) * amp


def splash(amp=0.6, size=1.0, seed=2):
    n = n_of(1.6 * size + 0.5)
    t = tt(n)
    rng = np.random.default_rng(seed)
    body = bp(noise(n), 300, 4000) * np.exp(-t * (6 / size))
    low = lp(noise(n), 400) * np.exp(-t * 10) * 0.8
    bub = np.zeros(n)
    for i in range(int(25 * size)):
        s = n_of(rng.uniform(0.05, 0.9 * size))
        ln = n_of(rng.uniform(0.02, 0.06))
        if s + ln < n:
            f = np.linspace(rng.uniform(400, 900), rng.uniform(900, 2200), ln)
            bub[s:s + ln] += np.sin(2 * np.pi * np.cumsum(f) / SR) * np.hanning(ln) * rng.uniform(0.1, 0.4)
    return (body + low + bub) * amp


def rumble(dur, amp=0.4, lo=25, hi=160):
    n = n_of(dur)
    return bp(brown(n) * 4 + noise(n) * 0.2, lo, hi) * amp


def rocks(dur, amp=0.4, density=30, seed=4):
    n = n_of(dur + 0.4)
    out = np.zeros(n)
    rng = np.random.default_rng(seed)
    for i in range(int(dur * density)):
        s = n_of(rng.uniform(0, dur))
        ln = n_of(0.12)
        f = rng.uniform(250, 900)
        tl = tt(ln)
        if s + ln < n:
            out[s:s + ln] += (np.sin(2 * np.pi * f * tl) * 0.5 + rng.standard_normal(ln) * 0.5) * np.exp(-tl * rng.uniform(25, 60)) * rng.uniform(0.2, 1)
    return (bp(out, 150, 5000) + rumble(dur + 0.4, 1.0) * 0.6) * amp


def breath(dur=1.2, amp=0.08, inhale=True):
    n = n_of(dur)
    t = tt(n) / dur
    centers = np.linspace(700, 1800, 10) if inhale else np.linspace(1500, 600, 10)
    x = sweep_filter(noise(n), centers, width=0.9)
    e = np.sin(np.pi * t) ** (1.2 if inhale else 0.8)
    return x * e * amp


def zap(amp=0.4):
    n = n_of(0.5)
    t = tt(n)
    crackle = hp(noise(n), 2500) * (RNG.random(n) < 0.08) * 3
    tone = np.sin(2 * np.pi * np.cumsum(2400 * np.exp(-t * 8) + 300) / SR) * 0.4
    return (crackle + tone) * np.exp(-t * 9) * amp


def portal_hum(dur, amp=0.15, power=None):
    """Low sci-fi hum with pulsing; power(t)->0..1.5 drives pitch and brightness."""
    n = n_of(dur)
    t = tt(n)
    pw = power(t) if power else np.ones(n)
    f = 48 * (1 + 0.18 * pw)
    x = saw_f(f, n) + 0.7 * saw_f(f * 1.5 * 1.003, n) + 0.5 * saw_f(f * 2.01, n)
    bright = lp(x, 1400)
    dark = lp(x, 260)
    k = np.clip(pw / 1.5, 0, 1)
    y = dark * (1 - k) + bright * k
    pulse = 1 + 0.35 * np.sin(2 * np.pi * (1.5 + 2.5 * k) * t)
    shimmer = np.zeros(n)
    for fr, ph in ((1760, 0), (2349, 1), (2637, 2), (3520, 3)):
        shimmer += np.sin(2 * np.pi * fr * t * (1 + 0.003 * np.sin(2 * np.pi * 0.3 * t + ph))) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.7 * t + ph))
    return (y * pulse * 0.8 + shimmer * 0.05 * k) * amp


def explosion(amp=1.0, dur=7.0):
    n = n_of(dur)
    t = tt(n)
    sub = np.sin(2 * np.pi * np.cumsum(28 + 50 * np.exp(-t * 3)) / SR) * np.exp(-t / 3.0)
    body = lp(noise(n), 900) * np.exp(-t / 1.6)
    roar_ = lp(brown(n) * 6, 250) * np.exp(-t / 3.5)
    crk = hp(noise(n), 2000) * (RNG.random(n) < 0.02) * 3 * np.exp(-t / 2.5)
    x = np.tanh((sub * 1.4 + body * 1.0 + roar_ * 0.8 + crk * 0.3) * 1.8)
    return x * env_ar(n, 0.004, 2.0, 1.0) * amp


# ----------------------------------------------------------------- reverb
def reverb_ir(sec=2.8, decay=2.2, seed=5, bright=6000):
    n = n_of(sec)
    t = tt(n)
    rng = np.random.default_rng(seed)
    ir = np.zeros((n, 2))
    for ch in range(2):
        x = rng.standard_normal(n) * np.exp(-t * 6.9 / decay)
        x = lp(x, bright)
        x[: n_of(0.012)] *= np.linspace(0, 1, n_of(0.012))
        ir[:, ch] = x
    return ir / np.sqrt((ir ** 2).sum(0)).max()


def apply_reverb(x, wet=0.3, ir=None):
    """x: (n, 2) stereo."""
    ir = reverb_ir() if ir is None else ir
    out = np.zeros((len(x) + len(ir) - 1, 2))
    for ch in range(2):
        out[:, ch] = signal.fftconvolve(x[:, ch], ir[:, ch])
    out = out[: len(x)]
    return x * (1 - wet * 0.5) + out * wet


# ----------------------------------------------------------------- non-verbal voice (character reactions)
VOWELS = {
    "a": [(1000, 1.0), (1500, 0.7), (3100, 0.35), (4200, 0.15)],
    "o": [(520, 1.0), (880, 0.55), (2900, 0.12)],
    "u": [(380, 1.0), (950, 0.3), (2600, 0.08)],
    "e": [(620, 1.0), (2100, 0.6), (3000, 0.25)],
    "h": [(800, 1.0), (1300, 0.7), (2600, 0.4)],
}


def _formants(src, vowel, shift=1.0, q=0.12):
    return sum(bp(src, f * shift * (1 - q), f * shift * (1 + q)) * g for f, g in VOWELS[vowel])


def voice(f0, dur, vowel="a", breath=0.15, rough=0.0, vib=(5.5, 0.02), shift=1.15, attack=0.05, release=0.2, drive=1.0):
    """A sung/shouted vowel. f0: list of (sec, Hz) points for the pitch contour."""
    n = n_of(dur)
    t = tt(n)
    xs, ys = zip(*f0)
    f = np.interp(t, xs, ys)
    f = f * (1 + vib[1] * np.sin(2 * np.pi * vib[0] * t)) * (1 + 0.006 * lp(RNG.standard_normal(n), 30))
    src = saw_f(f, n)
    if rough > 0:
        src = src * (1 - rough * 0.5 * (1 + np.sin(2 * np.pi * np.cumsum(f * 0.5) / SR)))
    src = lp(src, 5000)
    asp = bp(noise(n), 400, 6000) * breath
    y = _formants(src + asp, vowel, shift)
    if drive > 1:
        y = np.tanh(y * drive) / np.tanh(drive)
    e = env_ar(n, attack, release, 1.3)
    return y * e / (np.abs(y).max() + 1e-9)


def gasp(amp=0.5):
    """Sharp frightened inhale: 'hah!'"""
    n = n_of(0.5)
    t = tt(n)
    nz = _formants(bp(noise(n), 300, 6000), "h", 1.1, 0.18)
    nz = nz * np.exp(-t * 7) * env_ar(n, 0.015, 0.1)
    v = voice([(0, 420), (0.25, 520)], 0.25, "a", breath=0.6, shift=1.2, attack=0.01, release=0.15) * 0.35
    out = nz / (np.abs(nz).max() + 1e-9)
    out[: len(v)] += v
    return out * amp


def scream(dur=1.3, amp=0.6):
    """'Aaaah!' from a frightened young character."""
    f0 = [(0, 540), (0.12, 760), (0.45, 720), (dur * 0.75, 690), (dur, 560)]
    x = voice(f0, dur, "a", breath=0.25, rough=0.3, vib=(6.0, 0.025), shift=1.2, attack=0.04, release=0.3, drive=2.2)
    return x * amp


def ooh(dur=0.9, amp=0.35):
    """Wondering 'oooh'."""
    return voice([(0, 300), (0.3, 330), (dur, 250)], dur, "o", breath=0.35, vib=(4.5, 0.012), shift=1.15, attack=0.12,
                 release=0.35) * amp


def whimper(dur=0.9, amp=0.3):
    return voice([(0, 380), (0.3, 420), (dur, 340)], dur, "u", breath=0.5, vib=(8.0, 0.05), shift=1.15, attack=0.08,
                 release=0.3) * amp


def shaky_breath(dur=0.6, amp=0.2, inhale=True):
    n = n_of(dur)
    t = tt(n) / dur
    x = sweep_filter(noise(n), np.linspace(700, 1700, 10) if inhale else np.linspace(1500, 600, 10), width=0.9)
    trem = 0.6 + 0.4 * np.sin(2 * np.pi * 11 * tt(n))
    return x * np.sin(np.pi * t) * trem * amp / (np.abs(x).max() + 1e-9)


def pant(dur, rate=3.4, amp=0.3):
    """Running out of breath: 'hah-heh-hah-heh'."""
    n = n_of(dur)
    out = np.zeros(n)
    k = 0
    period = 1.0 / rate
    while k * period < dur - 0.2:
        inhale = k % 2 == 0
        seg = n_of(period * 0.85)
        s = n_of(k * period)
        if inhale:
            x = _formants(bp(noise(seg), 300, 6000), "h", 1.1, 0.2)
            x = x / (np.abs(x).max() + 1e-9) * np.sin(np.pi * np.linspace(0, 1, seg)) * 0.6
        else:
            x = voice([(0, 330), (period, 300)], period * 0.85, "h", breath=0.9, shift=1.15, attack=0.02, release=0.08) * 0.8
        out[s:s + len(x)] += x[: n - s]
        k += 1
    return out * amp
