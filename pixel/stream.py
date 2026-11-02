"""XIYIN 「余裕だもん」 PV v3: a VTuber stream of a rhythm runner (1920x1080, 30 fps, 0-178.65 s).

Premise (owner, 2026-11-01): XIYIN is a VTuber, not an in-game character. She streams herself playing a
Muse Dash-like runner; the runner is her avatar inside the game (pixel chibi, true side view, facing right and
looking where she runs; HD chibi since 2026-11-02). Opening: her streaming room with the computer; ending: the result screen, her goodbye,
then the PC's shutdown screen.

Layers per frame (back to front):
  room plate (opening / ending) or the game: hazed stage plate + HD game layer (pixel/mdgame.py, 1920x1080:
  floor, judgement rings, stage monster families, saws, pickups, hold ribbon, XIYIN's HD runner from
  pixel/mdrunner.py, hit effects, PERFECT / combo, HP / FEVER / score)
  stream overlay: VTuber cam (on-model HD stickers, one expression per lyric line), chat, LIVE bar,
  key-cap lyrics and hook stamps (pixel, x2), English subtitle (HD).
Game rules follow docs/runner_reference.md: constant scroll, enemies from the right on the beat in the air or
ground lane, punch on ground hits, jump + swipe on air hits then fall back, jump over gears, contact = damage
(HP, combo reset, MISS), pickups, Fever, pause with a 3-2-1 resume, result screen.

usage:
  stream.py preview <t> [<t> ...] --out sheet.png
  stream.py render --out pv.mp4 [--t0 0 --t1 178.65 --jobs 4]
"""
import argparse
import math
import random
import subprocess
import wave
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

import avatar as AV
import vtmotion as VMO
import blocks as B
import mdgame as MG
import scene as S
from stage import lyrics, put_text, text_mask

HERE = Path(__file__).parent
ROOT = HERE.parent
AUDIO = ROOT / "audio" / "t2_optimized_full.mp3"
W, H, OW, OH, FPS = 960, 540, 1920, 1080, 30
DUR = 178.65
BEAT, PH0 = 60 / 136, 0.024
INK, WHITE, NAVY, COBALT, SKY, CORAL, LEMON = B.INK, B.WHITE, B.NAVY, B.COBALT, B.SKY, B.CORAL, B.LEMON
GROUND = 450                     # game: feet line (pixel layer)
RUN_X = 300                      # avatar centre x
HIT_X = RUN_X + 62               # where notes are struck
AIR_Y = 280                      # air-lane note centre
V_G = 210.0                      # ground scroll px/s (matches the run stride)
V_E = 520.0                      # enemies run at her faster than the ground scrolls

GAME_IN, GAME_OUT = 11.9, 154.47  # the game fills the screen between these (monitor push-in / back to the room)
PAUSE = (44.14, 55.17)           # ちょっと待った ... せーの: the VTuber pauses the game
FEVER_T = 124.58                 # 本番 -> Fever for the final chorus
CLEAR_T = 151.9                  # STAGE CLEAR
SHUT_T = 170.4                   # the PC shutdown screen


def beat_t(k):
    return PH0 + k * BEAT


def beat_of(t):
    return (t - PH0) / BEAT


def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


# ---------------------------------------------------------------- time: the game freezes while paused
def game_time(t):
    if PAUSE[0] <= t < PAUSE[1]:
        return PAUSE[0]
    return t


_TS = np.arange(0, DUR + 1, 1 / 600)
_V = np.where((_TS >= PAUSE[0]) & (_TS < PAUSE[1]), 0.0, V_G) * (_TS >= GAME_IN - 0.5)
_X = np.concatenate([[0], np.cumsum((_V[1:] + _V[:-1]) / 2 / 600)])


def cam_x(t):
    return float(np.interp(t, _TS, _X))


# ---------------------------------------------------------------- stages
STAGES = [(GAME_IN, "sky", "roof"), (27.38, "sunset", "street"), (55.61, "pop", "checker"), (68.7, "night", "night"),
          (83.5, "pinkpop", "pink"), (97.6, "twilight", "stone"), (116.55, "climb", "roof"), (125.8, "festival", "wood")]
STAGE_END = [s[0] for s in STAGES[1:]] + [GAME_OUT]
WIPES = [(26.6, 27.9, 0, 1, "diag"), (55.17, 55.95, 1, 2, "center"), (68.3, 69.1, 2, 3, "center"),
         (82.9, 84.0, 3, 4, "diag"), (96.9, 98.2, 4, 5, "diag"), (115.9, 116.9, 5, 6, "up"),
         (125.0, 126.6, 6, 7, "curtain")]


def stage_at(t):
    i = 0
    for k, s in enumerate(STAGES):
        if t >= s[0]:
            i = k
    return i


def stage_plate(i, t):
    name = STAGES[i][1]
    a, b = STAGES[i][0], STAGE_END[i]
    u = min(1, max(0, (game_time(t) - a) / (b - a)))
    if name == "climb":
        return MG.plate_view("climb", 0.5, u)
    return MG.plate_view(name, 0.06 + 0.88 * u)


def game_background(t):
    for t0, t1, i, j, kind in WIPES:
        if t0 <= t < t1:
            p = (t - t0) / (t1 - t0)
            a, b = stage_plate(i, t), stage_plate(j, t)
            if kind == "curtain":
                return S.curtain(a, "curtain_closed", p / 0.4) if p < 0.5 else \
                    S.curtain(b, "curtain_closed", 1 - (p - 0.6) / 0.4)
            return S.wipe(a, b, p, kind)
    return stage_plate(stage_at(t), t)


def ground_style_at(t):
    for t0, t1, i, j, kind in WIPES:
        if t0 <= t < t1 and kind != "curtain":
            p = (t - t0) / (t1 - t0)
            a, b = STAGES[i][2], STAGES[j][2]
            return lambda x, a=a, b=b, p=p, kind=kind: b if bool(S.wipe_reached(kind, p, x * 2 + 30, OH - 90)) else a
    st = STAGES[stage_at(t)][2]
    if 125.0 <= t < 126.6:
        st = "wood" if t >= 125.8 else "roof"
    return lambda x: st


# ---------------------------------------------------------------- the chart (Muse Dash-style)
VERSES = [(13.2, 26.4), (28.2, 41.9), (69.6, 82.5), (84.5, 96.6), (98.3, 115.7)]
CHORUSES = [(56.3, 66.5), (126.9, 146.2)]
STEPS = (116.9, 124.2)           # 震えるつま先で ステップ踏んで: a gear on every beat, she hops them
HOLD = (146.70, 150.90)          # 最後まで 歌いきるよ: a sheet-music hold note
MISS_GEAR, MISS_BIRD = 42.61, 61.01
PATTERNS = [("g", "g", "a", "g"), ("g", "a", "a", "g"), ("a", "g", "g", "a"), ("g", "g", "g", "a")]


@lru_cache(None)
def chart():
    """(t, kind): g ground enemy, a air enemy, gear (jump over), note (pickup), heart, plus the two misses."""
    out = []
    bar = 0
    for a, b in VERSES:
        k0 = math.ceil(beat_of(a))
        k0 += (-k0) % 4
        for k in range(k0, math.floor(beat_of(b)) - 3, 4):
            pat = PATTERNS[bar % len(PATTERNS)]
            for j, kind in enumerate(pat):
                if bar % 4 == 3 and j == 2:
                    kind = "gear"
                out.append((beat_t(k + j), kind))
            if bar % 2 == 0:
                out.append((beat_t(k + 1.5), "note"))
            bar += 1
    for a, b in CHORUSES:
        k0 = math.ceil(beat_of(a))
        k0 += (-k0) % 4
        for k in range(k0, math.floor(beat_of(b)) - 3, 4):
            pat = PATTERNS[bar % len(PATTERNS)]
            for j, kind in enumerate(pat):
                out.append((beat_t(k + j), kind))
            out.append((beat_t(k + 3.5), "g"))                     # an eighth-note pair at each bar's end
            bar += 1
    for k in range(math.ceil(beat_of(STEPS[0])), math.floor(beat_of(STEPS[1])) + 1):
        out.append((beat_t(k), "gear"))
    out = [(t, k) for t, k in out if not (abs(t - MISS_BIRD) < 0.3 or 41.9 < t < 56.0)]
    out += [(MISS_GEAR, "gear_miss"), (MISS_BIRD, "a_miss"), (57.3, "heart")]
    return tuple(sorted(out))


def hits():
    return [c for c in chart() if c[1] in ("g", "a")]


@lru_cache(None)
def score_events():
    """(t, kind) in order: hit / miss / nocount / note / heart."""
    ev = [(t, "hit") for t, k in chart() if k in ("g", "a", "gear")]
    ev += [(t, "miss") for t, k in chart() if k in ("gear_miss", "a_miss")]
    ev += [(t, "note") for t, k in chart() if k == "note"]
    ev += [(t, "heart") for t, k in chart() if k == "heart"]
    ev += [(46.66, "nocount"), (62.6, "nocount")]
    ev += [(HOLD[0] + i * 0.25, "hit") for i in range(int((HOLD[1] - HOLD[0]) / 0.25))]
    return tuple(sorted(ev))


@lru_cache(None)
def _tally():
    """Running state after each event: (t, score, combo, max combo, hp, misses, fever gauge)."""
    score = combo = best = misses = 0
    hp, gauge, saved = 250, 0.0, (0, 250)
    out = []
    for t, kind in score_events():
        mult = 1.5 if t >= FEVER_T else 1.0
        if kind == "hit":
            combo += 1
            best = max(best, combo)
            score += int(200 * mult) + 2 * min(combo, 200)
            gauge = min(1.0, gauge + 1 / 140)
        elif kind == "note":
            score += 200
        elif kind == "heart":
            hp = min(250, hp + 40)
        elif kind == "miss":
            saved = (combo, hp)
            combo, hp, misses = 0, hp - 30, misses + 1
        elif kind == "nocount":                    # her ruling: the miss is scratched out, combo and HP restored
            combo, hp, misses = combo + saved[0], max(hp, saved[1]), max(0, misses - 1)
            best = max(best, combo)
        out.append((t, score, combo, best, hp, misses, gauge))
    return out


def state(t):
    g = game_time(t)
    cur = (0, 0, 0, 0, 250, 0, 0.0)
    for row in _tally():
        if row[0] > g:
            break
        cur = row
    return cur


# ---------------------------------------------------------------- avatar (in-game)
@lru_cache(None)
def air_runs():
    """Consecutive air notes keep her up: (rise_start, fall_end, [times])."""
    a = [t for t, k in chart() if k in ("a", "a_miss")]
    runs, cur = [], []
    for t in a:
        if cur and t - cur[-1] > 0.6:
            runs.append(cur)
            cur = []
        cur.append(t)
    if cur:
        runs.append(cur)
    return tuple((r[0] - 0.14, r[-1] + 0.42, tuple(r)) for r in runs)


def avatar_height(t):
    """Height above the ground: air-lane hops and gear jumps."""
    for a, b, ts in air_runs():
        if a <= t < b:
            up, top = 0.14, 120
            if t < ts[0]:
                return top * ease((t - a) / up)
            if t > ts[-1] + 0.12:
                u = (t - ts[-1] - 0.12) / (b - ts[-1] - 0.12)
                return top * (1 - u * u)
            return top
    for tg, k in chart():
        if k == "gear" and abs(t - tg) < 0.24:
            u = (t - tg + 0.24) / 0.48
            return 105 * 4 * u * (1 - u)          # clears the HD saws (about 150 px) with room to spare
    return 0.0


@lru_cache(None)
def hurt_frame(flash):
    """Hurt: the run master tilted back, flickering between her own colours and a light coral tint (as Muse Dash's
    damage blink; a white tint read as a white blob)."""
    base = AV.run_frame(3)
    im = legs_rot(base, 9)
    if flash:
        a = np.asarray(im).copy()
        m = a[..., 3] > 0
        a[m, :3] = (a[m, :3] * 0.6 + np.array(CORAL) * 0.4).astype(np.uint8)
        im = Image.fromarray(a, "RGBA")
    return AV._register(im, AV.feet_of(base))


def legs_rot(im, deg):
    import legs
    piv = (im.width / 2, AV.feet_of(im) - 4)
    return legs.rot_about(im, piv, deg)


def avatar_sprite(t):
    """(sprite, centre x, feet y) for song time t (the game time freezes during the pause)."""
    g = game_time(t)
    for m in (MISS_GEAR, MISS_BIRD):
        if 0 <= g - m < 0.4:
            return hurt_frame(int(g * 20) % 2), RUN_X - int(14 * math.sin(min(1, (g - m) / 0.4) * math.pi)), \
                GROUND - int(avatar_height(g) * 0.5)
    h = avatar_height(g)
    if g >= HOLD[0] and g < HOLD[1] + 0.2:
        return AV.run_at(g, V_G), RUN_X, GROUND
    for tt, kind in chart():
        if kind == "g" and 0 <= g - tt < 0.13:
            return AV.pose("punch"), RUN_X + 8, GROUND
        if kind == "a" and 0 <= g - tt < 0.15:
            return AV.pose("air"), RUN_X + 6, GROUND - int(h)
    if h > 0.5:
        rising = any(a <= g < ts[0] for a, b, ts in air_runs()) or any(
            k == "gear" and -0.24 < g - tt < 0 for tt, k in chart())
        return AV.jump_frame("up" if rising or h > 60 else "down"), RUN_X, GROUND - int(h)
    return AV.run_at(g, V_G), RUN_X, GROUND


# ---------------------------------------------------------------- game objects
@lru_cache(None)
def enemy(kind):
    return Image.open(HERE / "sprites4" / ("enemy_mouse.png" if kind == "g" else "enemy_bird.png")).convert("RGBA")


@lru_cache(None)
def gear_img(step):
    """A grey saw gear (pixel), rotation step 0-7."""
    r = 22
    a = np.zeros((2 * r + 6, 2 * r + 6, 4), np.uint8)
    c = r + 3
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    ang = np.arctan2(yy - c, xx - c) + step * math.pi / 32
    rad = np.hypot(yy - c, xx - c)
    teeth = (np.cos(ang * 10) > 0.2)
    body = rad <= r - 5
    tooth = (rad <= r) & teeth
    m = body | tooth
    a[m] = (150, 156, 176, 255)
    a[(rad <= r - 9)] = (190, 196, 214, 255)
    a[(rad <= 5)] = (90, 96, 120, 255)
    ring = m & ~ndimage.binary_erosion(m)
    a[ring] = (*INK, 255)
    return Image.fromarray(a, "RGBA")


def burst(img, x, y, age, cols=(LEMON, WHITE, COBALT)):
    d = ImageDraw.Draw(img)
    r = 10 + age * 160
    for k in range(10):
        ang = k * math.pi / 5 + 0.3
        px, py = x + int(r * math.cos(ang)), y + int(r * math.sin(ang))
        s = 3 if age < 0.15 else 2
        d.rectangle([px, py, px + s, py + s], fill=cols[k % len(cols)])


def slash(img, x, y, age, col=WHITE):
    """Paw-swipe arc in front of her on a hit."""
    if age > 0.16:
        return
    d = ImageDraw.Draw(img)
    r = 30 + int(age * 60)
    for k in range(9):
        ang = -1.1 + k * 0.28
        px, py = x + int(r * math.cos(ang)), y + int(r * math.sin(ang))
        d.rectangle([px, py, px + 3, py + 3], fill=col if k % 2 else SKY)


def draw_world_objects(img, g):
    cx_now = cam_x(g if g < PAUSE[0] else g)
    for tt, kind in chart():
        dt = tt - g
        if kind in ("gear", "gear_miss", "note", "heart"):     # fixed to the ground, scroll with it
            if dt < -1.2 or dt > 4.0:
                continue
            x = HIT_X - 30 + (cam_x(tt) - cx_now)
            if kind.startswith("gear"):
                if dt < 0 and kind == "gear_miss" and int(-dt * 14) % 2:
                    continue
                gi = gear_img(int(g * 30) % 8)
                img.alpha_composite(gi, (int(x) - gi.width // 2, GROUND - gi.height + 4))
            elif dt >= 0:
                ic = B.icon("note" if kind == "note" else "heart", 4)
                y = GROUND - 120 if kind == "note" else GROUND - 70
                img.alpha_composite(ic, (int(x) - ic.width // 2, y + int(4 * math.sin(g * 6 + tt))))
            elif dt > -0.3:
                burst(img, int(x), GROUND - 100, -dt, (SKY, WHITE))
        elif kind in ("g", "a", "a_miss"):
            if dt > 1.6 or dt < -0.6:
                continue
            lane = "a" if kind.startswith("a") else "g"
            sp = enemy(lane)
            x = HIT_X + 20 + dt * V_E
            y = (AIR_Y - sp.height // 2) if lane == "a" else (GROUND - sp.height)
            bob = int(3 * math.sin(g * 9 + tt * 3))
            if dt >= 0 or kind == "a_miss":
                if kind == "a_miss" and dt < 0:
                    if int(-dt * 14) % 2:
                        continue
                if x < W + 60:
                    img.alpha_composite(sp, (int(x) - sp.width // 2, y + bob))
            else:                                               # struck: knocked away, burst, judgement
                age = -dt
                kx, ky = int(x + age * 900), int(y - age * 500)
                if age < 0.3 or (age < 0.45 and int(age * 30) % 2 == 0):    # flies off, then flickers out
                    img.alpha_composite(sp, (kx - sp.width // 2, ky))
                burst(img, int(HIT_X + 20), y + sp.height // 2, age)
                if age < 0.35:
                    put_text(img, "PERFECT", "ps", (HIT_X + 20, y - 18 - int(age * 50)), COBALT, outline=WHITE,
                             anchor="mt")
                slash(img, RUN_X + 30, (AIR_Y if lane == "a" else GROUND - 70), age)
    if HOLD[0] - 1.5 <= g < HOLD[1] + 0.3:                      # the hold note: a ribbon she rides along
        x0 = HIT_X + max(0.0, HOLD[0] - g) * V_E
        x1 = HIT_X + max(0.0, HOLD[1] - g) * V_E
        y = GROUND - 60
        d = ImageDraw.Draw(img)
        if x1 > x0:
            d.rectangle([int(x0), y - 6, int(x1), y + 6], fill=SKY, outline=INK)
            d.rectangle([int(x0), y - 2, int(x1), y + 1], fill=WHITE)
        for xx in (x1,):
            img.alpha_composite(B.icon("star", 3), (int(xx) - 13, y - 15))
        if HOLD[0] <= g < HOLD[1]:
            for k in range(4):
                sx = HIT_X - 10 - ((g * 220 + k * 37) % 120)
                img.alpha_composite(B.icon("sparkle", 2), (int(sx), y - 20 + (k * 11) % 30))


def fever_trail(img, t):
    if not FEVER_T <= t < CLEAR_T:
        return
    d = ImageDraw.Draw(img)
    cols = [CORAL, LEMON, (120, 220, 150), SKY, (180, 140, 255)]
    for k, c in enumerate(cols):
        y = GROUND - 150 + k * 10 - int(avatar_height(t))
        d.rectangle([0, y, RUN_X - 40, y + 5], fill=c)


def draw_game_hud(img, t):
    _, score, combo, best, hp, misses, gauge = state(t)
    d = ImageDraw.Draw(img)
    img.alpha_composite(B.icon("heart", 3), (272, 36))
    d.rectangle([298, 38, 500, 50], fill=INK)
    frac = max(0.0, hp / 250)
    col = (120, 220, 130) if frac > 0.5 else (LEMON if frac > 0.25 else CORAL)
    d.rectangle([300, 40, 300 + int(198 * frac), 48], fill=col)
    put_text(img, f"{hp}", "ps", (506, 40), WHITE, outline=INK)
    d.rectangle([298, 54, 500, 59], fill=INK)
    fever = FEVER_T <= t < CLEAR_T + 0.5
    if fever:
        k = int(t * 12) % 5
        for i in range(10):
            d.rectangle([300 + i * 20, 55, 318 + i * 20, 58], fill=[CORAL, LEMON, (120, 220, 150), SKY, (180, 140, 255)][(i + k) % 5])
        put_text(img, "FEVER!", "ps", (506, 54), LEMON, outline=INK)
    else:
        d.rectangle([300, 55, 300 + int(198 * gauge), 58], fill=SKY)
    put_text(img, "SCORE", "ps", (560, 40), WHITE, outline=INK)
    put_text(img, f"{score:07d}", "ps", (612, 40), LEMON, outline=INK)
    put_text(img, f"MISS {misses}", "ps", (612, 54), CORAL if misses else WHITE, outline=INK)
    for a in (47.1, 62.6):
        if a - 0.45 <= t < a + 0.25:
            img.alpha_composite(B.icon("paw", 2), (690 + int((t - a) * -50), 50))
    if combo >= 3 and not hook_active(t):
        put_text(img, str(combo), "ps", (W // 2, 80), WHITE, outline=INK, scale=3, anchor="mt")
        put_text(img, "COMBO", "ps", (W // 2, 106), LEMON, outline=INK, anchor="mt")


def game_layer(t):
    """The game's own picture (pixel layer) at song time t; frozen while paused."""
    g = game_time(t)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    B.draw_ground(img, ground_style_at(g), cam_x(g), GROUND)
    draw_world_objects(img, g)
    fever_trail(img, g)
    sp, cx, feet = avatar_sprite(t)
    d = ImageDraw.Draw(img)
    air = max(0, GROUND - feet)
    w = max(20, 60 - air // 3)
    for i in range(-w // 2, w // 2, 2):                       # dithered contact shadow
        d.rectangle([cx + i + ((i // 2) % 2), GROUND - 2, cx + i + 1, GROUND - 1], fill=(20, 22, 50))
    img.alpha_composite(sp, (int(cx - sp.width // 2), int(feet - AV.feet_of(sp))))
    draw_game_hud(img, g)
    return img


@lru_cache(1)
def frozen_game():
    return MG.game_layer(PAUSE[0] - 1e-3)


# ---------------------------------------------------------------- the VTuber (model v3: vt3.py, motion: vtmotion.py)
# She sings along while she plays: a neutral face with lip-sync on the sung syllables and blinks, plus short
# expression accents on the key words (start, end, expression). Accents switch on a cut with a small pop.
ACCENTS = [
    (4.02, 4.50, "wink"), (7.69, 8.55, "smug"), (9.98, 10.70, "smug"),
    (14.19, 14.95, "smug"), (17.81, 19.30, "happy"), (23.34, 25.00, "smug"),
    (28.31, 29.20, "smug"), (31.78, 32.50, "wink"), (37.28, 38.00, "smug"), (39.06, 41.20, "sing"),
    (42.61, 42.99, "shocked"), (42.99, 44.14, "pain"), (44.14, 46.30, "angry"), (46.30, 47.40, "pout"),
    (49.67, 53.54, "flustered"), (53.54, 54.39, "closed"), (54.39, 55.20, "smug"),
    (55.64, 56.50, "happy"), (58.40, 59.40, "happy"), (59.41, 60.30, "smug"), (61.92, 62.70, "wink"),
    (64.46, 65.30, "smug"), (66.90, 67.54, "angry"), (67.54, 68.70, "happy"),
    (71.52, 72.30, "wink"), (74.90, 75.80, "smug"), (79.50, 82.50, "sing"),
    (84.81, 85.60, "shocked"), (86.38, 87.19, "angry"), (87.19, 89.70, "flustered"),
    (89.90, 90.80, "pout"), (93.46, 94.50, "angry"),
    (98.90, 101.00, "pout"), (103.75, 105.20, "flustered"), (107.48, 109.50, "happy"), (109.70, 111.00, "flustered"),
    (113.01, 114.00, "smug"), (119.32, 120.20, "smug"),
    (123.15, 123.90, "angry"), (124.58, 125.40, "smug"),
    (126.23, 127.00, "happy"), (128.90, 130.00, "happy"), (132.50, 133.30, "happy"),
    (133.29, 134.00, "smug"), (136.68, 137.24, "angry"), (137.24, 138.50, "happy"),
    (142.16, 142.77, "wink"), (142.77, 143.60, "happy"), (145.00, 145.80, "wink"),
    (146.70, 151.00, "sing"), (151.90, 153.50, "happy"),
    (154.47, 155.30, "smug"), (157.40, 158.40, "smug"), (159.33, 160.10, "wink"), (161.98, 162.80, "smug"),
    (166.00, 167.50, "happy")]
BIG_CAM = [(42.61, 54.39), (64.46, 67.9), (98.9, 103.2), (107.48, 109.5), (136.68, 137.3)]
VFACE = (358, 405, 260, 230)       # face box of model v3 (x, y, w, h) in 1024 units


def vt_state(t):
    """(expression, since, eyes closed, mouth) at t."""
    since = 0.0
    for a, b, name in ACCENTS:
        if a <= t < b:
            if name == "closed":                     # 深呼吸: eyes closed, mouth shut
                return "neutral", a, True, None
            return name, a, False, None
        if b <= t:
            since = b
    return "neutral", since, VMO.eyes_closed_at(t), VMO.mouth_at(t)


def vt_pop(t, since):
    """A small pop when the expression changes (cut, never a cross-fade)."""
    u = (t - since) / 0.16
    return 1.0 + 0.018 * math.sin(math.pi * u) if 0 <= u < 1 else 1.0


def vt_image(t, size):
    name, since, closed, mouth = vt_state(t)
    beat = beat_of(t) if GAME_IN - 1 <= t < GAME_OUT and not (PAUSE[0] <= t < PAUSE[1]) else None
    return VMO.render(name, t, size, closed, mouth, beat, vt_pop(t, since))


def draw_vtuber(canvas, t, box, face_frac=0.42, face_y=0.40):
    """Draw her model into the cam box (x0, y0, x1, y1), framed on her face."""
    x0, y0, x1, y1 = box
    fx, fy, fw, fh = VFACE
    s = (face_frac * (x1 - x0)) / fw
    size = max(8, int(1024 * s))
    im = vt_image(t, size)
    s = size / 1024
    px, py = (fx + fw / 2) * s, (fy + fh / 2) * s
    tx, ty = (x0 + x1) / 2, y0 + face_y * (y1 - y0)
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    layer.alpha_composite(im, (int(tx - px), int(ty - py)))
    mask = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(box, radius=26, fill=255)
    layer.putalpha(Image.fromarray(np.minimum(np.asarray(layer)[..., 3], np.asarray(mask)), "L"))
    canvas.alpha_composite(layer)


@lru_cache(None)
def cam_backdrop(w, h):
    """Her room behind her in the cam (the right half of the room plate, softly blurred)."""
    room = S.plate("room").crop((1000, 120, 1920, 1000)).filter(ImageFilter.GaussianBlur(3))
    return room.resize((w, h), Image.Resampling.LANCZOS)


def cam_box(t):
    """Small cam at the top right; it grows to centre stage for the big reactions."""
    small = (1478, 68, 1896, 480)
    big = (930, 96, 1840, 900)
    k = 0.0
    for a, b in BIG_CAM:
        if a - 0.25 <= t < b + 0.25:
            k = max(k, ease((t - a + 0.25) / 0.25) if t < a else (1 - ease((t - b) / 0.25) if t >= b else 1.0))
    return tuple(int(s + (g - s) * k) for s, g in zip(small, big)), k


def draw_cam(hd, t):
    box, k = cam_box(t)
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    d = ImageDraw.Draw(hd)
    d.rounded_rectangle([x0 - 8, y0 - 8, x1 + 8, y1 + 8], radius=32, fill=(255, 255, 255, 255))
    d.rounded_rectangle([x0 - 8, y0 - 8, x1 + 8, y1 + 8], radius=32, outline=(60, 109, 240, 255), width=5)
    for ex in (x0 + 34, x1 - 74):                       # cat-ear frame
        d.polygon([(ex, y0 - 6), (ex + 40, y0 - 6), (ex + 20 + (6 if ex > x0 + 40 else -6), y0 - 46)],
                  fill=(255, 255, 255, 255), outline=(60, 109, 240, 255), width=5)
    hd.paste(cam_backdrop(w, h), (x0, y0), ImageChops_round(w, h))
    draw_vtuber(hd, t, box)
    d.rounded_rectangle([x0 + 14, y1 - 46, x0 + 160, y1 - 12], radius=10, fill=(60, 109, 240, 255))
    d.text((x0 + 87, y1 - 29), "XIYIN", font=ui_font(24), fill=(255, 255, 255), anchor="mm")


@lru_cache(None)
def ImageChops_round(w, h):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=26, fill=255)
    return m


# ---------------------------------------------------------------- stream UI
@lru_cache(None)
def ui_font(size, bold=True):
    f = "MPLUSRounded1c-ExtraBold.ttf" if bold else "MPLUSRounded1c-Bold.ttf"
    return ImageFont.truetype(str(ROOT / "pv" / "fonts" / f), size)


TITLE = "【初見】フルコン余裕だもん！ ちゃんと見ててよね"
CHAT = [(1.2, "みけ", "こんばんは！"), (1.9, "しろ", "待機"), (2.6, "user0927", "きた！"), (3.4, "くろねこ", "かわいい"),
        (5.6, "みけ", "見てるよ"), (8.0, "しろ", "フルコンできる？"), (9.3, "ゆず", "がんばれー"), (11.0, "user0927", "いけ"),
        (15.0, "しろ", "うまい"), (18.0, "くろねこ", "大天才ｗ"), (21.0, "みけ", "準備バッチリ"), (24.0, "ゆず", "完璧"),
        (29.0, "user0927", "ざんねんｗ"), (32.2, "しろ", "余裕で草"), (38.0, "くろねこ", "キメた"), (42.8, "みけ", "えっ"),
        (43.1, "しろ", "あたったｗ"), (43.5, "ゆず", "だいじょうぶ？"), (44.5, "user0927", "ポーズｗｗ"),
        (46.8, "くろねこ", "ノーカン？"), (47.4, "みけ", "それはずるいｗ"), (48.2, "しろ", "ノーカンｗｗ"),
        (49.8, "ゆず", "ニヤニヤ"), (50.1, "user0927", "ｗｗｗ"), (50.4, "くろねこ", "ニヤニヤ"), (50.7, "みけ", "かわいい"),
        (51.0, "しろ", "ｗｗｗｗ"), (53.3, "ゆず", "がんばれー"), (55.9, "user0927", "きた！"), (58.0, "くろねこ", "余裕だ"),
        (61.3, "みけ", "いまミスった？"), (62.7, "しろ", "またノーカンｗ"), (64.8, "ゆず", "わらってないよ"),
        (65.6, "user0927", "ニヤニヤ"), (67.2, "くろねこ", "めっ されたｗ"), (67.9, "みけ", "もういっかい！"),
        (72.0, "しろ", "見てる見てる"), (75.8, "ゆず", "本気だ"), (79.0, "user0927", "いい声"), (85.0, "くろねこ", "スクショした"),
        (85.9, "みけ", "カシャ"), (86.6, "しろ", "きんしｗ"), (90.3, "ゆず", "なまいきｗ"), (99.4, "user0927", "ぷいっｗ"),
        (101.0, "くろねこ", "こっちむいて"), (104.3, "みけ", "あ、目があった"), (107.7, "しろ", "ふきだしたｗ"),
        (108.3, "ゆず", "かわいい"), (110.5, "user0927", "くやしいｗ"), (118.0, "くろねこ", "ステップ"),
        (124.7, "みけ", "ほんばん！"), (125.5, "しろ", "FEVER!!"), (130.2, "ゆず", "みせばｗ"), (137.0, "user0927", "またおこられた"),
        (139.5, "くろねこ", "見てるよ"), (143.2, "みけ", "まきこまれた"), (143.8, "しろ", "ｗｗｗ"), (148.0, "ゆず", "最後まで！"),
        (152.0, "user0927", "フルコン！？"), (152.6, "くろねこ", "888888"), (153.2, "みけ", "おめでとう！"),
        (155.0, "しろ", "余裕だったね"), (157.4, "ゆず", "さすが"), (160.0, "user0927", "ふふん"),
        (164.0, "くろねこ", "また来るね"), (165.2, "みけ", "おつかれ"), (166.4, "しろ", "おやすみー"), (167.6, "ゆず", "おつ〜")]
NAME_COL = {"みけ": (255, 123, 138), "しろ": (60, 109, 240), "user0927": (120, 180, 120), "くろねこ": (150, 110, 220),
            "ゆず": (230, 160, 40)}


def draw_top_bar(hd, t):
    d = ImageDraw.Draw(hd)
    d.rectangle([0, 0, OW, 54], fill=(255, 255, 255, 235))
    d.line([0, 54, OW, 54], fill=(60, 109, 240, 255), width=3)
    live = t < SHUT_T - 0.8
    d.rounded_rectangle([16, 10, 120, 44], radius=10, fill=(255, 90, 110, 255) if live else (150, 156, 176, 255))
    d.text((68, 27), "LIVE" if live else "OFF", font=ui_font(24), fill=(255, 255, 255), anchor="mm")
    d.text((136, 27), TITLE, font=ui_font(26, False), fill=(30, 40, 90), anchor="lm")
    viewers = 1204 + int(t * 9) % 41 + (380 if t > 126 else 0) + int(min(t, 20) * 20)
    sec = int(t) + 61 * 60 + 12
    d.text((OW - 24, 27), f"👁 {viewers:,}   {sec // 3600}:{sec // 60 % 60:02d}:{sec % 60:02d}".replace("👁 ", ""),
           font=ui_font(24, False), fill=(30, 40, 90), anchor="rm")


def draw_chat(hd, t, box=(24, 72, 452, 300)):
    x0, y0, x1, y1 = box
    panel = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel)
    pd.rounded_rectangle([0, 0, x1 - x0 - 1, y1 - y0 - 1], radius=18, fill=(255, 255, 255, 205),
                         outline=(60, 109, 240, 255), width=3)
    pd.text((18, 22), "チャット", font=ui_font(24), fill=(60, 109, 240), anchor="lm")
    msgs = [c for c in CHAT if c[0] <= t][-5:]
    y = y1 - y0 - 18
    for k, (ct, name, text) in enumerate(reversed(msgs)):
        age = t - ct
        slide = int(max(0, 1 - age / 0.2) * 20)
        y -= 40
        if y < 44:
            break
        pd.text((18, y + slide), name, font=ui_font(20), fill=NAME_COL.get(name, (80, 80, 80)), anchor="lm")
        nw = int(ui_font(20).getlength(name))
        pd.text((28 + nw, y + slide), text, font=ui_font(24, False), fill=(30, 40, 90), anchor="lm")
    hd.alpha_composite(panel, (x0, y0))


@lru_cache(None)
def sub_font():
    return ui_font(34, False)


EN = ["Hey, hey - keep your eyes on me, okay?", "Hmph. Okay, here I go.", "Today I'm a total genius.",
      "All prepped and ready - flawless, right?", "Too bad for you - this is easy.",
      "Watch me nail it, nice and smooth.", "Huh? Ow, ow, ow - wait a sec!", "That one doesn't count.",
      "Ugh, stop grinning at me!", "My cheeks are burning... deep breath... and go!", "It's easy - see? So easy.",
      "Hmph. That one was a no-count.", "You laughed, didn't you? No! One more time.",
      "Don't look away - keep watching.", "Even my bluffing is for real.", "I'll nail it with this voice.",
      "No screenshots - forget you saw that.", "Don't you dare call me cheeky.", "Even if I turn away with a huff...",
      "one look at you and I crack up.", "I won't end it on a sore note.", "Being a goody-two-shoes is boring, right?",
      "Taking steps on trembling toes,", "don't laugh - the real show starts now!", "It's easy - even easier now.",
      "The best part comes after the fall.", "You laughed, didn't you? No! One more time.",
      "Don't look away - keep watching.", "I'll pull you in too, laughing and all.", "I'll sing it all the way to the end.",
      "See? Told you it was easy.", "Heh, probably. Come back again, okay?"]


def current_line(t):
    cur, idx = None, -1
    for i, ln in enumerate(lyrics()):
        if ln["start"] - 0.3 <= t < ln["end"] + 0.5:
            cur, idx = ln, i
    return cur, idx


def draw_subtitle(hd, t):
    ln, i = current_line(t)
    if not ln:
        return
    ImageDraw.Draw(hd).text((OW // 2, 1050), EN[i], font=sub_font(), fill=(255, 255, 255), anchor="ms",
                            stroke_width=5, stroke_fill=(20, 26, 70))


def draw_keycaps(img, t, y=470):
    ln, _ = current_line(t)
    if not ln:
        return
    chars = []
    for ph in ln["phrases"]:
        chars += list(zip(ph["text"], ph["chars"]))
        chars.append((" ", None))
    caps = [(B.keycap(ch, t >= ct) if ct is not None else None, ct) for ch, ct in chars[:-1]]
    total = sum((c.width + 2) if c else 10 for c, _ in caps)
    x = W // 2 - total // 2
    for i, (c, ct) in enumerate(caps):
        if c is None:
            x += 10
            continue
        da = t - (ln["start"] - 0.3) - i * 0.02
        if da >= 0:
            yy = y - int(10 * max(0, 1 - da / 0.15)) + (2 if ct is not None and 0 <= t - ct < 0.1 else 0)
            img.alpha_composite(c, (x, yy))
        x += c.width + 2


HOOKS = [  # stream stamp words: (t_land, text, style, tile, cx, cy, leave)
    (46.66, "ノーカン", "cobalt", 3, 240, 250, 49.4), (55.64, "余裕だもん", "coral", 4, 470, 180, 57.25),
    (57.43, "余裕だもん", "gold", 4, 470, 180, 59.3), (61.92, "ノーカン", "cobalt", 4, 470, 180, 63.8),
    (124.58, "本番", "gold", 6, 470, 190, 125.6), (126.23, "余裕だもん", "white", 4, 470, 180, 128.2),
    (128.46, "余裕だもん", "gold", 4, 470, 180, 129.8), (156.66, "余裕でしょ", "cobalt", 3, 450, 78, 159.2),
    (163.32, "また来てよね", "cobalt", 3, 450, 78, 169.5)]   # room scenes: small, clear of the chat and her face


def hook_active(t):
    return any(a - 0.6 <= t < l + 0.8 for a, _, _, _, _, _, l in HOOKS)


def draw_hooks(img, t):
    for a, text, style, tile, cx, cy, leave in HOOKS:
        if a - 0.6 <= t < leave + 0.8:
            B.draw_word(img, text, cx, cy, tile, style, t, a, seed=int(a * 10), leave=(leave, 0.8))


def menu(img, x0, y0, title, items, sel, t, blink_from):
    d = ImageDraw.Draw(img)
    w, h = 240, 40 + 28 * len(items)
    d.rectangle([x0, y0, x0 + w, y0 + h], fill=INK, outline=WHITE, width=3)
    put_text(img, title, "ps", (x0 + 14, y0 + 12), LEMON, scale=2)
    for i, it in enumerate(items):
        on = i == sel
        if on and t >= blink_from and int(t * 12) % 2:
            continue
        put_text(img, ("▶ " if on else "  ") + it, "jp", (x0 + 14, y0 + 42 + 28 * i), LEMON if on else WHITE)


def draw_pause_ui(img, t):
    d = ImageDraw.Draw(img)
    if PAUSE[0] <= t < 54.39:
        put_text(img, "II PAUSE", "ps", (240, 160), WHITE, outline=INK, scale=3, anchor="mt")
    if PAUSE[0] + 0.3 <= t < 46.66:
        sel = 0 if t < 45.6 else (1 if t < 46.0 else 2)
        menu(img, 120, 196, "PAUSE", ["つづける", "やりなおす", "ノーカンにする"], sel, t, 46.2)
    for k, ct in enumerate((54.39, 54.56, 54.73)):
        if ct <= t < ct + 0.17 + (0.44 if k == 2 else 0):
            put_text(img, str(3 - k), "ps", (240, 230), WHITE, outline=INK, scale=6, anchor="mt")
    if 55.17 <= t < 55.7:
        put_text(img, "GO!", "ps", (480, 230), LEMON, outline=INK, scale=6, anchor="mt")
    if 67.95 <= t < 69.4:                       # after the big cam has shrunk back (it ends at 67.9)
        put_text(img, "STAGE 2", "ps", (470, 200), WHITE, outline=INK, scale=4, anchor="mt")
        put_text(img, "もういっかい！", "jp", (470, 240), LEMON, outline=INK, scale=2, anchor="mt")
    if 124.7 <= t < 126.4:
        put_text(img, "FEVER TIME!", "ps", (470, 270), LEMON, outline=INK, scale=3, anchor="mt")


NARRATION = [(44.3, 45.95, "＊ XIYINは ポーズボタンを おした。"), (47.3, 49.4, "＊ いまのは ノーカン らしい。"),
             (62.6, 63.9, "＊ また ノーカン らしい。")]
TYPE_CPS = 16


def draw_narration(img, t):
    for a, b, text in NARRATION:
        if a <= t < b:
            txt = text[:max(0, int((t - a) * TYPE_CPS))]
            d = ImageDraw.Draw(img)
            d.rectangle([24, 372, 456, 428], fill=(0, 0, 0), outline=WHITE, width=3)
            if txt:
                put_text(img, txt, "jp", (36, 384), WHITE, scale=2)


# ---------------------------------------------------------------- results screen
def draw_results(hd, t):
    """Result screen of the game (part of the game picture, under the stream overlay): Muse Dash-style portrait on
    the left, an opaque score panel in the middle, clear of the cam box at the top right."""
    u = ease((t - CLEAR_T - 0.4) / 0.5)
    if u <= 0:
        return
    _, score, combo, best, hp, misses, gauge = state(CLEAR_T)
    panel = Image.new("RGBA", (OW, OH), (0, 0, 0, 0))
    d = ImageDraw.Draw(panel)
    d.rectangle([0, 0, OW, OH], fill=(20, 26, 70, int(205 * u)))
    pw = 700
    x = int(OW + 40 - (OW + 40 - 740) * u)
    d.rounded_rectangle([x, 150, x + pw, 900], radius=30, fill=(255, 255, 255, 255), outline=(60, 109, 240, 255),
                        width=6)
    d.text((x + pw // 2, 220), "STAGE CLEAR", font=ui_font(64), fill=(60, 109, 240), anchor="mm")
    rows = [("SCORE", f"{score:07d}"), ("MAX COMBO", str(best)), ("PERFECT", str(len(hits()) + 40)),
            ("MISS", "0"), ("ノーカン", "×2")]
    for i, (k, v) in enumerate(rows):
        if t >= CLEAR_T + 0.9 + i * 0.18:
            y = 330 + i * 84
            d.text((x + 50, y), k, font=ui_font(40), fill=(30, 40, 90), anchor="lm")
            d.text((x + pw - 50, y), v, font=ui_font(46), fill=(255, 90, 110) if k == "ノーカン" else (30, 40, 90),
                   anchor="rm")
    if t >= CLEAR_T + 1.9:
        k = min(1.0, (t - CLEAR_T - 1.9) / 0.15)
        d.text((x + pw - 110, 800), "S", font=ui_font(int(140 + 60 * (1 - k))), fill=(255, 196, 40), anchor="mm",
               stroke_width=6, stroke_fill=(120, 60, 20))
    hd.alpha_composite(panel)
    if t >= CLEAR_T + 0.6:                                  # the Muse portrait, as on Muse Dash's result screen
        v = ease((t - CLEAR_T - 0.6) / 0.4)
        im = VMO.render("happy", t, 900)
        hd.alpha_composite(im, (int(-620 + 560 * v), OH - im.height + 60))


# ---------------------------------------------------------------- the room and the shutdown screen
MON = (476, 300, 926, 533)       # the monitor screen on the room plate


def room_frame(t, monitor_img, vt_visible=True, push=0.0):
    """Her room; monitor_img is shown on the monitor; push (0-1) zooms the view into the monitor."""
    room = S.plate("room").copy()
    if monitor_img is not None:
        mw, mh = MON[2] - MON[0], MON[3] - MON[1]
        shot = monitor_img.resize((mw, int(mw * 9 / 16)), Image.Resampling.LANCZOS)
        top = (shot.height - mh) // 2
        room.paste(shot.crop((0, top, mw, top + mh)), MON[:2])
        glare = Image.new("RGBA", (mw, mh), (255, 255, 255, 0))
        ImageDraw.Draw(glare).polygon([(mw * 0.55, 0), (mw * 0.75, 0), (mw * 0.45, mh), (mw * 0.25, mh)],
                                      fill=(255, 255, 255, 26))
        room.alpha_composite(glare, MON[:2])
    if vt_visible:                                   # her model, waist up, in front of her chair; while the view
        im = vt_image(t, 960)                        # pushes into the monitor she slides out to the right
        slide = int(760 * ease(push)) if push > 0 else 0
        room.alpha_composite(im, (1390 - im.width // 2 + slide, OH - im.height + 70))
    if push > 0:
        e = ease(push)
        x0 = MON[0] * e
        y0 = MON[1] * e
        x1 = OW + (MON[2] - OW) * e
        y1 = y0 + (x1 - x0) * 9 / 16
        room = room.crop((int(x0), int(y0), int(x1), int(y1))).resize((OW, OH), Image.Resampling.LANCZOS)
    return room


@lru_cache(None)
def title_screen():
    """The game's title screen (as shown on her monitor before she starts)."""
    hd = S.plate_view("sky", 0.06).copy()
    px = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    B.draw_ground(px, lambda x: "roof", 0, GROUND)
    B.draw_word(px, "PAW DASH!", W // 2, 170, 7, "white", 10, 0)
    put_text(px, "~ RHYTHM RUNNER ~", "ps", (W // 2, 250), COBALT, outline=WHITE, scale=2, anchor="mt")
    sp = AV.run_frame(0)
    px.alpha_composite(sp, (RUN_X - sp.width // 2, GROUND - AV.feet_of(sp)))
    hd.alpha_composite(px.resize((OW, OH), Image.Resampling.NEAREST))
    return hd


def title_frame(t):
    hd = title_screen().copy()
    if int(t * 2) % 2 == 0 or t > 9.98:
        px = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        put_text(px, "PRESS START" if t < 9.98 else "START!", "ps", (W // 2, 330), LEMON if t > 9.98 else WHITE,
                 outline=INK, scale=3, anchor="mt")
        hd.alpha_composite(px.resize((OW, OH), Image.Resampling.NEAREST))
    return hd


@lru_cache(None)
def desktop():
    """Her PC desktop (pastel, paw pattern) - an original look, no real OS branding."""
    a = np.zeros((OH, OW, 3), np.uint8)
    yy = np.linspace(0, 1, OH)[:, None]
    a[:] = (np.array([200, 222, 255]) * (1 - yy) + np.array([255, 220, 236]) * yy)[:, None, :].astype(np.uint8)[:, 0][:, None]
    im = Image.fromarray(a).convert("RGBA")
    paw = B.icon("paw", 6)
    for y in range(40, OH, 180):
        for x in range((y // 180) % 2 * 90 + 40, OW, 180):
            p = paw.copy()
            p.putalpha(Image.fromarray((np.asarray(p)[..., 3] * 0.18).astype(np.uint8)))
            im.alpha_composite(p, (x, y))
    return im


def shutdown_frame(t):
    u = t - SHUT_T
    hd = desktop().copy()
    d = ImageDraw.Draw(hd)
    veil = int(min(1.0, u / 0.6) * 150)
    hd.alpha_composite(Image.new("RGBA", (OW, OH), (20, 26, 70, veil)))
    cat = B.icon("cat", 18)
    hd.alpha_composite(cat, (OW // 2 - cat.width // 2, 300))
    d = ImageDraw.Draw(hd)
    msg = "シャットダウンしています…" if u < 3.6 else "おつかれさまでした"
    d.text((OW // 2, 600), msg, font=ui_font(54), fill=(255, 255, 255), anchor="mm")
    if u < 3.6:
        for k in range(8):
            ang = -math.pi / 2 + k * math.pi / 4 + u * 4.5
            r = 6 + (k * 2) % 9
            cx, cy = OW // 2 + int(44 * math.cos(ang)), 720 + int(44 * math.sin(ang))
            d.ellipse([cx - r // 2 - 3, cy - r // 2 - 3, cx + r // 2 + 3, cy + r // 2 + 3], fill=(255, 255, 255, 255))
    else:
        d.text((OW // 2, 690), "また来てね", font=ui_font(36, False), fill=(220, 230, 255), anchor="mm")
    d.text((OW // 2, 1010), "XIYIN-PC", font=ui_font(24, False), fill=(200, 210, 240), anchor="mm")
    off = u - 5.2                                             # the screen turns off
    if off > 0:
        k = min(1.0, off / 0.5)
        black = Image.new("RGBA", (OW, OH), (0, 0, 0, 255))
        h = max(2, int(OH * (1 - k) ** 2))
        if k < 1:
            box = (0, (OH - h) // 2, OW, (OH + h) // 2)
            black.paste(hd.crop(box), box[:2])
        hd = black
    return hd


# ---------------------------------------------------------------- frame
def game_frame(t):
    """The game picture (HD): hazed stage plate + the HD game layer (pixel/mdgame.py)."""
    hd = game_background(game_time(t)).copy()
    layer = frozen_game() if PAUSE[0] <= t < PAUSE[1] else MG.game_layer(t)
    fade = 1 - ease((t - CLEAR_T - 0.4) / 0.5)          # the result screen replaces the game
    if fade < 1:
        a = np.asarray(layer).copy()
        a[..., 3] = (a[..., 3] * max(0.0, fade)).astype(np.uint8)
        layer = Image.fromarray(a, "RGBA")
    hd.alpha_composite(layer)
    return hd


def stream_overlay(hd, t, game=True):
    px = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if game:
        if PAUSE[0] <= t < PAUSE[1]:
            hd = S.dim(hd, 0.45)
        draw_hooks(px, t)
        draw_pause_ui(px, t)
        draw_narration(px, t)
    else:
        draw_hooks(px, t)
    draw_keycaps(px, t, 470 if game else 476)
    hd.alpha_composite(px.resize((OW, OH), Image.Resampling.NEAREST))
    big = cam_box(t)[1]
    if game and big > 0:
        hd.alpha_composite(Image.new("RGBA", (OW, OH), (20, 26, 70, int(110 * big))))
    draw_top_bar(hd, t)
    if t < SHUT_T - 0.8:
        draw_chat(hd, t)
    if game:
        draw_cam(hd, t)
    draw_subtitle(hd, t)
    return hd


def compose(t):
    if t >= SHUT_T:
        return shutdown_frame(t)
    if t < GAME_IN:                                   # opening: her room; she starts the game
        push = max(0.0, (t - 10.6) / (GAME_IN - 10.6))
        hd = room_frame(t, title_frame(t), push=push)
        if t < 0.8:
            hd = Image.blend(Image.new("RGBA", (OW, OH), (0, 0, 0, 255)), hd, max(0.0, t / 0.8))
        return stream_overlay(hd, t, game=False) if push < 0.6 else hd
    if t < GAME_OUT:
        hd = game_frame(t)
        if t >= CLEAR_T:
            draw_results(hd, t)
        return stream_overlay(hd, t, game=True)
    pull = max(0.0, 1 - (t - GAME_OUT) / 0.9)          # back out of the monitor to her room
    mon = game_frame(min(t, GAME_OUT - 0.04))
    draw_results(mon, GAME_OUT - 0.04)
    if t > 169.9:
        mon = Image.blend(mon, desktop(), min(1.0, (t - 169.9) / 0.3))
    push_in = max(0.0, (t - 169.6) / (SHUT_T - 169.6))
    hd = room_frame(t, mon, push=max(pull, push_in))
    return stream_overlay(hd, t, game=False) if pull < 0.4 and push_in < 0.4 else hd


def frame(t):
    return compose(t).convert("RGB")


# ---------------------------------------------------------------- audio and render
def blips_wav(t0, t1, path, sr=48000):
    n = int((t1 - t0) * sr)
    out = np.zeros(n, np.float32)
    for a, b, text in NARRATION:
        for i, ch in enumerate(text):
            ct = a + (i + 1) / TYPE_CPS
            if ch.strip("　 ") and t0 <= ct < t1 and ct < b:
                k = int((ct - t0) * sr)
                L = int(0.03 * sr)
                tt = np.arange(L) / sr
                w = np.sign(np.sin(2 * np.pi * 700 * tt)) * np.exp(-tt * 60) * 0.10
                out[k:k + L] += w[:max(0, min(L, n - k))]
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes((np.clip(out, -1, 1) * 32767).astype(np.int16).tobytes())


def render_segment(args):
    f0, f1, out = args
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}",
           "-framerate", str(FPS), "-i", "-", "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
           "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-tune", "animation", "-g", "60",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(f0, f1):
        p.stdin.write(frame(i / FPS).tobytes())
    p.stdin.close()
    p.wait()
    return out


def render(t0, t1, out, jobs):
    out = Path(out)
    f0, f1 = round(t0 * FPS), round(t1 * FPS)
    n = f1 - f0
    cuts = [f0 + n * k // jobs for k in range(jobs + 1)]
    segs = [(cuts[k], cuts[k + 1], out.with_name(f"{out.stem}.part{k}.mp4")) for k in range(jobs)]
    with Pool(jobs) as pool:
        pool.map(render_segment, segs)
    lst = out.with_suffix(".txt")
    lst.write_text("".join(f"file '{s[2].name}'\n" for s in segs))
    video = out.with_name(f"{out.stem}.video.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                    str(video)], check=True)
    blips = out.with_suffix(".blips.wav")
    blips_wav(t0, t1, blips)
    dur = t1 - t0
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-ss", f"{t0:.3f}", "-t", f"{dur:.3f}",
                    "-i", str(AUDIO), "-i", str(blips), "-filter_complex",
                    f"[1:a]afade=t=in:d=0.05,afade=t=out:st={max(0, dur - 1.2):.3f}:d=1.2[s];"
                    "[s][2:a]amix=inputs=2:normalize=0,alimiter=limit=0.8:level=false[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
                    "-movflags", "+faststart", str(out)], check=True)
    for s in segs:
        s[2].unlink()
    for f in (lst, video, blips):
        f.unlink()
    print(out, n, "frames")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    pv = sub.add_parser("preview")
    pv.add_argument("times", type=float, nargs="+")
    pv.add_argument("--out", required=True)
    pv.add_argument("--cols", type=int, default=3)
    rd = sub.add_parser("render")
    rd.add_argument("--t0", type=float, default=0.0)
    rd.add_argument("--t1", type=float, default=DUR)
    rd.add_argument("--out", required=True)
    rd.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    if a.cmd == "preview":
        tiles = [frame(t).resize((OW // 2, OH // 2), Image.Resampling.LANCZOS) for t in a.times]
        cols = a.cols
        rows = (len(tiles) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * OW // 2, rows * (OH // 2 + 18)), (0, 0, 0))
        dd = ImageDraw.Draw(sheet)
        for k, (t, tile) in enumerate(zip(a.times, tiles)):
            x, y = (k % cols) * OW // 2, (k // cols) * (OH // 2 + 18)
            sheet.paste(tile, (x, y + 18))
            dd.text((x + 4, y + 2), f"t={t:.2f}", fill=(255, 220, 80))
        sheet.save(a.out)
    else:
        render(a.t0, a.t1, a.out, a.jobs)


if __name__ == "__main__":
    main()
