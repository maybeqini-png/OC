"""Hand-made abstract stage backdrops (1920x1080), drawn in code after the benchmark game's abstract backgrounds
(official Muse Dash trailer / screenshots): a flat two-colour gradient, big soft geometric shapes in a lighter tint
behind a haze, rings, diagonal dot grids, and a near layer of flat silhouettes, all scrolling in parallax with the
run. XIYIN's palette and motifs (cat heads, paw prints, hearts, stars, ribbons). No image model involved.

Layers are horizontally tileable strips (period P) built once and cropped per frame, so a frame costs a few
crops and composites.
"""
import math
import random
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OW, OH = 1920, 1080
P = 2880                       # tile period of every layer
SS = 2                         # supersampling for shapes

THEMES = {
    "pop": dict(top=(48, 92, 210), bottom=(140, 196, 255), far=(170, 210, 255), mid=(255, 255, 255),
                ring=[(255, 214, 90), (255, 140, 190), (255, 255, 255)], near=(36, 70, 170),
                accent=[(255, 140, 190), (255, 214, 90), (255, 255, 255)], motifs=("cat", "star", "paw", "diamond")),
    "pinkpop": dict(top=(236, 88, 160), bottom=(255, 196, 226), far=(255, 214, 236), mid=(255, 255, 255),
                    ring=[(120, 170, 255), (255, 240, 120), (255, 255, 255)], near=(196, 56, 130),
                    accent=[(120, 170, 255), (255, 255, 255), (255, 240, 120)], motifs=("heart", "paw", "cat", "star")),
}


def _shape(d, kind, cx, cy, r, rot, fill):
    if kind == "star":
        pts = []
        for i in range(10):
            rr = r if i % 2 == 0 else r * 0.46
            a = rot + i * math.pi / 5 - math.pi / 2
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        d.polygon(pts, fill=fill)
    elif kind == "diamond":
        pts = [(cx + r * math.cos(rot + k * math.pi / 2), cy + r * math.sin(rot + k * math.pi / 2)) for k in range(4)]
        d.polygon(pts, fill=fill)
    elif kind == "heart":
        s = r
        d.ellipse([cx - s, cy - s * 0.75, cx, cy + s * 0.2], fill=fill)
        d.ellipse([cx, cy - s * 0.75, cx + s, cy + s * 0.2], fill=fill)
        d.polygon([(cx - s * 0.96, cy - s * 0.15), (cx + s * 0.96, cy - s * 0.15), (cx, cy + s)], fill=fill)
    elif kind == "paw":
        d.ellipse([cx - r * 0.55, cy - r * 0.1, cx + r * 0.55, cy + r * 0.75], fill=fill)
        for dx, dy in ((-0.62, -0.42), (-0.22, -0.78), (0.22, -0.78), (0.62, -0.42)):
            d.ellipse([cx + dx * r - r * 0.22, cy + dy * r - r * 0.26, cx + dx * r + r * 0.22, cy + dy * r + r * 0.26],
                      fill=fill)
    elif kind == "cat":                                   # cat-head silhouette
        d.ellipse([cx - r, cy - r * 0.8, cx + r, cy + r * 0.85], fill=fill)
        d.polygon([(cx - r * 0.95, cy - r * 0.2), (cx - r * 0.75, cy - r * 1.25), (cx - r * 0.25, cy - r * 0.7)], fill=fill)
        d.polygon([(cx + r * 0.95, cy - r * 0.2), (cx + r * 0.75, cy - r * 1.25), (cx + r * 0.25, cy - r * 0.7)], fill=fill)


def _tile(draw_fn, h=OH):
    """Draw on a strip of width P plus margins m, then wrap: the strip is pasted at three periods and the middle
    period cropped, so shapes crossing an edge continue on the other side."""
    m = 600
    big = Image.new("RGBA", ((P + 2 * m) * SS, h * SS), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(big), m)
    big = big.resize((P + 2 * m, h), Image.Resampling.LANCZOS)
    tmp = Image.new("RGBA", (3 * P, h), (0, 0, 0, 0))
    for off in (0, P, 2 * P):
        tmp.alpha_composite(big, (off - m, 0)) if off - m >= 0 else tmp.alpha_composite(big.crop((m - off, 0, big.width, h)), (0, 0))
    return tmp.crop((P, 0, 2 * P, h))


@lru_cache(None)
def layers(name):
    T = THEMES[name]
    rng = random.Random(hash(name) & 0xffff)
    # base gradient
    y = np.linspace(0, 1, OH)[:, None, None]
    base = (np.array(T["top"]) * (1 - y) + np.array(T["bottom"]) * y) * np.ones((1, OW, 1))
    base = Image.fromarray(base.astype(np.uint8), "RGB").convert("RGBA")

    def far(d, m):                                       # huge soft shapes, light tint
        for i in range(9):
            kind = rng.choice(T["motifs"])
            cx = (m + i * P / 9 + rng.uniform(-80, 80)) * SS
            cy = rng.uniform(180, 760) * SS
            r = rng.uniform(220, 420) * SS
            _shape(d, kind, cx, cy, r, rng.uniform(-0.4, 0.4), (*T["far"], 120))

    def mid(d, m):                                       # rings + diagonal dot grid bands
        for i in range(5):
            cx = (m + i * P / 5 + rng.uniform(0, 200)) * SS
            cy = rng.uniform(200, 700) * SS
            for k in range(3):
                r = (rng.uniform(130, 260) - k * 36) * SS
                col = T["ring"][k % len(T["ring"])]
                d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*col, 210), width=int(16 * SS))
        for band in range(3):
            x0 = band * P / 3 + m
            for gx in range(0, 520, 34):
                for gy in range(0, 1080, 34):
                    x = x0 + gx + gy * 0.6
                    if 0.0 < ((gx + gy * 0.6) / 700) < 1:
                        d.ellipse([(x - 4) * SS, (gy - 4) * SS, (x + 4) * SS, (gy + 4) * SS], fill=(*T["mid"], 90))

    def near(d, m):                                      # flat silhouettes + accent confetti
        for i in range(14):
            kind = rng.choice(T["motifs"])
            cx = (m + i * P / 14 + rng.uniform(-40, 40)) * SS
            cy = rng.uniform(90, 820) * SS
            r = rng.uniform(40, 95) * SS
            _shape(d, kind, cx, cy, r, rng.uniform(-0.6, 0.6), (*T["near"], 150))
        for i in range(60):
            cx = (m + rng.uniform(0, P)) * SS
            cy = rng.uniform(40, 860) * SS
            _shape(d, "star", cx, cy, rng.uniform(8, 22) * SS, rng.uniform(0, 1), (*rng.choice(T["accent"]), 230))

    lf = _tile(far).filter(ImageFilter.GaussianBlur(10))
    lm = _tile(mid)
    ln = _tile(near)
    haze = Image.new("RGBA", (OW, OH), (*T["bottom"], 70))
    return base, lf, lm, ln, haze


def _crop(strip, x):
    x = int(x) % P
    if x + OW <= P:
        return strip.crop((x, 0, x + OW, OH))
    out = Image.new("RGBA", (OW, OH), (0, 0, 0, 0))
    out.alpha_composite(strip.crop((x, 0, P, OH)), (0, 0))
    out.alpha_composite(strip.crop((0, 0, OW - (P - x), OH)), (P - x, 0))
    return out


def view(name, cam, beat_phase=0.0):
    """Backdrop for a camera position (HD px the ground has scrolled); layers scroll at 0.12 / 0.3 / 0.6."""
    base, lf, lm, ln, haze = layers(name)
    img = base.copy()
    img.alpha_composite(_crop(lf, cam * 0.12))
    img.alpha_composite(haze)
    img.alpha_composite(_crop(lm, cam * 0.3))
    near = _crop(ln, cam * 0.6)
    bob = int(round(6 * math.sin(2 * math.pi * beat_phase)))            # near layer bobs on the beat
    img.alpha_composite(near, (0, bob))
    return img
