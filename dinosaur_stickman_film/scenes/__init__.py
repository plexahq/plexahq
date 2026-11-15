"""Scene registry and frame compositor.

Each scene module defines DURATION (seconds), optional XFADE (overlap with the
previous scene for a dissolve), CUES (named local times used by the soundtrack) and
render(c, t) drawing one frame at local time t.
"""
import importlib

from engine import post
from engine.core import layer, clamp

NAMES = [
    "s01_quiet_night",
    "s02_something_wrong",
    "s03_portal_opens",
    "s04_enter_portal",
    "s05_prehistoric_world",
    "s06_first_dinosaurs",
    "s07_trex",
    "s08_run",
    "s09_river",
    "s10_valley",
    "s11_second_attack",
    "s12_final_escape",
    "s13_beautiful_view",
    "s14_sky_light",
    "s15_asteroid",
    "s16_impact",
    "s17_final_image",
]

_mods = None


def modules():
    global _mods
    if _mods is None:
        import os
        here = os.path.dirname(os.path.abspath(__file__))
        _mods = [importlib.import_module("scenes." + n) for n in NAMES if os.path.exists(os.path.join(here, n + ".py"))]
    return _mods


def timeline():
    """[(module, start, end)] with dissolves overlapping."""
    out = []
    t = 0.0
    for m in modules():
        x = getattr(m, "XFADE", 0.0) if out else 0.0
        start = t - x
        out.append((m, start, start + m.DURATION))
        t = start + m.DURATION
    return out


def total():
    return timeline()[-1][2]


def cues():
    """All cues as absolute times: {'s03_portal_opens.burst': 31.2, ...}."""
    d = {}
    for m, s, e in timeline():
        name = m.__name__.split(".")[-1]
        d[name + ".start"] = s
        d[name + ".end"] = e
        for k, v in getattr(m, "CUES", {}).items():
            d[name + "." + k] = s + v
    return d


def render_at(c, T, frame):
    tl = timeline()
    active = [(m, s, e) for m, s, e in tl if s <= T < e]
    if not active:
        active = [tl[-1]]
    base = active[0]
    base[0].render(c, T - base[1])
    for m, s, e in active[1:]:
        x = getattr(m, "XFADE", 0.0)
        a = clamp((T - s) / x) if x > 0 else 1.0
        with layer(c, a=a):
            m.render(c, T - s)
    post.vignette(c, 0.42)
    post.grain(c, frame, 0.06)
