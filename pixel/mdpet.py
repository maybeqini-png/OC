"""XIYIN's companion, the sleepy cat spirit (Muse Dash's floating "Elfin" role; art/generated/md_style/c_sleepcat_49502
and its brat/c_wink_*, brat/c_awake_* variants).

It floats behind her shoulder, trailing her a little (it follows where she was 0.12 s ago) and bobbing on the beat.
It mirrors her sleeping-cat chest patch: it dozes through the run with Zz bubbles, peeks one eye open at each
ノーカン (her excuse makes it suspicious), and wakes fully - with a "!" pop - for the climb and both boss fights,
where it cheers; it nods off again after each BREAK!!.
"""
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import mdsprites as MD

SRC = Path(__file__).parent.parent / "art/generated/md_style"
TAKES = {"sleep": "c_sleepcat_49502", "wink": "brat/c_wink2_65112", "awake": "brat/c_awake2_65111"}
SIZE = 118                     # px (its cloud is about the width of her head)
LAG = 0.12
BEAT = 60 / 136
WINK = [(46.4, 48.4), (62.3, 64.2)]          # ノーカン


@lru_cache(None)
def sprite(state):
    src = Image.open(SRC / f"{TAKES[state]}.png").convert("RGB")
    a = np.asarray(src).astype(np.float32)
    # its drawn floor shadow (a flat blue ellipse below the cloud) goes: paint it white before the cut-out
    H = a.shape[0]
    low = np.zeros(a.shape[:2], bool)
    low[int(H * 0.78):] = True
    shadow = low & (a[..., 2] > a[..., 0] + 25) & (a.mean(-1) < 200)
    a[shadow] = 255
    im = MD.cutout(Image.fromarray(a.astype(np.uint8)))
    return im.resize((round(im.width * SIZE / im.height), SIZE), Image.Resampling.LANCZOS)


def awake_spans():
    import mdboss
    spans = [(mdboss.OMEN[0] + 0.4, mdboss.OMEN[1])]
    for key, b in mdboss.BOSSES.items():
        spans.append((b["warn"], mdboss.timeline(key)[2] + 1.3))
    return spans


def state(g):
    for a, b in awake_spans():
        if a <= g < b:
            return "awake", g - a
    for a, b in WINK:
        if a <= g < b:
            return "wink", g - a
    return "sleep", 0.0


def draw(img, g, cx, fy, height_at):
    """Behind her. cx, fy = her centre x and feet y now; height_at(g) = her height above the floor."""
    import mdgame as G
    lag_h = height_at(g - LAG)
    st, age = state(g)
    bob = 9 * math.sin(2 * math.pi * g / (2 * BEAT))
    x = cx - 118
    y = G.FLOOR - lag_h - 330 + bob
    sp = sprite(st)
    if age < 0.18 and st != "sleep":                       # pop when it changes state
        k = 1 + 0.25 * math.sin(math.pi * age / 0.18)
        sp = sp.resize((int(sp.width * k), int(sp.height * k)), Image.Resampling.BICUBIC)
    if st == "awake":                                      # cheering hop on the beat
        y -= 8 * abs(math.sin(math.pi * g / BEAT))
    img.alpha_composite(sp, (int(x - sp.width / 2), int(y - sp.height / 2)))
    d = ImageDraw.Draw(img)
    if st == "sleep":                                      # Zz bubbles drifting up
        for k in range(2):
            u = ((g / (2 * BEAT)) + k * 0.5) % 1
            zx, zy = x + 30 + 26 * u, y - 52 - 70 * u
            s = int(18 + 12 * u)
            a = int(255 * (1 - u))
            d.text((zx, zy), "z", font=_font(s), fill=(170, 210, 255, a), stroke_width=3, stroke_fill=(40, 60, 120, a))
    elif age < 0.5:                                        # "!" when it wakes / peeks
        a = int(255 * min(1.0, (0.5 - age) / 0.2))
        d.text((x + 36, y - 82 - 20 * min(1.0, age / 0.12)), "!", font=_font(46), fill=(255, 214, 74, a),
               stroke_width=5, stroke_fill=(90, 40, 60, a))


@lru_cache(None)
def _font(size):
    from PIL import ImageFont
    return ImageFont.truetype(str(Path(__file__).parent.parent / "pv/fonts/MPLUSRounded1c-ExtraBold.ttf"), size)
