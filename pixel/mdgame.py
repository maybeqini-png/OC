"""HD game layer of the stream PV (1920x1080), in a Muse Dash-like look (see docs/rhythm_game_style_reference.md).

Replaces the pixel game layer (960x540 at x2). Timing, chart, scoring and avatar physics stay in stream.py (pixel
units there, x2 here); this module only draws:
- stage plates under a pastel haze (soft blur + lift toward a stage tint) so the flat sprites read on top;
- a flat two-tone floor band per stage with slanted stripes scrolling with the ground;
- dashed judgement rings on both lanes in front of XIYIN;
- one monster family per stage (pixel/md/*.png, N5 V5 cut-outs): ground enemy, air enemy, spinning saw (the outer
  ring turns, the face in the hub stays upright); bob and tilt while coming, knocked away with a star burst;
- pickups (eighth note, heart), the hold ribbon (a music-staff band with a star), PERFECT pop-ups, combo on a paint
  splat, HP / FEVER bars and score at the top centre (the bottom band holds the lyric key-caps and subtitles);
- XIYIN's HD runner (pixel/mdrunner.py) with a soft contact shadow, strike frames, hurt blink, fever trail.
Everything is drawn anti-aliased (shapes 2x supersampled); nothing is drawn on white, so no white fringes.
"""
import math
import random
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import mdboss as BOSS
import mdbrat as BR
import mdpet as PET
import mdfx as FX
import mdrunner as RN
import mdsprites as MD
import scene as S

HERE = Path(__file__).parent
ROOT = HERE.parent
OW, OH = 1920, 1080
BEAT = 60 / 136
K = 2                                  # pixel-layer units -> HD
FLOOR = 900                            # feet line (pixel GROUND 450 x2)
RUN_X = 600
HIT_X = 724
AIR_Y = 560
GROUND_LANE = FLOOR - 82
V_E = 1040.0

FAMILY = {"sky": "k", "sunset": "u", "pop": "p", "night": "n", "pinkpop": "p", "twilight": "u", "climb": "n",
          "festival": "f"}
HUB = {"k": 0.52, "u": 0.80, "p": 0.60, "n": 0.36, "f": 0.30}       # saw hub radius (fraction): stays upright
HAZE = {"sky": ((228, 238, 255), 0.30), "sunset": ((255, 228, 220), 0.28), "pop": ((255, 240, 250), 0.30),
        "night": ((120, 100, 180), 0.22), "pinkpop": ((255, 232, 246), 0.30), "twilight": ((210, 190, 235), 0.26),
        "climb": ((228, 238, 255), 0.30), "festival": ((110, 80, 130), 0.18), "curtain_closed": ((0, 0, 0), 0.0),
        "curtain_open": ((0, 0, 0), 0.0)}
FLOOR_COL = {   # style: (band, top edge, stripe)
    "roof": ((150, 170, 235), (236, 241, 255), (132, 152, 222)),
    "street": ((226, 160, 172), (255, 232, 222), (208, 140, 156)),
    "checker": ((118, 168, 252), (246, 250, 255), (98, 148, 238)),
    "night": ((62, 46, 112), (152, 122, 222), (80, 62, 140)),
    "pink": ((255, 172, 214), (255, 236, 246), (240, 146, 196)),
    "stone": ((150, 130, 192), (226, 212, 246), (130, 110, 172)),
    "wood": ((190, 122, 92), (252, 216, 172), (166, 102, 76)),
    "blood": ((40, 6, 16), (150, 20, 36), (64, 10, 24)),
}
PINK, PINK_D, LEMON, CYAN, WHITE = (255, 96, 170), (214, 52, 128), (255, 226, 70), (80, 220, 255), (255, 255, 255)
NOTE_BLUE, HEART_PINK = (72, 140, 255), (255, 92, 142)


def ST():
    import stream
    return stream


@lru_cache(None)
def font(size):
    return ImageFont.truetype(str(ROOT / "pv" / "fonts" / "MPLUSRounded1c-ExtraBold.ttf"), size)


# ---------------------------------------------------------------- stage plates
@lru_cache(None)
def hazed(name):
    tint, k = HAZE.get(name, ((255, 255, 255), 0.0))
    p = S.plate(name).convert("RGB")
    if k <= 0:
        return p.convert("RGBA")
    p = p.filter(ImageFilter.GaussianBlur(1.6))
    return Image.blend(p, Image.new("RGB", p.size, tint), k).convert("RGBA")


def plate_view(name, u, v=0.0):
    p = hazed(name)
    x = int(round((p.width - OW) * min(1, max(0, u))))
    y = int(round((p.height - OH) * (1 - min(1, max(0, v)))))
    return p.crop((x, y, x + OW, y + OH))


# ---------------------------------------------------------------- floor
def draw_floor(img, style_at, cam):
    """Flat two-tone band from FLOOR down with slanted stripes; style per column (wipes switch it column-wise)."""
    a = np.asarray(img).copy()
    xs = np.arange(OW)
    styles = [style_at(x // K) for x in range(0, OW, 8)]
    off = cam * K
    yy = np.arange(FLOOR, OH)[:, None]
    for st in set(styles):
        if not st or st not in FLOOR_COL:
            continue
        band, top, stripe = FLOOR_COL[st]
        cols = np.repeat(np.array([s == st for s in styles]), 8)[:OW]
        reg = a[FLOOR:, :][:, cols]
        xx = xs[cols][None, :]
        u = ((xx + off + (yy - FLOOR) * 0.6) % 120) / 120.0          # slanted stripes, scroll with the ground
        st_m = (u < 0.42) & (yy > FLOOR + 14)
        col = np.where(st_m[..., None], np.array(stripe), np.array(band))
        col = np.where((yy < FLOOR + 10)[..., None], np.array(top), col)
        col = np.where(((yy >= FLOOR + 10) & (yy < FLOOR + 14))[..., None], np.array(stripe), col)
        reg[..., :3] = col
        reg[..., 3] = 255
        a[FLOOR:, :][:, cols] = reg
    img.paste(Image.fromarray(a, "RGBA"))


# ---------------------------------------------------------------- shapes (2x supersampled)
def _ss(w, h, draw, k=3):
    big = Image.new("RGBA", (w * k, h * k), (0, 0, 0, 0))
    draw(ImageDraw.Draw(big), k)
    return big.resize((w, h), Image.Resampling.LANCZOS)


@lru_cache(None)
def ring(step):
    """Dashed judgement ring, slowly turning."""
    r = 48

    def dr(d, k):
        c = (r + 6) * k
        for i in range(12):
            a0 = i * 30 + step * 2.5
            d.arc([c - r * k, c - r * k, c + r * k, c + r * k], a0, a0 + 17, fill=(255, 255, 255, 235), width=6 * k)
    return _ss(2 * r + 12, 2 * r + 12, dr)


@lru_cache(None)
def note_icon():
    def dr(d, k):
        o = 7 * k
        for col, grow in ((WHITE, o), (NOTE_BLUE, 0)):
            d.ellipse([(14 * k - grow), (52 * k - grow), (44 * k + grow), (74 * k + grow)], fill=col)
            d.rectangle([(38 * k - grow), (10 * k - grow), (44 * k + grow), (64 * k)], fill=col)
            d.polygon([(41 * k, 10 * k - grow), (66 * k + grow, 26 * k), (62 * k + grow, 40 * k + grow),
                       (41 * k, 28 * k)], fill=col)
        d.ellipse([20 * k, 56 * k, 30 * k, 62 * k], fill=(190, 220, 255))
    return _ss(84, 88, dr).rotate(-8, Image.Resampling.BICUBIC, expand=False)


@lru_cache(None)
def heart_icon(size=70):
    def dr(d, k):
        s = size * k
        for col, g in ((WHITE, 6 * k), (HEART_PINK, 0)):
            r = s * 0.27
            d.ellipse([s * 0.5 - 2 * r - g * 0.3 + s * 0.02, s * 0.12 - g, s * 0.5 + g * 0.3 + s * 0.02, s * 0.12 + 2 * r + g],
                      fill=col)
            d.ellipse([s * 0.5 - g * 0.3 - s * 0.02, s * 0.12 - g, s * 0.5 + 2 * r + g * 0.3 - s * 0.02, s * 0.12 + 2 * r + g],
                      fill=col)
            d.polygon([(s * 0.5 - 2 * r - g * 0.6 + s * 0.03, s * 0.36), (s * 0.5 + 2 * r + g * 0.6 - s * 0.03, s * 0.36),
                       (s * 0.5, s * 0.92 + g)], fill=col)
        d.ellipse([s * 0.22, s * 0.24, s * 0.34, s * 0.34], fill=(255, 200, 220))
    return _ss(size, size, dr)


@lru_cache(None)
def star_icon(size=56, col=LEMON):
    def dr(d, k):
        c = size * k / 2
        for fill, R in ((WHITE, c * 0.98), (col, c * 0.78)):
            pts = []
            for i in range(10):
                rr = R if i % 2 == 0 else R * 0.48
                a = -math.pi / 2 + i * math.pi / 5
                pts.append((c + rr * math.cos(a), c + rr * math.sin(a)))
            d.polygon(pts, fill=fill)
    return _ss(size, size, dr)


@lru_cache(None)
def text_img(s, size, fill, outline, ow):
    f = font(size)
    bb = f.getbbox(s)
    w, h = bb[2] - bb[0] + 2 * ow + 8, bb[3] - bb[1] + 2 * ow + 8
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((ow + 4 - bb[0], ow + 4 - bb[1]), s, font=f, fill=fill, stroke_width=ow, stroke_fill=outline)
    return im


def put(img, sp, cx, cy, alpha=1.0, scale=1.0):
    if scale != 1.0:
        sp = sp.resize((max(1, round(sp.width * scale)), max(1, round(sp.height * scale))), Image.Resampling.LANCZOS)
    if alpha < 1.0:
        a = np.asarray(sp).copy()
        a[..., 3] = (a[..., 3] * max(0.0, alpha)).astype(np.uint8)
        sp = Image.fromarray(a, "RGBA")
    img.alpha_composite(sp, (int(round(cx - sp.width / 2)), int(round(cy - sp.height / 2))))


# ---------------------------------------------------------------- monsters
def family_at(g):
    st = ST()
    return FAMILY.get(st.STAGES[st.stage_at(g)][1], "k")


@lru_cache(None)
def monster(fam, role):
    if fam == "chat":                         # the mini-boss's shots (pixel/mdboss.py)
        return BOSS.bubble("air" if role in ("air", "a2") else "ground")
    if f"{fam}_{role}" not in MD.PICKS:       # a family without that variant: its base enemy
        role = "air" if role in ("a2",) else "ground" if role in ("g2", "big", "gh_g") else \
            ("air" if role == "gh" else role)
    return MD.sprite(f"{fam}_{role}")


def role_for(tt, kind, lane, fam):
    """Which enemy design of the stage's family: big (heavy hit), ghost, or - alternating every bar, so a stage never
    shows one repeated design - the base enemy or its second design."""
    st = ST()
    if lane == "ground" and st.is_big(tt):
        return "big"
    if st.is_ghost(tt, kind):
        return "gh"
    alt = int(tt / (4 * BEAT)) % 2
    if lane == "air":
        return "a2" if alt else "air"
    return "g2" if alt else "ground"


def draw_mash(img, g, late, texts):
    """Mash enemy (Muse Dash's big rapid-hit enemy): a big family enemy runs in, plants itself in front of her and
    shudders while she hits it on every sixteenth, a HITS counter growing over it; on its last hit it is launched."""
    st = ST()
    for t0, t1 in st.MASH.items():
        if not (t0 - 1.9 <= g < t1 + 0.6):
            continue
        fam = family_at(t0)
        sp = monster(fam, "big")
        hx = HIT_X + 110
        if g < t0:                                         # running in
            x = hx + (t0 - g) * V_E
            put(img, sp, x, FLOOR + 6 - sp.height / 2 - abs(math.sin(g * 6)) * 6)
            continue
        n = sum(1 for tt, a in st.mash_hits() if a == t0 and tt <= g)
        last = max(tt for tt, a in st.mash_hits() if a == t0)
        if g < last + 2 / 30:                              # held: shudders on each hit, flashes
            d = (g - t0) % (BEAT / 4)
            k = max(0.0, 1 - d / 0.07)
            sq = sp.resize((int(sp.width * (1 + 0.08 * k)), int(sp.height * (1 - 0.07 * k))), Image.Resampling.BICUBIC)
            if d < 1 / 30:
                a = np.asarray(sq).copy()
                a[..., :3] = (a[..., :3] * 0.5 + 255 * 0.5).astype(np.uint8)
                sq = Image.fromarray(a, "RGBA")
            put(img, sq, hx + 8 * k, FLOOR + 6 - sq.height / 2)
            pal = FX.STAGE_PAL.get(st.STAGES[st.stage_at(t0)][1], "pink")
            late.append(lambda im, d=d, s_=int(g * 30), p_=pal: (
                FX.impact(im, hx - 60 + (s_ % 3) * 30, FLOOR - 140 + (s_ % 4) * 22, d, s_, p_, 0.9),
                FX.confetti(im, hx - 40, FLOOR - 120, d, s_, p_, 8)))
            texts.append(lambda im, n=n, d=d: (
                put(im, splat(), hx - 20, FLOOR - 420, scale=0.8 + 0.15 * max(0.0, 1 - d / 0.08)),
                put(im, text_img(f"{n}", 66, LEMON, (90, 30, 60), 8), hx - 20, FLOOR - 432,
                    scale=1 + 0.25 * max(0.0, 1 - d / 0.08)),
                put(im, text_img("HITS", 26, WHITE, (90, 30, 60), 5), hx - 20, FLOOR - 384)))
        else:                                              # launched
            a2 = g - last - 2 / 30
            if a2 < 0.4:
                put(img, monster_tilt(fam, "big", int(-a2 * 900) % 360), hx + a2 * 1100, FLOOR - 140 - a2 * 1800 + a2 * a2 * 900,
                    alpha=1 - max(0.0, a2 - 0.3) / 0.1)


@lru_cache(maxsize=256)                       # bounded: spinning launched enemies make one rotation per degree
def monster_tilt(fam, role, deg):
    return monster(fam, role).rotate(deg, Image.Resampling.BICUBIC, expand=True)


@lru_cache(None)
def saw(fam, step):
    """Saw with its outer ring turned (24 steps per turn) and the hub (face) upright."""
    sp = monster(fam, "saw")
    rot = sp.rotate(step * 15, Image.Resampling.BICUBIC, center=(sp.width / 2, sp.height / 2))
    a, b = np.asarray(sp).astype(np.float32), np.asarray(rot).astype(np.float32)
    yy, xx = np.mgrid[0:sp.height, 0:sp.width]
    r = np.hypot(xx - sp.width / 2, yy - sp.height / 2) / (min(sp.size) / 2)
    w = np.clip((r - HUB[fam]) / 0.04, 0, 1)[..., None]
    pa, pb = a[..., :3] * a[..., 3:] / 255, b[..., :3] * b[..., 3:] / 255
    al = a[..., 3:] * (1 - w) + b[..., 3:] * w
    rgb = (pa * (1 - w) + pb * w) / np.maximum(al / 255, 1e-3)
    return Image.fromarray(np.dstack([rgb, al]).clip(0, 255).astype(np.uint8), "RGBA")


def burst(img, x, y, age, cols=(LEMON, WHITE, PINK)):
    """Star burst + ring flash on a hit."""
    if age > 0.4:
        return
    u = age / 0.4
    if age < 0.12:
        r = 30 + age * 700
        lay = Image.new("RGBA", (int(2 * r + 20), int(2 * r + 20)), (0, 0, 0, 0))
        ImageDraw.Draw(lay).ellipse([10, 10, 10 + 2 * r, 10 + 2 * r], outline=(255, 255, 255, int(230 * (1 - age / 0.12))),
                                    width=8)
        img.alpha_composite(lay, (int(x - r - 10), int(y - r - 10)))
    for k in range(7):
        ang = k * 2 * math.pi / 7 + 0.4
        d = 30 + 190 * (1 - (1 - u) ** 2)
        sz = int(46 * (1 - u) + 10)
        put(img, star_icon(56, cols[k % len(cols)]), x + d * math.cos(ang), y + d * math.sin(ang),
            alpha=1 - u * u, scale=sz / 56)


def slash(img, x, y, age):
    """Swipe arc in front of her on a hit."""
    if age > 0.14:
        return
    u = age / 0.14
    w, h = 220, 220
    lay = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    a0 = -70 + 40 * u
    d.arc([20, 20, 2 * w - 20, 2 * h - 20], a0, a0 + 120, fill=(255, 255, 255, int(240 * (1 - u))), width=26)
    d.arc([44, 44, 2 * w - 44, 2 * h - 44], a0 + 10, a0 + 110, fill=(170, 220, 255, int(200 * (1 - u))), width=10)
    lay = lay.resize((w, h), Image.Resampling.LANCZOS)
    img.alpha_composite(lay, (int(x - w / 2), int(y - h / 2)))


def perfect(img, x, y, age):
    if age > 0.38:
        return
    sc = 1.35 - 0.35 * min(1, age / 0.07)
    put(img, text_img("PERFECT", 46, PINK, WHITE, 7), x, y - age * 90, alpha=1 - max(0, (age - 0.26) / 0.12), scale=sc)


def miss_text(img, x, y, age):
    if age > 0.5:
        return
    put(img, text_img("MISS", 44, (150, 150, 190), WHITE, 7), x, y - age * 60, alpha=1 - max(0, (age - 0.35) / 0.15))


def draw_world(img, g, late=None, texts=None):
    """Monsters, saws, pickups; hit effects go to `late` (drawn over everything) and judgements to `texts`."""
    st = ST()
    late = [] if late is None else late
    texts = [] if texts is None else texts
    cx_now = st.cam_x(g)
    for tt, kind in st.chart():
        dt = tt - g
        if kind in ("gear", "gear_miss", "note", "heart"):            # fixed to the ground, scroll with it
            if dt < -1.2 or dt > 4.0:
                continue
            x = HIT_X - 60 + (st.cam_x(tt) - cx_now) * K
            if x > OW + 120 or x < -200:
                continue
            if kind.startswith("gear"):
                if dt < 0 and kind == "gear_miss" and int(-dt * 14) % 2:
                    continue
                fam = family_at(tt)
                sp = saw(fam, int((g * 30) % 24))
                bob = 0
                drop = BOSS.saw_drop(tt, g, x) if kind == "gear" else (x, 0)
                if drop is None:                                     # still in the looming king's mouth
                    continue
                x, bob = drop
                img.alpha_composite(sp, (int(x - sp.width / 2), int(FLOOR + 14 - sp.height + bob)))
                if bob < 0:                                          # falling: smear above it
                    for k_, al_ in ((1, 0.35), (2, 0.18)):
                        put(img, sp, x, FLOOR + 14 - sp.height / 2 + bob - k_ * 40, alpha=al_)
                    continue
                for t0_, thr_, land_ in BOSS.omen_throws():          # landing: dust and ring
                    if abs(t0_ - tt) < 1e-6 and 0 <= g - land_ < 0.34:
                        FX.ring_flash(img, x, FLOOR, g - land_, (255, 120, 120))
                        FX.puffs(img, x - 20, FLOOR - 10, g - land_, int(tt * 77), 4, 80)
                FX.grind(img, x - sp.width * 0.1, FLOOR + 6, g, int(tt * 100))
                if kind == "gear_miss" and dt < 0:
                    miss_text(img, HIT_X, FLOOR - 200, -dt)
                if kind == "gear" and -0.6 < dt < 0.3:               # dodge: take-off, sparks, PASS, landing
                    sd = int(tt * 1000)
                    late.append(lambda im, a=-dt, s_=sd: (
                        FX.ring_flash(im, RUN_X, FLOOR, a + 0.24), FX.puffs(im, RUN_X - 40, FLOOR - 20, a + 0.24, s_, 3, 70),
                        a >= 0 and FX.clear_spark(im, RUN_X + 10, FLOOR - 70, a, s_),
                        a >= 0.24 and FX.ring_flash(im, RUN_X, FLOOR, a - 0.24, (255, 220, 140)),
                        a >= 0.24 and FX.puffs(im, RUN_X + 20, FLOOR - 20, a - 0.24, s_ + 1, 3, 70)))
                    if dt < 0:
                        texts.append(lambda im, a=-dt: FX.judgement(im, HIT_X + 150, FLOOR - 360, a, "pass", "PASS"))
            elif dt >= 0:
                ic = MD.sprite("note2") if kind == "note" else heart_icon()
                y = FLOOR - 250 if kind == "note" else FLOOR - 150
                put(img, ic, x, y + 8 * math.sin(g * 6 + tt))
            elif dt > -0.95:
                yy_ = FLOOR - 250 if kind == "note" else FLOOR - 150
                FX.impact(img, x, yy_, -dt, int(tt * 1000), "blue", 0.6)
                FX.confetti(img, x, yy_, -dt, int(tt * 1000), "blue", 10)
        elif kind in ("g", "a", "a_miss"):
            if dt > 1.9 or dt < -0.6:
                continue
            lane = "air" if kind.startswith("a") else "ground"
            fam = family_at(tt)
            x = HIT_X + 40 + dt * V_E
            role = role_for(tt, kind, lane, fam)
            gh = st.is_ghost(tt, kind)
            bk = BOSS.thrown(tt)                                     # fired by a boss: only after it leaves the muzzle
            if bk == "mini":
                fam = "chat"
            if bk and dt >= 0:
                tilt = round(4 * math.sin(g * 7 + tt))
                sp = monster_tilt(fam, lane, tilt)
                pos = BOSS.projectile(bk, tt, g, lane, x, monster(fam, lane).height)
                if pos is not None:
                    for k, al in ((2, 0.18), (1, 0.35)):             # speed smear behind the shot
                        put(img, sp, pos[0] + k * 26, pos[1], alpha=al)
                    put(img, sp, pos[0], pos[1])
                continue
            if dt >= 0 or kind == "a_miss":
                if kind == "a_miss" and dt < 0:
                    if int(-dt * 14) % 2:
                        continue
                    miss_text(img, HIT_X, AIR_Y - 150, -dt)
                if x > OW + 200:
                    continue
                # ghost: fades out between 1.1 and 0.45 s before her, flickering back for a frame now and then
                al_ = 1.0 if not gh else max(0.0, min(1.0, (dt - 0.45) / 0.65)) + (0.35 if int(g * 30) % 9 == 0 and dt < 0.45 else 0)
                if lane == "air":
                    tilt = round(5 * math.sin(g * 5 + tt))
                    sp = monster_tilt(fam, role, tilt)
                    y = AIR_Y + 10 * math.sin(g * 7 + tt * 3)
                    put(img, sp, x, y, alpha=min(1.0, al_))
                else:
                    ph = g * 9 + tt * 3
                    tilt = round(4 * math.sin(ph)) if role != "big" else round(2 * math.sin(ph * 0.5))
                    sp = monster_tilt(fam, role, tilt)
                    hop = abs(math.sin(ph)) * (10 if role != "big" else 4)
                    put(img, sp, x, FLOOR + 6 - sp.height / 2 - hop, alpha=min(1.0, al_))
            else:                                                    # struck (see mdfx.py for the timeline)
                age = -dt
                pal = FX.STAGE_PAL.get(st.STAGES[st.stage_at(tt)][1], "pink")
                seed = int(tt * 1000)
                base = monster(fam, role)
                y0 = AIR_Y if lane == "air" else FLOOR + 6 - base.height / 2
                hx = HIT_X + 40
                stop = 2 / 30                                        # hit-stop: 2 frames held, squashed
                if age < stop:
                    sq = base.resize((int(base.width * 1.18), int(base.height * 0.84)), Image.Resampling.LANCZOS)
                    if age < 1 / 30:                                 # 1-frame white flash on the target
                        a = np.asarray(sq).copy()
                        a[..., :3] = (a[..., :3] * 0.35 + 255 * 0.65).astype(np.uint8)
                        sq = Image.fromarray(a, "RGBA")
                    put(img, sq, hx, y0 + (base.height - sq.height) / 2)
                else:
                    a2 = age - stop
                    if a2 < 0.32:
                        sp = monster_tilt(fam, role, int(-a2 * 1100) % 360)
                        for k, al in ((2, 0.18), (1, 0.36), (0, 1.0)):       # smear ghosts along the flight
                            ak = max(0.0, a2 - k * 0.022)
                            kx, ky = hx + ak * 950, y0 - ak * 2300 + ak * ak * 700     # launched steeply up
                            put(img, sp, kx, ky, alpha=al * (1 - max(0, a2 - 0.22) / 0.1))
                iy = AIR_Y if lane == "air" else FLOOR - 120               # impact at her strike point
                ix = RUN_X + 150
                late.append(lambda im, a=age, s_=seed, p_=pal, y_=iy, ln=lane: (     # drawn over all objects
                    FX.confetti(im, ix + 60, y_, a, s_, p_), FX.impact(im, ix, y_, a, s_, p_, 1.3),
                    ln == "ground" and FX.puffs(im, hx + 30, FLOOR - 30, a, s_),
                    FX.swoosh(im, HIT_X + 50, (AIR_Y + 10 if ln == "air" else FLOOR - 120), a, up=(ln == "air"))))
                jx, jy = 0, ((seed // 13) % 3 - 1) * 34      # rapid hits stack, offset
                texts.append(lambda im, a=age, p_=pal, ln=lane, jx=jx, jy=jy: FX.judgement(
                    im, HIT_X + 150 + jx, ((AIR_Y - 170) if ln == "air" else FLOOR - 340) + jy, a, p_))
    for hold in st.HOLDS:
        if hold[0] - 1.9 <= g < hold[1] + 0.45:
            draw_hold(img, g, hold)


HOLD_Y = FLOOR - 150                    # ground ribbon centre (her mid height, as in the reference)


@lru_cache(None)
def ribbon_tile(fam, h=150):
    """Seamless ribbon tile from the family's N5 ribbon (rb_<fam>_6800x): cut out, scaled to height h, the right
    third cross-faded into the left so it tiles, plus a soft glow behind."""
    import mdsprites as MDs
    name = {"k": "rb_k_68001", "u": "rb_u_68001", "p": "rb_p_68001", "n": "rb_n_68001", "f": "rb_f_68001"}.get(
        fam, "rb_n_68001")
    src = Image.open(MDs.SRC / f"{name}.png").convert("RGB")
    src = src.crop((int(src.width * 0.12), 0, int(src.width * 0.88), src.height))   # no wrapper ends / knots
    pale = fam == "k"                                     # the cream cloud band: only near-white is background
    im = MDs.cutout(src, light=246 if pale else 200, sat_max=10 if pale else 60)
    im = im.resize((round(im.width * (h - 30) / im.height), h - 30), Image.Resampling.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    w = a.shape[1]
    ov = w // 4
    left, right = a[:, :ov], a[:, w - ov:]
    t = np.linspace(0, 1, ov)[None, :, None]
    a2 = a[:, : w - ov].copy()
    a2[:, :ov] = right * (1 - t) + left * t
    tile = Image.fromarray(a2.clip(0, 255).astype(np.uint8), "RGBA")
    out = Image.new("RGBA", (tile.width, h), (0, 0, 0, 0))
    glow = Image.new("RGBA", out.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).rectangle((0, 22, tile.width, h - 22), fill=(255, 255, 255, 110))
    out.alpha_composite(glow.filter(ImageFilter.GaussianBlur(10)))
    out.alpha_composite(tile, (0, 15))
    return out


@lru_cache(None)
def staff_tile(w=1200, h=150):
    """Glowing music-staff band (tileable, w px): five stripes cyan / violet / white over a soft glow, white note
    glyphs and treble clefs riding on it (reference: Muse Dash hold note, official screenshot)."""
    big = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    d.rectangle([0, 2 * 18, 2 * w, 2 * (h - 18)], fill=(60, 30, 130, 170))          # dark violet backing
    cols = [(110, 230, 255), (190, 140, 255), (245, 250, 255), (190, 140, 255), (110, 230, 255)]
    for i, c in enumerate(cols):
        yy = 2 * (24 + i * 24)
        d.rectangle([0, yy, 2 * w, yy + 2 * (9 if i in (0, 4) else 6)], fill=(*c, 255))
    glow = big.filter(ImageFilter.GaussianBlur(16))
    out = Image.new("RGBA", big.size, (0, 0, 0, 0))
    out.alpha_composite(glow)
    out.alpha_composite(big)
    out = out.resize((w, h), Image.Resampling.LANCZOS)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 92)
    dd = ImageDraw.Draw(out)
    glyphs = ["\u266C", "\u2669", "\u266B", "\u266A", "\u266C", "\u266B", "\u266A", "\u2669"]
    for k, gl in enumerate(glyphs):
        x = 40 + k * (w // len(glyphs))
        yo = [-6, 6, -2, 8, 0, -4, 6, 2][k]
        try:
            dd.text((x, 18 + yo), gl, font=f, fill=(255, 255, 255, 255), stroke_width=5, stroke_fill=(110, 70, 220, 255))
        except Exception:
            pass
    return out


@lru_cache(None)
def hold_star(size, step):
    """Thick tilted cyan star with a white core and a glow (the hold's tail / head)."""
    def dr(d, k):
        c = size * k / 2
        rot = 0.25 + step * 0.02

        def pts(R, r):
            out = []
            for i in range(10):
                rr = R if i % 2 == 0 else r
                a = rot + i * math.pi / 5 - math.pi / 2
                out.append((c + rr * math.cos(a), c + rr * math.sin(a)))
            return out
        d.polygon(pts(c * 0.92, c * 0.5), fill=(90, 210, 255, 255))
        d.polygon(pts(c * 0.72, c * 0.38), fill=(230, 250, 255, 255))
        d.polygon(pts(c * 0.5, c * 0.27), fill=(120, 225, 255, 255))
    im = _ss(size, size, dr)
    g = im.filter(ImageFilter.GaussianBlur(10))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.alpha_composite(g)
    out.alpha_composite(im)
    return out


@lru_cache(None)
def hold_disc(r):
    """Translucent pale-blue disc with a white ring (her held-note aura)."""
    def dr(d, k):
        c = r * k
        d.ellipse([0, 0, 2 * c - 1, 2 * c - 1], fill=(150, 200, 255, 120))
        rr = c * 0.62
        d.ellipse([c - rr, c - rr, c + rr, c + rr], outline=(255, 255, 255, 235), width=int(9 * k))
    return _ss(2 * r, 2 * r, dr)


@lru_cache(None)
def hold_burst(size, step):
    """White star burst at the hit point (as in the reference): a big white star, white blobs around it, a cyan
    inner star; spins a little each frame."""
    rng = random.Random(step)

    def dr(d, k):
        c = size * k / 2
        for i in range(7):
            a = i * 2 * math.pi / 7 + step * 0.3
            r = c * rng.uniform(0.18, 0.28)
            x, y = c + c * 0.55 * math.cos(a), c + c * 0.55 * math.sin(a)
            d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 255))

        def star(R, rr, rot, col):
            pts = []
            for i in range(10):
                q = R if i % 2 == 0 else rr
                a = rot + i * math.pi / 5 - math.pi / 2
                pts.append((c + q * math.cos(a), c + q * math.sin(a)))
            d.polygon(pts, fill=col)
        star(c * 0.95, c * 0.45, step * 0.12, (255, 255, 255, 255))
        star(c * 0.5, c * 0.24, step * 0.12, (150, 235, 255, 255))
    return _ss(size, size, dr)


def draw_hold(img, g, hold):
    """Hold note (reference: official screenshot): a ribbon from the hit point to a big star in its lane; while held,
    a translucent disc with a white ring around her, a pulsing white burst and flying tick marks. The ribbon skin is
    the stage family's (art/generated/md_style/rb_*, N5), tiled seamlessly; the last hold keeps the music staff."""
    st = ST()
    h0, h1, lane = hold
    HOLD_Y = AIR_Y + 20 if lane == "a" else FLOOR - 150
    x0 = HIT_X + max(0.0, h0 - g) * V_E
    x1 = HIT_X + max(0.0, h1 - g) * V_E
    holding = h0 <= g < h1
    if holding:
        put(img, hold_disc(300), RUN_X + 40, HOLD_Y)
    if x1 > x0 + 2:
        w = int(min(OW + 60, x1) - x0)
        if w > 0:
            tile = ribbon_tile(family_at(h0)) if hold != st.HOLDS[-1] else staff_tile()
            off = int((g * V_E) % tile.width)                   # glyphs ride with the ribbon
            n = w // tile.width + 2
            long = Image.new("RGBA", (n * tile.width, tile.height), (0, 0, 0, 0))
            for k in range(n):
                long.paste(tile, (k * tile.width, 0))
            strip = long.crop((off, 0, off + w, tile.height))
            a = np.asarray(strip).copy()                        # soft fade-in at the head
            ramp = np.clip(np.arange(w) / 40.0, 0, 1)
            a[..., 3] = (a[..., 3] * ramp[None, :]).astype(np.uint8)
            img.alpha_composite(Image.fromarray(a, "RGBA"), (int(x0), int(HOLD_Y - tile.height / 2)))
    step = int(g * 30)
    if x1 < OW + 120:
        put(img, hold_star(190, step % 30), x1, HOLD_Y)
    if g < h0:
        put(img, hold_star(150, step % 30), x0, HOLD_Y)
    if holding:
        pulse = 1 + 0.12 * math.sin(g * 2 * math.pi * 136 / 60 * 2)
        put(img, hold_burst(int(260 * pulse), step % 12), HIT_X - 20, HOLD_Y)
        lay = Image.new("RGBA", (700, 700), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        rng = random.Random(step)
        for i in range(10):                                     # tick marks flying out of the disc
            ang = rng.uniform(0, 2 * math.pi)
            r0 = rng.uniform(150, 300)
            FX.taper_line(d, 350 + r0 * math.cos(ang), 350 + r0 * math.sin(ang), 350 + (r0 + 30) * math.cos(ang),
                          350 + (r0 + 30) * math.sin(ang), 6, 2, (255, 255, 255, 230))
        img.alpha_composite(lay, (int(RUN_X + 40 - 350), int(HOLD_Y - 350)))
    if h1 <= g < h1 + 0.4:                                      # release: the tail star bursts
        FX.impact(img, HIT_X, HOLD_Y, g - h1, 77, "blue", 1.2)
        FX.confetti(img, HIT_X, HOLD_Y, g - h1, 77, "blue", 24)


# ---------------------------------------------------------------- avatar
@lru_cache(None)
def anchor(sp_id):
    sp = _SP[sp_id]
    a = np.asarray(sp.getchannel("A"))[: int(sp.height * 0.55)] > 128
    xs = np.nonzero(a)[1]
    return float(xs.mean()) if len(xs) else sp.width / 2


_SP = {}


def _anchor(sp):
    if id(sp) in RN.AX:                      # armed frames: anchor on her body, never on the mic
        return RN.AX[id(sp)]
    _SP[id(sp)] = sp
    return anchor(id(sp))


# ---------------------------------------------------------------- loadout
# Her loadout changes through the PV and the weapon is not always there: bare sleeve punches first, the paw mic for
# the first chorus (余裕だもん) and the night stage, put away for the screenshot gag and the sulky / eerie stretches,
# back for the Fever finale. Stage index -> armed.
# Checked against the official trailer: Muse Dash never makes a weapon appear or vanish mid-run - a gameplay clip keeps
# one loadout from start to end, and a loadout change happens between clips behind a full-screen character close-up.
# So the swap happens only while a cut-in band (stream.CUTINS, its close-up showing the new loadout) or the festival
# curtain covers her: the stage switch times (55.61, 83.5, 125.8 s) all fall in those covered spans.
LOADOUT = {0: False, 1: False, 2: True, 3: True, 4: False, 5: False, 6: False, 7: True}


def armed_at(t):
    return LOADOUT.get(ST().stage_at(t), False)


def loadout_changes():
    st = ST()
    out = []
    for i, (t0, *_rest) in enumerate(st.STAGES):
        if i and LOADOUT.get(i) != LOADOUT.get(i - 1):
            out.append((t0, LOADOUT.get(i)))
    return out


@lru_cache(None)
def hurt_frame(flash):
    im, feet = RN.run_frame(4)
    im = im.rotate(8, Image.Resampling.BICUBIC, expand=True, center=(im.width / 2, feet))
    if flash:
        a = np.asarray(im).copy()
        m = a[..., 3] > 0
        a[m, :3] = (a[m, :3] * 0.55 + np.array((255, 120, 130)) * 0.45).astype(np.uint8)
        im = Image.fromarray(a, "RGBA")
    al = np.asarray(im.getchannel("A"))
    return im, float(np.nonzero(al.any(1))[0].max())


# ---------------------------------------------------------------- her attitude (pixel/mdbrat.py)
# Cheeky-brat flourishes between hits, as Muse Dash characters show short poses in the run: a peace sign on
# 準備もバッチリ, a smug finger wag right before she trips (キメちゃうよ -> えっ) and after the mini-boss BREAK!!, akanbe on 笑ったでしょ, ぷいって and after the main-boss BREAK!!, the めっ boop
# toward the viewer at 66.82 / 137.36, a flustered stumble on each miss and a peace-sign wink at STAGE CLEAR.
# A taunt only plays where no note falls and she is on the ground; in armed sections the paw mic is slung on her back.
TAUNT_LEN, BOOP_LEN = 0.55, 0.5


@lru_cache(None)
def acts():
    st = ST()
    notes = [tt for tt, k in st.chart() if k in ("g", "a", "a_miss", "gear", "gear_miss")]
    busy = [(a, b) for a, b, *_ in st.WIPES] + [(a - 0.3, b + 0.3) for a, b, ln in st.HOLDS]

    def free(t0, t1):
        if any(t0 - 0.06 <= n <= t1 + 0.06 for n in notes) or any(a < t1 and t0 < b for a, b in busy):
            return False
        return all(st.avatar_height(t0 + k * (t1 - t0) / 8) <= 0.5 for k in range(9))

    def place(t, key):
        for k in range(30):
            t0 = t + k * 0.05
            if free(t0, t0 + TAUNT_LEN):
                return (t0, t0 + TAUNT_LEN, key)
        return None
    hm, hb = BOSS.timeline("mini")[2], BOSS.timeline("main")[2]
    out = [place(24.45, "peace"), place(40.35, "wag"), place(64.35, "akanbe"), place(96.2, "akanbe"), place(hm + 0.6, "wag"),
           place(hb + 1.05, "akanbe")]
    out += [(66.82 - 0.12, 66.82 - 0.12 + BOOP_LEN, "boop"), (137.36 - 0.12, 137.36 - 0.12 + BOOP_LEN, "boop")]
    out += [(st.CLEAR_T - 0.1, st.CLEAR_T + 2.0, "peace")]
    return tuple(sorted(a for a in out if a))


def act_at(g):
    for t0, t1, key in acts():
        if t0 <= g < t1:
            return key, g - t0
    return None, 0.0


@lru_cache(None)
def act_sprite(key, armed, flash=False):
    """The pose; armed: the paw mic slung across her back (behind her); flash: the coral damage tint."""
    import mdweapon as WP
    sp, feet = BR.pose(key)
    ax = RN.AX[id(sp)]
    if armed:
        mic, (px, py) = WP.mic_sprite(round(RN.mic_len()), 12)
        pad = mic.height
        cv = Image.new("RGBA", (mic.width + 2 * pad, mic.height + 2 * pad), (0, 0, 0, 0))
        cv.alpha_composite(mic, (pad, pad))
        cv = cv.rotate(38, Image.Resampling.BICUBIC, center=(px + pad, py + pad))   # head up behind her shoulder
        bb = cv.getbbox()
        cv = cv.crop(bb)
        grip = (px + pad - bb[0], py + pad - bb[1])
        top = np.nonzero(np.asarray(sp.getchannel("A")).any(1))[0].min()
        hx, hy = ax + 18, top + 0.62 * (feet - top)        # pommel low behind her back
        L, T = min(0, int(hx - grip[0])), min(0, int(hy - grip[1]))
        W = max(sp.width, int(hx - grip[0]) + cv.width) - L
        H = max(sp.height, int(hy - grip[1]) + cv.height) - T
        out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        out.alpha_composite(cv, (int(hx - grip[0]) - L, int(hy - grip[1]) - T))
        out.alpha_composite(sp, (-L, -T))
        sp, feet, ax = out, feet - T, ax - L
    if flash:
        a = np.asarray(sp).copy()
        m = a[..., 3] > 0
        a[m, :3] = (a[m, :3] * 0.6 + np.array((255, 123, 138)) * 0.4).astype(np.uint8)
        sp = Image.fromarray(a, "RGBA")
    RN._register(sp, ax)
    return sp, feet


def avatar(t):
    """(sprite, feet row in sprite, centre x, feet y)."""
    st = ST()
    g = st.game_time(t)
    armed = armed_at(t)
    for m in (st.MISS_GEAR, st.MISS_BIRD):
        if 0 <= g - m < 0.45:                                # flustered stumble, coral damage blink
            sp, feet = act_sprite("fluster", armed, int(g * 20) % 2 == 1)
            return sp, feet, RUN_X - 28 * math.sin(min(1, (g - m) / 0.45) * math.pi), \
                FLOOR - st.avatar_height(g) * K * 0.5
    key, age = act_at(g)
    if key in ("boop", "peace") or (key and st.avatar_height(g) <= 0.5):
        sp, feet = act_sprite(key, armed)
        return sp, feet, RUN_X + (10 if key == "boop" else 0), FLOOR
    h = st.avatar_height(g) * K
    for h0_, h1_, ln_ in st.HOLDS:                 # holding a ribbon: running (ground) or riding the board (air)
        if h0_ <= g < h1_ + 0.12:
            if h > 20:                                         # air ribbon: riding the board, not running
                return (*RN.ride_at(g, armed), RUN_X, FLOOR - h)
            return (*RN.run_at(g, armed=armed), RUN_X, FLOOR - h)
    ng = na = 0
    pick = None
    for tt, kind in st.chart():                      # the latest struck note (Hell chart: hits overlap)
        if tt > g:
            break
        if kind in ("g", "a") and g - tt < STRIKE_HOLD[kind][armed]:
            pick = (tt, kind, ng, na)
        ng += kind == "g"
        na += kind == "a"
    mash = next((t0 for tt, t0 in st.mash_hits() if 0 <= g - tt < BEAT / 4), None)
    if mash is not None:                             # mash: a different strike drawing on every sixteenth
        i = int((g - mash) / (BEAT / 4))
        if armed:
            return (*BR.armed(BR.ARMED_GROUND[i % len(BR.ARMED_GROUND)]), RUN_X + 16, FLOOR)
        return (*RN.strike_frame("punch" if i % 2 == 0 else "air"), RUN_X + 16, FLOOR - (30 if i % 2 else 0))
    if pick:
        tt, kind, ng_, na_ = pick
        if st.is_gemini(tt):                         # Gemini: the air strike at mid height hits both lanes
            if armed:
                return (*BR.armed("airslam"), RUN_X + 12, FLOOR - h)
            return (*RN.strike_frame("air"), RUN_X + 12, FLOOR - h)
        if kind == "g":
            if armed:                     # a different attack drawing on each hit, as in Muse Dash
                return (*BR.armed(BR.ARMED_GROUND[ng_ % len(BR.ARMED_GROUND)]), RUN_X + 16, FLOOR)
            return (*RN.strike_frame("punch"), RUN_X + 16, FLOOR)
        if armed:
            return (*BR.armed(BR.ARMED_AIR[na_ % len(BR.ARMED_AIR)]), RUN_X + 12, FLOOR - h)
        return (*RN.strike_frame("air"), RUN_X + 12, FLOOR - h)
    if h > 1:
        rising = any(a <= g < ts[0] for a, b, ts in st.air_runs()) or any(
            k == "gear" and -0.24 < g - tt < 0 for tt, k in st.chart())
        sb = board_state(g)
        if sb is not None and sb[4] == 1 and h > 40:            # on the board: the riding stance
            return (*RN.ride_at(g, armed), RUN_X, FLOOR - h)
        return (*RN.jump_frame("up" if rising or h > 120 else "down", armed), RUN_X, FLOOR - h)
    return (*RN.run_at(g, armed=armed), RUN_X, FLOOR)


# ---------------------------------------------------------------- her hover board, animated with the flight
# Owner 2026-11-04: the board popped in and out as a flat sprite. Now it is an object with its own motion, driven by
# the same air-lane timing as her flight (stream.air_runs / stream._flight):
#   swoop-in  0.22 s before take-off it zips in from behind and below, banking, its jet igniting (flash, flame grows)
#   catch     it meets her feet as she rises; she lands on it (a small dip of the board = her weight)
#   ride      it stays under her feet, lagging a touch behind her bob, tilting with her vertical speed, jet flickering
#             on the beat, sparkle trail behind
#   kick-off  as she drops it is pushed back and up by her jump (recoil), spins a little
#   park/exit if she takes off again within 0.6 s it hovers behind her and swoops back; otherwise it banks away
#             backwards and up out of the picture, jet trailing
# Position: target path -> second-order dynamics (f 4.2 Hz, damping 0.55), simulated once at 120 Hz; rotation from
# its own velocity plus the dock tilt.
BOARD_DT = 1 / 120


@lru_cache(None)
def _board_track():
    st = ST()
    runs = st.air_runs()
    ts = np.arange(st.GAME_IN, st.GAME_OUT, BOARD_DT)
    tx, ty, mode = np.empty_like(ts), np.empty_like(ts), np.zeros(len(ts), np.int8)
    off = (-420.0, FLOOR - 620.0)                                 # parked out of the picture, behind and above
    # only real flights get the board (Muse Dash: a single air note is a plain jump); short hops stay hops
    runs = tuple(r for r in runs if r[1] - r[0] >= 0.8)
    for i, g in enumerate(ts):
        tx[i], ty[i] = off
        for j, (a, b, notes) in enumerate(runs):
            nxt = runs[j + 1][0] if j + 1 < len(runs) else 1e9
            prv = runs[j - 1][1] if j > 0 else -1e9
            if a - 0.24 <= g < b - st.AIR_DROP * 0.7:              # swoop-in, catch, ride
                h = st.avatar_height(max(g, a)) * K
                tx[i], ty[i] = RUN_X + 6, FLOOR - h + 12
                mode[i] = 1 if g >= a else 2
                if g < a and a - prv < 0.6:                       # it was parked right behind her
                    mode[i] = 2
                break
            if b - st.AIR_DROP * 0.7 <= g < nxt and nxt - b < 1.5 and g < nxt - 0.24:
                tx[i], ty[i] = RUN_X - 150, FLOOR - 250            # parked behind her, waiting
                mode[i] = 3
                break
            if b - st.AIR_DROP * 0.7 <= g < b + 0.25:              # kick-off: pushed back and up
                u = (g - (b - st.AIR_DROP * 0.7)) / 0.3
                tx[i], ty[i] = RUN_X - 260 * u, FLOOR - 300 - 180 * u
                mode[i] = 4
                break
    # springs (the first sample starts parked)
    f, z, r = 4.2, 0.55, 1.1
    k1, k2, k3 = z / (math.pi * f), 1 / (2 * math.pi * f) ** 2, r * z / (2 * math.pi * f)
    T = BOARD_DT
    xs, ys = np.empty_like(ts), np.empty_like(ts)
    xs[0], ys[0] = off
    vx = vy = 0.0
    px, py = tx[0], ty[0]
    vxs, vys = np.zeros_like(ts), np.zeros_like(ts)
    for i in range(1, len(ts)):
        dx, dy = (tx[i] - px) / T, (ty[i] - py) / T
        px, py = tx[i], ty[i]
        if mode[i] == 1:                                          # riding: locked under her feet (a 3-frame lag)
            j = max(0, i - 3)
            xs[i], ys[i] = tx[i], 0.6 * ty[i] + 0.4 * ty[j]
            vx, vy = (xs[i] - xs[i - 1]) / T, (ys[i] - ys[i - 1]) / T
        else:
            xs[i] = xs[i - 1] + T * vx
            ys[i] = ys[i - 1] + T * vy
            vx += T * (tx[i] + k3 * dx - xs[i] - k1 * vx) / k2
            vy += T * (ty[i] + k3 * dy - ys[i] - k1 * vy) / k2
        vxs[i], vys[i] = vx, vy
    return ts, xs, ys, vxs, vys, mode


def board_state(g):
    st = ST()
    if not st.GAME_IN <= g < st.GAME_OUT - 0.05:
        return None
    ts, xs, ys, vxs, vys, mode = _board_track()
    i = int((g - ts[0]) / BOARD_DT)
    if i < 0 or i >= len(ts):
        return None
    return xs[i], ys[i], vxs[i], vys[i], int(mode[i])


@lru_cache(None)
def hover_board(power):
    """Hover board v2 (art/generated/md_style/hv2_board_*, N5): steady thruster jet (length by power 0..8) and a
    soft cyan under-glow; no per-frame random flicker (owner: the board flickered)."""
    bd = MD.sprite("hover2")
    W, H = bd.width + 60, bd.height + 110
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    cx, top = W / 2, bd.height * 0.78
    d.ellipse((cx - bd.width * 0.42, top - 10, cx + bd.width * 0.42, top + 26), fill=(120, 230, 255, 70 + 10 * power))
    if power:
        L = 26 + 7 * power
        d.polygon([(cx - 26, top), (cx + 26, top), (cx, top + L)], fill=(120, 230, 255, 170))
        d.polygon([(cx - 11, top), (cx + 11, top), (cx, top + L * 0.7)], fill=(235, 252, 255, 240))
    out.alpha_composite(lay.filter(ImageFilter.GaussianBlur(4)))
    out.alpha_composite(bd, (30, 0))
    return out


def _mount_time(g):
    """Start of the current ride (the moment she lands on the board), or None."""
    st = ST()
    for a, b, notes in st.air_runs():
        if a - 0.05 <= g < b:
            return a + 0.06
    return None


def draw_board(img, g, cx=None, fy=None, dx=0.0):
    sb = board_state(g)
    if sb is None:
        return
    x, y, vx, vy, mode = sb
    st = ST()
    beat = 0.5 + 0.5 * math.cos(2 * math.pi * (g - st.PH0) / BEAT)
    if mode == 1 and cx is not None:                       # riding: exactly under her feet, her weight on it
        tm = _mount_time(g) or g
        a_ = max(0.0, g - tm)
        dip = 18 * math.exp(-a_ / 0.13) * math.cos(2 * math.pi * a_ / 0.26)   # lands on it: dips, springs back
        x, y = cx + dx + 4, fy + 16 + dip
        rot = max(-6.0, min(6.0, st.avatar_velocity(g) / 220))
        power = int(round(4 + 3 * beat))
    else:
        rot = max(-12.0, min(12.0, -vy / 120 - vx / 220))
        power = 3 if mode in (2, 3) else 2
    if x < -300 or y < -260:
        return
    bd = hover_board(power).rotate(rot, Image.Resampling.BICUBIC, expand=True)
    sp = math.hypot(vx, vy)
    if sp > 700 and mode != 1:                             # streak behind it while it flies in / away
        for k, al in ((1, 0.30), (2, 0.14)):
            put(img, bd, x - vx * k / 40, y - vy * k / 40, alpha=al)
    put(img, bd, x, y)
    if mode == 1:                                          # slipstream: soft cyan streaks trailing back
        for k in range(4):
            u = ((g * 2.2 + k / 4) % 1)
            yy = y + 30 + (k % 2) * 10
            put(img, streak_img(int(70 + 120 * u)), x - 80 - 200 * u, yy, alpha=0.55 * (1 - u))
        tm = _mount_time(g)
        if tm is not None and 0 <= g - tm < 0.3:          # landing on the board: shock ring + sparks + jet flash
            FX.ring_flash(img, x, y + 30, g - tm, (150, 235, 255))
            burst(img, int(x), int(y + 20), g - tm, cols=((150, 235, 255), WHITE, (120, 160, 255)))


@lru_cache(None)
def streak_img(w):
    im = Image.new("RGBA", (w, 10), (0, 0, 0, 0))
    a = np.zeros((10, w, 4), np.uint8)
    a[..., :3] = (190, 245, 255)
    xs = np.linspace(0, 1, w)
    a[3:7, :, 3] = (255 * xs ** 1.5).astype(np.uint8)
    return Image.fromarray(a, "RGBA")


@lru_cache(None)
def _hover_board_unused(flick):
    """The cat-paw hover board (art/generated/md_style/hv_board_66103) with a flickering cyan jet under it."""
    bd = MD.sprite("hover")
    W, H = bd.width + 40, bd.height + 70
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    jet = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(jet)
    L = 40 + 10 * flick
    for k, (col, w) in enumerate((((120, 230, 255, 140), 34), ((220, 250, 255, 230), 16))):
        d.polygon([(W / 2 - w, bd.height - 8), (W / 2 + w, bd.height - 8), (W / 2, bd.height - 8 + L - k * 12)],
                  fill=col)
    out.alpha_composite(jet.filter(ImageFilter.GaussianBlur(3)))
    out.alpha_composite(bd, (20, 0))
    return out


@lru_cache(None)
def shadow_img(w):
    def dr(d, k):
        d.ellipse([0, 0, w * k - 1, 18 * k - 1], fill=(20, 16, 50, 70))
    return _ss(w, 18, dr)


# ---------------------------------------------------------------- motion (Muse Dash feel)
# Studied frame by frame on the official trailer (30 fps): poses snap rather than float; every hit lunges toward the
# enemy with a lean and a stretch, smeared for 1-2 frames, then she is straight back to running; she snaps to the
# air lane and back in 2-3 frames; landings squash and kick up dust puffs. Timings from game-feel guides: squash /
# stretch 2-4 frames, smear 1-2 frames, hit lunge settles within about 5 frames.
STRIKE_HOLD = {"g": (0.11, 0.11), "a": (0.12, 0.12)}     # (unarmed, armed) seconds; Hell chart: 8ths 0.22 s


def strike_at(t):
    """(kind, age) of the hit pose showing at song time t, or (None, 0)."""
    st = ST()
    g = st.game_time(t)
    armed = armed_at(t)
    best = None
    for tt, kind in st.chart():                      # the latest note whose pose is still showing
        if tt > g:
            break
        if kind in STRIKE_HOLD and g - tt < STRIKE_HOLD[kind][armed]:
            best = (kind, g - tt)
    for tt, t0 in st.mash_hits():
        if 0 <= g - tt < 0.06:
            best = ("g", g - tt)
    return best if best else (None, 0.0)


def edge_age(g, up):
    """Seconds since she left the ground (up) / touched down (not up), if within 0.4 s."""
    st = ST()
    step = 1 / 120
    h1 = st.avatar_height(g)
    for k in range(1, 49):
        h0 = st.avatar_height(g - k * step)
        if up and h0 <= 0.5 < h1:
            return (k - 1) * step
        if not up and h0 > 0.5 >= h1:
            return (k - 1) * step
        h1 = h0
    return None


def _xform(sp, piv, sx, sy, rot):
    """Scale about the pivot (her feet / anchor) and rotate about it; returns (image, pivot in it)."""
    w, h = sp.size
    im = sp.resize((max(1, round(w * sx)), max(1, round(h * sy))), Image.Resampling.BICUBIC)
    pad = int(max(im.size) * 0.25) + 4
    cv = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    cv.alpha_composite(im, (pad, pad))
    c = (piv[0] * sx + pad, piv[1] * sy + pad)
    if rot:
        cv = cv.rotate(rot, Image.Resampling.BICUBIC, center=c)
    return cv, c


def _ghost(sp, col, alpha):
    a = np.asarray(sp).copy()
    a[..., :3] = col
    a[..., 3] = (a[..., 3] * alpha).astype(np.uint8)
    return Image.fromarray(a, "RGBA")


def motion(t):
    """(sx, sy, rot_deg, dx) for her sprite at song time t."""
    g = ST().game_time(t)
    key, age = act_at(g)
    if key and age < 0.1:                                   # each flourish pops in (stretch, settle)
        q = 0.08 * (1 - age / 0.1)
        return 1 - 0.6 * q, 1 + q, 0.0, 0.0
    if key == "boop" and 0.1 <= age < 0.22:                 # the boop: a quick lunge toward the viewer
        k = math.sin(math.pi * (age - 0.1) / 0.12)
        return 1 + 0.06 * k, 1 + 0.06 * k, -4 * k, 14 * k
    kind, age = strike_at(t)
    if kind:
        u = min(1.0, age / 0.12)
        k = (1 - u) ** 2
        sx, sy = (1.07, 0.95) if age < 0.034 else (1.0 + 0.02 * k, 1.0)
        return sx, sy, (-7 if kind == "g" else -4) * k, 38 * k
    land = edge_age(g, False)
    if land is not None and land < 0.15:
        q = 0.15 * (1 - land / 0.15) ** 2 * (1 if land > 0.017 else 0.6)
        return 1 + 0.8 * q, 1 - q, 0.0, 0.0
    take = edge_age(g, True)
    if take is not None and take < 0.09:
        q = 0.12 * (1 - take / 0.09)
        return 1 - 0.55 * q, 1 + q, 0.0, 0.0
    if ST().avatar_height(g) <= 0.5 and not key:              # running: lean into the stride, bounce on contacts
        ph = 2 * math.pi * (g - ST().PH0) / BEAT
        return 1 - 0.018 * abs(math.cos(ph)), 1 + 0.025 * abs(math.cos(ph)), -2.0 - 1.5 * math.sin(ph), 0.0
    sb = board_state(g)
    if sb is not None and sb[4] == 1 and ST().avatar_height(g) > 40 and not key:   # riding: leaning into the wind
        v = ST().avatar_velocity(g)
        sway = 1.5 * math.sin(2 * math.pi * (g - ST().PH0) / (2 * BEAT))
        return 1.0, 1.0, -6.0 + sway + max(-5.0, min(5.0, v / 200)), 0.0
    v = ST().avatar_velocity(g)                             # in flight: lean back rising, nose down falling,
    if abs(v) > 30:                                         # stretch along the motion (secondary motion)
        st_ = min(0.10, abs(v) / 9000)
        return 1 - 0.5 * st_, 1 + st_, max(-8.0, min(8.0, v / 160)), 0.0
    return 1.0, 1.0, 0.0, 0.0


# ---------------------------------------------------------------- speed lines and boost strips
# Owner 2026-11-04: "there aren't enough speed boost strips". Muse Dash keeps the playfield rushing: thin flickering
# speed lines run all through a stage and thicken with the music; at each big moment a set of wide coloured boost
# strips sweeps across the screen. Here: speed lines everywhere in the game, their number following the song's energy
# (data/songmap.json RMS per sixteenth: 6 in the quietest bars up to 30 in the loudest), and boost strips - three wide
# tapered bands in the stage palette sweeping right to left in 0.45 s - on every chorus start, every Gemini, after
# each mash enemy and boss BREAK!!, and when she first takes the hover board up in a section.
BOOST_COLS = {"pink": ((255, 60, 170), (90, 200, 255), (160, 80, 255)),
              "gold": ((255, 170, 30), (255, 90, 120), (255, 220, 60))}


@lru_cache(None)
def _energy():
    sm = ST().songmap()
    return np.array([p["t"] for p in sm]), np.array([p["rms"] for p in sm])


def speed_density(g):
    st = ST()
    if not st.GAME_IN + 0.6 <= g < st.CLEAR_T or st.PAUSE[0] <= g < st.PAUSE[1]:
        return 0
    ts, e = _energy()
    v = float(np.interp(g, ts, np.convolve(e, np.ones(16) / 16, mode="same")))
    return int(6 + 24 * min(1.0, max(0.0, (v - 0.35) / 0.55)))


@lru_cache(None)
def boost_times():
    st = ST()
    out = [a for a, b in st.CHORUSES] + sorted(st.gemini_times())
    out += [t1 + 0.1 for t0, t1 in st.MASH.items()]
    out += [BOSS.timeline(k)[2] + 0.5 for k in BOSS.BOSSES]
    prev = -9
    for a, b, notes in st.air_runs():
        if a - prev > 4:
            out.append(a)
        prev = b
    return tuple(sorted(out))


@lru_cache(None)
def boost_strip(w, h, col):
    a = np.zeros((h, w, 4), np.uint8)
    a[..., :3] = col
    xs = np.linspace(0, 1, w)[None, :]
    ys = np.abs(np.linspace(-1, 1, h))[:, None]
    a[..., 3] = (255 * np.clip(xs * 1.4, 0, 1) * (1 - xs ** 6) * (1 - ys ** 2.5)).astype(np.uint8)
    core = ys[:, 0] < 0.22                                   # bright white core along the strip
    a[core, :, :3] = 255
    return Image.fromarray(a, "RGBA")


def draw_boost(img, g):
    st = ST()
    for t0 in boost_times():
        a = g - t0
        if not 0 <= a < 0.45:
            continue
        pal = BOOST_COLS.get(FX.STAGE_PAL.get(st.STAGES[st.stage_at(t0)][1], "pink"), BOOST_COLS["pink"])
        for k, (y, h) in enumerate(((AIR_Y - 130, 96), (AIR_Y + 70, 60), (FLOOR - 160, 112))):
            u = (a - 0.04 * k) / 0.38
            if not 0 <= u < 1:
                continue
            w = 900 + 500 * (k % 2)
            x = OW + 200 - (OW + w + 400) * (1 - (1 - u) ** 2)
            put(img, boost_strip(w, h, pal[k]), x + w / 2, y, alpha=1 - u ** 3)


def draw_avatar(img, t, fever=False):
    st = ST()
    g = st.game_time(t)
    sp, feet, cx, fy = avatar(t)
    air = FLOOR - fy
    put(img, shadow_img(max(60, int(150 - air * 0.3))), cx, FLOOR + 4)
    PET.draw(img, g, cx, fy, ST().avatar_height)              # her sleepy cat spirit, behind her shoulder
    ax = _anchor(sp)
    sx, sy, rot, dx = motion(t)
    if (sx, sy, rot) != (1.0, 1.0, 0.0):
        sp, (ax, feet) = _xform(sp, (ax, feet), sx, sy, rot)
    x0, y0 = int(round(cx + dx - ax)), int(round(fy - feet))
    draw_board(img, g, cx, fy, dx)
    kind, age = strike_at(t)
    if kind and age < 0.07:                                 # 1-2 frame smear behind the lunge
        for k, (off, col, al) in enumerate(((-30, (255, 255, 255), 0.42), (-62, (200, 236, 255), 0.24))):
            img.alpha_composite(_ghost(sp, col, al), (x0 + off, y0))
    if fever:
        FX.afterimages(img, sp, x0, y0, g)
    img.alpha_composite(sp, (x0, y0))
    key, age = act_at(g)
    if key == "boop" and 0.1 <= age < 0.5:                  # めっ: coral word + paw pop toward the viewer
        u = (age - 0.1) / 0.4
        sc = 1.3 - 0.3 * min(1.0, u / 0.25)
        put(img, text_img("めっ", 84, (255, 123, 138), (90, 30, 60), 9), cx + 150, fy - 300 - 30 * u,
            alpha=1 - max(0.0, (u - 0.7) / 0.3), scale=sc)
        burst(img, int(cx + 120), int(fy - 190), age - 0.1, cols=((255, 123, 138), WHITE, PINK))
    if key in ("wag", "akanbe") and age < 0.4:              # a cheeky sparkle by her face
        put(img, star_icon(56, LEMON), cx + 70 + 20 * age, fy - 300 - 40 * age, alpha=1 - age / 0.4,
            scale=0.7 + age)
    gear_near = any(k_ == "gear" and abs(g - tt) < 0.6 for tt, k_ in st.chart())
    if not gear_near:                                       # air lane: take-off and landing dust (saws have their own)
        land, take = edge_age(g, False), edge_age(g, True)
        if land is not None:
            FX.ring_flash(img, cx, FLOOR, land)
            FX.puffs(img, cx - 30, FLOOR - 16, land, int(g * 10), 3, 66)
        if take is not None:
            FX.puffs(img, cx - 50, FLOOR - 12, take, int(g * 10) + 1, 2, 54)


def fever_trail(img, g):
    st = ST()
    if not st.FEVER_T <= g < st.CLEAR_T:
        return
    h = st.avatar_height(g) * K
    cols = [(255, 120, 150), (255, 210, 90), (130, 230, 160), (110, 200, 255), (190, 150, 255)]
    lay = Image.new("RGBA", (RUN_X, 120), (0, 0, 0, 0))
    a = np.zeros((120, RUN_X, 4), np.uint8)
    xs = np.arange(RUN_X)
    fade = np.clip(xs / 260, 0, 1) ** 1.5
    for k, c in enumerate(cols):
        y0 = 14 + k * 18 + int(4 * math.sin(g * 10 + k))
        a[y0:y0 + 14, :, :3] = c
        a[y0:y0 + 14, :, 3] = (200 * fade).astype(np.uint8)
    lay = Image.fromarray(a, "RGBA")
    img.alpha_composite(lay, (0, int(FLOOR - 250 - h)))


# ---------------------------------------------------------------- HUD (top centre)
@lru_cache(None)
def bar_shape(w, h, slant, col, out):
    def dr(d, k):
        d.polygon([(slant * k, 0), (w * k - 1, 0), ((w - slant) * k - 1, h * k - 1), (0, h * k - 1)], fill=out)
        o = 4 * k
        d.polygon([(slant * k + o, o), (w * k - 1 - o, o), ((w - slant) * k - 1 - o, h * k - 1 - o), (o, h * k - 1 - o)],
                  fill=col)
    return _ss(w, h, dr)


def slant_fill(img, x, y, w, h, slant, frac, col):
    if frac <= 0:
        return
    full = bar_shape(w, h, slant, col, col)
    cut = full.crop((0, 0, max(1, int(slant + (w - slant) * frac)), h))
    img.alpha_composite(cut, (x, y))


def draw_hud(img, t):
    st = ST()
    g = t
    _, score, combo, best, hp, misses, gauge = st.state(g)
    x0, y0 = 560, 64
    img.alpha_composite(bar_shape(470, 34, 14, (60, 40, 90), WHITE), (x0, y0))
    frac = max(0.0, hp / 250)
    slant_fill(img, x0 + 6, y0 + 6, 458, 22, 10, frac, PINK if frac > 0.3 else (255, 80, 90))
    put(img, heart_icon(62), x0 - 6, y0 + 16)
    put(img, text_img(f"{hp}", 26, WHITE, (60, 40, 90), 5), x0 + 500, y0 + 17)
    y1 = y0 + 42
    img.alpha_composite(bar_shape(400, 22, 10, (40, 50, 90), WHITE), (x0 + 30, y1))
    fever = st.FEVER_T <= g < st.CLEAR_T + 0.5
    if fever:
        k = (g * 3) % 1
        cols = [(255, 120, 150), (255, 210, 90), (130, 230, 160), (110, 200, 255), (190, 150, 255)]
        for i in range(10):
            slant_fill(img, x0 + 34 + i * 39, y1 + 4, 40, 14, 6, 1.0, cols[(i + int(g * 8)) % 5])
        put(img, text_img("FEVER!", 30, LEMON, PINK_D, 6), x0 + 480, y1 + 11 + 2 * math.sin(g * 12))
    else:
        slant_fill(img, x0 + 34, y1 + 4, 392, 14, 6, gauge, CYAN)
        put(img, text_img("FEVER", 20, WHITE, (40, 50, 90), 4), x0 + 470, y1 + 11)
    # score
    put(img, text_img("SCORE", 22, WHITE, (60, 40, 90), 5), 1160, 72)
    put(img, text_img(f"{score:07d}", 40, LEMON, (60, 40, 90), 6), 1310, 76)
    put(img, text_img(f"MISS {misses}", 22, (255, 140, 150) if misses else WHITE, (60, 40, 90), 5), 1310, 116)
    for a in (47.1, 62.6):                    # the nocount paw wipes the miss counter (as the pixel version)
        if a - 0.45 <= t < a + 0.25:
            put(img, star_icon(40, PINK), 1390 + (t - a) * -100, 116)
    if combo >= 3 and not st.hook_active(t):
        draw_combo(img, combo, g)


@lru_cache(None)
def splat():
    rng = np.random.default_rng(7)

    def dr(d, k):
        c = 120 * k
        d.ellipse([c - 92 * k, c - 70 * k, c + 92 * k, c + 70 * k], fill=(255, 150, 200, 235))
        for i in range(11):
            a = i * 2 * math.pi / 11 + rng.uniform(-0.2, 0.2)
            r = rng.uniform(70, 100) * k
            rr = rng.uniform(12, 22) * k
            x, y = c + r * math.cos(a) * 1.15, c + r * math.sin(a) * 0.8
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(255, 150, 200, 235))
    return _ss(240, 240, dr)


def draw_combo(img, combo, g):
    st = ST()
    last = max([tt for tt, k in st.score_events() if tt <= g and k == "hit"] or [0])
    pop = 1 + 0.25 * max(0.0, 1 - (g - last) / 0.1)
    put(img, splat(), 960, 214, alpha=0.9)
    put(img, text_img(str(combo), 78, LEMON, PINK_D, 9), 960, 200, scale=pop)
    put(img, text_img("COMBO", 26, WHITE, PINK_D, 6), 960, 262)


# ---------------------------------------------------------------- layer
def hit_shake(g):
    """Short vertical shake on each strike (4 frames, 7 px, alternating), inside the play area; the bosses' big
    moments (landing, throws, defeat) shake harder."""
    b = BOSS.shake(g) or BOSS.omen_shake(g)
    if b:
        return b
    st = ST()
    for tt, kind in st.chart():
        a = g - tt
        if kind in ("g", "a") and 0 <= a < 4 / 30:
            return int(round(7 * (1 - a * 30 / 4) * (1 if int(a * 30) % 2 == 0 else -1)))
    return 0


def game_layer(t, hud=True):
    st = ST()
    g = st.game_time(t)
    img = Image.new("RGBA", (OW, OH), (0, 0, 0, 0))
    fever = st.FEVER_T <= g < st.CLEAR_T
    if fever:                                                # Fever backdrop: bands + flickering speed streaks
        sky = Image.new("RGBA", (OW, OH), (0, 0, 0, 0))
        FX.fever_bands(sky, g)
        FX.speed_streaks(sky, g)
        img.alpha_composite(sky.crop((0, 0, OW, FLOOR)), (0, 0))
    if not fever:                                            # speed lines follow the song's energy (all game long)
        n = speed_density(g)
        if n:
            sky = Image.new("RGBA", (OW, OH), (0, 0, 0, 0))
            FX.speed_streaks(sky, g, n=n, y0=150, y1=FLOOR - 40)
            al = np.asarray(sky.getchannel("A")).astype(np.float32) * 0.9
            sky.putalpha(Image.fromarray(al.astype(np.uint8)))
            img.alpha_composite(sky)
    draw_boost(img, g)
    draw_floor(img, st.ground_style_at(g), st.cam_x(g))
    BOSS.draw_atmosphere(img, g)                             # boss: oppressive vignette breathing on the beat
    BOSS.draw_omen(img, g)                                   # climb: the Daruma King looms and throws the saws
    world = Image.new("RGBA", (OW, OH), (0, 0, 0, 0))
    rs = int(g * 30) % 30
    put(world, ring(rs), HIT_X + 40, AIR_Y)
    put(world, ring(rs), HIT_X + 40, GROUND_LANE)
    late, texts = [], []
    draw_world(world, g, late, texts)
    draw_mash(world, g, late, texts)
    BOSS.draw_boss(world, g)                                 # over the enemies it throws, under her
    if any(k == "gear" and abs(g - tt) < 0.24 for tt, k in st.chart()):          # jump smear over a saw
        ghosts = []
        for k in (3, 2, 1):
            sp, feet, cx, fy = avatar(t - k / 30)
            ghosts.append((sp, cx - _anchor(sp) - k * 8, fy - feet))
        FX.dodge_trail(world, ghosts)
    draw_avatar(world, t, fever)
    for f in late:
        f(world)
    for f in texts:
        f(world)
    img.alpha_composite(world, (0, hit_shake(g)))
    if fever and g - st.FEVER_T < 0.6:
        sp, feet, cx, fy = avatar(t)
        FX.radial_burst(img, cx, fy - 140, g - st.FEVER_T)
    if hud:
        draw_hud(img, g)
        BOSS.draw_ui(img, g)
    return img
