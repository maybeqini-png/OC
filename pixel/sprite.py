"""Turn an anime source drawing of XIYIN into a pixel sprite with one fixed, hand-designed palette.

usage: sprite.py convert <src.png> <grid.txt> [--block 15]   source drawing -> editable text grid
       sprite.py render <grid.txt> <out.png> [--preview big.png]

Steps (all deterministic):
1. Cut out: flood-fill the plain background from the borders, keep the largest connected part (drops emphasis
   marks, sound-effect text and floor shadows that the generator adds around the character).
2. Classify every source pixel into a role (line, hair, sweater, skin, ...) from its HSV values. In the sources the
   hair and the sweater are both dark navy; they separate by saturation (hair ~0.49, sweater ~0.35, same hue).
3. Downsample block by block: small features (lines, eyes, stripes, blush) win a block when they cover enough of it,
   otherwise the most common role wins. A fixed block size keeps one pixel scale across all sprites.
4. Clean up: lone pixels take their neighbours' role; the silhouette edge becomes the outline colour.
5. Paint roles with PALETTE, where the hair is clearly brighter than the sweater (README section 3).
"""
import argparse
from collections import deque

import numpy as np
from PIL import Image

# role -> RGB. Hair is lighter than the sweater on purpose so the two read apart at pixel size.
PALETTE = {
    "line": (20, 24, 52),
    "hair_dark": (38, 58, 150),
    "hair": (56, 88, 206),
    "hair_light": (112, 150, 244),
    "sweater_dark": (15, 18, 38),
    "sweater": (30, 36, 72),
    "cobalt": (60, 109, 240),
    "sky": (156, 196, 255),
    "white": (244, 246, 251),
    "skin": (255, 234, 222),
    "skin_shadow": (238, 182, 166),
    "pink": (255, 150, 168),
    "coral": (255, 110, 128),
    "shorts": (82, 86, 102),
    "shorts_dark": (58, 61, 74),
    "boots": (34, 36, 46),
    "boots_light": (62, 66, 84),
}
ROLES = list(PALETTE)
SMALL = {"line": 0.24, "white": 0.22, "cobalt": 0.22, "sky": 0.22, "coral": 0.2, "pink": 0.26}


def cutout(a):
    """Foreground mask: everything not reachable from the border through background-coloured pixels."""
    h, w, _ = a.shape
    corners = np.concatenate([a[:8, :8], a[:8, -8:], a[-8:, :8], a[-8:, -8:]]).reshape(-1, 3)
    bg = np.median(corners, 0)
    near = (np.abs(a - bg).sum(2) < 24 / 255) & (a.max(2) - a.min(2) < 18 / 255)   # light, nearly neutral
    seen = np.zeros((h, w), bool)
    q = deque((y, x) for y in range(h) for x in (0, w - 1) if near[y, x])
    q.extend((y, x) for x in range(w) for y in (0, h - 1) if near[y, x])
    for y, x in q:
        seen[y, x] = True
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and near[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                q.append((ny, nx))
    fg = ~seen
    return largest_component(fg)


def largest_component(mask):
    h, w = mask.shape
    lab = np.zeros((h, w), np.int32)
    best, best_n, cur = 0, 0, 0
    for sy, sx in zip(*np.nonzero(mask)):
        if lab[sy, sx]:
            continue
        cur += 1
        n, q = 0, deque([(sy, sx)])
        lab[sy, sx] = cur
        while q:
            y, x = q.popleft()
            n += 1
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not lab[ny, nx]:
                    lab[ny, nx] = cur
                    q.append((ny, nx))
        if n > best_n:
            best, best_n = cur, n
    return lab == best


def hsv(a):
    mx, mn = a.max(2), a.min(2)
    d = mx - mn
    s = np.where(mx > 0, d / np.maximum(mx, 1e-6), 0)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    h = np.zeros_like(mx)
    m = d > 1e-6
    h = np.where(m & (mx == r), ((g - b) / np.maximum(d, 1e-6)) % 6, h)
    h = np.where(m & (mx == g), (b - r) / np.maximum(d, 1e-6) + 2, h)
    h = np.where(m & (mx == b), (r - g) / np.maximum(d, 1e-6) + 4, h)
    return h * 60, s, mx


def classify(a):
    """Role index per pixel (float RGB 0..1 input)."""
    h, s, v = hsv(a)
    role = np.full(h.shape, ROLES.index("sweater"), np.int16)

    def put(name, m):
        role[m] = ROLES.index(name)

    blue = (h >= 195) & (h <= 265)
    warm = (h <= 50) | (h >= 330)
    put("shorts", (s < 0.22) & (v >= 0.30) & (v < 0.62))
    put("shorts_dark", (s < 0.22) & (v >= 0.26) & (v < 0.33))
    put("boots", (s < 0.10) & (v < 0.30))
    put("boots_light", (s < 0.10) & (v >= 0.30) & (v < 0.42) & (a[..., 2] - a[..., 0] < 0.03))
    # Hair and sweater are both dark navy, and how saturated each one comes out varies between generations, so
    # split the dark blues of THIS image in two (2-means on saturation, value, hue): the more saturated / brighter
    # group is the hair.
    dark_blue = blue & (v >= 0.16) & (v < 0.62) & (s >= 0.15)
    X = np.stack([s[dark_blue], v[dark_blue], (h[dark_blue] - 220) / 60], 1)
    c = np.array([np.percentile(X, 20, 0), np.percentile(X, 80, 0)])
    for _ in range(20):
        lab = ((X[:, None] - c[None]) ** 2).sum(2).argmin(1)
        c = np.array([X[lab == k].mean(0) if (lab == k).any() else c[k] for k in range(2)])
    hair_k = int(np.argmax(c[:, 0] + c[:, 1]))
    is_hair = np.zeros(h.shape, bool)
    is_hair[dark_blue] = lab == hair_k
    is_sweater = dark_blue & ~is_hair
    hv, sv = v[is_hair], v[is_sweater]
    h_lo, h_hi = (np.percentile(hv, 25), np.percentile(hv, 88)) if hv.size else (0, 1)
    s_lo = np.percentile(sv, 30) if sv.size else 0
    put("sweater_dark", is_sweater & (v < s_lo))
    put("sweater", is_sweater & (v >= s_lo))
    put("hair_dark", is_hair & (v < h_lo))
    put("hair", is_hair & (v >= h_lo) & (v < h_hi))
    put("hair_light", (is_hair & (v >= h_hi)) | (blue & (s >= 0.35) & (v >= 0.62) & (v < 0.72) & (s < 0.62)))
    put("cobalt", blue & (s >= 0.62) & (v >= 0.52))
    put("sky", blue & (s >= 0.25) & (s < 0.62) & (v >= 0.72))
    put("skin", warm & (s >= 0.035) & (s < 0.20) & (v >= 0.80))
    put("skin_shadow", warm & (s >= 0.15) & (s < 0.40) & (v >= 0.70))
    put("pink", warm & (s >= 0.28) & (v >= 0.70))
    put("coral", warm & (s >= 0.45) & (v >= 0.55) & (v < 0.92) & (h >= 330))
    put("white", (s < 0.035) & (v >= 0.88))
    put("line", v < 0.16)
    return role


def downsample(role, fg, block):
    h, w = role.shape
    H, W = h // block, w // block
    out = np.full((H, W), -1, np.int16)
    n = block * block
    for y in range(H):
        for x in range(W):
            m = fg[y * block:(y + 1) * block, x * block:(x + 1) * block]
            if m.sum() < 0.45 * n:
                continue
            r = role[y * block:(y + 1) * block, x * block:(x + 1) * block][m]
            cnt = np.bincount(r, minlength=len(ROLES))
            pick = int(cnt.argmax())
            for name, frac in SMALL.items():
                i = ROLES.index(name)
                if cnt[i] >= frac * n and i != pick:
                    pick = i
                    break
            out[y, x] = pick
    return out


def cleanup(g):
    H, W = g.shape
    out = g.copy()
    for y in range(H):
        for x in range(W):
            if g[y, x] < 0:
                continue
            nb = [g[y + dy, x + dx] for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))
                  if 0 <= y + dy < H and 0 <= x + dx < W]
            if nb and all(v != g[y, x] for v in nb):
                vals = [v for v in nb if v >= 0]
                if vals and g[y, x] not in (ROLES.index("white"), ROLES.index("cobalt"), ROLES.index("coral")):
                    out[y, x] = max(set(vals), key=vals.count)
    # light gaps between hair strands come out white: give them the surrounding hair colour
    white, hair = ROLES.index("white"), {ROLES.index(r) for r in ("hair_dark", "hair", "hair_light")}
    for y in range(H):
        for x in range(W):
            if out[y, x] == white:
                nb = [out[y + dy, x + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                      if (dy or dx) and 0 <= y + dy < H and 0 <= x + dx < W]
                hn = [v for v in nb if v in hair]
                if len(hn) >= 2 or (len(hn) >= 1 and any(v < 0 for v in nb)):
                    out[y, x] = max(set(hn), key=hn.count)
    line = ROLES.index("line")
    for y in range(H):
        for x in range(W):
            if out[y, x] >= 0 and any(not (0 <= y + dy < H and 0 <= x + dx < W) or out[y + dy, x + dx] < 0
                                      for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out[y, x] = line
    return out


def paint(g):
    H, W = g.shape
    im = np.zeros((H, W, 4), np.uint8)
    for i, name in enumerate(ROLES):
        im[g == i, :3] = PALETTE[name]
        im[g == i, 3] = 255
    return Image.fromarray(im, "RGBA")


# One character per role, so sprites are stored as text grids that can be hand-edited and diffed.
CHARS = {"line": "K", "hair_dark": "h", "hair": "H", "hair_light": "L", "sweater_dark": "s", "sweater": "S",
         "cobalt": "C", "sky": "Y", "white": "W", "skin": "F", "skin_shadow": "f", "pink": "P", "coral": "R",
         "shorts": "G", "shorts_dark": "g", "boots": "B", "boots_light": "b"}
FROM_CHAR = {c: ROLES.index(r) for r, c in CHARS.items()}


def grid_to_text(g):
    return "\n".join("".join("." if v < 0 else CHARS[ROLES[v]] for v in row) for row in g) + "\n"


def text_to_grid(text):
    rows = [r for r in text.splitlines() if r and not r.startswith("#")]
    w = max(len(r) for r in rows)
    return np.array([[FROM_CHAR.get(c, -1) for c in r.ljust(w, ".")] for r in rows], np.int16)


def erode(m, r):
    out = m.copy()
    for _ in range(r):
        e = out.copy()
        e[1:] &= out[:-1]; e[:-1] &= out[1:]; e[:, 1:] &= out[:, :-1]; e[:, :-1] &= out[:, 1:]
        out = e
    return out


def convert(src, block):
    a = np.asarray(Image.open(src).convert("RGB")).astype(np.float32) / 255
    fg = erode(cutout(a), 3)   # drop the anti-aliased fringe that otherwise reads as white edge pixels
    ys, xs = np.nonzero(fg)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    # pad the crop to whole blocks, anchored at the feet (bottom) and the horizontal centre
    hh = -(-(y1 - y0) // block) * block
    ww = -(-(x1 - x0) // block) * block
    y0 = max(0, y1 - hh)
    cx = (x0 + x1) // 2
    x0 = max(0, cx - ww // 2)
    a, fg = a[y0:y0 + hh, x0:x0 + ww], fg[y0:y0 + hh, x0:x0 + ww]
    return cleanup(downsample(classify(a), fg, block))


def load(path):
    """Sprite image from a hand-editable text grid."""
    return paint(text_to_grid(open(path, encoding="utf-8").read()))


def preview(im, out, scale=8):
    bg = Image.new("RGBA", im.size, (200, 205, 220, 255))
    bg.alpha_composite(im)
    big = bg.resize((im.width * scale, im.height * scale), Image.Resampling.NEAREST)
    from PIL import ImageDraw
    d = ImageDraw.Draw(big)
    for x in range(0, im.width, 5):          # coordinate ticks every 5 px, for hand edits of the grid
        d.line([(x * scale, 0), (x * scale, 3)], fill=(255, 0, 0))
    for y in range(0, im.height, 5):
        d.line([(0, y * scale), (3, y * scale)], fill=(255, 0, 0))
    big.save(out)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("convert", help="source drawing -> text grid")
    c.add_argument("src")
    c.add_argument("grid")
    c.add_argument("--block", type=int, default=15)
    r = sub.add_parser("render", help="text grid -> PNG (+ optional enlarged preview)")
    r.add_argument("grid")
    r.add_argument("out")
    r.add_argument("--preview")
    a = ap.parse_args()
    if a.cmd == "convert":
        g = convert(a.src, a.block)
        open(a.grid, "w", encoding="utf-8").write(grid_to_text(g))
        print(a.grid, g.shape[::-1])
    else:
        im = load(a.grid)
        im.save(a.out)
        if a.preview:
            preview(im, a.preview)
        print(a.out, im.size)


if __name__ == "__main__":
    main()
