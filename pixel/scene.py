"""HD layer of the full PV: anime background plates, lyric-prop stickers and plate transitions (1920x1080).

Plates and props are NovelAI V5 drawings (art/generated/anime_bg, prompts and seeds in its manifest) in a flat
2D anime style. Plates are upscaled x2 with Real-ESRGAN (upscale.py) and stored in pixel/plates/ at 1080 px
height; props are cut out from their white background and given a white sticker border.
"""
import math
import random
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).parent
ROOT = HERE.parent
SRC = ROOT / "art" / "generated" / "anime_bg"
PLATES = HERE / "plates"
OW, OH = 1920, 1080


@lru_cache(None)
def plate(name):
    return Image.open(PLATES / f"{name}.png").convert("RGBA")


def plate_view(name, u, v=0.0):
    """1920x1080 window of a plate: u (0..1) pans left to right, v (0..1) pans bottom to top (tall plates)."""
    p = plate(name)
    x = int(round((p.width - OW) * min(1, max(0, u))))
    y = int(round((p.height - OH) * (1 - min(1, max(0, v)))))
    return p.crop((x, y, x + OW, y + OH))


# ---------------------------------------------------------------- stickers
PROPS = {  # chosen take per prop (rejected takes stay in art/generated/anime_bg with their manifest rows)
    "s1_crown": "s1_crown_9401", "s2_phone": "s2_phone_9402", "s3_mic": "s3_mic_9403", "k02_trophy": "k02_trophy_9622",
    "k03_stamp": "k03_stamp_9603", "k04_star": "k04_star_9604", "k05_camera": "k05_camera_9605",
    "k06_heart": "k06_heart_9606", "k07_penlight": "k07_penlight_9607", "k08_bandage": "k08_bandage_9608",
    "k09_controller": "k09_controller_9609", "k10_catplush": "k10_catplush_9610", "k12_ribbon": "k12_ribbon_9612"}


@lru_cache(None)
def sticker_base(name):
    """Cut a prop out of its white background (border-connected near-white), cropped to the object."""
    f = SRC / f"{PROPS[name]}.png"
    a = np.asarray(Image.open(f).convert("RGB")).astype(int)
    white = a.min(2) > 232
    lab, _ = ndimage.label(white)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    fg = ~np.isin(lab, list(edge))
    fg = ndimage.binary_opening(fg, iterations=2)
    lab2, n = ndimage.label(fg)                         # drop specks far from the object
    if n > 1:
        sizes = ndimage.sum(fg, lab2, range(1, n + 1))
        fg = np.isin(lab2, [i + 1 for i, s in enumerate(sizes) if s > 0.01 * sizes.max()])
    ys, xs = np.nonzero(fg)
    rgba = np.dstack([a.astype(np.uint8), (fg * 255).astype(np.uint8)])[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return Image.fromarray(rgba, "RGBA")


@lru_cache(None)
def sticker(name, size, border=8):
    """Prop scaled so its longer side is `size` px, with a white sticker border and a soft navy drop shadow."""
    im = sticker_base(name)
    s = size / max(im.size)
    im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.Resampling.LANCZOS)
    al = np.asarray(im)[..., 3] > 110
    pad = border + 10
    big = np.pad(al, pad)
    ring = ndimage.binary_dilation(big, iterations=border, structure=ndimage.generate_binary_structure(2, 1))
    ring = ndimage.binary_closing(ring, iterations=2)
    out = np.zeros((*big.shape, 4), np.uint8)
    sh = np.roll(np.roll(ring, 7, 0), 5, 1)
    out[sh] = (24, 30, 80, 80)
    out[ring] = (255, 255, 255, 255)
    o = Image.fromarray(out, "RGBA")
    o.alpha_composite(im, (pad, pad))
    return o


def ease_out_back(u, c=1.7):
    u = min(1.0, max(0.0, u))
    return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2


def put_sticker(img, name, cx, cy, size, t, t_in, t_out=None, bob=8, tilt=0.0, seed=0):
    """Pop a sticker in at t_in (scale overshoot), bob gently, pop out at t_out."""
    if t < t_in or (t_out is not None and t >= t_out + 0.2):
        return
    k = ease_out_back((t - t_in) / 0.3)
    if t_out is not None and t >= t_out:
        k = max(0.0, 1 - (t - t_out) / 0.2)
    k = round(k * 20) / 20                                 # quantized scales keep the cache small
    if k <= 0:
        return
    s = sticker(name, max(8, int(size * k)))
    ang = tilt + 3 * math.sin(t * 2.2 + seed)
    if abs(ang) > 0.5:
        s = s.rotate(ang, resample=Image.Resampling.BICUBIC, expand=True)
    y = cy + bob * math.sin(t * 3.0 + seed)
    img.alpha_composite(s, (int(cx - s.width / 2), int(y - s.height / 2)))


# ---------------------------------------------------------------- transitions (operate on whole HD plates)
def tile_flip(a, b, p, tile=120, direction="diag", edge=(255, 255, 255)):
    """Block-flip wipe from a to b: each tile squashes to a line and opens up showing b (p = 0..1)."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    out = a.copy()
    cols, rows = OW // tile, OH // tile
    span = 0.55                                            # share of the wipe each tile spends flipping
    for r in range(rows):
        for c in range(cols):
            if direction == "diag":
                order = (c + r * 0.6) / (cols + rows * 0.6)
            elif direction == "center":
                order = math.hypot(c - cols / 2 + 0.5, (r - rows / 2 + 0.5) * 1.6) / math.hypot(cols / 2, rows * 0.8)
            else:
                order = c / cols
            u = (p - order * (1 - span)) / span
            if u <= 0:
                continue
            box = (c * tile, r * tile, (c + 1) * tile, (r + 1) * tile)
            if u >= 1:
                out.paste(b.crop(box), box[:2])
                continue
            src = a if u < 0.5 else b
            h = max(1, int(tile * abs(1 - 2 * u)))
            piece = src.crop(box).resize((tile, h), Image.Resampling.BILINEAR)
            out.paste(edge + (255,), box)
            out.paste(piece, (box[0], box[1] + (tile - h) // 2))
    return out


def curtain(img, closed, p):
    """Curtain halves from the closed-curtain plate slide in over img (p = 0 open .. 1 closed)."""
    if p <= 0:
        return img
    cp = plate_view(closed, 0.5)
    half = OW // 2
    e = 1 - (1 - min(1, p)) ** 2
    off = int(half * (1 - e))
    out = img.copy()
    out.paste(cp.crop((0, 0, half, OH)), (-off, 0))
    out.paste(cp.crop((half, 0, OW, OH)), (half + off, 0))
    return out


def dither_mix(a, b, p, cell=4):
    """Ordered-dither crossfade on a coarse grid (pixel-art fade)."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    B8 = np.array([[0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26], [12, 44, 4, 36, 14, 46, 6, 38],
                   [60, 28, 52, 20, 62, 30, 54, 22], [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
                   [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21]]) / 64
    m = np.kron(np.tile(B8, (OH // (8 * cell) + 1, OW // (8 * cell) + 1)), np.ones((cell, cell)))[:OH, :OW] < p
    A, Bm = np.asarray(a), np.asarray(b)
    out = A.copy()
    out[m] = Bm[m]
    return Image.fromarray(out, "RGBA")


def dim(img, k=0.45, colour=(27, 35, 64)):
    """Checker-dithered dim toward navy (2 px cells, the pixel layer's grid)."""
    a = np.asarray(img).copy()
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    m = ((yy // 2 + xx // 2) % 2 == 0)
    a[m, :3] = (a[m, :3] * (1 - k) + np.array(colour) * k).astype(np.uint8)
    a[~m, :3] = (a[~m, :3] * (1 - k * 0.5) + np.array(colour) * k * 0.5).astype(np.uint8)
    return Image.fromarray(a, "RGBA")
