"""Generic pixel snap for N5 game props (enemies): cut out the white background, quantize to a small palette,
take the majority colour per cell, then a 1 px dark outline. (Characters use snap.clean with the sheet palette.)

usage:  props.py src.png out.png --height 80 [--colors 12] [--crop x0 y0 x1 y1]
"""
import argparse

import numpy as np
from PIL import Image
from scipy import ndimage

import sprite

OUTLINE = (24, 28, 54)


def snap_prop(src, height, colors=12, crop=None):
    im = Image.open(src).convert("RGB")
    if crop:
        im = im.crop(crop)
    a = np.asarray(im).astype(np.float32) / 255
    fg = sprite.cutout(a)
    ys, xs = np.nonzero(fg)
    sl = (slice(ys.min(), ys.max() + 1), slice(xs.min(), xs.max() + 1))
    im = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    fg = fg[sl]
    q = im.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, kmeans=3, dither=Image.Dither.NONE)
    pal = np.array(q.getpalette()[:colors * 3]).reshape(-1, 3)
    idx = np.asarray(q)
    cell = idx.shape[0] / height
    H, W = height, int(round(idx.shape[1] / cell))
    out = np.full((H, W), -1, np.int32)
    for y in range(H):
        y0, y1 = int(round(y * cell)), max(int(round((y + 1) * cell)), int(round(y * cell)) + 1)
        for x in range(W):
            x0, x1 = int(round(x * cell)), max(int(round((x + 1) * cell)), int(round(x * cell)) + 1)
            m = fg[y0:y1, x0:x1]
            if m.mean() < 0.5:
                continue
            out[y, x] = np.bincount(idx[y0:y1, x0:x1][m], minlength=colors).argmax()
    solid = out >= 0
    edge = solid & ~ndimage.binary_erosion(solid, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]]),
                                           border_value=0)
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[solid, :3] = pal[out[solid]]
    rgba[solid, 3] = 255
    rgba[edge, :3] = OUTLINE
    return Image.fromarray(rgba, "RGBA")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--height", type=int, default=80)
    ap.add_argument("--colors", type=int, default=12)
    ap.add_argument("--crop", type=int, nargs=4)
    a = ap.parse_args()
    snap_prop(a.src, a.height, a.colors, a.crop).save(a.out)
