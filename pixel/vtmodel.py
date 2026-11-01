"""XIYIN's VTuber model: the owner's reference sheet bust itself (upscaled, never redrawn) with switchable eyes
and mouth, like a Live2D model's expression set.

Each variant is a V5 img2img take of the base (art/generated/vtuber2/prompts.sh); only its eye or mouth region is
aligned to the base (best shift on a ring around the region) and pasted with a feathered ellipse, so the face,
hair, body and costume stay exactly as on the sheet. One cut-out mask (from the base's white background) serves
all variants.

usage:  vtmodel.py build      paste the chosen regions -> art/generated/vtuber2/<name>.png
        vtmodel.py sheet out.png
"""
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

import sprite

ROOT = Path(__file__).parent.parent
GEN = ROOT / "art" / "generated"
V2 = GEN / "vtuber2"
BASE = V2 / "base_sheet_bust.png"           # the owner's reference sheet bust, upscaled (her face exactly as drawn)
FACE = (505, 430, 150, 110)                 # face ellipse centre x, y, radii x, y on BASE
FACE_BOX = (380, 330, 250, 200)             # x, y, w, h (cam framing)
EYES = ((436, 412, 50, 30), (574, 390, 50, 32))
MOUTH = ((520, 462, 34, 22),)

EXPR = {"base": BASE, "blink": V2 / "blink.png", "talk": V2 / "talk.png"}
# name: (raw take, regions to paste)
PASTES = {"blink": ("blinkc_0.45_31005_raw.png", EYES), "talk": ("talk_0.50_31001_raw.png", MOUTH)}


def region_mask(shape, ellipses, feather=5.0):
    H, W = shape
    yy, xx = np.mgrid[0:H, 0:W]
    m = np.zeros((H, W), np.float32)
    for cx, cy, rx, ry in ellipses:
        m = np.maximum(m, ((((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2) <= 1).astype(np.float32))
    return ndimage.gaussian_filter(m, feather)


def transplant(base, raw, ellipses, search=8):
    """Paste the regions (ellipses) of raw onto base, after aligning raw on a ring around them."""
    B = np.asarray(base.convert("RGB")).astype(np.float32)
    R = np.asarray(raw.convert("RGB").resize(base.size, Image.Resampling.LANCZOS)).astype(np.float32)
    H, W = B.shape[:2]
    inner = region_mask((H, W), ellipses, 0) > 0.5
    grow = [(cx, cy, rx * 1.6, ry * 1.6) for cx, cy, rx, ry in ellipses]
    ring = (region_mask((H, W), grow, 0) > 0.5) & ~inner
    best, shift = None, (0, 0)
    for dy in range(-search, search + 1):
        for dx in range(-search, search + 1):
            Rs = np.roll(np.roll(R, dy, 0), dx, 1)
            err = float(np.mean((Rs[ring] - B[ring]) ** 2))
            if best is None or err < best:
                best, shift = err, (dx, dy)
    Rs = np.roll(np.roll(R, shift[1], 0), shift[0], 1)
    m = region_mask((H, W), ellipses)[..., None]
    out = B * (1 - m) + Rs * m
    return Image.fromarray(out.clip(0, 255).astype(np.uint8)), shift


@lru_cache(None)
def alpha():
    """Cut-out mask: the sheet's background is pure white and her skin is near-white, so only pixels that are
    almost pure white AND connected to the image border are background; enclosed pure-white gaps between hair
    strands (outside the face) are removed too."""
    a = np.asarray(Image.open(BASE).convert("RGB")).astype(np.int16)
    white = a.min(2) >= 247
    lab, n = ndimage.label(white)
    border = set(np.unique(np.concatenate([lab[0], lab[:, 0], lab[:, -1]]))) - {0}
    bg = np.isin(lab, list(border))
    H, W = white.shape
    yy, xx = np.mgrid[0:H, 0:W]
    cx, cy, rx, ry = FACE
    face = ((xx - cx) / (rx * 1.15)) ** 2 + ((yy - cy) / (ry * 1.3)) ** 2 <= 1
    sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
    gaps = np.isin(lab, [k + 1 for k, s in enumerate(sizes) if s >= 60]) & ~face
    fg = ~(bg | gaps)
    fg = ndimage.binary_opening(fg, iterations=1)
    fg = ndimage.binary_erosion(fg, iterations=1)
    return fg


@lru_cache(None)
def edge_fix():
    """For each pixel within 3 px of the cut edge, the nearest pixel 4+ px inside (to replace white fringe)."""
    fg = alpha()
    inner = ndimage.binary_erosion(fg, iterations=4)
    _, (iy, ix) = ndimage.distance_transform_edt(~inner, return_indices=True)
    band = fg & ~ndimage.binary_erosion(fg, iterations=3)
    return band, iy, ix


@lru_cache(None)
def model(name):
    a = np.asarray(Image.open(EXPR[name]).convert("RGB").resize((1024, 1024), Image.Resampling.LANCZOS)).copy()
    band, iy, ix = edge_fix()
    lum = a.astype(np.int16).sum(2)
    src = a[iy, ix]
    light = band & (lum > src.astype(np.int16).sum(2) + 30)    # lighter than the inside: white fringe
    a[light] = src[light]
    al = Image.fromarray((alpha() * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))
    im = Image.fromarray(a).convert("RGBA")
    im.putalpha(al)
    return im


@lru_cache(maxsize=96)
def model_scaled(name, size):
    return model(name).resize((size, size), Image.Resampling.LANCZOS)


def build():
    base = Image.open(BASE)
    for name, (raw, regions) in PASTES.items():
        out, shift = transplant(base, Image.open(V2 / raw), regions)
        out.save(EXPR[name])
        print(name, "from", raw, "shift", shift)


def sheet(out):
    names = list(EXPR)
    s = 300
    S = Image.new("RGB", (s * 6, (len(names) + 5) // 6 * (s + 20)), (230, 232, 240))
    from PIL import ImageDraw
    d = ImageDraw.Draw(S)
    for i, n in enumerate(names):
        if not EXPR[n].exists():
            continue
        x, y = (i % 6) * s, (i // 6) * (s + 20)
        S.paste(model_scaled(n, s), (x, y + 20), model_scaled(n, s))
        d.text((x + 4, y + 4), n, fill=(0, 0, 0))
    S.save(out)


if __name__ == "__main__":
    if sys.argv[1] == "build":
        build()
    else:
        sheet(sys.argv[2])
