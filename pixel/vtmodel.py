"""XIYIN's VTuber model: the owner's reference sheet bust itself (upscaled, never redrawn) with switchable eyes
and mouth, like a Live2D model's expression set.

Each variant is a V5 img2img take of the base (art/generated/vtuber2/prompts.sh); only its eye or mouth region is
aligned to the base (best shift on a ring around the region) and pasted with a feathered ellipse, so the face,
hair, body and costume stay exactly as on the sheet. One cut-out mask (from the base's white background) serves
all variants.

usage:  vtmodel.py candidates out.png <name> ...     both seeds per expression (choose takes)
        vtmodel.py build <esrgan models dir> [name ...] -> art/generated/vtuber2/final/<name>.png (2048 px)
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

CHEEKS = ((430, 455, 42, 24), (592, 438, 42, 24))
EM = EYES + MOUTH
EMC = EYES + MOUTH + CHEEKS
FINAL = V2 / "final"                         # 2048 px finished frames (Real-ESRGAN x4plus-anime, downsampled)
SHEET = ROOT / "art" / "reference" / "oc_reference_sheet.webp"
SHEET_CROP = (176, 0, 848, 672)
# name: (raw take, regions to paste); "base" is the sheet bust itself
PASTES = {
    "blink": ("blinkc_0.45_31005_raw.png", EYES), "talk": ("talk_0.50_31001_raw.png", MOUTH),
    # open-eye moods keep the sheet's own eyes; only the mouth changes
    "smug": ("smug_32002_raw.png", MOUTH), "angry": ("angry_32002_raw.png", MOUTH),
    "shocked": ("shocked_32001_raw.png", MOUTH),
    "wink": ("wink_32001_raw.png", EM), "cheer": ("cheer_32001_raw.png", EMC), "pain": ("pain_32001_raw.png", EM),
    "hmph": ("hmph_32001_raw.png", EM), "flustered": ("flustered_32002_raw.png", EMC),
    "honest": ("honest_32001_raw.png", EM), "sing": ("sing_32001_raw.png", EM), "laugh": ("laugh_32001_raw.png", EMC),
    "frustrated": ("frustrated_32002_raw.png", EMC)}
ALIAS = {"determined": "smug"}             # the sheet's own confident face already covers it
DESPECK = {"cheer"}                        # takes with stray specks on the skin (no intended tears)


def despeck(im, max_area=60):
    """Remove small stray marks on her skin inside the face (fill with the surrounding skin colour)."""
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    H, W = a.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    cx, cy, rx, ry = FACE
    face = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1
    i = a.astype(np.int16)
    skin = (i[..., 0] > 225) & (i[..., 1] > 185) & (i[..., 2] > 165) & (i[..., 0] >= i[..., 2])
    odd = face & ~skin & (i[..., 2] > i[..., 0] + 15)          # bluish marks
    lab, n = ndimage.label(odd)
    out = a.copy()
    for k, sl in enumerate(ndimage.find_objects(lab), start=1):
        comp = lab[sl] == k
        if comp.sum() > max_area:
            continue
        ys = slice(max(0, sl[0].start - 4), sl[0].stop + 4)
        xs = slice(max(0, sl[1].start - 4), sl[1].stop + 4)
        c2 = lab[ys, xs] == k
        ring = ndimage.binary_dilation(c2, iterations=3) & ~c2
        if skin[ys, xs][ring].mean() > 0.8:                     # isolated on skin (not part of an eye or lash)
            out[ys, xs][ndimage.binary_dilation(c2, iterations=1)] = np.median(a[ys, xs][ring], 0)
    return Image.fromarray(out.clip(0, 255).astype(np.uint8))
EXPR = {n: FINAL / f"{n}.png" for n in ["base", *PASTES]}


def region_mask(shape, ellipses, feather=5.0):
    H, W = shape
    yy, xx = np.mgrid[0:H, 0:W]
    m = np.zeros((H, W), np.float32)
    for cx, cy, rx, ry in ellipses:
        m = np.maximum(m, ((((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2) <= 1).astype(np.float32))
    return ndimage.gaussian_filter(m, feather)


@lru_cache(None)
def skin_mask():
    """Her skin on the 1024 base (plus a 2 px margin): cheek pastes may only change skin, never hair."""
    a = np.asarray(Image.open(BASE).convert("RGB")).astype(np.int16)
    skin = (a[..., 0] > 225) & (a[..., 1] > 185) & (a[..., 2] > 165) & (a[..., 0] >= a[..., 2])
    skin = ndimage.binary_opening(skin, iterations=1)
    return ndimage.gaussian_filter(ndimage.binary_dilation(skin, iterations=2).astype(np.float32), 1.5)


def transplant(base, raw, ellipses, search=8):
    """Paste the regions (ellipses) of raw onto base, after aligning raw on a ring around them. Cheek regions
    are limited to skin."""
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
    core = [e for e in ellipses if e not in CHEEKS]
    cheeks = [e for e in ellipses if e in CHEEKS]
    m = region_mask((H, W), core) if core else np.zeros((H, W), np.float32)
    if cheeks:
        m = np.maximum(m, region_mask((H, W), cheeks) * skin_mask())
    m = m[..., None]
    out = B * (1 - m) + Rs * m
    return Image.fromarray(out.clip(0, 255).astype(np.uint8)), shift


@lru_cache(None)
def alpha():
    """Cut-out mask at 2048 from the final base. The sheet's background is pure white and her skin is near-white,
    so only near-pure-white connected to the image border is background. Enclosed white gaps are removed when
    their surroundings are hair and lines with almost no skin (background seen between strands); white parts of
    the design (ear fur, eye whites, highlights) border skin and are kept."""
    a = np.asarray(Image.open(FINAL / "base.png").convert("RGB")).astype(np.int16)
    white = a.min(2) >= 244
    lab, n = ndimage.label(white)
    border = set(np.unique(np.concatenate([lab[0], lab[:, 0], lab[:, -1]]))) - {0}
    bg = np.isin(lab, list(border))
    hair = (a[..., 2] > a[..., 0] + 40) & (a[..., 2] > a[..., 1] + 20)
    skin = (a[..., 0] > 230) & (a[..., 1] > 190) & (a[..., 2] > 170) & ~white
    gaps = np.zeros_like(bg)
    objs = ndimage.find_objects(lab)
    for k, sl in enumerate(objs, start=1):
        if k in border or sl is None:
            continue
        ys = slice(max(0, sl[0].start - 3), sl[0].stop + 3)
        xs = slice(max(0, sl[1].start - 3), sl[1].stop + 3)
        comp = lab[ys, xs] == k
        ring = ndimage.binary_dilation(comp, iterations=2) & ~comp
        if ring.sum() and hair[ys, xs][ring].mean() > 0.12 and skin[ys, xs][ring].mean() < 0.15:
            gaps[ys, xs] |= comp
    fg = ~(bg | gaps)
    fg = ndimage.binary_opening(fg, iterations=1)
    fg = ndimage.binary_erosion(fg, iterations=1)
    return fg


@lru_cache(None)
def edge_fix():
    """For pixels within 4 px of the cut edge, the nearest pixel 6+ px inside (to replace white fringe)."""
    fg = alpha()
    inner = ndimage.binary_erosion(fg, iterations=6)
    _, (iy, ix) = ndimage.distance_transform_edt(~inner, return_indices=True)
    band = fg & ~ndimage.binary_erosion(fg, iterations=4)
    return band, iy, ix


@lru_cache(None)
def model(name):
    """2048 RGBA frame of the model."""
    name = ALIAS.get(name, name)
    a = np.asarray(Image.open(EXPR[name]).convert("RGB")).copy()
    band, iy, ix = edge_fix()
    lum = a.astype(np.int16).sum(2)
    src = a[iy, ix]
    light = band & (lum > src.astype(np.int16).sum(2) + 30)
    a[light] = src[light]
    al = Image.fromarray((alpha() * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.9))
    im = Image.fromarray(a).convert("RGBA")
    im.putalpha(al)
    return im


@lru_cache(maxsize=96)
def model_scaled(name, size):
    """The model at size x size; FACE / FACE_BOX are in 1024 units (scale by size / 1024)."""
    return model(name).resize((size, size), Image.Resampling.LANCZOS)


@lru_cache(None)
def base_lanczos():
    """The sheet bust at 1024 (plain Lanczos; the anime upscaler then works from the sheet's own pixels)."""
    return Image.open(SHEET).convert("RGB").crop(SHEET_CROP).resize((1024, 1024), Image.Resampling.LANCZOS)


def anime_up(im, models):
    """x4plus-anime x4, then Lanczos down to x2 (crisp lines, clean flat colour)."""
    import upscale
    big = upscale.upscale(im, models, "realesrgan-x4plus-anime", 4)
    return big.resize((im.width * 2, im.height * 2), Image.Resampling.LANCZOS)


def build(models, names=None):
    FINAL.mkdir(exist_ok=True)
    base = base_lanczos()
    if not (FINAL / "base.png").exists():
        anime_up(base, models).save(FINAL / "base.png")
        print("base")
    base2 = np.asarray(Image.open(FINAL / "base.png").convert("RGB")).astype(np.float32)
    for name, (raw, regions) in PASTES.items():
        if names and name not in names:
            continue
        comp, shift = transplant(base, Image.open(V2 / raw), regions)
        xs = [cx for cx, cy, rx, ry in regions]
        x0 = int(min(cx - rx for cx, cy, rx, ry in regions)) - 48
        x1 = int(max(cx + rx for cx, cy, rx, ry in regions)) + 48
        y0 = int(min(cy - ry for cx, cy, rx, ry in regions)) - 48
        y1 = int(max(cy + ry for cx, cy, rx, ry in regions)) + 48
        up = np.asarray(anime_up(comp.crop((x0, y0, x1, y1)), models)).astype(np.float32)
        core = [(cx, cy, rx * 1.25, ry * 1.25) for cx, cy, rx, ry in regions if (cx, cy, rx, ry) not in CHEEKS]
        cheeks = [e for e in regions if e in CHEEKS]
        m = region_mask((1024, 1024), core, 4.0) if core else np.zeros((1024, 1024), np.float32)
        if cheeks:
            m = np.maximum(m, region_mask((1024, 1024), cheeks, 4.0) * skin_mask())
        if name in DESPECK:
            comp = despeck(comp)
        m2 = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize((2048, 2048), Image.Resampling.BILINEAR))
        m2 = (m2[y0 * 2:y1 * 2, x0 * 2:x1 * 2].astype(np.float32) / 255)[..., None]
        out = base2.copy()
        out[y0 * 2:y1 * 2, x0 * 2:x1 * 2] = out[y0 * 2:y1 * 2, x0 * 2:x1 * 2] * (1 - m2) + up * m2
        Image.fromarray(out.clip(0, 255).astype(np.uint8)).save(FINAL / f"{name}.png")
        print(name, "from", raw, "shift", shift)


def candidates(names, out):
    """Quick 1024 composites of both seeds per expression, face close-ups, for choosing takes."""
    from PIL import ImageDraw
    base = base_lanczos()
    rows = []
    for n in names:
        regions = EMC if n in ("cheer", "flustered", "laugh", "frustrated") else EM
        row = []
        for raw in sorted(V2.glob(f"{n}_3*_raw.png")):
            comp, _ = transplant(base, Image.open(raw), regions)
            row.append((raw.name, comp.crop((330, 300, 710, 560))))
        rows.append(row)
    S = Image.new("RGB", (2 * 380 * len(rows[0]) // 2 * 2, 0 or 1), (0, 0, 0))
    cols = 4
    flat = [c for r in rows for c in r]
    S = Image.new("RGB", (cols * 380, ((len(flat) + cols - 1) // cols) * 280), (30, 30, 40))
    d = ImageDraw.Draw(S)
    for i, (nm, im) in enumerate(flat):
        x, y = (i % cols) * 380, (i // cols) * 280
        S.paste(im, (x, y + 18))
        d.text((x + 4, y + 3), nm, fill=(255, 220, 80))
    S.save(out)


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
    if sys.argv[1] == "build":                    # vtmodel.py build MODELS_DIR [name ...]
        build(sys.argv[2], sys.argv[3:] or None)
    elif sys.argv[1] == "candidates":             # vtmodel.py candidates out.png name ...
        candidates(sys.argv[3:], sys.argv[2])
    else:
        sheet(sys.argv[2])
