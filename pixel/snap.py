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
    blue = fg & (h >= 190) & (h <= 265) & (v >= 0.10) & (s >= 0.15)
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
        if area < 0.0015 * total and v[sl][m].mean() > 0.70:   # eyes, hair clip: keep their own bright blue
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


def face_width(a, fg):
    """Width (source px) of the face: the largest skin-coloured blob in the upper half of the figure."""
    h, s, v = sprite.hsv(a)
    skin = fg & ((h <= 40) | (h >= 345)) & (s >= 0.03) & (s < 0.35) & (v >= 0.80)
    skin[a.shape[0] // 2:] = False
    comp, n = ndimage.label(skin)
    if n == 0:
        return None
    i = int(np.argmax(ndimage.sum(skin, comp, range(1, n + 1)))) + 1
    xs = np.nonzero(comp == i)[1]
    return xs.max() - xs.min() + 1


def snap(src, height=160, colors=32, recolor=True, face_px=None):
    """face_px: size by face width (art px) instead of figure height, so every pose shares one pixel scale."""
    a = np.asarray(Image.open(src).convert("RGB")).astype(np.float32) / 255
    fg = sprite.cutout(a)
    ys, xs = np.nonzero(fg)
    sl = (slice(ys.min(), ys.max() + 1), slice(xs.min(), xs.max() + 1))
    a, fg = a[sl], fg[sl]
    parts = part_labels(a, fg) if recolor else np.zeros(fg.shape, np.int8)
    fw = face_width(a, fg) if face_px else None
    cell = fw / face_px if fw else a.shape[0] / height
    H, W = int(round(a.shape[0] / cell)), int(round(a.shape[1] / cell))
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


# ---------------------------------------------------------------- v3: clean pixel art with one fixed palette
# The NovelAI "pixel art" is soft (over half of its colour runs are 1 px: blended edges, in-between colours), so
# re-gridding its own colours looks blurry. v3 maps every source pixel to a fixed, role-based palette first
# (hair / sweater / socks+boots / accents by brightness rank inside the part, everything else by nearest colour),
# then takes the majority per cell, with thin features (outline, pupils, mouth, eye shine) winning thin cells,
# then despeckles and redraws a clean 1 px silhouette outline.
OUTLINE = (24, 28, 54)
PART_RAMPS = {
    1: ([(40, 58, 118), (56, 78, 148), (73, 99, 173), (118, 146, 214)], [0.15, 0.30, 0.43, 0.12]),   # hair
    2: ([(28, 31, 50), (44, 48, 74), (60, 66, 96)], [0.20, 0.55, 0.25]),                              # sweater
    3: ([(30, 32, 46), (48, 52, 72), (66, 72, 96)], [0.35, 0.45, 0.20]),                              # socks, boots
    4: ([(71, 97, 174), (150, 180, 235)], [0.6, 0.4]),                                                # accents
}
OTHER = {"outline": OUTLINE, "skin": (255, 236, 226), "skin_shadow": (240, 196, 186), "blush": (255, 165, 170),
         "ear_pink": (236, 160, 168), "iris": (64, 110, 222), "iris_light": (130, 175, 245), "pupil": (28, 38, 86),
         "white": (248, 250, 255), "mouth": (196, 80, 100), "shorts": (76, 80, 100), "shorts_dark": (56, 60, 78),
         "cobalt": (71, 97, 174), "sky": (156, 196, 255)}
THIN = {"outline": 0.28, "pupil": 0.25, "mouth": 0.25, "white": 0.3, "iris_light": 0.3}


def _lab(rgb):
    c = np.asarray(rgb, np.float32) / 255
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def clean(src, height=112):
    a = np.asarray(Image.open(src).convert("RGB")).astype(np.float32) / 255
    fg = sprite.cutout(a)
    ys, xs = np.nonzero(fg)
    sl = (slice(ys.min(), ys.max() + 1), slice(xs.min(), xs.max() + 1))
    a, fg = a[sl], fg[sl]
    parts = part_labels(a, fg)
    colours = list(OTHER.values())
    names = list(OTHER.keys())
    base = len(colours)
    for g, (ramp, _) in PART_RAMPS.items():
        colours += ramp
    pal = np.array(colours, np.float32)
    idx = np.full(fg.shape, -1, np.int16)
    lum = a @ np.array([0.299, 0.587, 0.114], np.float32)
    off = base
    for g, (ramp, share) in PART_RAMPS.items():
        m = fg & (parts == g)
        if m.any():
            L = lum[m]
            r = (np.argsort(np.argsort(L, kind="stable"), kind="stable") + 0.5) / len(L)
            idx[m] = off + np.searchsorted(np.cumsum(share)[:-1], r)
        off += len(ramp)
    m = fg & (parts == 0)
    lab_src = _lab(a[m] * 255)
    lab_pal = _lab(np.array(list(OTHER.values()), np.float32))
    idx[m] = ((lab_src[:, None] - lab_pal[None]) ** 2).sum(2).argmin(1)
    # very dark pixels anywhere are outline
    idx[fg & (lum < 0.13)] = names.index("outline")
    cell = a.shape[0] / height
    H, W = height, int(round(a.shape[1] / cell))
    out = np.full((H, W), -1, np.int16)
    thin = {names.index(k): v for k, v in THIN.items()}
    for y in range(H):
        y0, y1 = int(round(y * cell)), max(int(round((y + 1) * cell)), int(round(y * cell)) + 1)
        for x in range(W):
            x0, x1 = int(round(x * cell)), max(int(round((x + 1) * cell)), int(round(x * cell)) + 1)
            mm = fg[y0:y1, x0:x1]
            if mm.mean() < 0.5:
                continue
            cnt = np.bincount(idx[y0:y1, x0:x1][mm], minlength=len(pal))
            pick = int(cnt.argmax())
            for i, frac in thin.items():
                if i != pick and cnt[i] >= frac * mm.sum():
                    pick = i
                    break
            out[y, x] = pick
    out = despeckle(out)
    o = names.index("outline")
    edge = (out >= 0) & ~ndimage.binary_erosion(out >= 0, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]]),
                                                 border_value=0)
    out[edge] = o
    rgba = np.zeros((H, W, 4), np.uint8)
    ok = out >= 0
    rgba[ok, :3] = pal[out[ok]]
    rgba[ok, 3] = 255
    return Image.fromarray(rgba, "RGBA")
