"""Alice-MV-style game pieces on the 960x540 screen: beveled block words that assemble from flying tiles,
key-cap kana tiles, ground tiles and small game icons. Everything is drawn on the pixel grid.
"""
import math
import random
from functools import lru_cache

import numpy as np
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from stage import text_mask

INK = (24, 28, 64)
WHITE = (250, 251, 255)
COBALT = (60, 109, 240)
SKY = (156, 196, 255)
NAVY = (27, 35, 64)
CORAL = (255, 123, 138)
LEMON = (255, 214, 74)

# word styles: face, bevel light, bevel dark, outline, shadow
STYLES = {
    "white": (WHITE, (255, 255, 255), (170, 196, 245), COBALT, (40, 62, 150)),
    "cobalt": (COBALT, SKY, (36, 64, 160), INK, (20, 26, 70)),
    "gold": ((255, 204, 60), (255, 240, 160), (214, 140, 30), (120, 60, 20), (90, 40, 20)),
    "coral": (CORAL, (255, 200, 206), (200, 70, 96), (110, 30, 60), (80, 20, 50)),
    "pink": ((255, 150, 200), (255, 220, 240), (220, 90, 160), (110, 30, 90), (70, 20, 60)),
    "cyan": ((110, 235, 255), (220, 252, 255), (40, 160, 220), (20, 40, 110), (14, 20, 60)),
    "lemon": (LEMON, (255, 244, 180), (214, 160, 30), (110, 70, 20), (80, 50, 20)),
    "navy": (NAVY, (70, 90, 150), (16, 20, 44), WHITE, (10, 12, 30)),
}


def ease_out(u):
    u = min(1.0, max(0.0, u))
    return 1 - (1 - u) ** 3


def ease_out_back(u):
    u = min(1.0, max(0.0, u))
    c = 1.9
    return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2


BOLD = Path(__file__).parent.parent / "pv" / "fonts" / "MPLUSRounded1c-ExtraBold.ttf"


@lru_cache(None)
def glyph_mask(text, font="jp"):
    m = np.asarray(text_mask(text, font)) > 0
    rows = np.nonzero(m.any(1))[0]
    return m[rows.min():rows.max() + 1] if len(rows) else m


@lru_cache(None)
def bold_mask(text, cells=24, k=8, thr=0.45):
    """Block-word glyphs: M PLUS Rounded 1c ExtraBold rendered at cells*k px and area-sampled onto a cell grid
    (strokes come out 2-3 cells wide, so the words stay readable as blocks)."""
    f = ImageFont.truetype(str(BOLD), cells * k)
    w = int(f.getlength(text)) + 4 * k
    im = Image.new("L", (w, cells * k * 2), 0)
    ImageDraw.Draw(im).text((2 * k, k), text, font=f, fill=255)
    a = np.asarray(im).astype(float) / 255
    H, W = a.shape[0] // k, a.shape[1] // k
    m = a[:H * k, :W * k].reshape(H, k, W, k).mean((1, 3)) > thr
    ys, xs = np.nonzero(m)
    ref = Image.new("L", im.size, 0)                    # crop rows to a reference glyph box so baselines agree
    ImageDraw.Draw(ref).text((2 * k, k), "国", font=f, fill=255)
    rb = ref.getbbox()
    y0, y1 = min(ys.min(), rb[1] // k), max(ys.max() + 1, -(-rb[3] // k))
    return m[y0:y1, xs.min():xs.max() + 1]


@lru_cache(None)
def tile(t, style):
    """One beveled block tile, t x t."""
    face, light, dark, _, _ = STYLES[style]
    a = np.zeros((t, t, 4), np.uint8)
    a[:] = (*face, 255)
    b = max(1, t // 5)
    a[:b, :] = (*light, 255)
    a[:, :b] = (*light, 255)
    a[t - b:, :] = (*dark, 255)
    a[:, t - b:] = (*dark, 255)
    a[t - b:, :b] = (*dark, 255)
    if t >= 8:
        a[b, b] = (255, 255, 255, 255)
    return Image.fromarray(a, "RGBA")


@lru_cache(None)
def word_layout(text, t):
    """Tile positions (x, y) of a block word, relative to its top-left, and its size."""
    m = bold_mask(text)
    ys, xs = np.nonzero(m)
    return list(zip((xs * t).tolist(), (ys * t).tolist())), (m.shape[1] * t, m.shape[0] * t)


@lru_cache(None)
def word_base(text, t, style):
    """Outline + drop shadow under the word (drawn once the tiles have landed)."""
    m = bold_mask(text)
    M = np.kron(m, np.ones((t, t), bool))
    sh = max(2, t // 2)
    h, w = M.shape
    canvas = np.zeros((h + sh + 4, w + sh + 4, 4), np.uint8)
    full = np.zeros(canvas.shape[:2], bool)
    full[2 + sh:2 + sh + h, 2 + sh:2 + sh + w] |= M
    full[2:2 + h, 2:2 + w] |= M
    o = full.copy()
    o[1:] |= full[:-1]; o[:-1] |= full[1:]; o[:, 1:] |= full[:, :-1]; o[:, :-1] |= full[:, 1:]
    o2 = o.copy()
    o2[1:] |= o[:-1]; o2[:-1] |= o[1:]; o2[:, 1:] |= o[:, :-1]; o2[:, :-1] |= o[:, 1:]
    _, _, _, outline, shadow = STYLES[style]
    canvas[o2] = (*outline, 255)
    canvas[full] = (*shadow, 255)
    return Image.fromarray(canvas, "RGBA")


@lru_cache(None)
def word_image(text, t, style):
    base = word_base(text, t, style).copy()
    ti = tile(t, style)
    for x, y in word_layout(text, t)[0]:
        base.alpha_composite(ti, (x + 2, y + 2))
    return base


def draw_word(img, text, cx, cy, t, style, t_now, t_land, seed=0, assemble=0.55, leave=None, flash=True):
    """Draw a block word centred at (cx, cy). Tiles fly in during [t_land - assemble, t_land]; with leave=(t0, dur)
    they scatter and fall after t0."""
    pos, (w, h) = word_layout(text, t)
    x0, y0 = int(cx - w // 2), int(cy - h // 2)
    t0 = t_land - assemble
    if t_now < t0:
        return
    if leave and t_now >= leave[0] + leave[1]:
        return
    if t_now >= t_land and not (leave and t_now >= leave[0]):
        img.alpha_composite(word_image(text, t, style), (x0 - 2, y0 - 2))
        if flash and t_now < t_land + 0.07:                 # landing flash: faces white for two frames
            f = tile(t, "white")
            for x, y in pos:
                img.alpha_composite(f, (x0 + x, y0 + y))
        return
    rng = random.Random(f"{text}/{seed}")
    ti = tile(t, style)
    n = len(pos)
    for i, (x, y) in enumerate(pos):
        r1, r2, r3 = rng.random(), rng.random(), rng.random()
        if leave and t_now >= leave[0]:                    # scatter: hop up then fall with gravity
            u = t_now - leave[0] - r3 * 0.12
            if u < 0:
                px, py = x0 + x, y0 + y
            else:
                px = x0 + x + (r1 - 0.5) * 160 * u
                py = y0 + y - (60 + 120 * r2) * u + 1500 * u * u
        else:                                              # assemble: fly in from above / the right
            delay = (x / max(1, w)) * assemble * 0.45 + r3 * assemble * 0.15
            u = (t_now - t0 - delay) / (assemble * 0.55)
            if u <= 0:
                continue
            e = ease_out_back(u)
            sx = x0 + x + (r1 - 0.3) * 420
            sy = y0 + y - 260 - r2 * 240
            px = sx + (x0 + x - sx) * e
            py = sy + (y0 + y - sy) * e
        img.alpha_composite(ti, (int(px), int(py)))


# ---------------------------------------------------------------- key-cap kana (karaoke / furigana)
@lru_cache(None)
def keycap(ch, sung, size=26):
    m = glyph_mask(ch) if ch.strip() else np.zeros((1, 1), bool)
    w = max(size, m.shape[1] + 10)
    h = size + 4
    a = np.zeros((h + 2, w + 2, 4), np.uint8)
    face = COBALT if sung else WHITE
    edge = (30, 54, 140) if sung else (150, 176, 230)
    im = Image.fromarray(a, "RGBA")
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w, h], radius=4, fill=INK)
    d.rounded_rectangle([1, 1, w - 1, h - 1], radius=3, fill=edge)
    d.rounded_rectangle([1, 1, w - 1, h - 5], radius=3, fill=face)
    d.line([4, 3, w - 5, 3], fill=(255, 255, 255) if not sung else SKY)
    a = np.asarray(im).copy()
    gy, gx = (h - 4 - m.shape[0]) // 2 + 1, (w - m.shape[1]) // 2 + 1
    col = WHITE if sung else NAVY
    sub = a[gy:gy + m.shape[0], gx:gx + m.shape[1]]
    sub[m] = (*col, 255)
    return Image.fromarray(a, "RGBA")


# ---------------------------------------------------------------- pixel icons (char grids)
PALETTE = {"K": INK, "C": COBALT, "W": WHITE, "Y": SKY, "R": CORAL, "L": LEMON, "N": NAVY,
           "G": (120, 220, 150), "P": (255, 170, 210), "O": (255, 150, 60), "D": (214, 160, 30)}
ICONS = {
    "heart": [".KK.KK.", "KRRKRRK", "KRWRRRK", "KRRRRRK", ".KRRRK.", "..KRK..", "...K..."],
    "star": ["....K....", "...KLK...", "...KLK...", "KKKLLLKKK", "KLLLWLLLK", ".KLLLLLK.", "..KLLLK..",
             ".KLLKLLK.", ".KLK.KLK.", ".KK...KK."],
    "coin": ["..KKKK..", ".KLLLLK.", "KLWLLDLK", "KLWLDDLK", "KLLLDDLK", "KLLLLDLK", ".KLDDDK.", "..KKKK.."],
    "paw": ["..KK.KK..", ".KCCKCCK.", ".KCCKCCK.", "KKKKKKKKK", "KCCCCCCCK", "KCCCWCCCK", "KCCWWWCCK",
            ".KCCCCCK.", "..KKKKK.."],
    "note": ["...KKKK", "...KCCK", "...K..K", "...K..K", "KKKK.KK", "KCCKKCK", "KKKK.KK"],
    "cat": ["K.......K", "KK.....KK", "KYKKKKKYK", "KYYYYYYYK", "KYKYYYKYK", "KYYYRYYYK", ".KYYYYYK.",
            "..KKKKK.."],
    "check": ["........KK", ".......KGK", "......KGK.", "KK...KGK..", "KGK.KGK...", ".KGKGK....", "..KGK.....",
              "...K......"],
    "cross": ["KK....KK", "KRK..KRK", ".KRKKRK.", "..KRRK..", "..KRRK..", ".KRKKRK.", "KRK..KRK", "KK....KK"],
    "camera": ["..KKKK......", "KKKWWKKKKKKK", "KNNNNNNNNNNK", "KNNNKKKKNNNK", "KNNKYYYYKNNK", "KNNKYWYYKNNK",
               "KNNKYYYYKNNK", "KNNNKKKKNNNK", "KNNNNNNNNNNK", "KKKKKKKKKKKK"],
    "crown": ["K..K..K", "KLKLKLK", "KLLLLLK", "KLWLWLK", "KLLLLLK", "KKKKKKK"],
    "sparkle": ["..W..", "..W..", "WWWWW", "..W..", "..W.."],
}


@lru_cache(None)
def icon(name, k=1):
    rows = ICONS[name]
    a = np.zeros((len(rows), len(rows[0]), 4), np.uint8)
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c != ".":
                a[y, x] = (*PALETTE[c], 255)
    if k > 1:
        a = np.kron(a, np.ones((k, k, 1), np.uint8))
    return Image.fromarray(a, "RGBA")


# ---------------------------------------------------------------- ground tiles (30 px, three rows: 450-540)
GT = 30
# per section: lip (top edge), face colours (alternate for checkers), seam, ink, pattern
GROUND_STYLES = {
    "stage": dict(lip=(255, 226, 170), face=[(196, 132, 88), (182, 120, 80)], seam=(130, 80, 56), ink=(60, 34, 30),
                  pattern="plank"),
    "roof": dict(lip=(255, 255, 255), face=[(214, 224, 240), (200, 212, 234)], seam=(160, 174, 206),
                 ink=(70, 84, 130), pattern="tile"),
    "street": dict(lip=(255, 220, 190), face=[(214, 160, 150), (196, 144, 140)], seam=(150, 100, 108),
                   ink=(60, 34, 56), asphalt=(84, 60, 88), mark=(255, 236, 210), pattern="road"),
    "checker": dict(lip=(255, 255, 255), face=[(60, 109, 240), (240, 246, 255)], seam=(40, 80, 200),
                    ink=(24, 40, 120), pattern="checker"),
    "night": dict(lip=(120, 200, 140), face=[(30, 70, 70), (24, 56, 60)], seam=(16, 40, 46), ink=(10, 24, 34),
                  soil=(36, 38, 70), pattern="grass"),
    "pink": dict(lip=(255, 255, 255), face=[(255, 150, 196), (255, 236, 246)], seam=(230, 110, 170),
                 ink=(150, 50, 110), pattern="checker"),
    "stone": dict(lip=(255, 214, 220), face=[(160, 130, 168), (146, 118, 158)], seam=(104, 80, 124),
                  ink=(56, 36, 76), pattern="tile"),
    "wood": dict(lip=(255, 230, 150), face=[(176, 108, 72), (160, 98, 66)], seam=(110, 62, 50), ink=(56, 30, 30),
                 pattern="plank"),
    "dawn": dict(lip=(255, 255, 255), face=[(236, 222, 236), (224, 210, 230)], seam=(190, 170, 200),
                 ink=(110, 90, 130), pattern="tile"),
}


@lru_cache(None)
def ground_column(style, col_parity):
    """One 30 x 90 column of the ground for a world column (parity alternates checkers, joints and lane dashes)."""
    g = GROUND_STYLES[style]
    t = GT
    a = np.zeros((90, t, 4), np.uint8)
    f0, f1 = g["face"]
    pat = g["pattern"]
    if pat == "checker":
        for row in range(3):
            face = g["face"][(row + col_parity) % 2]
            a[row * t:(row + 1) * t] = (*face, 255)
            a[row * t:row * t + 2] = (*[min(255, v + 30) for v in face], 255)
    elif pat == "tile":
        for row in range(3):
            y0 = row * t
            a[y0:y0 + t] = (*(f0 if row == 0 else f1), 255)
            a[y0 + t - 1, :] = (*g["seam"], 255)
            a[y0:y0 + t, t - 1] = (*g["seam"], 255)
            if row == 0:
                a[y0 + 5:y0 + 7, 2:t - 3] = (*[min(255, v + 18) for v in f0], 255)
    elif pat == "plank":                                     # boards 90 px long, joints staggered per row
        a[:] = (*f0, 255)
        for y in range(5, 90, 15):
            a[y, :] = (*g["seam"], 255)
            a[y + 1, :] = (*[min(255, v + 24) for v in f0], 255)
            if (col_parity + y // 15) % 3 == 0:
                a[y:y + 15, 0] = (*g["seam"], 255)
        a[50:, :] = (*f1, 255)
        for y in range(50, 90, 15):
            a[y, :] = (*g["seam"], 255)
    elif pat == "road":
        a[:22] = (*f0, 255)                                   # sidewalk
        a[21, :] = (*g["seam"], 255)
        a[5:22, t - 1] = (*g["seam"], 255)
        a[22:27] = (*g["lip"], 255)                            # curb
        a[27, :] = (*g["ink"], 255)
        a[28:] = (*g["asphalt"], 255)
        a[28:31] = (*[max(0, v - 20) for v in g["asphalt"]], 255)
        if col_parity % 2:
            a[58:62, 2:t - 2] = (*g["mark"], 255)
    elif pat == "grass":
        a[:] = (*g["soil"], 255)
        a[:14] = (*f0, 255)
        for x in range(t):                                     # ragged grass edge
            d = 14 + (3 if (x * 7 + (col_parity % 2) * 3) % 5 == 0 else 0) + (x % 3 == 0)
            a[14:d, x] = (*f0, 255)
        a[4:7, :] = (*g["lip"], 255)
        for x in range(1, t, 6):
            a[1:4, x] = (*g["lip"], 255)
        for (x, y) in ((5, 40), (19, 58), (11, 76), (26, 30)):
            a[y:y + 2, x:x + 3] = (*[min(255, v + 25) for v in g["soil"]], 255)
    if pat != "grass":
        a[0:4, :] = (*g["lip"], 255)
        a[4, :] = (*g["ink"], 255)
    a[0, :] = (*g["ink"], 255)
    return Image.fromarray(a, "RGBA")


def draw_ground(img, style_at, cam_x, y0=450):
    """Ground band; style_at(screen_x) gives the style per column (lets transitions switch it column by column)."""
    off = int(math.floor(cam_x))
    first = math.floor(off / GT)
    for c in range(first, first + 960 // GT + 2):
        x = c * GT - off
        st = style_at(x)
        if st:
            img.alpha_composite(ground_column(st, c % 6), (x, y0))


@lru_cache(None)
def step_block(style, h):
    """A stair block GT*2 wide, h tall (top lip + tile faces)."""
    col = ground_column(style, 0)
    im = Image.new("RGBA", (GT * 2, h), (0, 0, 0, 0))
    for x in (0, GT):
        for y in range(0, h, 90):
            im.alpha_composite(col if y == 0 else col.crop((0, 30, GT, 90)).resize((GT, 90)), (x, y))
    return im
