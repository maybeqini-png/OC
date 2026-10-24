"""Designed (code-drawn) backgrounds in anime background-art grammar: flat fills, few tones, crisp shapes.

Replaces the generated plates, whose measured micro-texture (2.5) and soft-gradient share (0.26) were 3x the
reference MVs' backgrounds (0.8 / 0.05-0.12, docs/research_pv_language.md §7). Every element is a designed shape:
- MIRROR SEA: night sky in three flat bands with a soft blend only at their seams, two-tone cloud banks drawn as
  merged ellipses, a crisp moon (flat disc, flat shadow side, three flat craters, banded halo), stars with
  4-point glints that twinkle on 3s, sea as one flat tone with horizontal light strokes under the moon (the TV-anime
  way of drawing a reflection) that shimmer on 3s, horizon line;
- STAGE (graphic): flat navy field, one spotlight cone with a hard-soft edge, floor ellipse, the hook word as a wall.
All motion is quantised (shimmer on 3s, twinkles on 3s) like hand-drawn effects animation.
"""
from functools import lru_cache

import cv2
import numpy as np

import look as L

W, H = L.W, L.H
NIGHT = dict(sky=((0.035, 0.05, 0.13), (0.07, 0.11, 0.26), (0.16, 0.25, 0.48)), sea=(0.045, 0.07, 0.17),
             sea_far=(0.10, 0.16, 0.34), moon=((0.93, 0.97, 1.0), (0.74, 0.84, 0.97)),
             cloud=((0.12, 0.17, 0.36), (0.19, 0.27, 0.52)), halo=(0.42, 0.55, 0.85), rim=(0.35, 0.47, 0.8),
             horizon=(0.55, 0.68, 0.95))
# the reflection world ("real her"): the same place, turned light - sky blue and white, the moon pale
HONEST = dict(sky=((0.40, 0.56, 0.90), (0.58, 0.74, 0.99), (0.83, 0.91, 1.0)), sea=(0.24, 0.39, 0.78),
              sea_far=(0.55, 0.70, 0.98), moon=((1.0, 1.0, 1.0), (0.88, 0.93, 1.0)),
              cloud=((0.70, 0.82, 1.0), (0.92, 0.96, 1.0)), halo=(0.92, 0.96, 1.0), rim=(1.0, 1.0, 1.0),
              horizon=(0.95, 0.98, 1.0))


def _aa_fill(canvas, mask_u8, color, alpha=1.0):
    m = cv2.GaussianBlur(mask_u8.astype(np.float32) / 255, (0, 0), 0.8)[..., None] * alpha
    canvas[:] = canvas * (1 - m) + np.array(color, np.float32) * m


@lru_cache(maxsize=8)
def sea_static(horizon=0.585, moon=(0.36, 0.40), moon_r=0.20, w=W, h=H, world="night"):
    """The parts of the sea that do not move (cached): sky bands, clouds, moon, horizon, sea fill."""
    P = NIGHT if world == "night" else HONEST
    SKY_TOP, SKY_MID, SKY_LOW = P["sky"]
    SEA, SEA_FAR = P["sea"], P["sea_far"]
    MOON_LIT, MOON_SHADE = P["moon"]
    CLOUD_A, CLOUD_B = P["cloud"]
    f = np.zeros((h, w, 3), np.float32)
    hy = int(h * horizon)
    # sky: one smooth vertical gradient (anime BG skies are gradients; the flatness lives in the shapes)
    y = (np.arange(hy, dtype=np.float32) / hy)[:, None, None]
    c0, c1, c2 = (np.array(c, np.float32) for c in (SKY_TOP, SKY_MID, SKY_LOW))
    u = np.clip(y / 0.6, 0, 1)
    col = c0 * (1 - u) + c1 * u
    v = np.clip((y - 0.6) / 0.4, 0, 1) ** 1.4
    f[:hy] = col * (1 - v) + c2 * v
    # moon glow (soft) + crisp disc with a flat shadow crescent and flat craters
    mx, my, r = int(w * moon[0]), int(h * moon[1]), int(h * moon_r)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt((xx - mx) ** 2 + (yy - my) ** 2) / r
    glow = np.clip(np.exp(-((d - 1) / 0.9) ** 2) * (d > 1) * 0.35 + np.exp(-((d - 1) / 0.25) ** 2) * (d > 1) * 0.25, 0, 1)
    f[:hy] = f[:hy] * (1 - glow[:hy, :, None]) + np.array(P["halo"], np.float32) * glow[:hy, :, None]
    disc = np.zeros((h, w), np.uint8)
    cv2.circle(disc, (mx, my), r, 255, -1, cv2.LINE_AA)
    disc[hy:] = 0
    _aa_fill(f, disc, MOON_LIT)
    shade = np.zeros((h, w), np.uint8)
    cv2.circle(shade, (mx + int(r * 0.42), my - int(r * 0.08)), int(r * 0.92), 255, -1, cv2.LINE_AA)
    _aa_fill(f, cv2.bitwise_and(disc, cv2.bitwise_not(shade)), MOON_SHADE)
    # cumulus banks on the horizon: puffy clusters (circles), cel-painted in three tones: shadow base, body, lit crown
    rng = np.random.default_rng(7)
    for bank, (y_frac, scale, tone) in enumerate(((0.86, 1.0, CLOUD_A), (0.94, 1.25, CLOUD_B))):
        body = np.zeros((h, w), np.uint8)
        x = -60.0
        base_y = int(hy * y_frac)
        while x < w + 60:
            cw = rng.uniform(120, 260) * scale
            for k in range(rng.integers(3, 6)):
                rr = int(rng.uniform(0.25, 0.5) * cw * 0.5)
                cxk = int(x + rng.uniform(0, cw))
                cyk = int(base_y - rng.uniform(0, 0.9) * rr)
                cv2.circle(body, (cxk, cyk), rr, 255, -1, cv2.LINE_AA)
            x += cw * rng.uniform(0.8, 1.3)
        body[base_y + 2:] = 0
        body[hy:] = 0
        _aa_fill(f, body, tone)
        # lit crown: the body shifted down, subtracted -> a band along the top edges facing the moon
        shifted = np.zeros_like(body)
        sh = int(9 * scale)
        shifted[sh:] = body[:-sh]
        crown = cv2.bitwise_and(body, cv2.bitwise_not(shifted))
        _aa_fill(f, crown, P["rim"], 0.55)
        # shadow base: the lowest band of each bank
        base = np.zeros_like(body)
        base[base_y - int(14 * scale):base_y + 2] = 255
        _aa_fill(f, cv2.bitwise_and(body, base), tuple(0.82 * c for c in tone), 0.8)
    # sea: one flat tone, a slightly lighter far band, crisp horizon line
    f[hy:] = SEA
    far = int(h * 0.04)
    f[hy:hy + far] = SEA_FAR
    f[hy:hy + far] = f[hy:hy + far] * np.linspace(1, 0, far)[:, None, None] + np.array(SEA, np.float32) * np.linspace(0, 1, far)[:, None, None]
    cv2.line(f, (0, hy), (w, hy), P["horizon"], 2, cv2.LINE_AA)
    return f, hy, (mx, my, r)


def stars(f, t, seed=11, n=70, y_max=None, fps=24, k=1.0):
    rng = np.random.default_rng(seed)
    y_max = y_max or int(f.shape[0] * 0.45)
    step = int(np.floor(t * fps / 3))  # twinkle state changes on 3s
    for i in range(n):
        x, y = int(rng.uniform(0, f.shape[1])), int(rng.uniform(0, y_max))
        big = rng.random() < 0.12
        tw = np.random.default_rng(step * 1000 + i).random()
        a = 0.55 + 0.45 * tw
        col = np.array((0.85, 0.92, 1.0), np.float32) * a * k
        if big:
            L_ = 6 + 6 * tw  # four-point glint as one filled star shape (drawn, not two separate strokes)
            q = 1.6
            pts = np.int32([(x, y - L_), (x + q, y - q), (x + L_, y), (x + q, y + q), (x, y + L_), (x - q, y + q),
                            (x - L_, y), (x - q, y - q)])
            cv2.fillPoly(f, [pts], col.tolist(), cv2.LINE_AA)
        else:
            cv2.circle(f, (x, y), 1, (col * 0.9).tolist(), -1, cv2.LINE_AA)
    return f


def moon_road(f, t, hy, moon, fps=24, width=1.0, stroke=(0.80, 0.89, 1.0)):
    """Horizontal light strokes on the water under the moon; redrawn on 3s (hand-drawn shimmer)."""
    mx, my, r = moon
    step = int(np.floor(t * fps / 3))
    rng = np.random.default_rng(step)
    layer = np.zeros_like(f)
    y = hy + 6
    HH = f.shape[0]
    while y < HH:
        depth = (y - hy) / (HH - hy)
        spread = r * (0.55 + 1.8 * depth) * width
        rows = int(2 + depth * 5)
        for _ in range(rows):
            cx = mx + rng.normal(0, spread * 0.35)
            ln = rng.uniform(12, 60) * (0.5 + 1.6 * depth)
            th = max(1, int(1 + depth * 2.5))
            a = np.clip(1 - abs(cx - mx) / (spread * 1.1), 0, 1) * (0.9 - 0.4 * depth)
            cv2.line(layer, (int(cx - ln / 2), y), (int(cx + ln / 2), y), (0.75 * a, 0.86 * a, 1.0 * a), th, cv2.LINE_AA)
        y += int(4 + depth * 14)
    a = np.clip(layer.max(axis=2, keepdims=True) * 1.2, 0, 1)
    f[:] = f * (1 - a) + np.array(stroke, np.float32) * a
    return f


def ripples(f, t, cx, cy, onsets, fps=24, life=1.4, rx0=40, grow=520, squash=0.16, color=(0.78, 0.88, 1.0)):
    """Concentric water rings from her feet, one per sung onset; drawn on 2s, two thin flat lines each."""
    tq = np.floor(t * fps / 2) * 2 / fps
    for o in onsets:
        u = (tq - o) / life
        if not 0 <= u < 1:
            continue
        rx = rx0 + grow * (1 - (1 - u) ** 2)
        a = (1 - u) ** 1.3
        for k, (dr, w_) in enumerate(((0, 2), (-0.12, 1))):
            rr = rx * (1 + dr)
            if rr < 6:
                continue
            col = tuple(float(c * a * (0.9 if k else 1.0)) for c in color)
            layer = np.zeros_like(f)
            cv2.ellipse(layer, (int(cx), int(cy)), (int(rr), int(rr * squash)), 0, 0, 360, col, w_ + 1, cv2.LINE_AA)
            f[:] = np.maximum(f, layer)
    return f


def sea(t, onsets=(), feet=None, moon_xy=(0.36, 0.40), moon_r=0.20, horizon=0.585, h=H, world="night"):
    base, hy, moon = sea_static(horizon, moon_xy, moon_r, W, h, world)
    f = base.copy()
    stars(f, t)
    moon_road(f, t, hy, moon, stroke=(0.80, 0.89, 1.0) if world == "night" else (0.93, 0.97, 1.0))
    if feet is not None and len(onsets):
        ripples(f, t, feet[0], feet[1], onsets)
    return f, hy, moon


def stage(t, spot_x=0.62, word=None, word_color=L.CORAL, word_reveal=1.0):
    """Graphic stage: flat navy, one spotlight cone (hard core + one soft step), floor ellipse."""
    f = np.zeros((H, W, 3), np.float32)
    f[:] = (0.05, 0.07, 0.16)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx = W * spot_x
    half = 80 + yy * 0.42
    d = np.abs(xx - cx) / half
    core = (d < 1.0).astype(np.float32)
    soft = np.clip((1.25 - d) / 0.25, 0, 1) * (1 - core)
    beam = (core * 0.16 + soft * 0.07) * (0.55 + 0.45 * yy / H)
    f += np.array((0.6, 0.72, 1.0), np.float32) * beam[..., None]
    fl = np.zeros((H, W), np.uint8)
    cv2.ellipse(fl, (int(cx), int(H * 0.93)), (int(half[-1, 0] * 1.05), 46), 0, 0, 360, 255, -1, cv2.LINE_AA)
    _aa_fill(f, fl, (0.22, 0.3, 0.55), 0.9)
    return f
