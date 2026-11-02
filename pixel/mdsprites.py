"""HD game sprites in a flat, thick-outline style (Muse Dash-like genre look; original designs) from N5 drawings.

Cut-out without white fringes: the drawings sit on white and their outer edge is always the dark outline, so
- background = light pixels connected to the image border (the outline blocks the flood fill, so light parts of the
  drawing inside the outline stay);
- edge pixels (next to the background) are an unknown mix of the outline colour and white: alpha is solved from
  that mix, alpha = (255 - L) / (255 - L_outline), and their colour is set to the outline colour (no white left);
- a soft ground shadow (light, connected to the background) is removed by the same flood fill.

usage: python3 mdsprites.py build [out_sheet.png]
"""
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).parent
ROOT = HERE.parent
SRC = ROOT / "art/generated/md_style"
DST = HERE / "md"

PICKS = {                       # sprite name -> (N5 take, height in px at 1080p, facing)
    "mouse": ("m_mouse_41001", 150),
    "box": ("m_box_41001", 150),
    "bubble": ("m_bubble_41001", 140),
    "taiyaki": ("m_taiyaki_41001", 130),
    "yarn": ("o_yarn_41001", 130),
}


def cutout(im, light=200, edge=2):
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    lum = a.mean(-1)
    sat = a.max(-1) - a.min(-1)
    cand = (lum >= light) & (sat < 60)
    lab, _ = ndimage.label(cand)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    bg = np.isin(lab, list(border))
    fg = ~bg
    fg = ndimage.binary_opening(fg, iterations=1)
    fg = ndimage.binary_fill_holes(fg) & fg | (fg & ~bg)
    band = fg & ~ndimage.binary_erosion(fg, iterations=edge)
    # outline colour: the darkest pixels just inside the band
    inner = ndimage.binary_erosion(fg, iterations=edge) & ~ndimage.binary_erosion(fg, iterations=edge + 4)
    dark = a[inner & (lum < np.percentile(lum[inner], 30))]
    out_col = np.median(dark, 0) if len(dark) else np.array([30, 30, 40], np.float32)
    lo = float(out_col.mean())
    alpha = fg.astype(np.float32)
    al = np.clip((255 - lum) / max(1.0, 255 - lo), 0, 1)
    alpha[band] = al[band]
    rgb = a.copy()
    lighter = band & (lum > lo + 8)
    rgb[lighter] = out_col
    rgba = np.dstack([rgb, alpha * 255]).clip(0, 255).astype(np.uint8)
    out = Image.fromarray(rgba, "RGBA")
    return out.crop(out.getbbox())


@lru_cache(None)
def sprite(name, height=None):
    take, h = PICKS[name]
    im = Image.open(DST / f"{name}.png").convert("RGBA")
    h = height or h
    w = round(im.width * h / im.height)
    return im.resize((w, h), Image.Resampling.LANCZOS)        # Pillow resizes RGBA premultiplied


def build(sheet=None):
    DST.mkdir(exist_ok=True)
    tiles = []
    for name, (take, h) in PICKS.items():
        im = cutout(Image.open(SRC / f"{take}.png"))
        im.save(DST / f"{name}.png")
        tiles.append(im)
        print(name, im.size)
    if sheet:
        bgs = [(30, 24, 60), (255, 120, 200), (120, 200, 255)]
        th = 300
        W = sum(int(t.width * th / t.height) + 20 for t in tiles)
        S = Image.new("RGB", (W, th * 3 + 40))
        for r, bgc in enumerate(bgs):
            S.paste(Image.new("RGB", (W, th + 10), bgc), (0, r * (th + 10)))
            x = 10
            for t in tiles:
                s = t.resize((int(t.width * th / t.height), th), Image.Resampling.LANCZOS)
                S.paste(s, (x, r * (th + 10) + 5), s)
                x += s.width + 20
        S.save(sheet)


if __name__ == "__main__" and sys.argv[1] == "build":
    build(sys.argv[2] if len(sys.argv) > 2 else None)
