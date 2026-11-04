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
from PIL import Image, ImageDraw, ImageFilter, ImageFont

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
# WARNING card; it then enters on 吹き出しちゃうな (about 104 s). Distance after the trailer (91.3 / 92.0 s): the boss
# centre at 85 % and its muzzle at 70 % of the space right of the player, so shots cross about half the screen; the
# stream cam shrinks into the top-right corner during the fight to make room (stream.cam_box).
BOSSES = {   # sprite-px anchors: muzzle (where every shot leaves), eyes (glow); x, y = screen position at rest
    "mini": dict(take="b3_mini_62011", name="ニヤニヤチャット", title="THE GRINNING CHAT", warn=103.45, enter=104.4,
                 last=115.5, h=560, x=1700, y=580, ground=False, col=(255, 110, 190), dark=(60, 14, 70),
                 aura=(255, 40, 150), eyes=((474, 233, 46), (287, 257, 46)), eye_col=(255, 60, 170),
                 muzzle=(5, 583)),
    "main": dict(take="b2_main_62003", name="ナナコロビ大王", title="NANAKOROBI THE DARUMA KING", warn=126.6,
                 enter=127.15, last=146.3, h=580, x=1625, y=None, ground=True, col=(255, 180, 60), dark=(80, 6, 16),
                 aura=(255, 70, 20), eyes=((307, 410, 60), (525, 370, 64)), eye_col=(255, 230, 60),
                 muzzle=(330, 545)),
}
FIRE_PRE, FIRE_POST = 0.12, 0.14          # anticipation before a shot, recoil after (s)
SMOKE = 0.45                               # muzzle smoke life (s) - lingers 6-10 frames in the reference


def _scale(key):
    b = BOSSES[key]
    return b["h"] / _raw(key).height


@lru_cache(None)
def _raw(key):
    return MD.cutout(Image.open(SRC / f"{BOSSES[key]['take']}.png"))


@lru_cache(None)
def sprite(key):
    """The boss sprite at its game size. The mini-boss (a cream cloud cat on white) is shaded to dusk mauve so it reads
    as a threat on the darkened stage; its eyes and megaphone keep their hot pink."""
    b = BOSSES[key]
    im = _raw(key)
    if key == "mini":
        a = np.asarray(im).astype(np.float32)
        rgb = a[..., :3]
        sat = rgb.max(-1) - rgb.min(-1)
        lum = rgb.mean(-1)
        body = (sat < 90) & (lum > 120)
        t = np.clip((lum - 120) / 135, 0, 1)[..., None]
        yy = np.linspace(0, 1, a.shape[0])[:, None, None]
        lo, hi = np.array((52, 24, 70), np.float32), np.array((176, 110, 168), np.float32)
        shade = lo + (hi - lo) * t * (1 - 0.35 * yy)                  # darker toward its swirl tail
        rgb[body] = shade[body]
        im = Image.fromarray(np.dstack([rgb, a[..., 3]]).clip(0, 255).astype(np.uint8), "RGBA")
    return im.resize((round(im.width * b["h"] / im.height), b["h"]), Image.Resampling.LANCZOS)


@lru_cache(None)
def glowing(key, level):
    """Sprite with glowing eyes (level 0..7 = beat pulse) and a pad for the aura."""
    b = BOSSES[key]
    sp = sprite(key)
    k = _scale(key)
    pad = 60
    cv = Image.new("RGBA", (sp.width + 2 * pad, sp.height + 2 * pad), (0, 0, 0, 0))
    # aura: blurred silhouette behind, pulsing
    al = np.asarray(sp.getchannel("A")).astype(np.float32)
    big = np.zeros((cv.height, cv.width), np.float32)
    big[pad:pad + sp.height, pad:pad + sp.width] = al
    big = np.asarray(Image.fromarray(big.astype(np.uint8)).filter(ImageFilter.GaussianBlur(26))).astype(np.float32)
    aura = np.zeros((cv.height, cv.width, 4), np.uint8)
    aura[..., :3] = b["aura"]
    aura[..., 3] = np.clip(big * (0.55 + 0.35 * level / 7), 0, 255).astype(np.uint8)
    cv.alpha_composite(Image.fromarray(aura, "RGBA"))
    cv.alpha_composite(sp, (pad, pad))
    # eyes: soft additive glow + hot core
    g = Image.new("RGBA", cv.size, (0, 0, 0, 0))
    dg = ImageDraw.Draw(g)
    for ex, ey, r in b["eyes"]:
        cx, cy, rr = pad + ex * k, pad + ey * k, r * k * (1.3 + 0.25 * level / 7)
        dg.ellipse((cx - rr, cy - rr * 0.8, cx + rr, cy + rr * 0.8), fill=(*b["eye_col"], 255))
    g = g.filter(ImageFilter.GaussianBlur(10 + 2 * level / 7))
    ga = np.asarray(g).astype(np.float32)
    base = np.asarray(cv).astype(np.float32)
    add = ga[..., :3] * (ga[..., 3:] / 255) * (0.55 + 0.35 * level / 7)
    base[..., :3] = np.minimum(255, base[..., :3] + add)
    base[..., 3] = np.maximum(base[..., 3], ga[..., 3] * 0.6)
    return Image.fromarray(base.astype(np.uint8), "RGBA"), pad


@lru_cache(None)
def flash(key):
    a = np.asarray(sprite(key)).copy()
    a[..., :3] = (a[..., :3] * 0.6 + 255 * 0.4).astype(np.uint8)        # light flinch (shooting its shots)
    return Image.fromarray(a, "RGBA")


def muzzle(key):
    """Screen position of the muzzle at rest."""
    b = BOSSES[key]
    sp = sprite(key)
    k = _scale(key)
    mx, my = b["muzzle"]
    left = b["x"] - sp.width / 2
    top = (900 - sp.height) if b["ground"] else (b["y"] - sp.height / 2)
    return left + mx * k, top + my * k


def lead(key):
    import mdgame as G
    return (muzzle(key)[0] - (G.HIT_X + 40)) / G.V_E               # flight time from the muzzle to her


def _chart():
    import stream as st
    return st.chart()


@lru_cache(None)
def timeline(key):
    """Her hits during the fight (HP), the throws (when each enemy leaves the boss) and the defeat time."""
    import mdgame as G
    b = BOSSES[key]
    L = lead(key)
    shots = [t for t, k in _chart() if k in ("g", "a", "a_miss") and b["enter"] + 0.35 <= t - L and t <= b["last"]]
    hits = [t for t in shots if t >= b["enter"]]
    return tuple(hits), tuple(t - L for t in shots), hits[-1]


@lru_cache(None)
def _shot_notes():
    out = {}
    for key in BOSSES:
        hits, throws, dead = timeline(key)
        L = lead(key)
        for t in throws:
            out[round(t + L, 4)] = key
    return out


def thrown(tt):
    """The boss that fires the note at chart time tt (it then flies out of that boss's muzzle), or None."""
    return _shot_notes().get(round(tt, 4))


@lru_cache(None)
def bubble(role):
    """Mini-boss shot: a mocking speech bubble (ｗｗ) - pink on the ground lane, cyan in the air."""
    W, H = 190, 150
    S2 = 3
    im = Image.new("RGBA", (W * S2, H * S2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fill = (255, 120, 190) if role == "ground" else (120, 220, 255)
    dark = (90, 20, 80) if role == "ground" else (20, 60, 120)
    def blob(o, col):
        d.rounded_rectangle((12 * S2 - o, 10 * S2 - o, 178 * S2 + o, 112 * S2 + o), 48 * S2, fill=col)
        d.polygon([(132 * S2, 104 * S2), (176 * S2 + o, 140 * S2 + o), (112 * S2, 108 * S2)], fill=col)
    blob(7 * S2, dark)
    blob(0, fill)
    d.rounded_rectangle((34 * S2, 22 * S2, 120 * S2, 38 * S2), 8 * S2, fill=(255, 255, 255, 120))
    f = ImageFont.truetype(str(Path(__file__).parent.parent / "pv/fonts/MPLUSRounded1c-ExtraBold.ttf"), 78 * S2)
    d.text((95 * S2, 64 * S2), "ｗｗ", font=f, fill=(255, 255, 255), anchor="mm", stroke_width=7 * S2,
           stroke_fill=dark)
    return im.resize((W, H), Image.Resampling.LANCZOS)


def projectile(key, tt, g, lane, x, sp_h):
    """(x, y_centre) of a fired shot, or None before it leaves the muzzle: it leaves the muzzle and settles into its
    lane over its first 0.2 s, flying straight on from there."""
    import mdgame as G
    mx, my = muzzle(key)
    t_fire = tt - lead(key)
    if g < t_fire:
        return None
    lane_y = G.AIR_Y if lane == "air" else G.FLOOR + 6 - sp_h / 2
    u = ease_out((g - t_fire) / 0.2)
    return x, my + (lane_y - my) * u


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
    if not b["ground"] and 0.0 <= a < 0.45:                    # the chat bursts in laughing
        u = a / 0.45
        return int(round(13 * (1 - u) * (1 if int(a * 30) % 2 == 0 else -1)))
    if b["ground"] and 0.32 <= a < 0.32 + 0.4:                 # the daruma lands
        u = (a - 0.32) / 0.4
        return int(round(18 * (1 - u) * (1 if int(a * 30) % 2 == 0 else -1)))
    for t0 in (dead, dead + 0.75 if b["ground"] else None):    # defeat (and the daruma's last thud)
        if t0 is not None and 0 <= g - t0 < 0.35:
            u = (g - t0) / 0.35
            return int(round(14 * (1 - u) * (1 if int((g - t0) * 30) % 2 == 0 else -1)))
    for tt in throws:                                           # kick on each shot
        if 0 <= g - tt < 3 / 30:
            return int(round(6 * (1 if int((g - tt) * 30) % 2 == 0 else -1)))
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
    dim = Image.new("RGBA", img.size, (*b["dark"], int(255 * 0.46 * fade)))    # the whole stage dims around it
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
    for tt in throws:                                           # winds up, then recoils as it fires
        d = g - tt
        if -FIRE_PRE <= d < 0:                                  # anticipation: draws back, swells
            k = math.sin(math.pi / 2 * (d + FIRE_PRE) / FIRE_PRE)
            x += 22 * k
            sx, sy = sx * (1 + 0.05 * k), sy * (1 + 0.05 * k)
            rot += (-5 if b["ground"] else 4) * k
        elif 0 <= d < FIRE_POST:                                # fire: snaps forward then kicks back
            k = 1 - d / FIRE_POST
            x += -30 * k * (1 if d < 0.04 else -0.6)
            sx, sy = sx * (1 + 0.08 * k), sy * (1 - 0.07 * k)
            rot += (7 if b["ground"] else -6) * k
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
        beat = 0.5 + 0.5 * math.cos(2 * math.pi * (g - b["enter"]) / BEAT)
        if fl:
            src, gp = flash(key), 0
        else:
            src, gp = glowing(key, int(round(beat * 7)))
        h0 = sprite(key).height
        sp = src.resize((max(1, int(src.width * sx)), max(1, int(src.height * sy))), Image.Resampling.BICUBIC)
        gpx, gpy = gp * sx, gp * sy
        if b["ground"]:                                         # pivot at its round base
            pad = sp.height
            cv = Image.new("RGBA", (sp.width + 2 * pad, sp.height + 2 * pad), (0, 0, 0, 0))
            cv.alpha_composite(sp, (pad, pad))
            piv = (pad + sp.width * 0.5, pad + gpy + h0 * sy * 0.97)
            cv = cv.rotate(rot, Image.Resampling.BICUBIC, center=piv)
            img.alpha_composite(cv, (int(x - piv[0]), int(y - piv[1])))
        else:
            rs = sp.rotate(rot, Image.Resampling.BICUBIC, expand=True)
            img.alpha_composite(rs, (int(x - rs.width / 2), int(y - rs.height / 2)))
        mx, my = muzzle(key)
        mx += x - b["x"]
        my += (y - (b["y"] if not b["ground"] else 900.0))
        for tt in throws:                                       # muzzle: charge glow, flash, lingering smoke
            d = g - tt
            if -FIRE_PRE <= d < 0:
                r = 18 + 40 * (d + FIRE_PRE) / FIRE_PRE
                lay = Image.new("RGBA", (int(4 * r), int(4 * r)), (0, 0, 0, 0))
                ImageDraw.Draw(lay).ellipse((r, r, 3 * r, 3 * r), fill=(*b["eye_col"], 200))
                lay = lay.filter(ImageFilter.GaussianBlur(r / 3))
                img.alpha_composite(lay, (int(mx - 2 * r), int(my - 2 * r)))
            elif 0 <= d < SMOKE:
                if d < 2 / 30:
                    FX.ring_flash(img, mx, my, d * 2)
                    star = Image.new("RGBA", (220, 220), (0, 0, 0, 0))
                    ds = ImageDraw.Draw(star)
                    ds.polygon([(110, 0), (124, 96), (220, 110), (124, 124), (110, 220), (96, 124), (0, 110),
                                (96, 96)], fill=(255, 255, 255, 240))
                    img.alpha_composite(star, (int(mx - 110), int(my - 110)))
                FX.puffs(img, mx + 10, my, d * 0.34 / SMOKE, int(tt * 100), 6, 120)
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


# ---------------------------------------------------------------- omen: the Daruma King looms over the climb
# Owner 2026-11-04: the climb (piano staircase, 震えるつま先で ステップ踏んで, 116.6-125.8 s) leads into the main boss and
# should threaten her. As boss foreshadowing in the reference games (the boss watching from the background before
# the fight): the king's dark silhouette with glowing eyes rises behind the staircase, grows closer every bar, and
# throws every saw of the step section down onto her path (they drop from its raised paw and land with a thud - none
# appears from nowhere); its eyes blink on the beat; at the top of the climb (into Fever) its eyes flare and the
# screen shakes, then the cut-in, the WARNING and its drop from above.
OMEN = (116.55, 125.0)          # climb stage .. festival cut-in
OMEN_FLARE = 123.9              # eyes flare, roar shake
SAW_FALL = 0.32                 # a thrown saw falls this long before landing
SAW_LAND_X = 1230               # where thrown saws land (game px)


@lru_cache(None)
def silhouette(level):
    """The king as a near-black maroon silhouette with a thin red rim and glowing eyes (level 0..7 = pulse)."""
    b = BOSSES["main"]
    raw = _raw("main")
    a = np.asarray(raw).astype(np.float32)
    rgb = a[..., :3] * 0.10 + np.array((46, 6, 18), np.float32) * 0.90
    al = a[..., 3]
    edge = (al > 0) & ~np.asarray(Image.fromarray((al > 128).astype(np.uint8) * 255).filter(
        ImageFilter.MinFilter(9))).astype(bool)
    rgb[edge] = (225, 40, 60)                                    # red rim light
    sil = Image.fromarray(np.dstack([rgb, al]).clip(0, 255).astype(np.uint8), "RGBA")
    pad = 80
    cv = Image.new("RGBA", (sil.width + 2 * pad, sil.height + 2 * pad), (0, 0, 0, 0))
    halo = np.zeros((cv.height, cv.width), np.uint8)                # red aura so it reads on the dark climb
    halo[pad:pad + sil.height, pad:pad + sil.width] = al.astype(np.uint8)
    halo = np.asarray(Image.fromarray(halo).filter(ImageFilter.GaussianBlur(30))).astype(np.float32)
    ha = np.zeros((cv.height, cv.width, 4), np.uint8)
    ha[..., :3] = (255, 40, 60)
    ha[..., 3] = np.clip(halo * (0.55 + 0.3 * level / 7), 0, 255).astype(np.uint8)
    cv.alpha_composite(Image.fromarray(ha, "RGBA"))
    cv.alpha_composite(sil, (pad, pad))
    g = Image.new("RGBA", cv.size, (0, 0, 0, 0))
    dg = ImageDraw.Draw(g)
    for ex, ey, r in b["eyes"]:
        rr = r * (1.25 + 0.35 * level / 7)
        dg.ellipse((pad + ex - rr, pad + ey - rr * 0.75, pad + ex + rr, pad + ey + rr * 0.75), fill=(255, 220, 60, 255))
    g = g.filter(ImageFilter.GaussianBlur(14 + 4 * level / 7))
    ga = np.asarray(g).astype(np.float32)
    base = np.asarray(cv).astype(np.float32)
    base[..., :3] = np.minimum(255, base[..., :3] + ga[..., :3] * (ga[..., 3:] / 255) * (0.8 + 0.6 * level / 7))
    base[..., 3] = np.maximum(base[..., 3], ga[..., 3] * 0.7)
    core = Image.new("RGBA", cv.size, (0, 0, 0, 0))                # hot pupils
    dc = ImageDraw.Draw(core)
    for ex, ey, r in b["eyes"]:
        dc.ellipse((pad + ex - r * 0.35, pad + ey - r * 0.3, pad + ex + r * 0.35, pad + ey + r * 0.3),
                   fill=(255, 250, 210, 255))
    out = Image.fromarray(base.astype(np.uint8), "RGBA")
    out.alpha_composite(core)
    return out, pad


def omen_on(g):
    return OMEN[0] <= g < OMEN[1]


def _omen_geom(g):
    """(centre x, top y, height px, alpha) of the looming silhouette: eyes held at about y 300, left of the cam."""
    u = (g - OMEN[0]) / (OMEN[1] - OMEN[0])
    h = 620 + 440 * u ** 1.3                                     # closer every bar
    cx = 1180 - 40 * u
    top = 300 - 0.38 * h + 14 * math.sin(2 * math.pi * (g - OMEN[0]) / (4 * BEAT))   # slow sway
    a = min(1.0, (g - OMEN[0]) / 2.2) * (1 - min(1.0, max(0.0, (g - (OMEN[1] - 0.25)) / 0.25)))
    return cx, top, h, a * 0.95


def _omen_mouth(g):
    cx, top, h, a = _omen_geom(g)
    return cx - 0.5 * h + 0.44 * h, top + 0.53 * h


def omen_throws():
    """Saws of the step section: (chart time, throw time, landing time)."""
    import mdgame as G
    import stream as st
    v = st.V_G * G.K
    out = []
    for tt, k in st.chart():
        if k == "gear" and OMEN[0] + 1.6 <= tt < OMEN[1]:
            land = tt - (SAW_LAND_X - (G.HIT_X - 60)) / v
            out.append((tt, land - SAW_FALL, land))
    return out


def saw_drop(tt, g, x):
    """For a saw thrown by the king: None = not yet thrown (do not draw); else (x, y_offset): it arcs out of the
    king's mouth onto her path (y_offset < 0 above its resting height on the floor)."""
    import mdgame as G
    for t0, thr, land in omen_throws():
        if abs(t0 - tt) < 1e-6:
            if g < thr:
                return None
            if g < land:
                u = (g - thr) / SAW_FALL
                mx, my = _omen_mouth(thr)
                rest_y = G.FLOOR - 70
                xx = mx + (x - mx) * u
                yy = my + (rest_y - my) * u * u - 140 * math.sin(math.pi * u) * (1 - u)
                return xx, yy - rest_y
            return x, 0
    return x, 0


def draw_omen(img, g):
    """Behind the play objects, over the stage: the looming king (eyes pulse on the beat, lean on each throw)."""
    if not omen_on(g):
        return
    cx, top, h, a = _omen_geom(g)
    beat = 0.5 + 0.5 * math.cos(2 * math.pi * (g - OMEN[0]) / BEAT)
    flare = max(0.0, 1 - abs(g - OMEN_FLARE - 0.3) / 0.6) if g > OMEN_FLARE - 0.3 else 0.0
    level = min(7, int(round(beat * 5 + flare * 7)))
    sil, pad = silhouette(level)
    k = h / _raw("main").height
    sp = sil.resize((round(sil.width * k), round(sil.height * k)), Image.Resampling.BICUBIC)
    rot = 0.0
    for t0, thr, land in omen_throws():                           # rocks toward her as it hurls each saw
        d = g - thr
        if -0.1 <= d < 0.25:
            rot += 6 * math.sin(math.pi * (d + 0.1) / 0.35)
    if rot:
        sp = sp.rotate(rot, Image.Resampling.BICUBIC, center=(sp.width / 2, sp.height * 0.95))
    if a < 1:
        al = np.asarray(sp.getchannel("A")).astype(np.float32) * a
        sp.putalpha(Image.fromarray(al.astype(np.uint8)))
    img.alpha_composite(sp, (int(cx - sp.width / 2), int(top - pad * k)))
    if flare > 0:                                                 # the roar: red flash over the stage
        img.alpha_composite(Image.new("RGBA", img.size, (200, 20, 40, int(70 * flare))))


def omen_shake(g):
    if not omen_on(g):
        return 0
    if OMEN_FLARE <= g < OMEN_FLARE + 0.6:                        # roar
        d = g - OMEN_FLARE
        return int(round(16 * (1 - d / 0.6) * (1 if int(d * 30) % 2 == 0 else -1)))
    for t0, thr, land in omen_throws():                           # thud as each saw lands
        d = g - land
        if 0 <= d < 4 / 30:
            return int(round(7 * (1 - d * 30 / 4) * (1 if int(d * 30) % 2 == 0 else -1)))
    return 0
