"""Hand-drawn pixel faces for XIYIN's sprites.

The converter (sprite.py) keeps the body but cannot keep a readable face at ~80 px. Each sprite gets its face
redrawn from the same small set of eye / mouth templates, placed by hand (FACES below), so her expressions stay
consistent and cheeky across all sprites.

usage: faces.py            -> pixel/sprites/<name>.txt (auto grid + face) and <name>.png for every entry in FACES
Template characters are sprite.CHARS ('.' = leave the pixel as it is, '_' = skin).
"""
from pathlib import Path

import numpy as np

import sprite

EYES = {
    "smug_l": ["KKKKK", ".hCCY", "..CC."],      # heavy lid, iris peeking: the default smug look
    "smug_r": ["KKKKK", "YCCh.", ".CC.."],
    "open_l": [".KKK.", "KYCCK", "KCCCK", ".hhh."],
    "open_r": [".KKK.", "KCCYK", "KCCCK", ".hhh."],
    "shock": [".KKK.", "KWWWK", "KWCWK", ".KKK."],
    "happy": ["..K..", ".K_K.", "K___K"],        # ^ (closed, smiling)
    "closed": ["_____", "KKKKK"],               # calm / pouting closed eye
    "squint_l": ["K....", ".KKK.", "K...."],    # >
    "squint_r": ["....K", ".KKK.", "....K"],    # <
}
MOUTHS = {
    "cat": ["K.K.K", ".K.K."],                  # :3 smug cat mouth
    "grin_fang": ["KKKKK", "KWRRK", ".KKK."],   # open grin, fang on the left
    "open": [".KK.", "KRRK", ".KK."],
    "small_o": ["KK", "KK"],
    "tongue": ["KKKK", ".RR.", ".RR."],         # あっかんべー
    "pout": [".K.", "K.K"],
    "flat": ["KKK"],
}
BLUSH = ["PP"]

# per sprite: "clean" rectangle (x0, y0, x1, y1) is reset to skin (hair pixels inside are kept), then eyes, mouth and
# blush templates are stamped at (x, y). "recolor" / "clear" fix body parts the converter got wrong; the silhouette
# outline is redrawn afterwards.
FACES = {
    "s01_idle_smug": {"clean": (15, 19, 31, 31), "eyes": [("smug_l", 15, 22), ("smug_r", 25, 22)],
                      "mouth": ("cat", 20, 28), "blush": [(15, 26), (28, 26)],
                      "recolor": [(18, 31, 30, 35, "P", "f")]},
    "s02_tap_jump": {"clean": (17, 17, 34, 29), "eyes": [("open_l", 17, 21), ("open_r", 27, 18)],
                     "mouth": ("grin_fang", 23, 25), "blush": [(17, 25), (31, 22)]},
    "s03_trip": {"clean": (12, 19, 27, 30), "eyes": [("shock", 11, 20), ("shock", 21, 20)],
                 "mouth": ("open", 17, 26), "blush": [],
                 "recolor": [(15, 59, 28, 71, "sSh", "B"), (36, 58, 52, 62, "sSh", "B")],
                 "clear": [(25, 71, 54, 76), (0, 75, 54, 76)]},
    "s04_nocount_x": {"clean": (15, 16, 31, 26), "eyes": [("closed", 15, 17), ("closed", 25, 17)],
                      "mouth": ("pout", 21, 22), "blush": [(15, 21), (28, 21)]},
    "s05_me_boop": {"clean": (11, 22, 29, 32), "eyes": [("happy", 12, 24), ("open_r", 22, 23)],
                    "mouth": ("open", 18, 29), "blush": [(11, 28), (26, 28)],
                    "recolor": [(10, 69, 34, 80, "hH", "B"), (10, 60, 34, 69, "Y", "C")]},
    "s06_akanbe": {"clean": (14, 20, 30, 31), "eyes": [("open_l", 13, 24), ("squint_r", 25, 23)],
                   "mouth": ("tongue", 21, 28), "blush": [(26, 27)]},
    "s07_pupu_laugh": {"clean": (15, 20, 30, 29), "eyes": [("smug_l", 14, 23), ("smug_r", 24, 21)],
                       "mouth": None, "blush": [(15, 26), (27, 25)]},
}


def stamp(g, tpl, x, y):
    for dy, row in enumerate(tpl):
        for dx, c in enumerate(row):
            if c == ".":
                continue
            yy, xx = y + dy, x + dx
            if 0 <= yy < g.shape[0] and 0 <= xx < g.shape[1]:
                g[yy, xx] = sprite.FROM_CHAR["F"] if c == "_" else sprite.FROM_CHAR[c]


def smooth(g, passes=2):
    """Remove single-pixel speckle inside hair and sweater (shade changes only, silhouette untouched)."""
    fams = [{sprite.FROM_CHAR[c] for c in "hHL"}, {sprite.FROM_CHAR[c] for c in "sS"}]
    H, W = g.shape
    for _ in range(passes):
        out = g.copy()
        for y in range(1, H - 1):
            for x in range(1, W - 1):
                fam = next((f for f in fams if g[y, x] in f), None)
                if fam is None:
                    continue
                nb = [g[y + dy, x + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]
                if sum(n in fam for n in nb) >= 6:
                    best = max(fam, key=nb.count)
                    if nb.count(best) >= 5:
                        out[y, x] = best
        g = out
    return g


def apply(g, spec):
    g = smooth(g)
    x0, y0, x1, y1 = spec["clean"]
    keep = {sprite.FROM_CHAR[c] for c in "hHL"}
    for y in range(y0, y1):
        for x in range(x0, x1):
            if g[y, x] >= 0 and g[y, x] not in keep:
                g[y, x] = sprite.FROM_CHAR["F"]
    for name, x, y in spec["eyes"]:
        stamp(g, EYES[name], x, y)
    if spec.get("mouth"):
        stamp(g, MOUTHS[spec["mouth"][0]], spec["mouth"][1], spec["mouth"][2])
    for x, y in spec.get("blush", []):
        stamp(g, BLUSH, x, y)
    for x0, y0, x1, y1, src, dst in spec.get("recolor", []):
        sub = g[y0:y1, x0:x1]
        for c in src:
            sub[sub == sprite.FROM_CHAR[c]] = sprite.FROM_CHAR[dst]
    for x0, y0, x1, y1 in spec.get("clear", []):
        g[y0:y1, x0:x1] = -1
    return outline(g)


def outline(g):
    """Silhouette edge pixels become the outline colour (redone after hand edits)."""
    H, W = g.shape
    line = sprite.FROM_CHAR["K"]
    out = g.copy()
    for y in range(H):
        for x in range(W):
            if g[y, x] >= 0 and any(not (0 <= y + dy < H and 0 <= x + dx < W) or g[y + dy, x + dx] < 0
                                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out[y, x] = line
    return out


def main():
    d = Path(__file__).parent / "sprites"
    for name, spec in FACES.items():
        g = sprite.text_to_grid((d / f"{name}.auto.txt").read_text(encoding="utf-8"))
        g = apply(g, spec)
        (d / f"{name}.txt").write_text(sprite.grid_to_text(g), encoding="utf-8")
        im = sprite.paint(g)
        im.save(d / f"{name}.png")
        print(name, im.size)


if __name__ == "__main__":
    main()
