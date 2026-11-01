"""XIYIN's VTuber model: one fixed bust (made from the owner's sheet, young proportions as on the sheet) with
switchable faces, like a Live2D model's expression set.

Every expression image shares the base bust's body, hair and costume: the V5 img2img variant's face region is
aligned to the base (best shift in an annulus round the face) and pasted with a feathered ellipse. One cut-out
mask (from the base's plain grey background) serves all expressions. The renderer adds blinks and a mouth flap on
the sung syllables for the neutral face.

usage:  vtmodel.py build      paste the faces of art/generated/vtuber/*_raw.png -> art/generated/vtuber/*.png
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
BASE = GEN / "nai_test" / "a3_img2img_v5_s050.png"
FACE = (517, 473, 168, 128)                 # ellipse centre x, y, radii x, y (from the earlier face pastes)
FACE_BOX = (349, 346, 337, 255)             # x, y, w, h

EXPR = {
    "base": BASE, "blink": GEN / "nai_test" / "b_blink_final.png", "talk": GEN / "nai_test" / "c_mouth_final.png",
    "shocked": GEN / "expr" / "e3_shocked.png", "flustered": GEN / "expr" / "e4_flustered.png",
    "wink": GEN / "expr" / "e5_meh_squint.png", "laugh": GEN / "expr" / "e6_laughing.png",
    "honest": GEN / "expr" / "e7_honest.png",
    "pain": GEN / "vtuber" / "v08_pain.png", "angry": GEN / "vtuber" / "v09_angry.png",
    "hmph": GEN / "vtuber" / "v10_hmph.png", "smug": GEN / "vtuber" / "v11_smug.png",
    "determined": GEN / "vtuber" / "v12_determined.png", "frustrated": GEN / "vtuber" / "v13_frustrated.png",
    "sing": GEN / "vtuber" / "v14_sing.png", "cheer": GEN / "vtuber" / "v15_cheer.png",
}


def face_mask(shape, feather=14.0, grow=1.0):
    H, W = shape
    yy, xx = np.mgrid[0:H, 0:W]
    cx, cy, rx, ry = FACE
    e = ((xx - cx) / (rx * grow)) ** 2 + ((yy - cy) / (ry * grow)) ** 2
    m = (e <= 1).astype(np.float32)
    return ndimage.gaussian_filter(m, feather)


def transplant(base, raw, search=10):
    """Paste raw's face onto base after aligning it (minimum difference in a ring around the face)."""
    B = np.asarray(base.convert("RGB")).astype(np.float32)
    R = np.asarray(raw.convert("RGB").resize(base.size, Image.Resampling.LANCZOS)).astype(np.float32)
    H, W = B.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    cx, cy, rx, ry = FACE
    e = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
    ring = (e > 1.0) & (e < 1.8)
    best, shift = None, (0, 0)
    for dy in range(-search, search + 1, 2):
        for dx in range(-search, search + 1, 2):
            Rs = np.roll(np.roll(R, dy, 0), dx, 1)
            err = float(np.mean((Rs[ring] - B[ring]) ** 2))
            if best is None or err < best:
                best, shift = err, (dx, dy)
    Rs = np.roll(np.roll(R, shift[1], 0), shift[0], 1)
    m = face_mask((H, W))[..., None]
    out = B * (1 - m) + Rs * m
    return Image.fromarray(out.clip(0, 255).astype(np.uint8)), shift


@lru_cache(None)
def alpha():
    """Cut-out mask from the base's plain background (shared by all expressions; their bodies are identical)."""
    a = np.asarray(Image.open(BASE).convert("RGB")).astype(np.float32) / 255
    fg = sprite.cutout(a)
    corners = np.concatenate([a[:8, :8], a[:8, -8:]]).reshape(-1, 3)
    bg = np.median(corners, 0)
    near = (np.abs(a - bg).sum(2) < 0.07) & (a.max(2) - a.min(2) < 0.08)
    lab, n = ndimage.label(near & fg)                   # background pockets enclosed by hair strands
    if n:
        sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
        pockets = np.isin(lab, [k + 1 for k, s in enumerate(sizes) if s >= 40])
        fg &= ~ndimage.binary_dilation(pockets, iterations=1)
    fg = ndimage.binary_erosion(fg, iterations=1)
    al = (fg * 255).astype(np.uint8)
    return Image.fromarray(al).filter(ImageFilter.GaussianBlur(0.8))


@lru_cache(None)
def model(name):
    im = Image.open(EXPR[name]).convert("RGB").resize((1024, 1024), Image.Resampling.LANCZOS).convert("RGBA")
    im.putalpha(alpha())
    return im


@lru_cache(maxsize=96)
def model_scaled(name, size):
    return model(name).resize((size, size), Image.Resampling.LANCZOS)


def build():
    base = Image.open(BASE)
    for raw in sorted((GEN / "vtuber").glob("*_raw.png")):
        out, shift = transplant(base, Image.open(raw))
        dst = raw.with_name(raw.name.replace("_raw", ""))
        out.save(dst)
        print(dst.name, "shift", shift)


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
