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

PICKS = {                       # sprite name -> (N5 take, height in px at 1080p)
    "mochi": ("s2_mochi_44012", 150),         # sky stage, ground enemy
    "plane": ("s2_plane_44012", 140),         # sky stage, air enemy
    "pinwheel": ("s_pinwheel_44001", 120),    # sky stage, saw obstacle (jump over)
    "xiyin_run": ("x_run_42001", 250),        # HD chibi runner test
}


def cutout(im, light=200, sat_max=60, band_px=3):
    """Flat sprite on white -> RGBA without a white fringe.
    background = light, unsaturated pixels connected to the border (the coloured outline stops the flood fill);
    edge band: each pixel is a mix of the nearest inside colour C_in and white W, so
    alpha = |P - W| / |C_in - W| (projected), colour = C_in (the white is removed, not just faded)."""
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    lum = a.mean(-1)
    sat = a.max(-1) - a.min(-1)
    lab, _ = ndimage.label((lum >= light) & (sat < sat_max))
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    fg = ~np.isin(lab, list(border))
    fg = ndimage.binary_opening(fg, iterations=1)
    lab2, n = ndimage.label(fg)                       # drop specks and detached marks (speed lines are kept if big)
    if n:
        sizes = ndimage.sum(fg, lab2, range(1, n + 1))
        fg = np.isin(lab2, [i + 1 for i, s in enumerate(sizes) if s >= 400])
    inner = ndimage.binary_erosion(fg, iterations=band_px)
    _, (iy, ix) = ndimage.distance_transform_edt(~inner, return_indices=True)
    c_in = a[iy, ix]
    W = np.array([255, 255, 255], np.float32)
    d_in = c_in - W
    proj = ((a - W) * d_in).sum(-1) / np.maximum((d_in * d_in).sum(-1), 1.0)
    alpha = np.where(inner, 1.0, np.where(fg, np.clip(proj, 0, 1), 0.0))
    rgb = np.where(inner[..., None], a, c_in)
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
