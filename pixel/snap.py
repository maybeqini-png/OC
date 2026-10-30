"""Snap a pixel-art-style source drawing onto a true pixel grid and recolour it to the OC reference sheet (sprite v2).

The v1 converter (sprite.py) shrank full illustrations, which gave noisy hair, broken outlines and tiny faces.
v2 starts from sources that NovelAI already drew as pixel art (big eyes, clean clusters) and:
1. cuts the plain background away (largest connected part, so stray marks are dropped),
2. labels source pixels by part: hair (the more saturated group of the dark blues, split per image by 2-means),
   sweater, socks (blue patches touching the boots) and accents (small blue patches inside the sweater: collar and
   tie stripes),
3. locks the colours to one palette from the character (median cut, no dithering) and snaps every grid cell to its
   majority colour; thin dark features (outlines, eye lines, mouth) win a cell when they cover 30% of it,
4. repaints hair / sweater / socks / accents with ramps sampled from `art/reference/oc_reference_sheet.webp`,
   keeping each cell's light-to-dark position, so the hair is the sheet's royal blue and clearly brighter than the
   slate-navy sweater (the generator draws both as dark navy),
5. removes lone pixels. The AI's own faces are kept; nothing is redrawn.

usage: snap.py <src.png> <out.png> [--height 160] [--colors 32]
"""
import argparse

import numpy as np
from PIL import Image
from scipy import ndimage

import sprite

# ramps from the reference sheet (dark -> light) with the share of the part's cells each shade takes (by
# brightness rank). Most of her hair in the sheet is the base royal blue (73, 99, 173), so the base gets the
# largest share; see README section 1.
RAMPS = {
    1: ([(40, 58, 118), (56, 78, 148), (73, 99, 173), (96, 124, 199), (132, 158, 224)],
        [0.12, 0.23, 0.45, 0.14, 0.06]),                                    # hair, tail, ears
    2: ([(30, 33, 52), (42, 46, 70), (56, 61, 89), (70, 76, 106)], [0.10, 0.25, 0.55, 0.10]),   # sweater
    3: ([(30, 33, 52), (42, 46, 70), (56, 61, 89)], [0.2, 0.4, 0.4]),                           # socks
    4: ([(71, 97, 174), (110, 140, 210)], [0.6, 0.4]),                                          # cobalt accents
}


def part_labels(a, fg):
    """0 = keep colour, 1 hair, 2 sweater, 3 socks, 4 accent (per source pixel)."""
    h, s, v = sprite.hsv(a)
    blue = fg & (h >= 195) & (h <= 265) & (v >= 0.10) & (v < 0.75) & (s >= 0.15)
    X = np.stack([s[blue], v[blue], (h[blue] - 220) / 60], 1)
    c = np.array([np.percentile(X, 20, 0), np.percentile(X, 80, 0)])
    for _ in range(20):
        lab = ((X[:, None] - c[None]) ** 2).sum(2).argmin(1)
        c = np.array([X[lab == k].mean(0) if (lab == k).any() else c[k] for k in range(2)])
    hair_k = int(np.argmax(c[:, 0] + c[:, 1]))
    hair = np.zeros(a.shape[:2], bool)
    hair[blue] = lab == hair_k
    sweater = blue & ~hair
    out = np.zeros(a.shape[:2], np.int8)
    out[sweater] = 2
    # boots: solid dark, unsaturated areas in the lower part (opening removes the thin outlines everywhere else)
    dark = fg & (v < 0.35) & ((s < 0.30) | sweater)    # these boots come out dark navy or dark grey
    boots = ndimage.binary_opening(dark, iterations=2)
    boots[: int(0.72 * a.shape[0])] = False
    near_boots = ndimage.binary_dilation(boots, iterations=6)
    comp, n = ndimage.label(hair)
    H = a.shape[0]
    total = fg.sum()
    for i, sl in enumerate(ndimage.find_objects(comp), 1):
        m = comp[sl] == i
        area = m.sum()
        cy = (sl[0].start + sl[0].stop) / 2
        if cy > 0.55 * H and (near_boots[sl] & m).any():
            out[sl][m] = 3
            continue
        if area < 0.004 * total:
            ring = ndimage.binary_dilation(m, iterations=3) & ~m
            if ring.any() and sweater[sl][ring].mean() > 0.5:
                out[sl][m] = 4
                continue
        out[sl][m] = 1
    # the tail is drawn navy like the sweater but is hair-coloured on the sheet: a thin, curvy navy patch that is
    # not part of the torso (fill ratio of its box is low) and does not touch the boots
    comp, n = ndimage.label(sweater)
    if n > 1:
        sizes = ndimage.sum(sweater, comp, range(1, n + 1))
        torso = int(np.argmax(sizes)) + 1
        for i, sl in enumerate(ndimage.find_objects(comp), 1):
            if i == torso:
                continue
            m = comp[sl] == i
            area = m.sum()
            fill = area / m.size
            if (near_boots[sl] & m).any():
                out[sl][m] = 3
            elif area > 0.003 * total and fill < 0.4:
                out[sl][m] = 1
    # socks: hair-blue pixels low on the figure, right above / beside the boots
    low = np.zeros_like(fg)
    low[int(0.70 * a.shape[0]):] = True
    near_sock = ndimage.binary_dilation(out == 3, iterations=12)
    out[(out == 1) & low & near_sock] = 3
    return out


def snap(src, height=160, colors=32, recolor=True):
    a = np.asarray(Image.open(src).convert("RGB")).astype(np.float32) / 255
    fg = sprite.cutout(a)
    ys, xs = np.nonzero(fg)
    sl = (slice(ys.min(), ys.max() + 1), slice(xs.min(), xs.max() + 1))
    a, fg = a[sl], fg[sl]
    parts = part_labels(a, fg) if recolor else np.zeros(fg.shape, np.int8)
    cell = a.shape[0] / height
    H, W = height, int(round(a.shape[1] / cell))
    px = (a[fg] * 255).astype(np.uint8).reshape(-1, 1, 3)
    pal_img = Image.fromarray(px).quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = np.array(pal_img.getpalette()[: colors * 3]).reshape(colors, 3).astype(np.float32)
    lum = pal @ np.array([0.299, 0.587, 0.114])
    idx = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).quantize(palette=pal_img, dither=Image.Dither.NONE))
    out = np.full((H, W), -1, np.int16)
    grp = np.zeros((H, W), np.int8)
    for y in range(H):
        y0, y1 = int(round(y * cell)), max(int(round((y + 1) * cell)), int(round(y * cell)) + 1)
        for x in range(W):
            x0, x1 = int(round(x * cell)), max(int(round((x + 1) * cell)), int(round(x * cell)) + 1)
            m = fg[y0:y1, x0:x1]
            if m.mean() < 0.5:
                continue
            cnt = np.bincount(idx[y0:y1, x0:x1][m], minlength=colors)
            pick = cnt.argmax()
            dark = cnt * (lum < 60)                    # outline / eye-line / mouth colours
            if dark.max() >= 0.3 * m.sum() and lum[pick] >= 60:
                pick = dark.argmax()
            out[y, x] = pick
            if lum[pick] >= 40:                         # outlines keep their colour
                grp[y, x] = np.bincount(parts[y0:y1, x0:x1][m], minlength=5).argmax()
    out = despeckle(out)
    rgb = np.zeros((H, W, 3), np.float32)
    ok = out >= 0
    rgb[ok] = pal[out[ok]]
    for g, (ramp, share) in RAMPS.items():
        m = ok & (grp == g)
        if not m.any():
            continue
        L = lum[out[m]]
        rank = (np.argsort(np.argsort(L, kind="stable"), kind="stable") + 0.5) / len(L)   # 0..1 by brightness
        # equal source colours must get one shade: use the mean rank of each source colour
        src = out[m]
        mean_rank = {k: rank[src == k].mean() for k in np.unique(src)}
        r = np.array([mean_rank[k] for k in src])
        edges = np.cumsum(share)[:-1]
        rgb[m] = np.array(ramp, np.float32)[np.searchsorted(edges, r)]
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., :3] = np.clip(rgb, 0, 255)
    rgba[..., 3] = ok * 255
    return Image.fromarray(rgba, "RGBA")


def despeckle(g):
    H, W = g.shape
    out = g.copy()
    for y in range(1, H - 1):
        for x in range(1, W - 1):
            v = g[y, x]
            nb = [g[y + 1, x], g[y - 1, x], g[y, x + 1], g[y, x - 1]]
            if v >= 0 and all(n != v for n in nb):
                vals = [n for n in nb if n >= 0]
                best = max(set(vals), key=vals.count) if vals else v
                if vals.count(best) >= 3:
                    out[y, x] = best
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--height", type=int, default=160)
    ap.add_argument("--colors", type=int, default=32)
    ap.add_argument("--no-recolor", action="store_true")
    a = ap.parse_args()
    im = snap(a.src, a.height, a.colors, not a.no_recolor)
    im.save(a.out)
    print(a.out, im.size)


if __name__ == "__main__":
    main()
