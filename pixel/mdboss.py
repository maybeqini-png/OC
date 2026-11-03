"""Mini-boss and main boss for the PV's game (owner 2026-11-03: "don't forget the main boss and mini-boss; they should
match the oppressive vibe of the lyrics, though this track doesn't have a heavy, intense feel overall").

The pressure in the lyrics is being laughed at after the stumble (笑ったでしょ / 吹き出しちゃう / わらうな) and the tearful
climb, so the bosses are cute but mocking, and the oppression comes from the presentation, as in the reference games
(Muse Dash bosses hold the right edge and throw the enemies into the lanes; roguelike bosses get a WARNING card, a
name plate and an HP bar, the stage darkens around them and the screen shakes on their big moves):
- mini-boss ニヤニヤチャット "THE GRINNING CHAT" (twilight verse, ぷいって ... いいこちゃんなんて): the mocking chat as a
  smug cloud-cat with a megaphone (art/generated/md_style/b3_mini_62011). Floats over the air lane, sways, leans in
  and "shouts" every enemy out of its megaphone; flinches white at each of her hits; at the last hit it deflates in a
  spin and bursts into speech-bubble confetti.
- main boss ナナコロビ大王 "NANAKOROBI THE DARUMA KING" (final chorus, Fever): a red daruma lucky-cat king
  (b2_main_62003). Drops in from above with a heavy landing (big shake, dust), rocks on its round base to the beat,
  rocks forward to fling each enemy, flinches at her hits; at the last hit it topples over - and, being a daruma,
  bounces upright once (七転び八起き, the song's 転んだあとが見せ場じゃん) before bursting into festival fireworks.
- while a boss is up: a slow magenta-violet vignette that breathes on the beat, a big boss shadow, a WARNING band
  before it enters, and its name plate + HP bar at the bottom right (HP drops with each of her hits).
"""
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import mdfx as FX
import mdsprites as MD

SRC = Path(__file__).parent.parent / "art/generated/md_style"
BEAT = 60 / 136


def ease_out(u):
    u = min(1.0, max(0.0, u))
    return 1 - (1 - u) ** 3


def ease_in(u):
    u = min(1.0, max(0.0, u))
    return u * u


# mini-boss timing: after the streamer's big-cam reaction (stream.BIG_CAM 98.9-103.2 s), which would cover the
# WARNING card; it then enters on 吹き出しちゃうな (about 104 s). Both bosses stay left of / below the stream's cam
# box (top right, x 1478-1896, y 68-480 on the game picture) so their heads are never hidden behind it.
BOSSES = {
    "mini": dict(take="b3_mini_62011", name="ニヤニヤチャット", title="THE GRINNING CHAT", warn=103.45, enter=104.4,
                 last=115.5, h=400, x=1380, y=610, ground=False, col=(255, 110, 190), dark=(70, 20, 70)),
    "main": dict(take="b2_main_62003", name="ナナコロビ大王", title="NANAKOROBI THE DARUMA KING", warn=126.6,
                 enter=127.15, last=146.3, h=540, x=1500, y=None, ground=True, col=(255, 180, 60), dark=(90, 10, 20)),
}


@lru_cache(None)
def sprite(key):
    b = BOSSES[key]
    im = MD.cutout(Image.open(SRC / f"{b['take']}.png"))
    return im.resize((round(im.width * b["h"] / im.height), b["h"]), Image.Resampling.LANCZOS)


@lru_cache(None)
def flash(key):
    a = np.asarray(sprite(key)).copy()
    a[..., :3] = (a[..., :3] * 0.25 + 255 * 0.75).astype(np.uint8)
    return Image.fromarray(a, "RGBA")


def _chart():
    import stream as st
    return st.chart()


@lru_cache(None)
def timeline(key):
    """Her hits during the fight (HP), the throws (when each enemy leaves the boss) and the defeat time."""
    import mdgame as G
    b = BOSSES[key]
    hits = [t for t, k in _chart() if k in ("g", "a") and b["enter"] + 0.3 <= t <= b["last"]]
    lead = (b["x"] - G.HIT_X - 40) / G.V_E                       # enemy flight time from the boss to her
    throws = [t - lead for t, k in _chart() if k in ("g", "a", "a_miss") and b["enter"] <= t - lead < hits[-1]]
    return tuple(hits), tuple(throws), hits[-1]


def active(g):
    for key, b in BOSSES.items():
        hits, throws, dead = timeline(key)
        if b["warn"] <= g < dead + 1.6:
            return key
    return None


def shake(g):
    """Extra vertical shake (px) for the boss's big moments."""
    k = active(g)
    if not k:
        return 0
    b = BOSSES[k]
    hits, throws, dead = timeline(k)
    a = g - b["enter"]
    if b["ground"] and 0.32 <= a < 0.32 + 0.4:                 # the daruma lands
        u = (a - 0.32) / 0.4
        return int(round(18 * (1 - u) * (1 if int(a * 30) % 2 == 0 else -1)))
    for t0 in (dead, dead + 0.75 if b["ground"] else None):    # defeat (and the daruma's last thud)
        if t0 is not None and 0 <= g - t0 < 0.35:
            u = (g - t0) / 0.35
            return int(round(14 * (1 - u) * (1 if int((g - t0) * 30) % 2 == 0 else -1)))
    for tt in throws:                                           # small kick on each throw
        if 0 <= g - tt < 3 / 30:
            return int(round(4 * (1 if int((g - tt) * 30) % 2 == 0 else -1)))
    return 0


@lru_cache(None)
def vignette(col, W=1920, H=1080):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W * 0.45) / (W * 0.62)) ** 2 + ((yy - H * 0.48) / (H * 0.62)) ** 2)
    a = np.clip((d - 0.55) / 0.6, 0, 1) ** 1.4
    out = np.zeros((H, W, 4), np.uint8)
    out[..., :3] = col
    out[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def draw_atmosphere(img, g):
    """Under the world: the oppressive vignette breathing on the beat while a boss is up."""
    k = active(g)
    if not k:
        return
    b = BOSSES[k]
    hits, throws, dead = timeline(k)
    fade = min(1.0, (g - b["warn"]) / 0.8) * (1 - min(1.0, max(0.0, (g - dead - 0.6) / 1.0)))
    beat = 0.5 + 0.5 * math.cos(2 * math.pi * (g - b["enter"]) / BEAT)
    dim = Image.new("RGBA", img.size, (*b["dark"], int(255 * 0.30 * fade)))    # the whole stage dims around it
    img.alpha_composite(dim)
    v = vignette(b["dark"])
    a = np.asarray(v.getchannel("A")).astype(np.float32) * fade * (0.62 + 0.18 * beat)
    lay = v.copy()
    lay.putalpha(Image.fromarray(a.astype(np.uint8)))
    img.alpha_composite(lay)


def _state(key, g):
    """(x, y_bottom_or_centre, scale_x, scale_y, rot, flash, alpha) of the boss at game time g, or None."""
    b = BOSSES[key]
    hits, throws, dead = timeline(key)
    a = g - b["enter"]
    if a < 0 or g > dead + 1.6:
        return None
    x, y = float(b["x"]), (b["y"] if not b["ground"] else 900.0)
    sx = sy = 1.0
    rot = 0.0
    alpha = 1.0
    if b["ground"]:
        if a < 0.32:                                            # drops from above
            y = -60 + (900 + 60) * ease_in(a / 0.32)
            sy, sx = 1.12, 0.92
        elif a < 0.6:                                           # landing squash
            q = 0.22 * (1 - (a - 0.32) / 0.28) ** 2
            sx, sy = 1 + q, 1 - q
        else:                                                   # rocks on its round base to the beat
            rot = 5 * math.sin(2 * math.pi * (g - b["enter"]) / (2 * BEAT))
    else:
        if a < 0.6:                                             # slides in from the right, overshooting
            u = a / 0.6
            x = b["x"] + 520 * (1 - ease_out(u)) - 30 * math.sin(math.pi * u)
        y = b["y"] + 22 * math.sin(2 * math.pi * (g - b["enter"]) / (2 * BEAT))
        rot = 4 * math.sin(2 * math.pi * (g - b["enter"]) / (4 * BEAT))
    for tt in throws:                                           # leans in and flings / shouts each enemy out
        d = g - tt
        if -0.08 <= d < 0.16:
            k = math.sin(math.pi * (d + 0.08) / 0.24)
            x -= 34 * k
            sx, sy = sx * (1 + 0.07 * k), sy * (1 - 0.06 * k)
            rot += (6 if b["ground"] else -5) * k
    fl = any(0 <= g - tt < 2 / 30 for tt in hits)                # flinches white on her hits
    for tt in hits:
        if 0 <= g - tt < 0.12:
            x += 14 * (1 - (g - tt) / 0.12)
    if g >= dead:                                               # defeat
        d = g - dead
        fl = d < 3 / 30
        if b["ground"]:                                         # topples back, bounces upright once, bursts
            if d < 0.35:
                rot = -80 * ease_out(d / 0.35)
            elif d < 0.75:
                rot = -80 + 80 * ease_out((d - 0.35) / 0.4) + 12 * math.sin((d - 0.35) / 0.4 * math.pi)
            else:
                rot = 0
            alpha = 1.0 if d < 0.95 else 0.0
        else:                                                   # deflates in a spin
            u = min(1.0, d / 0.55)
            rot = 540 * ease_in(u)
            sx = sy = 1 - 0.85 * ease_in(u)
            x += 160 * u
            alpha = 1.0 if d < 0.55 else 0.0
    return x, y, sx, sy, rot, fl, alpha


def draw_boss(img, g):
    """Over the enemies (they come out of it), under XIYIN and the hit effects."""
    key = active(g)
    if not key:
        return
    b = BOSSES[key]
    st_ = _state(key, g)
    if st_ is None:
        return
    x, y, sx, sy, rot, fl, alpha = st_
    hits, throws, dead = timeline(key)
    # big soft shadow on the floor
    sh = Image.new("RGBA", (520, 70), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((0, 0, 519, 69), fill=(20, 10, 40, 110 if b["ground"] else 70))
    sw = 1.0 if b["ground"] else 0.6
    sh = sh.resize((int(520 * sw), int(70 * sw)))
    if alpha > 0:
        img.alpha_composite(sh, (int(x - sh.width / 2), 900 - sh.height // 2 + 4))
        sp = flash(key) if fl else sprite(key)
        sp = sp.resize((max(1, int(sp.width * sx)), max(1, int(sp.height * sy))), Image.Resampling.BICUBIC)
        if b["ground"]:                                         # pivot at its round base
            pad = sp.height
            cv = Image.new("RGBA", (sp.width + 2 * pad, sp.height + 2 * pad), (0, 0, 0, 0))
            cv.alpha_composite(sp, (pad, pad))
            piv = (pad + sp.width * 0.5, pad + sp.height * 0.97)
            cv = cv.rotate(rot, Image.Resampling.BICUBIC, center=piv)
            img.alpha_composite(cv, (int(x - piv[0]), int(y - piv[1])))
        else:
            rs = sp.rotate(rot, Image.Resampling.BICUBIC, expand=True)
            img.alpha_composite(rs, (int(x - rs.width / 2), int(y - rs.height / 2)))
    if g >= dead:                                               # burst: confetti / fireworks
        t0 = dead + (0.95 if b["ground"] else 0.5)
        cy = (y - b["h"] * 0.5) if b["ground"] else y
        for k in range(3):
            if g - t0 - k * 0.08 < 0:
                continue
            FX.impact(img, x + (k - 1) * 120, cy + (k % 2) * 80 - 40, g - t0 - k * 0.08, 900 + k,
                      "gold" if b["ground"] else "pink", 1.6)
            FX.confetti(img, x + (k - 1) * 120, cy, g - t0 - k * 0.08, 910 + k, "gold" if b["ground"] else "pink", 40)
        if b["ground"] and 0.75 <= g - dead < 1.15:
            FX.ring_flash(img, x, 900, g - dead - 0.75)
            FX.puffs(img, x - 120, 880, g - dead - 0.75, 77, 5, 110)
    if b["ground"] and 0.32 <= g - b["enter"] < 0.8:            # landing dust
        a_ = g - b["enter"] - 0.32
        FX.ring_flash(img, x, 900, a_, (255, 220, 160))
        FX.puffs(img, x - 160, 880, a_, 55, 5, 120)
        FX.puffs(img, x + 160, 880, a_, 56, 5, 120)


def _font(size):
    return FX._font(size)


@lru_cache(None)
def warn_band(W=1920):
    """WARNING band: black / magenta hazard stripes with a white WARNING!! word."""
    H = 150
    lay = Image.new("RGBA", (W + 400, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rectangle((0, 0, W + 400, H), fill=(30, 10, 40, 235))
    for i in range(-2, (W + 400) // 60 + 2):
        x = i * 60
        d.polygon([(x, 0), (x + 30, 0), (x + 30 - 24, 18), (x - 24, 18)], fill=(255, 60, 150, 255))
        d.polygon([(x, H - 18), (x + 30, H - 18), (x + 30 - 24, H), (x - 24, H)], fill=(255, 60, 150, 255))
    return lay


def draw_ui(img, g):
    """WARNING card before a boss and the boss name plate + HP bar (bottom right)."""
    key = active(g)
    if not key:
        return
    b = BOSSES[key]
    hits, throws, dead = timeline(key)
    W = img.width
    if b["warn"] <= g < b["enter"] + 0.35:                     # WARNING!! band slides through the middle
        u = (g - b["warn"]) / (b["enter"] + 0.35 - b["warn"])
        band = warn_band(W)
        off = int(-200 * u)
        a = 1.0 if 0.12 < u < 0.85 else (u / 0.12 if u <= 0.12 else (1 - u) / 0.15)
        lay = band.crop((200 + off, 0, 200 + off + W, band.height))
        if a < 1:
            al = np.asarray(lay.getchannel("A")).astype(np.float32) * max(0.0, a)
            lay.putalpha(Image.fromarray(al.astype(np.uint8)))
        img.alpha_composite(lay, (0, 330))
        if int(g * 8) % 2 == 0 or u > 0.2:
            word = FX.banded_text("WARNING!!", 96, "pink")
            FX.put(img, word, W // 2 + int(30 * (0.5 - u)), 405, max(0.0, min(1.0, a)))
            sub = FX.banded_text(b["title"], 34, "pink")
            FX.put(img, sub, W // 2, 465, max(0.0, min(1.0, a)))
    if g >= b["enter"] and g < dead + 0.9:                      # name plate + HP bar
        appear = ease_out((g - b["enter"]) / 0.4)
        x0, y0, wbar = 1380, 948, 480
        n_done = sum(1 for t in hits if t <= g)
        hp = 1 - n_done / max(1, len(hits))
        d = ImageDraw.Draw(img)
        xs = x0 + int(80 * (1 - appear))
        d.polygon([(xs, y0), (xs + wbar, y0), (xs + wbar - 14, y0 + 22), (xs - 14, y0 + 22)], fill=(30, 15, 45, 230))
        fillw = int((wbar - 10) * hp)
        if fillw > 0:
            d.polygon([(xs + 5, y0 + 4), (xs + 5 + fillw, y0 + 4), (xs + fillw - 7, y0 + 18), (xs - 7, y0 + 18)],
                      fill=b["col"])
        d.text((xs + 6, y0 - 44), b["name"], font=_font(34), fill=(255, 255, 255), stroke_width=5,
               stroke_fill=(40, 20, 60))
        d.text((xs + 8 + _font(34).getlength(b["name"]) + 14, y0 - 30), b["title"], font=_font(18),
               fill=(255, 220, 240), stroke_width=4, stroke_fill=(40, 20, 60))
    if dead + (0.95 if b["ground"] else 0.5) <= g < dead + 1.6:    # BREAK!! over the burst
        FX.judgement(img, 1450, 470, g - dead - (0.95 if b["ground"] else 0.5), "gold" if b["ground"] else "pink",
                     "BREAK!!", 96)
