"""Finishing pass: vignette, film grain, fades and letterbox-free framing."""
import numpy as np
import skia

from .core import W, H, clamp, paint, rad, sprite, draw_img, SAMPLING

_GRAIN = []


def vignette(c, a=0.55, col=(0, 0, 0)):
    if a <= 0:
        return
    img = sprite(("vig", str(col)), W // 2, H // 2, lambda cv: cv.drawRect(
        skia.Rect(0, 0, W // 2, H // 2),
        paint(shader=rad((W / 4, H / 4), W * 0.36, [(0, col, 0), (0.55, col, 0.0), (0.8, col, 0.45), (1, col, 1)]))))
    p = skia.Paint()
    p.setAlphaf(clamp(a))
    c.save()
    c.scale(2, 2)
    c.drawImage(img, 0, 0, SAMPLING, p)
    c.restore()


def _grain_tiles():
    if not _GRAIN:
        rs = np.random.RandomState(99)
        for i in range(8):
            n = (rs.rand(H // 2, W // 2) * 255).astype(np.uint8)
            rgba = np.dstack([n, n, n, np.full_like(n, 255)])
            img = skia.Image.fromarray(rgba, colorType=skia.ColorType.kRGBA_8888_ColorType)
            _GRAIN.append(img)
    return _GRAIN


def grain(c, frame, a=0.05):
    if a <= 0:
        return
    tiles = _grain_tiles()
    img = tiles[frame % len(tiles)]
    p = skia.Paint()
    p.setAlphaf(clamp(a))
    p.setBlendMode(skia.BlendMode.kOverlay)
    c.save()
    c.scale(2, 2)
    c.drawImage(img, 0, 0, skia.SamplingOptions(skia.FilterMode.kNearest), p)
    c.restore()


def fade(c, a, col=(0, 0, 0)):
    if a > 0.001:
        c.drawRect(skia.Rect(-10, -10, W + 10, H + 10), paint(col, clamp(a)))
