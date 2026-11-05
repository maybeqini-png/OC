"""Fix the stream-cam pout frame (owner 2026-11-05: "the colours on the face look off", 1:40): its closed eyes had
grey-blue smudges under them and dark grey lids. The face of a V5 img2img redraw (art/generated/vtuber3/fix,
pout_0.30_69002, same expression, clean pink blush) is transplanted back into final/pout.png with a feathered
ellipse, its colours matched to the frame's skin.

usage: python3 vtfix.py
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).parent.parent
FINAL = ROOT / "art/generated/vtuber3/final/pout.png"
FIX = ROOT / "art/generated/vtuber3/fix/pout_0.30_69002.png"
BOX = (560, 380)                     # crop origin in the 2048 frame (fix/pout_crop.png)
EDGE = 70                            # feather width at the crop's edges (in hair / background, where lines are busy)


# cheeks (crop px): the redraw's puffed cheeks carry soft airbrushed contour lines that read as smudges (owner
# 2026-11-05: "both cheeks look painted on"). Inside these ellipses every skin pixel is repainted as flat cel skin with
# one soft round blush, as the other expressions are drawn; dark line art is kept.
CHEEKS = [((232, 772), (150, 125)), ((612, 620), (120, 100))]


def flat_cheeks(img):
    a = np.asarray(img).astype(np.float32)
    H, W = a.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = a.mean(-1)
    dark = lum < 170
    from scipy import ndimage
    near_line = ndimage.binary_dilation(dark, iterations=2)
    skinish = (r > 215) & (r > b + 4) & ~near_line
    base = np.median(a[(r > 240) & (g > 225) & (r > b + 8) & (yy > 400) & (yy < 900)], 0)
    blush = np.array((250, 188, 196), np.float32)
    for (cx, cy), (rx, ry) in CHEEKS:
        d = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
        inside = (d < 1.0) & skinish
        w = np.clip(1 - d, 0, 1) ** 1.2 * 0.55                 # soft round blush, strongest in the middle
        flat = base[None, None, :] * (1 - w[..., None]) + blush[None, None, :] * w[..., None]
        edge = np.clip((1.0 - d) / 0.15, 0, 1)[..., None]       # blend into the untouched skin at the rim
        a[inside] = (flat * edge + a * (1 - edge))[inside]
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


def build():
    base = Image.open(FINAL).convert("RGB")
    crop = base.crop((BOX[0], BOX[1], BOX[0] + 1024, BOX[1] + 1024))
    red = flat_cheeks(Image.open(FIX).convert("RGB").resize((1024, 1024)))
    a, b = np.asarray(crop).astype(np.float32), np.asarray(red).astype(np.float32)
    skin = (a[..., 0] > 235) & (a[..., 0] > a[..., 2] + 15) & (b[..., 0] > 235)
    b[skin] += np.median(a[skin] - b[skin], 0)              # the frame's skin tone (the seam never crosses skin)
    red = Image.fromarray(b.clip(0, 255).astype(np.uint8))
    # the whole face comes from the redraw (owner 2026-11-05: blending two drawings across the cheek left a ghosted,
    # painted-on outline); the seam lies at the crop's edges, in the hair and background, feathered there only
    m = Image.new("L", (1024, 1024), 0)
    ImageDraw.Draw(m).rectangle((EDGE, EDGE, 1023 - EDGE, 1023 - EDGE), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(EDGE / 2.5))
    out = base.copy()
    out.paste(Image.composite(red, crop, m), BOX)
    out.save(FINAL)
    return out


if __name__ == "__main__":
    build()
