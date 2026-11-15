"""The illustrated hero (comic style): pale round face, big expressive eyes, thick
brows, messy chestnut hair, red-orange jacket, olive backpack, jeans and boots.

Side views reuse the stickman Pose (engine/stickman.py), so every gait cycle and
pose from the film drives this character. Front and back views have their own
simple puppets for close-ups, running at the camera and over-the-shoulder shots."""
import math

import skia

from .core import (TAU, clamp, lerp, rgb, mix, shade, paint, lin, rad, poly, spline, taper, ellipse, noise)
from . import stickman as sm
from .toon import ink, stroke, union, limb, ellipse_path, INK, cel_bands

HR = 15.0          # head radius (stickman units)
COL = dict(
    skin="#f7f3ea", skin_sh="#d8d0d8", hair="#4b2c1f", hair_sh="#2f1a12", hair_hi="#6e4430",
    jacket="#e4512f", jacket_sh="#b0361f", jacket_hi="#ff7a50", jacket_dk="#9c2e1b",
    pack="#76843a", pack_sh="#556126", strap="#4f5a22",
    jeans="#3d63a5", jeans_sh="#2b4778", boot="#7b4a28", boot_sh="#55311a", sole="#2c211c",
    mouth="#6a1a24", tongue="#e06a74", teeth="#fbf8f2", eye="#fdfcf8", pupil="#141217",
)


def _lw(s):
    return min(8.5, 0.55 * s + 1.6)


def _rot(v, a):
    c, s_ = math.cos(a), math.sin(a)
    return (v[0] * c - v[1] * s_, v[0] * s_ + v[1] * c)


def _norm(v):
    l = math.hypot(*v) or 1.0
    return (v[0] / l, v[1] / l)


# ----------------------------------------------------------------- head
def _hair_path(view, face, f):
    """Hair in head-local unit space (radius 1, y down), before mirroring."""
    circ = skia.Path()
    circ.addCircle(0, -0.02, 1.08)
    pts = []
    if view == "back":
        for i in range(25):
            x = -1.4 + 2.8 * i / 24
            pts.append((x, 0.62 + (0.08 if i % 2 else 0.0)))
    else:
        fc = clamp(face, -1, 1) * f * 0.45            # fringe follows where the face looks
        for i in range(29):
            x = -1.4 + 2.8 * i / 28
            d = x - fc
            base = -0.40 + 0.42 * clamp(abs(d) - 0.55, 0, 1)
            if view == "side":
                back = -f * x
                base += 0.6 * clamp(back - 0.05, 0, 1)
            tooth = 0.13 if i % 2 else 0.0
            pts.append((x, base + tooth))
    region = poly(pts + [(1.4, -1.8), (-1.4, -1.8)])
    hair = skia.Op(circ, region, skia.PathOp.kIntersect_PathOp)
    spikes = []
    for sx, sy, ang, ln in ((-0.25, -1.0, -0.6, 0.26), (0.12, -1.05, 0.2, 0.3), (0.5, -0.9, 0.8, 0.22)):
        a = -math.pi / 2 + ang
        tip = (sx + math.cos(a) * ln, sy + math.sin(a) * ln)
        b1 = (sx + math.cos(a + 1.57) * 0.13, sy + math.sin(a + 1.57) * 0.13)
        b2 = (sx + math.cos(a - 1.57) * 0.13, sy + math.sin(a - 1.57) * 0.13)
        spikes.append(spline([b1, ((b1[0] + tip[0]) / 2 + 0.03, (b1[1] + tip[1]) / 2), tip, b2, (sx, sy + 0.1)], closed=True,
                             tension=0.4))
    return union(hair, *spikes)


def _to_head(path, hc, r, ang, mirror):
    m = skia.Matrix()
    m.preTranslate(hc[0], hc[1])
    m.preRotate(math.degrees(ang))
    m.preScale(r * mirror, r)
    p = skia.Path(path)
    p.transform(m)
    return p


def head(c, hc, s, f=1.0, ang=0.0, face=1.0, view="side", expr=None, lw=None):
    """Draw the head centred at hc. face: 1 = looking toward facing direction (3/4 view),
    0 = at the camera, -1 = away. expr keys: eye, eye_s, look, look_y, brow_up, brow_in, mouth, smile."""
    e = expr or {}
    r = HR * s
    lw = lw or _lw(s)
    mir = 1.0 if f >= 0 else -1.0
    # ear (opposite side to the gaze)
    if view != "back" and abs(face) > 0.25:
        ex = -math.copysign(1, face * f) * 0.9
        ep = ellipse_path(*_local(hc, r, ang, (ex, 0.08)), r * 0.17, r * 0.23, ang)
        ink(c, ep, COL["skin"], lw * 0.8, shadow=COL["skin_sh"], off=r * 0.06)
    hp = skia.Path()
    hp.addCircle(hc[0], hc[1], r)
    ink(c, hp, COL["skin"], lw, shadow=COL["skin_sh"], highlight=False, off=r * 0.22)
    if view == "back":
        hair = _to_head(_hair_path("back", 0, 1), hc, r, ang, 1.0)
        ink(c, hair, COL["hair"], lw, shadow=COL["hair_sh"], highlight=COL["hair_hi"], off=r * 0.16)
        return
    # eyes
    fa = clamp(face, -1, 1)
    sx = fa * f
    cx = sx * 0.40
    sp = 0.64 * (1 - 0.42 * abs(fa))
    eo = clamp(e.get("eye", 1.0))
    es = e.get("eye_s", 1.0)
    look = e.get("look", 0.0) + sx * 0.35
    look_y = e.get("look_y", 0.0)
    for k, ex in enumerate((cx - sp / 2, cx + sp / 2)):
        far = (k == 0 and sx > 0.2) or (k == 1 and sx < -0.2)
        sc = (1 - 0.18 * abs(fa)) if far else 1.0
        exw, eyw = _local(hc, r, ang, (ex, 0.06))
        rw, rh = r * 0.19 * sc * es, r * 0.245 * sc * es
        if eo < 0.12:
            stroke(c, [(exw - rw, eyw + rh * 0.1), (exw, eyw + rh * 0.35), (exw + rw, eyw + rh * 0.1)], lw * 0.9)
            continue
        ep = ellipse_path(exw, eyw, rw, rh, ang)
        c.drawPath(ep, paint(COL["eye"]))
        c.save()
        c.clipPath(ep, skia.ClipOp.kIntersect, True)
        pr = min(rw, rh) * (0.86 - 0.3 * (es - 1))
        px = exw + clamp(look, -1, 1) * (rw - pr * 0.75)
        py = eyw + clamp(look_y, -1, 1) * (rh - pr * 0.8) * 0.8 + rh * 0.08
        c.drawCircle(px, py, pr, paint(COL["pupil"]))
        c.drawCircle(px - pr * 0.35, py - pr * 0.4, pr * 0.33, paint((1, 1, 1)))
        c.drawCircle(px + pr * 0.35, py + pr * 0.35, pr * 0.14, paint((1, 1, 1), 0.85))
        if eo < 0.98:
            lid = rh * 2 * (1 - eo)
            c.drawRect(skia.Rect(exw - rw * 1.2, eyw - rh * 1.2, exw + rw * 1.2, eyw - rh + lid), paint(COL["skin"]))
            c.drawLine(exw - rw, eyw - rh + lid, exw + rw, eyw - rh + lid, paint(INK, stroke=lw * 0.7))
        c.restore()
        c.drawPath(ep, paint(INK, stroke=lw * 0.75))
    # brows
    up = e.get("brow_up", 0.0)
    inner = e.get("brow_in", 0.0)
    for k, ex in enumerate((cx - sp / 2, cx + sp / 2)):
        side = -1 if k == 0 else 1          # -1 left eye, +1 right eye (screen)
        far = (k == 0 and sx > 0.2) or (k == 1 and sx < -0.2)
        w = 0.2 * (0.8 if far else 1.0)
        yb = -0.27 - 0.1 * up * es
        a_in = (ex - side * w * 0.2, yb - 0.14 * inner - 0.01)
        a_out = (ex + side * w, yb + 0.05 * inner + 0.01)
        p0, p1 = _local(hc, r, ang, a_in), _local(hc, r, ang, a_out)
        stroke(c, [p0, p1], lw * 1.25)
    # mouth
    m = e.get("mouth", 0.0)
    smile = e.get("smile", 0.0)
    mx = cx * 0.85
    my = 0.47
    if m < 0.08:
        w = 0.17
        pts = [(mx - w, my - 0.04 * smile), (mx, my + 0.06 * smile - 0.01), (mx + w, my - 0.04 * smile)]
        stroke(c, [_local(hc, r, ang, q) for q in pts], lw * 0.85)
    else:
        mw = (0.13 + 0.09 * m) * e.get("mouth_w", 1.0)
        mh = 0.06 + 0.24 * m
        mc = _local(hc, r, ang, (mx, my + mh * 0.3))
        mp = ellipse_path(mc[0], mc[1], r * mw, r * mh, ang)
        c.drawPath(mp, paint(COL["mouth"]))
        c.save()
        c.clipPath(mp, skia.ClipOp.kIntersect, True)
        tc = _local(hc, r, ang, (mx, my + mh * 1.05))
        c.drawPath(ellipse_path(tc[0], tc[1], r * mw * 0.8, r * mh * 0.6, ang), paint(COL["tongue"]))
        if m > 0.45:
            t0 = _local(hc, r, ang, (mx, my + mh * 0.3 - mh * 0.95))
            c.drawPath(ellipse_path(t0[0], t0[1], r * mw * 0.85, r * mh * 0.28, ang), paint(COL["teeth"]))
        c.restore()
        c.drawPath(mp, paint(INK, stroke=lw * 0.8))
    # hair on top
    hair = _to_head(_hair_path(view, fa, f), hc, r, ang, 1.0)
    ink(c, hair, COL["hair"], lw, shadow=COL["hair_sh"], highlight=COL["hair_hi"], off=r * 0.16)


def _local(hc, r, ang, q):
    x, y = _rot((q[0] * r, q[1] * r), ang)
    return (hc[0] + x, hc[1] + y)


# ----------------------------------------------------------------- side view (drives from a stickman Pose)
def boot_path(ankle, f, s, lift=0.0):
    x, y = ankle
    l = 11.5 * s
    h = 6.5 * s
    pts = [(x - f * 4.5 * s, y - h * 0.55), (x + f * 2 * s, y - h * 0.8), (x + f * (l - 3 * s), y - h * 0.25),
           (x + f * l, y + h * 0.15), (x + f * (l - 1.5 * s), y + h * 0.5), (x - f * 4.8 * s, y + h * 0.5)]
    return spline(pts, closed=True, tension=0.45)


def side(c, p, expr=None, light_rim=None, shadow_y=None):
    """Draw the hero from a stickman Pose (side view)."""
    s = p.s
    f = p.f
    lw = _lw(s)
    J = sm.joints(p)
    hip, neck = J["hip"], J["neck"]
    a = _norm((neck[0] - hip[0], neck[1] - hip[1]))
    nf = (-a[1] * f, a[0] * f)
    if shadow_y is not None:
        cx = (J["ft_n"][0] + J["ft_f"][0]) / 2
        hgt = max(0.0, shadow_y - max(J["ft_n"][1], J["ft_f"][1]))
        k = clamp(1 - hgt / (60 * s))
        ellipse(c, cx, shadow_y + 2 * s, 20 * s * (0.6 + 0.4 * k), 3.6 * s, paint((0.1, 0.12, 0.05), 0.32 * k, blur=2.5 * s))

    def P(u, off=0.0):
        return (hip[0] + (neck[0] - hip[0]) * u + nf[0] * off, hip[1] + (neck[1] - hip[1]) * u + nf[1] * off)

    def leg(side_):
        kn, ft = J["kn_" + side_], J["ft_" + side_]
        far = side_ == "f"
        col, sh = (shade(rgb(COL["jeans"]), -0.15), COL["jeans_sh"]) if far else (COL["jeans"], COL["jeans_sh"])
        path = limb(hip, kn, ft, 6.4 * s, 5.6 * s, 5.0 * s)
        ink(c, path, col, lw, shadow=sh, off=4 * s)
        bp = boot_path(ft, f, s)
        ink(c, bp, shade(rgb(COL["boot"]), -0.15) if far else COL["boot"], lw, shadow=COL["boot_sh"], off=3 * s)
        b = bp.getBounds()
        c.drawLine(b.left() + 2 * s, b.bottom() - 1.4 * s, b.right() - 2 * s, b.bottom() - 1.4 * s, paint(COL["sole"], stroke=2.2 * s))

    def arm(side_):
        sh_ = P(0.86, 1.0)
        el, hd = J["el_" + side_], J["hand_" + side_]
        far = side_ == "f"
        col = shade(rgb(COL["jacket"]), -0.18) if far else COL["jacket"]
        ink(c, limb(sh_, el, hd, 5.4 * s, 4.8 * s, 4.4 * s), col, lw, shadow=COL["jacket_sh"], highlight=COL["jacket_hi"], off=3.4 * s)
        d = _norm((hd[0] - el[0], hd[1] - el[1]))
        cuff = (hd[0] - d[0] * 2.5 * s, hd[1] - d[1] * 2.5 * s)
        ink(c, ellipse_path(cuff[0], cuff[1], 4.8 * s, 2.6 * s, math.atan2(d[1], d[0]) + math.pi / 2), COL["jacket_dk"], lw * 0.8,
            shadow=False)
        hp_ = skia.Path()
        hp_.addCircle(hd[0] + d[0] * 2.2 * s, hd[1] + d[1] * 2.2 * s, 4.4 * s)
        ink(c, hp_, COL["skin"], lw * 0.9, shadow=COL["skin_sh"], off=2 * s)

    arm("f")
    leg("f")
    leg("n")
    # backpack
    bc = P(0.55, -11.5 * s)
    ang = math.atan2(a[1], a[0]) + math.pi / 2
    bpk = skia.Path()
    bpk.addRRect(skia.RRect.MakeRectXY(skia.Rect(-6.5 * s, -10 * s, 6.5 * s, 10 * s), 4 * s, 4 * s))
    m = skia.Matrix()
    m.setTranslate(bc[0], bc[1])
    m.preRotate(math.degrees(ang))
    bpk.transform(m)
    ink(c, bpk, COL["pack"], lw, shadow=COL["pack_sh"], off=4 * s)
    # torso / jacket
    wf = [(-0.14, 10.2), (0.0, 10.4), (0.3, 10.8), (0.62, 10.6), (0.88, 9.4), (1.0, 6.8)]
    wb = [(-0.14, 9.6), (0.0, 9.8), (0.3, 10.0), (0.62, 10.0), (0.88, 9.0), (1.0, 6.4)]
    pts = [P(u, w * s) for u, w in wf] + [P(u, -w * s) for u, w in reversed(wb)]
    torso = spline(pts, closed=True, tension=0.45)
    ink(c, torso, COL["jacket"], lw, shadow=COL["jacket_sh"], highlight=COL["jacket_hi"], off=5 * s)
    c.save()
    c.clipPath(torso, skia.ClipOp.kIntersect, True)
    stroke(c, [P(0.95, 3 * s), P(0.4, 9.5 * s), P(0.1, 10.5 * s)], 3.2 * s, COL["strap"])
    stroke(c, [P(-0.1, 6.0 * s), P(0.9, 6.0 * s)], lw * 0.55, shade(rgb(COL["jacket_sh"]), -0.3))
    hem = [P(-0.1, 11 * s), P(-0.1, -11 * s)]
    stroke(c, hem, 4.2 * s, COL["jacket_dk"])
    c.restore()
    # collar
    cc = P(0.97)
    ink(c, ellipse_path(cc[0], cc[1], 8.6 * s, 4.4 * s, ang + math.pi / 2), COL["jacket_dk"], lw, shadow=False)
    # head
    hd_dir = _norm((J["head"][0] - neck[0], J["head"][1] - neck[1]))
    hc = (neck[0] + hd_dir[0] * (1.5 + HR) * s, neck[1] + hd_dir[1] * (1.5 + HR) * s)
    head_ang = math.atan2(hd_dir[0], -hd_dir[1])
    ex = dict(eye=p.eye, eye_s=p.eye_s, look=p.look, look_y=p.look_y)
    ex.update(expr or {})
    head(c, hc, s, f, head_ang, p.face, "side" if p.face > -0.95 else "back", ex, lw)
    arm("n")
    return J, hc


# ----------------------------------------------------------------- front / back puppets
def front(c, x, y, s, t=0.0, expr=None, arms=None, run=None, back=False, head_turn=0.0, lean=0.0, bob=0.0, shadow_y=None):
    """Front (or back) view standing at hip point (x, y).
    arms: dict(l=(raise, bend), r=(raise, bend)) raise 0 = down, 1 = horizontal, 1.6 = hands up.
    run: gait phase for running at the camera (None = standing)."""
    lw = _lw(s)
    y = y - bob * s
    hip = (x, y)
    up = _rot((0, -1), lean)
    neck = (x + up[0] * 31 * s, y + up[1] * 31 * s)
    if shadow_y is not None:
        ellipse(c, x, shadow_y + 2 * s, 22 * s, 4 * s, paint((0.1, 0.12, 0.05), 0.3, blur=3 * s))
    # legs
    for side_ in (-1, 1):
        hx = x + side_ * 5.5 * s
        if run is not None:
            u = math.sin(run * TAU + (0 if side_ < 0 else math.pi))
            lift = max(0.0, u)
            knee = (hx + side_ * 1.5 * s, y + 23 * s * (1 - 0.55 * lift))
            foot = (hx + side_ * 2.0 * s, knee[1] + 22 * s * (1 - 0.35 * lift) - 3 * s * lift)
        else:
            knee = (hx + side_ * 1.0 * s, y + 23 * s)
            foot = (hx + side_ * 2.0 * s, y + 45 * s)
        ink(c, limb((hx, y), knee, foot, 6.4 * s, 5.6 * s, 5.0 * s), COL["jeans"], lw, shadow=COL["jeans_sh"], off=4 * s)
        bp = ellipse_path(foot[0], foot[1] + 1.5 * s, 6.2 * s, 5.0 * s)
        ink(c, bp, COL["boot"], lw, shadow=COL["boot_sh"], off=3 * s)
    # arms behind the torso when the hands are low
    def arm(side_, front_layer):
        ra, bend = (arms or {}).get("l" if side_ < 0 else "r", (0.15, 0.3))
        if run is not None:
            sw = math.sin(run * TAU + (math.pi if side_ < 0 else 0))
            ra, bend = 0.35 + 0.3 * sw, 1.6
        sh_ = (neck[0] + side_ * 10.5 * s + up[0] * -3 * s, neck[1] + 3 * s)
        if run is not None:
            bend = -1.9 + 0.4 * sw
        a1 = side_ * (0.15 + ra * 1.15)
        el = (sh_[0] + math.sin(a1) * 16.5 * s, sh_[1] + math.cos(a1) * 16.5 * s)
        a2 = a1 + side_ * bend
        hd = (el[0] + math.sin(a2) * 15.5 * s, el[1] + math.cos(a2) * 15.5 * s)
        if (hd[1] < neck[1] + 14 * s or (run is not None and sw > 0)) != front_layer:
            return
        ink(c, limb(sh_, el, hd, 5.4 * s, 4.8 * s, 4.4 * s), COL["jacket"], lw, shadow=COL["jacket_sh"], highlight=COL["jacket_hi"],
            off=3.4 * s)
        hp_ = skia.Path()
        hp_.addCircle(hd[0], hd[1] + 1.5 * s, 4.6 * s)
        ink(c, hp_, COL["skin"], lw * 0.9, shadow=COL["skin_sh"], off=2 * s)
    for sd in (-1, 1):
        arm(sd, False)
    # torso
    pts = [(x - 12 * s, y + 4 * s), (x - 12.8 * s, y - 12 * s), (x - 11.5 * s, y - 26 * s), (x - 7 * s, y - 31.5 * s),
           (x + 7 * s, y - 31.5 * s), (x + 11.5 * s, y - 26 * s), (x + 12.8 * s, y - 12 * s), (x + 12 * s, y + 4 * s)]
    m = skia.Matrix()
    m.setRotate(math.degrees(lean), x, y)
    torso = spline(pts, closed=True, tension=0.4)
    torso.transform(m)
    ink(c, torso, COL["jacket"], lw, shadow=COL["jacket_sh"], highlight=COL["jacket_hi"], off=5 * s)
    c.save()
    c.concat(m)
    c.clipPath(spline(pts, closed=True, tension=0.4), skia.ClipOp.kIntersect, True)
    if back:
        bpk = skia.Path()
        bpk.addRRect(skia.RRect.MakeRectXY(skia.Rect(x - 9 * s, y - 27 * s, x + 9 * s, y - 2 * s), 4 * s, 4 * s))
        c.restore()
        c.save()
        c.concat(m)
        ink(c, bpk, COL["pack"], lw, shadow=COL["pack_sh"], off=4 * s)
        pk = skia.Path()
        pk.addRRect(skia.RRect.MakeRectXY(skia.Rect(x - 6 * s, y - 13 * s, x + 6 * s, y - 4 * s), 2.5 * s, 2.5 * s))
        ink(c, pk, COL["pack_sh"], lw * 0.8, shadow=False)
        for sd in (-1, 1):
            stroke(c, [(x + sd * 7 * s, y - 27 * s), (x + sd * 8 * s, y - 31 * s)], 3.4 * s, COL["strap"])
    else:
        stroke(c, [(x, y - 30 * s), (x, y + 3 * s)], lw * 0.7, shade(rgb(COL["jacket_sh"]), -0.35))
        for sd in (-1, 1):
            stroke(c, [(x + sd * 7.5 * s, y - 31 * s), (x + sd * 8.5 * s, y - 14 * s), (x + sd * 8 * s, y + 2 * s)], 3.4 * s, COL["strap"])
            ink(c, ellipse_path(x + sd * 6.5 * s, y - 5 * s, 3.4 * s, 2.2 * s), COL["jacket_sh"], lw * 0.6, shadow=False)
        stroke(c, [(x - 12.5 * s, y + 1 * s), (x + 12.5 * s, y + 1 * s)], 4.2 * s, COL["jacket_dk"])
    c.restore()
    ink(c, ellipse_path(neck[0], neck[1] + 0.5 * s, 9.5 * s, 4.2 * s, lean), COL["jacket_dk"], lw, shadow=False)
    hc = (neck[0] + up[0] * (1.5 + HR) * s, neck[1] + up[1] * (1.5 + HR) * s)
    ex = dict(expr or {})
    face = ex.pop("face", 0.0)
    head(c, hc, s, 1.0, lean + head_turn * 0.15, face, "back" if back else ("front" if abs(face) < 0.5 else "side"), ex, lw)
    for sd in (-1, 1):
        arm(sd, True)
    return hc
