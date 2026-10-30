"""XIYIN 「余裕だもん」 - full PV renderer (0-178.65 s, 1920x1080, 30 fps).

Two layers per frame:
  HD layer (1920x1080)  - 2D anime background plates and lyric-prop stickers drawn with NovelAI V5 (scene.py),
                          English subtitles, flashes.
  pixel layer (960x540) - the game: ground tiles, block-word lyrics, coins and targets, XIYIN's pixel sprite,
                          HUD, key-cap lyric row, chat, narration. Shown at x2 with nearest-neighbour.
Every frame is a pure function of the song time t (nothing random at render time), so segments render in parallel.

usage:
  pv.py preview <t> [<t> ...] --out sheet.png
  pv.py render --out pv.mp4 [--t0 0 --t1 178.65 --jobs 4]
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
from PIL import Image, ImageDraw, ImageFont

import anim
import blocks as B
import scene as S
from stage import lyrics, put_text, text_mask, font

HERE = Path(__file__).parent
ROOT = HERE.parent
AUDIO = ROOT / "audio" / "t2_optimized_full.mp3"
W, H, OW, OH, FPS = 960, 540, 1920, 1080, 30
DUR = 178.65
BEAT, PH0 = 60 / 136, 0.024                    # beat grid measured from the onset envelope (no drift)
GROUND = 450
RUN_X = 250                                    # XIYIN's centre while running (pixel-layer x)
INK, WHITE, NAVY, COBALT, SKY = B.INK, B.WHITE, B.NAVY, B.COBALT, B.SKY
CORAL, LEMON = B.CORAL, B.LEMON


def beat_t(k):
    return PH0 + k * BEAT


def beat_of(t):
    return (t - PH0) / BEAT


# ---------------------------------------------------------------- camera
SPEED_KEYS = [(0, 0), (11.9, 0), (12.9, 150), (27.0, 150), (28.0, 180), (42.3, 180), (42.61, 0), (54.73, 0),
              (55.6, 240), (64.2, 240), (64.8, 30), (68.3, 30), (69.3, 150), (83.0, 150), (84.0, 170), (98.3, 170),
              (99.2, 20), (109.2, 20), (110.2, 150), (116.2, 150), (116.55, 136), (125.2, 136), (125.6, 0),
              (126.0, 0), (126.8, 240), (150.4, 240), (152.2, 0), (DUR + 1, 0)]
_KT = np.array([k[0] for k in SPEED_KEYS])
_KV = np.array([k[1] for k in SPEED_KEYS], float)
_TS = np.arange(0, DUR + 1, 1 / 600)
_V = np.interp(_TS, _KT, _KV)
_X = np.concatenate([[0], np.cumsum((_V[1:] + _V[:-1]) / 2 / 600)])


def cam_x(t):
    return float(np.interp(t, _TS, _X))


def speed(t):
    return float(np.interp(t, _KT, _KV))


# ---------------------------------------------------------------- sections and plates
SECTIONS = [  # start, plate key, ground style, rim colour for the sprite on dark plates
    (0.0, "title", "stage", None), (12.38, "sky", "roof", None), (27.38, "sunset", "street", None),
    (42.61, "gag", "street", (255, 255, 255)), (55.61, "pop", "checker", None),
    (68.8, "night", "night", (200, 220, 255)), (83.5, "pinkpop", "pink", None),
    (97.6, "twilight", "stone", None), (116.55, "climb", "roof", (255, 236, 200)),
    (125.8, "festival", "wood", (255, 226, 180)), (153.6, "dawn", "dawn", None)]
SEC_END = [s[0] for s in SECTIONS[1:]] + [DUR]
TRANS = [  # t0, t1, from section index, to section index, kind
    (10.6, 12.38, 0, 1, "diag"), (26.6, 27.9, 1, 2, "diag"), (54.73, 55.61, 3, 4, "center"),
    (68.3, 69.3, 4, 5, "center"), (82.9, 84.0, 5, 6, "diag"), (96.9, 98.2, 6, 7, "diag"),
    (115.9, 116.9, 7, 8, "up"), (125.0, 126.6, 8, 9, "curtain"), (152.6, 154.2, 9, 10, "diag")]


def section_at(t):
    i = 0
    for k, s in enumerate(SECTIONS):
        if t >= s[0]:
            i = k
    return i


def sec_u(i, t):
    a, b = SECTIONS[i][0], SEC_END[i]
    return (t - a) / (b - a)


def plate_of(i, t):
    """The section's HD background at time t (also used outside its time range during transitions)."""
    key = SECTIONS[i][1]
    u = min(1, max(0, sec_u(i, t)))
    if key == "title":
        if t < 4.02:
            return S.plate_view("curtain_closed", 0.5)
        return S.curtain(S.plate_view("curtain_open", 0.5), "curtain_closed", 1 - (t - 4.02) / 0.9)
    if key == "gag":
        if t < 52.0:
            return S.plate_view("shock", 0.5 + 0.02 * math.sin(t * 40) * (t < 42.9))
        return S.dither_mix(S.plate_view("shock", 0.5), S.plate_view("blush", (t - 52) / 4), (t - 52.0) / 0.6)
    if key == "climb":
        return S.plate_view("climb", 0.5, climb_lift(t) / CLIMB_TOTAL)
    if key == "festival":
        return S.plate_view("festival", 0.1 + 0.8 * u)
    if key == "dawn":
        return S.plate_view("dawn", 0.15 + 0.5 * min(1, u * 1.6))
    return S.plate_view(key, 0.08 + 0.84 * u)


def flip_progress(tr, t):
    t0, t1 = tr[0], tr[1]
    return min(1, max(0, (t - t0) / (t1 - t0)))


def background(t):
    for tr in TRANS:
        if tr[0] <= t < tr[1]:
            a, b = plate_of(tr[2], t), plate_of(tr[3], t)
            p = flip_progress(tr, t)
            if tr[4] == "curtain":                       # close (0-0.4), hold, open (0.6-1)
                if p < 0.5:
                    return S.curtain(a, "curtain_closed", p / 0.4)
                return S.curtain(b, "curtain_closed", 1 - (p - 0.6) / 0.4)
            return S.tile_flip(a, b, p, direction={"up": "diag"}.get(tr[4], tr[4]))
    return plate_of(section_at(t), t)


def ground_style_at(t):
    """Per-screen-column ground style (switches in step with the plate flip)."""
    for tr in TRANS:
        if tr[0] <= t < tr[1] and tr[4] != "curtain":
            a, b = SECTIONS[tr[2]][2], SECTIONS[tr[3]][2]
            p = flip_progress(tr, t)
            cols, rows = OW // 120, OH // 120

            def f(x, a=a, b=b, p=p, kind=tr[4]):
                c, r = min(cols - 1, max(0, (x * 2) // 120)), rows - 1
                if kind == "center":
                    order = math.hypot(c - cols / 2 + 0.5, (r - rows / 2 + 0.5) * 1.6) / math.hypot(cols / 2, rows * 0.8)
                else:
                    order = (c + r * 0.6) / (cols + rows * 0.6)
                return b if (p - order * 0.45) / 0.55 >= 0.5 else a
            return f
    st = SECTIONS[section_at(t)][2]
    if 125.0 <= t < 126.6:
        st = "wood" if t >= 125.8 else "roof"
    return lambda x: st


# ---------------------------------------------------------------- the climb (block stairs, one step per beat)
CLIMB_B0 = round(beat_of(116.55))               # first step beat
CLIMB_N = round(beat_of(125.2)) - CLIMB_B0       # number of steps
STEP_H = 30
CLIMB_TOTAL = CLIMB_N * STEP_H


def climb_lift(t):
    """XIYIN's height above the ground during the climb (hops one step per beat)."""
    if t < 116.55 or t >= 125.8:
        return 0.0
    k = beat_of(t) - CLIMB_B0
    if k >= CLIMB_N:
        return float(CLIMB_TOTAL)
    i, f = int(k), k - int(k)
    hop = 4 * f * (1 - f) * 34
    return i * STEP_H + min(1, f * 1.6) * STEP_H + hop


def cam_lift(t):
    """Camera follows the climb smoothly (lagging slightly)."""
    if t < 116.55 or t >= 125.8:
        return 0.0
    return climb_lift(t - 0.12)


# ---------------------------------------------------------------- lyrics, words, subtitles
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

# (t_land, text, style, tile, cx, cy, anchored to the world, scatter time or None)
WORDS = [
    (1.4, "余裕だもん", "white", 6, 480, 175, False, 3.9),
    (4.02, "ねえねえ", "cobalt", 3, 700, 250, False, 6.9),
    (9.98, "いくよ!", "coral", 4, 480, 170, False, 11.2),
    (17.81, "大天才", "gold", 5, 600, 185, True, None),
    (23.34, "完璧", "cobalt", 6, 620, 180, True, None),
    (31.78, "余裕", "cobalt", 6, 620, 180, True, None),
    (37.28, "キメ", "lemon", 6, 640, 185, True, None),
    (42.61, "えっ", "lemon", 4, 470, 210, False, 43.7),
    (46.66, "ノーカン", "cobalt", 5, 500, 175, False, 49.4),
    (54.39, "せーの", "coral", 4, 480, 190, False, 55.1),
    (55.64, "余裕だもん", "coral", 5, 600, 160, True, 57.0),
    (57.43, "余裕だもん", "gold", 5, 600, 170, True, None),
    (61.92, "ノーカン", "cobalt", 5, 620, 175, True, 64.3),
    (71.52, "見ててよね", "white", 4, 620, 180, True, None),
    (75.66, "本気", "gold", 6, 620, 175, True, None),
    (78.38, "この声", "cyan", 5, 600, 170, True, 81.2),
    (79.7, "キメ!", "lemon", 4, 760, 290, True, 82.4),
    (86.38, "禁止", "navy", 6, 520, 180, False, 87.6),
    (89.9, "なまいき", "cobalt", 5, 620, 180, True, None),
    (93.46, "言わせない", "navy", 4, 640, 185, True, None),
    (99.38, "ぷいっ", "pink", 5, 560, 190, False, 102.8),
    (107.48, "ぷふっ", "lemon", 5, 560, 190, False, 109.6),
    (109.7, "悔しい", "coral", 5, 640, 180, True, None),
    (113.48, "つまんない", "navy", 4, 660, 185, True, 115.7),
    (124.58, "本番", "gold", 7, 560, 170, False, 125.35),
    (126.23, "余裕だもん", "white", 5, 600, 160, True, 127.25),
    (127.38, "もっと", "lemon", 4, 700, 290, True, None),
    (128.46, "余裕だもん", "gold", 5, 600, 165, True, None),
    (132.34, "見せ場", "coral", 6, 620, 175, True, None),
    (142.16, "見ててよね", "white", 4, 620, 175, True, None),
    (144.7, "きみも", "cyan", 6, 640, 175, True, None),
    (146.7, "最後まで", "gold", 5, 640, 175, True, None),
    (156.66, "余裕でしょ", "white", 5, 480, 150, False, 159.2),
    (163.32, "また来てよね", "cobalt", 5, 480, 150, False, 169.9),
]


@lru_cache(None)
def word_plan():
    """Anchored words scatter before the next word lands if they are still on screen."""
    out = []
    for i, w in enumerate(WORDS):
        t_land, text, style, tile, cx, cy, anchored, leave = w
        if anchored and leave is None:
            nxt = next((v for v in WORDS[i + 1:] if v[0] - t_land < 8), None)
            if nxt:
                leave = nxt[0] - 0.7
            else:
                leave = t_land + 4.5
        out.append((t_land, text, style, tile, cx, cy, anchored, leave))
    return out


def word_x(w, t):
    t_land, _, _, _, cx, _, anchored, _ = w
    return cx - (cam_x(t) - cam_x(t_land)) if anchored else cx


def draw_words(img, t):
    for w in word_plan():
        t_land, text, style, tile, cx, cy, anchored, leave = w
        if t < t_land - 0.6 or (leave is not None and t > leave + 0.8):
            continue
        x = word_x(w, t)
        if x < -500 or x > W + 500:
            continue
        B.draw_word(img, text, int(x), cy + int(cam_lift(t)) * 0, tile, style, t, t_land,
                    seed=int(t_land * 100), leave=(leave, 0.8) if leave else None)


def current_line(t):
    cur, idx = None, -1
    for i, ln in enumerate(lyrics()):
        if ln["start"] - 0.3 <= t < ln["end"] + 0.5:
            cur, idx = ln, i
    return cur, idx


def draw_keycaps(img, t):
    ln, _ = current_line(t)
    if not ln:
        return
    chars = []
    for ph in ln["phrases"]:
        for ch, ct in zip(ph["text"], ph["chars"]):
            chars.append((ch, ct))
        chars.append((" ", None))
    chars = chars[:-1]
    caps = [(B.keycap(ch, t >= ct) if ct is not None else None, ct) for ch, ct in chars]
    total = sum((c.width + 2) if c else 10 for c, _ in caps)
    x = W // 2 - total // 2
    appear = ln["start"] - 0.3
    for i, (c, ct) in enumerate(caps):
        if c is None:
            x += 10
            continue
        da = t - appear - i * 0.02                      # caps hop in one after another
        if da < 0:
            x += c.width + 2
            continue
        y = 12 - int(10 * max(0, 1 - da / 0.15))
        if ct is not None and 0 <= t - ct < 0.1:        # pressed on its syllable
            y += 2
        img.alpha_composite(c, (x, y))
        x += c.width + 2


@lru_cache(None)
def sub_font():
    return ImageFont.truetype(str(ROOT / "pv" / "fonts" / "MPLUSRounded1c-Bold.ttf"), 34)


def draw_subtitle(hd, t):
    ln, i = current_line(t)
    if not ln or i < 0:
        return
    d = ImageDraw.Draw(hd)
    d.text((OW // 2, 1046), EN[i], font=sub_font(), fill=(255, 255, 255), anchor="ms", stroke_width=5,
           stroke_fill=(20, 26, 70))


# ---------------------------------------------------------------- game objects: coins, hop blocks, targets
RUN_SPANS = [(13.4, 41.6), (69.6, 82.6), (84.2, 97.0), (110.4, 115.8)]
CHORUS_SPANS = [(56.0, 64.0), (127.0, 150.2)]
MISS_TIMES = (42.61, 61.01)


@lru_cache(None)
def hops():
    """Hop-over blocks: every 8 beats in the verses (two beats in the air)."""
    out = []
    for a, b in RUN_SPANS:
        k = math.ceil(beat_of(a + 1.0))
        k += (8 - k % 8) % 8
        while beat_t(k + 2) < b - 0.5:
            out.append(k)
            k += 8
    return tuple(out)


@lru_cache(None)
def coins():
    """Coins on the off beats while running (in the air along each hop arc)."""
    out = []
    hop_beats = set()
    for k in hops():
        hop_beats.update({k, k + 1, k + 2})
    for a, b in RUN_SPANS:
        for k in range(math.ceil(beat_of(a)), math.floor(beat_of(b))):
            if k % 2 and k not in hop_beats:
                out.append((beat_t(k), "ground"))
            elif k in hop_beats and k != hops()[0] - 999:
                if k - 1 in hop_beats or k + 1 in hop_beats:
                    out.append((beat_t(k), "air"))
    return tuple(sorted(set(out)))


@lru_cache(None)
def targets():
    """Chorus targets on every beat; lanes alternate every two beats. One is missed on purpose (61.0)."""
    out = []
    for a, b in CHORUS_SPANS:
        for k in range(math.ceil(beat_of(a)), math.floor(beat_of(b)) + 1):
            tt = beat_t(k)
            lane = "air" if (k // 2) % 2 else "ground"
            miss = abs(tt - MISS_TIMES[1]) < 0.25
            out.append((tt, lane, miss))
    return tuple(out)


def hop_at(t):
    """(height, in_air) of the current hop."""
    for k in hops():
        a, b = beat_t(k), beat_t(k + 2)
        if a <= t < b:
            u = (t - a) / (b - a)
            return 110 * 4 * u * (1 - u), True
    return 0.0, False


def events_before(t):
    """Hits counted for combo / score: coins and targets up to t, with misses."""
    ev = [(c[0], False) for c in coins()] + [(x[0], x[2]) for x in targets()]
    return sorted(e for e in ev if e[0] <= t)


NOCOUNT = (47.1, 62.6)                          # the paw scratches the MISS out and the combo comes back


@lru_cache(None)
def _combo_table():
    ev = sorted([(c[0], "hit") for c in coins()] + [(x[0], "miss" if x[2] else "hit") for x in targets()]
                + [(MISS_TIMES[0], "miss")] + [(n, "nocount") for n in NOCOUNT])
    combo, saved, out = 0, 0, []
    for tt, kind in ev:
        if kind == "miss":
            saved, combo = combo, 0
        elif kind == "nocount":
            combo, saved = combo + saved, 0
        else:
            combo += 1
        out.append((tt, combo))
    return out, None


def combo_at(t):
    c = 0
    for tt, v in _combo_table()[0]:
        if tt > t:
            break
        c = v
    return c


def miss_count(t):
    n = sum(1 for m in MISS_TIMES if t >= m)
    return max(0, n - sum(t >= x for x in NOCOUNT))


def score_at(t):
    return 1000 * len([e for e in events_before(t) if not e[1]]) + 120 * min(400, combo_at(t))


# ---------------------------------------------------------------- XIYIN
def xiyin(t):
    """(sprite, centre x, feet y, mirrored)."""
    lift = climb_lift(t) - cam_lift(t)
    cx = RUN_X
    if t < 4.02:
        return None
    if t < 11.9:                                          # title: on stage in the spotlight
        rise = 1 - S.ease_out_back((t - 4.02) / 0.45) if t < 4.5 else 0
        name = "p01_smug_a"
        if 5.4 <= t < 7.69:
            name = "p08_me"
        elif 7.69 <= t < 9.98:
            name = "p01_smug_b"
        elif 9.98 <= t:
            name = "p03_hit_ground"
        sp, feet = anim.pose(name)
        return sp, 480, GROUND + int(rise * 260), False
    if t < 13.6:                                          # starts running, eases to the run position
        u = min(1, (t - 11.9) / 1.7)
        cx = int(480 + (RUN_X - 480) * (1 - (1 - u) ** 2))
    if 42.61 <= t < 54.73:                                # the stumble gag
        if t < 44.14:
            sp, feet = anim.pose("p05_trip")
            y = GROUND - int(40 * math.sin(min(1, (t - 42.61) / 0.45) * math.pi)) if t < 43.06 else GROUND
            shake = 3 if 43.0 < t < 43.3 and int(t * 30) % 2 else 0
            return sp, cx + shake, y, False
        if t < 46.3:
            return anim.pose("p05_trip")[0], cx, GROUND, False
        if t < 50.9:
            return anim.pose("p06_nocount")[0], cx, GROUND, False
        if t < 52.0:
            return anim.pose("p07_akanbe")[0], cx, GROUND, False
        if t < 53.54:
            return anim.pose("p01_smug_b")[0], cx, GROUND, False
        if t < 54.39:
            breath = int(3 * math.sin((t - 53.54) * 7))
            return anim.pose("p01_smug_a")[0], cx, GROUND + breath, False
        return anim.jump_frame()[0], cx, GROUND - 10, False
    if 64.6 <= t < 68.3:                                  # 笑ったでしょ / めっ / もういっかい
        name = "p01_smug_b" if t < 67.06 else ("p08_me" if t < 67.54 else "p01_smug_a")
        return anim.pose(name)[0], cx, GROUND, False
    if 85.82 <= t < 87.19:                                # スクショ: blocks the camera
        return anim.pose("p03_hit_ground")[0], cx, GROUND, False
    if 93.4 <= t < 95.4:
        return anim.pose("p06_nocount")[0], cx, GROUND, False
    if 99.2 <= t < 109.7:                                 # ぷいっ / 目があえば / ぷふっ
        if t < 103.75:
            return anim.pose("p06_nocount")[0], cx, GROUND, True
        if t < 107.48:
            return anim.pose("p01_smug_b")[0], cx, GROUND, False
        return anim.pose("p09_giggle")[0], cx, GROUND, False
    if 136.68 <= t < 137.3:
        return anim.pose("p08_me")[0], cx, GROUND, False
    if t >= 150.9:                                        # stage clear and the ending
        u = min(1, max(0, (t - 150.9) / 1.6))
        cx = int(RUN_X + (480 - RUN_X) * (1 - (1 - u) ** 2))
        if t < 152.3:
            sp, feet = anim.run_at(t * min(1, speed(t) / 200 + 0.3))
            return sp, cx, GROUND, False
        name = "p01_smug_a"
        for a, n in ((152.3, "p01_smug_b"), (153.6, "p01_smug_a"), (154.47, "p01_smug_b"), (156.66, "p03_hit_ground"),
                     (157.8, "p01_smug_b"), (159.33, "p01_smug_a"), (161.98, "p09_giggle"), (163.32, "p08_me"),
                     (170.5, "p01_smug_a")):
            if t >= a:
                name = n
        return anim.pose(name)[0], 480, GROUND, False
    # chorus hits
    for tt, lane, miss in targets():
        if 0 <= t - tt < 0.2 and not miss:
            if lane == "air":
                return anim.pose("p04_hit_air")[0], cx + 10, GROUND - 90, False
            return anim.pose("p03_hit_ground")[0], cx + 10, GROUND, False
    for tt, lane, miss in targets():                      # jump up toward an air target
        if lane == "air" and not miss and 0 <= tt - t < 0.2:
            return anim.jump_frame()[0], cx, GROUND - int(90 * (1 - (tt - t) / 0.2)), False
    if 30.14 <= t < 30.7:
        return anim.pose("p07_akanbe")[0], cx, GROUND, False
    h, air = hop_at(t)
    if air:
        return anim.jump_frame()[0], cx, GROUND - int(h) - int(lift), False
    if 116.55 <= t < 125.8:
        k = beat_of(t) - CLIMB_B0
        f = k - math.floor(k)
        sp = anim.jump_frame()[0] if 0.15 < f < 0.75 and k < CLIMB_N else anim.run_at(t)[0]
        return sp, cx, GROUND - int(lift), False
    return anim.run_at(t)[0], cx, GROUND - int(lift), False


_MIRROR = {}


def mirrored(im):
    if id(im) not in _MIRROR:
        _MIRROR[id(im)] = (im, im.transpose(Image.Transpose.FLIP_LEFT_RIGHT))
    return _MIRROR[id(im)][1]


def draw_xiyin(img, t, rim_col):
    st = xiyin(t)
    if not st:
        return
    sp, cx, feet, mirror = st
    _, fy = anim.grounded(sp)
    if mirror:
        sp = mirrored(sp)
    if rim_col:
        sp = anim.rim(sp, rim_col)
    img.alpha_composite(sp, (int(cx - sp.width // 2), int(feet - fy)))
    return cx, feet - fy


# ---------------------------------------------------------------- pixel FX
def burst(img, x, y, age, cols=(LEMON, WHITE, COBALT)):
    d = ImageDraw.Draw(img)
    r = 8 + age * 140
    for a in range(10):
        ang = a * math.pi / 5 + 0.3
        px, py = x + int(r * math.cos(ang)), y + int(r * math.sin(ang))
        s = 3 if age < 0.15 else 2
        d.rectangle([px, py, px + s, py + s], fill=cols[a % len(cols)])


@lru_cache(None)
def target_icon(lane):
    return B.icon("cat" if lane == "air" else "paw", 4)


@lru_cache(None)
def hop_block():
    im = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
    im.alpha_composite(B.tile(40, "cobalt"))
    im.alpha_composite(B.icon("cat", 3), (6, 8))
    return im


def draw_objects(img, t):
    if 42.9 <= t < 54.9:
        return
    cx_now = cam_x(t)
    lift = int(climb_lift(t) - cam_lift(t)) * 0
    hit_x = RUN_X + 40
    for k in hops():                                       # hop-over blocks
        tm = (beat_t(k) + beat_t(k + 2)) / 2
        x = hit_x - 40 + (cam_x(tm) - cx_now)
        if -60 < x < W + 60:
            img.alpha_composite(hop_block(), (int(x) - 20, GROUND - 40))
    if 40.5 <= t < 44.14:                                  # the っ block she trips on
        x = hit_x - 30 + (cam_x(42.61) - cx_now)
        B.draw_word(img, "っ", int(x), GROUND - 22, 2, "lemon", t, 0)
    for tt, lane in coins():
        dt = tt - t
        if dt < -0.35 or dt > 5:
            continue
        x = hit_x + (cam_x(tt) - cx_now)
        y = GROUND - 60 if lane == "ground" else GROUND - 150
        if dt >= 0:
            if x < W + 40:
                img.alpha_composite(B.icon("coin", 3), (int(x) - 12, y - 12 + int(3 * math.sin(t * 8 + tt))))
        else:
            burst(img, int(x), y, -dt, (LEMON, WHITE))
    for tt, lane, miss in targets():
        dt = tt - t
        if dt < -0.5 or dt > 5 or not any(a - 1.2 <= t < b + 0.6 for a, b in CHORUS_SPANS):
            continue
        x = hit_x + 30 + (cam_x(tt) - cx_now)
        y = GROUND - 70 if lane == "ground" else GROUND - 190
        ic = target_icon(lane)
        if dt >= 0 or (miss and dt > -0.5):
            if miss and dt < 0 and int(-dt * 15) % 2:
                continue
            if x < W + 40:
                img.alpha_composite(ic, (int(x) - ic.width // 2, y - ic.height // 2 + int(4 * math.sin(t * 6 + tt))))
        elif dt > -0.32:
            burst(img, int(x), y, -dt)
            put_text(img, "PERFECT", "ps", (int(x), y - 34 - int(-dt * 40)), COBALT, outline=WHITE, anchor="mt")


STAIR_STYLES = ("coral", "lemon", "cyan", "pink", "cobalt", "white")


@lru_cache(None)
def stair_column(k, h):
    """One step of the rainbow block stairs: two beveled blocks on a pale column."""
    im = Image.new("RGBA", (60, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    face = B.STYLES[STAIR_STYLES[k]][0]
    d.rectangle([0, 0, 59, h - 1], fill=tuple(int(v * 0.55 + 230 * 0.45) for v in face), outline=INK)
    for y in range(36, h, 30):
        d.line([2, y, 57, y], fill=tuple(int(v * 0.45 + 200 * 0.55) for v in face))
    im.alpha_composite(B.tile(30, STAIR_STYLES[k]), (0, 0))
    im.alpha_composite(B.tile(30, STAIR_STYLES[k]), (30, 0))
    d.rectangle([0, 0, 59, 29], outline=INK)
    return im


def draw_stairs(img, t):
    if not 115.9 <= t < 125.8:
        return
    lift = cam_lift(t)
    cx_now = cam_x(t)
    x0 = RUN_X - 30 + (cam_x(beat_t(CLIMB_B0)) - cx_now)
    for i in range(CLIMB_N + 1):
        x = int(x0 + i * 60 + 30)
        top = GROUND - (i + 1) * STEP_H + int(lift)
        if -60 < x < W + 10 and top < H:
            img.alpha_composite(stair_column(i % len(STAIR_STYLES), max(30, H - top)), (x, top))
            if i % 4 == 1 and top + 8 < H:
                put_text(img, "STEP", "ps", (x + 30, top + 40), WHITE, outline=INK, anchor="mt")


def confetti(img, t, seed=0, n=40, cols=(CORAL, LEMON, SKY, WHITE, COBALT)):
    rng = random.Random(seed)
    d = ImageDraw.Draw(img)
    for i in range(n):
        x0, sp, ph = rng.uniform(0, W), rng.uniform(60, 130), rng.uniform(0, 10)
        y = (ph * 60 + t * sp) % (H + 40) - 20
        x = x0 + 20 * math.sin(t * 2 + ph)
        w = 4 if int(t * 8 + ph) % 2 else 2
        d.rectangle([int(x), int(y), int(x) + w, int(y) + 4], fill=cols[i % len(cols)])


def fireworks(img, t, t0, t1):
    if not t0 <= t < t1:
        return
    d = ImageDraw.Draw(img)
    for k in range(math.ceil(beat_of(t0)), math.floor(beat_of(t)) + 1):
        if k % 2:
            continue
        age = t - beat_t(k)
        if not 0 <= age < 1.2:
            continue
        rng = random.Random(k)
        cx, cy = rng.uniform(80, W - 80), rng.uniform(50, 230)
        col = rng.choice([CORAL, LEMON, SKY, (255, 160, 220), WHITE])
        r = 18 + 110 * (1 - (1 - min(1, age / 0.7)) ** 3)
        for a in range(16):
            ang = a * math.pi / 8 + rng.random() * 0.1
            for j in range(3):
                rr = r - j * 9
                if rr <= 0:
                    continue
                px, py = cx + rr * math.cos(ang), cy + rr * math.sin(ang) + 30 * age * age
                if age > 0.9 and (a + j) % 2:
                    continue
                s = 3 - j
                d.rectangle([int(px), int(py), int(px) + s, int(py) + s], fill=col if j < 2 else WHITE)


def shooting_stars(img, t, t0, t1):
    if not t0 <= t < t1:
        return
    d = ImageDraw.Draw(img)
    for k in range(int(t0), int(t1)):
        if k % 3:
            continue
        age = t - k - 0.3
        if 0 <= age < 0.6:
            rng = random.Random(k)
            x, y = rng.uniform(300, W), rng.uniform(20, 160)
            for j in range(14):
                px, py = x - (age * 500) + j * 4, y + (age * 250) - j * 2
                d.rectangle([int(px), int(py), int(px) + 1, int(py) + 1], fill=WHITE if j < 4 else SKY)


# ---------------------------------------------------------------- HUD and UI
CHAT = [(42.75, "えっ"), (43.0, "こけたｗ"), (43.4, "だいじょうぶ？"), (44.4, "ポーズｗｗ"), (46.7, "ノーカン？"),
        (47.3, "それはずるいｗ"), (48.1, "ノーカンｗｗ"), (49.8, "ニヤニヤ"), (50.0, "ｗｗｗ"), (50.3, "ニヤニヤ"),
        (50.6, "かわいい"), (50.9, "ｗｗｗｗ"), (51.5, "べーされたｗ"), (53.3, "がんばれー"), (55.8, "きた！"),
        (61.2, "いまミスった？"), (62.6, "またノーカンｗ"), (64.7, "わらってないよ"), (65.5, "ニヤニヤ"),
        (67.1, "めっ されたｗ"), (67.9, "もういっかい！"), (85.0, "スクショした"), (86.0, "カシャ"),
        (86.6, "きんしｗ"), (90.2, "なまいきｗ"), (99.6, "ぷいっｗ"), (101.0, "こっちむいて"), (104.4, "あ、目があった"),
        (107.7, "ふきだしたｗ"), (108.3, "かわいい"), (124.7, "ほんばん！"), (132.5, "みせばｗ"), (137.0, "またおこられた"),
        (144.9, "まきこまれた"), (145.5, "ｗｗｗ"), (151.6, "おめでとう！"), (152.4, "888888"), (155.0, "おつかれ"),
        (157.2, "余裕だったね"), (164.0, "また来るね"), (165.0, "おやすみー"), (166.2, "おつ〜")]

NARRATION = [(44.25, 45.9, "＊ XIYINは ポーズボタンを おした。"), (46.35, 49.0, "＊ いまのは ノーカン らしい。"),
             (62.4, 63.9, "＊ また ノーカン らしい。"), (99.6, 102.4, "＊ XIYINは そっぽを むいた。"),
             (107.7, 109.5, "＊ こらえきれなかった。")]
TYPE_CPS = 16


def typed(t):
    for a, b, text in NARRATION:
        if a <= t < b:
            return text[:max(0, int((t - a) * TYPE_CPS))]
    return None


def draw_hud(img, t):
    if t < 4.02 or t >= 175.5:
        return
    d = ImageDraw.Draw(img)
    live = t < 166.5
    d.rectangle([10, 10, 66, 26], fill=CORAL if live else (120, 126, 150), outline=INK)
    put_text(img, "LIVE" if live else "OFF", "ps", (22 if live else 26, 14), WHITE)
    if live and int(t * 2) % 2:
        d.rectangle([14, 16, 17, 19], fill=WHITE)
    viewers = 1204 + int(t * 9) % 41 + (300 if t > 126 else 0)
    put_text(img, f"{viewers:,} watching", "mi", (72, 14), WHITE, outline=INK)
    lv = 12 + (t >= 17.81) + (t >= 31.78) + (t >= 75.66) + (t >= 124.58)
    lv = 99 if t >= 151.9 else lv
    put_text(img, f"LV {lv:02d}", "ps", (12, 34), WHITE, outline=INK)
    d.rectangle([60, 35, 160, 41], fill=INK)
    frac = (beat_of(t) % 32) / 32 if lv < 99 else 1
    d.rectangle([61, 36, 61 + int(98 * frac), 40], fill=LEMON)
    if 17.81 <= t < 19.2 or 124.58 <= t < 125.8:
        put_text(img, "LV UP!", "ps", (170, 34 - int(min(1, (t % 1)) * 4)), LEMON, outline=INK)
    put_text(img, "SCORE", "ps", (W - 200, 14), WHITE, outline=INK)
    put_text(img, f"{score_at(t):07d}", "ps", (W - 120, 14), LEMON, outline=INK)
    mc = miss_count(t)
    put_text(img, f"MISS {mc}", "ps", (W - 120, 30), CORAL if mc else WHITE, outline=INK)
    for a in NOCOUNT:
        if a - 0.4 <= t < a + 0.3:
            img.alpha_composite(B.icon("paw", 2), (W - 40 + int((t - a) * -60), 26))
    c = combo_at(t)
    if c >= 3 and 12.4 <= t and not (42.61 <= t < 55.6) and t < 152.0 and not zoomed(t):
        bump = 2 if any(0 <= t - e[0] < 0.08 for e in events_before(t)[-1:]) else 0
        put_text(img, str(c), "ps", (W // 2, 54 - bump), WHITE, outline=INK, scale=3, anchor="mt")
        put_text(img, "COMBO", "ps", (W // 2, 82), LEMON, outline=INK, scale=1, anchor="mt")


def draw_chat(img, t):
    if zoomed(t):
        return
    d = ImageDraw.Draw(img)
    floor = 420
    for ct, text in sorted(CHAT, reverse=True):
        age = t - ct
        if not 0 <= age < 2.6:
            continue
        m = text_mask(text, "jp")
        y = min(380 - int(age * 26), floor - m.height - 10)
        floor = y - 4
        if y < 160:
            break
        x = W - 16 - m.width - 10
        d.rounded_rectangle([x - 6, y - 4, x + m.width + 6, y + m.height + 4], radius=4, fill=WHITE, outline=COBALT)
        put_text(img, text, "jp", (x, y), NAVY)


def draw_narration(img, t):
    txt = typed(t)
    if txt is None:
        return
    d = ImageDraw.Draw(img)
    bx0, by0, bx1, by1 = 340, 340, 770, 404
    d.rectangle([bx0, by0, bx1, by1], fill=(0, 0, 0), outline=WHITE, width=3)
    if txt:
        put_text(img, txt, "jp", (bx0 + 16, by0 + 14), WHITE, scale=2)


def zoomed(t):
    return 67.06 <= t < 67.54 or 136.68 <= t < 137.2


def dim(img, k=0.55):
    a = np.asarray(img).copy()
    yy, xx = np.mgrid[0:H, 0:W]
    m = (yy + xx) % 2 == 0
    a[m, :3] = (a[m, :3] * (1 - k) + np.array(NAVY) * k).astype(np.uint8)
    return Image.fromarray(a, "RGBA")


def menu(img, x0, y0, title, items, sel, t, blink_from):
    d = ImageDraw.Draw(img)
    w = 220
    h = 34 + 28 * len(items)
    d.rectangle([x0, y0, x0 + w, y0 + h], fill=INK, outline=WHITE, width=3)
    put_text(img, title, "ps", (x0 + 14, y0 + 12), LEMON, scale=2)
    for i, it in enumerate(items):
        on = i == sel
        if on and t >= blink_from and int(t * 12) % 2:
            continue
        put_text(img, ("▶ " if on else "  ") + it, "jp", (x0 + 14, y0 + 38 + 28 * i), LEMON if on else WHITE, scale=1)


def draw_events(img, t):
    d = ImageDraw.Draw(img)
    if t < 4.02:                                           # title screen
        put_text(img, "YOYUU DAMON!", "ps", (480, 262), WHITE, outline=INK, scale=3, anchor="mt")
        put_text(img, "XIYIN no NAMAHAISHIN", "ps", (480, 300), SKY, outline=INK, scale=1, anchor="mt")
        if t > 1.6 and int(t * 1.6) % 2 == 0:
            put_text(img, "PRESS START", "ps", (480, 380), LEMON, outline=INK, scale=2, anchor="mt")
    if 3.6 <= t < 4.1:
        put_text(img, "PRESS START", "ps", (480, 380), WHITE, outline=CORAL, scale=2, anchor="mt")
    if 8.62 <= t < 9.98:                                   # そろそろ: loading
        u = (t - 8.62) / 1.36
        d.rectangle([330, 470, 630, 490], fill=INK, outline=WHITE, width=2)
        d.rectangle([334, 474, 334 + int(292 * u), 486], fill=LEMON)
        put_text(img, "LOADING", "ps", (480, 498), WHITE, outline=INK, anchor="mt")
    for i, ct in enumerate((19.5, 20.86, 21.82)):            # 準備もバッチリ: three boxes get ticked
        if ct - 0.3 <= t < 23.2:
            x, y = 640 + i * 90, 300
            d.rectangle([x, y, x + 56, y + 56], fill=WHITE, outline=INK, width=3)
            if t >= ct:
                img.alpha_composite(B.icon("check", 5), (x + 4, y + 8))
    if 17.81 <= t < 18.9:
        put_text(img, "+1 LV", "ps", (RUN_X, 200 - int((t - 17.81) * 30)), LEMON, outline=INK, scale=2, anchor="mt")
    # stumble
    if 42.61 <= t < 43.7:
        put_text(img, "MISS", "ps", (RUN_X + 120, 120), CORAL, outline=INK, scale=5, anchor="mt")
    if 43.0 <= t < 44.14:                                  # stars circling her head
        for i in range(3):
            ang = t * 7 + i * 2.1
            img.alpha_composite(B.icon("star", 2), (RUN_X - 10 + int(50 * math.cos(ang)), 220 + int(14 * math.sin(ang))))
    if 44.14 <= t < 54.4:
        put_text(img, "II PAUSE", "ps", (480, 76), WHITE, outline=INK, scale=3, anchor="mt")
    if 44.6 <= t < 47.1:
        sel = 0 if t < 46.0 else 1
        menu(img, 370, 130, "PAUSE", ["つづける", "ノーカンにする", "やりなおす"], sel, t, 46.66)
    if 52.0 <= t < 54.39:                                  # ほっぺが熱い: blush steam
        for i in range(3):
            age = (t * 1.5 + i / 3) % 1
            put_text(img, "ぽっ", "jp", (RUN_X + 60 + i * 16, 230 - int(age * 40)), CORAL, outline=WHITE)
    if 53.54 <= t < 54.39:
        put_text(img, "すー… はー…", "jp", (RUN_X + 70, 270), NAVY, outline=WHITE, scale=2)
    if 54.39 <= t < 55.1:
        put_text(img, "READY?" if t < 54.73 else "GO!", "ps", (480, 300), LEMON, outline=INK, scale=4, anchor="mt")
    if 61.01 <= t < 61.6:
        put_text(img, "MISS", "ps", (RUN_X + 120, 300), CORAL, outline=INK, scale=3, anchor="mt")
    if 67.54 <= t < 68.3:                                  # RETRY
        menu(img, 600, 180, "RETRY?", ["もういっかい", "やめる"], 0, t, 67.9)
    if 85.82 <= t < 85.95:                                 # camera flash
        d.rectangle([0, 0, W, H], fill=WHITE)
    if 151.9 <= t < 156.4:                                 # result window
        u = min(1, (t - 151.9) / 0.4)
        y0 = int(-260 + 330 * (1 - (1 - u) ** 3)) if t < 155.8 else int(70 - (t - 155.8) * 600)
        d.rectangle([560, y0, 920, y0 + 230], fill=INK, outline=WHITE, width=3)
        put_text(img, "STAGE CLEAR!", "ps", (740, y0 + 14), LEMON, scale=2, anchor="mt")
        rows = [("SCORE", f"{score_at(151.9):07d}"), ("MAX COMBO", str(max(v for _, v in _combo_table()[0]))),
                ("MISS", "0"), ("ノーカン", "x2"), ("RANK", "S")]
        for i, (k, v) in enumerate(rows):
            if t >= 152.3 + i * 0.25:
                put_text(img, k, "jp" if k == "ノーカン" else "ps", (580, y0 + 50 + i * 34), WHITE, scale=1)
                put_text(img, v, "ps", (900 - len(v) * 16, y0 + 50 + i * 34), LEMON if k == "RANK" else WHITE, scale=2)
    if 170.0 <= t < 175.8:                                 # save card + credits
        u = min(1, (t - 170.0) / 0.5)
        x0 = int(980 - 400 * (1 - (1 - u) ** 3))
        d.rectangle([x0, 70, x0 + 360, 200], fill=WHITE, outline=COBALT, width=3)
        put_text(img, "セーブしました", "jp", (x0 + 20, 86), NAVY, scale=2)
        put_text(img, "XIYIN  LV 99", "ps", (x0 + 20, 128), COBALT, scale=2)
        put_text(img, "MISS 0  (ノーカン x2)", "jp", (x0 + 20, 160), NAVY)
        cr = ["Song 「余裕だもん」  AI-generated (Gemini / Lyria)", "Character  XIYIN (original)",
              "Art  NovelAI V5 + code", "Fonts  Fusion Pixel / M+ / Press Start 2P", "Made with Python + FFmpeg"]
        n = sum(1 for i in range(len(cr)) if t >= 170.6 + i * 0.4)
        if n:
            d.rectangle([24, 214, 352, 226 + 22 * n], fill=INK, outline=WHITE, width=2)
        for i, line in enumerate(cr[:n]):
            put_text(img, line, "jp", (36, 222 + i * 22), WHITE)


# ---------------------------------------------------------------- stickers (HD props on the plate)
STICKERS = [  # name, cx, cy (output px), size, t_in, t_out
    ("k09_controller", 1640, 820, 240, 1.4, 4.02), ("k10_catplush", 360, 760, 260, 4.6, 10.6),
    ("s1_crown", 1500, 230, 280, 17.6, 22.6),
    ("k02_trophy", 1560, 420, 320, 23.2, 26.6), ("k04_star", 1580, 300, 280, 36.9, 41.0),
    ("k08_bandage", 1300, 640, 240, 43.0, 46.2), ("k03_stamp", 1560, 640, 260, 46.66, 49.4),
    ("k06_heart", 1500, 320, 300, 52.0, 54.6), ("s3_mic", 1560, 420, 330, 76.6, 82.6),
    ("k05_camera", 1520, 380, 300, 84.81, 86.38), ("k03_stamp", 1520, 380, 340, 86.38, 88.4),
    ("s2_phone", 1250, 520, 260, 86.5, 88.4), ("k12_ribbon", 1560, 300, 240, 89.9, 93.3),
    ("k07_penlight", 1580, 330, 300, 144.4, 150.4), ("k02_trophy", 420, 420, 320, 152.0, 156.0),
    ("k10_catplush", 1500, 760, 260, 163.3, 175.0)]


def draw_stickers(hd, t):
    for i, (name, cx, cy, size, a, b) in enumerate(STICKERS):
        if a <= t < b + 0.25:
            S.put_sticker(hd, name, cx, cy, size, t, a, b, seed=i)


# ---------------------------------------------------------------- frame
def pixel_layer(t):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    i = section_at(t)
    rim_col = SECTIONS[i][3]
    if 4.02 <= t:
        lift = int(cam_lift(t))
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        B.draw_ground(g, ground_style_at(t), cam_x(t), GROUND + lift)
        img.alpha_composite(g)
    draw_stairs(img, t)
    fireworks(img, t, 126.2, 151.9)
    shooting_stars(img, t, 69.0, 83.0)
    draw_words(img, t)
    if not zoomed(t):
        draw_objects(img, t)
    draw_xiyin(img, t, rim_col)
    if 55.6 <= t < 64.2 or 126.6 <= t < 156:
        confetti(img, t, seed=int(t > 100))
    if zoomed(t):                                          # めっ: x2 punch-in on her
        z = img.crop((RUN_X - 240, 120, RUN_X + 240, 390)).resize((W, H), Image.Resampling.NEAREST)
        img = z
        B.draw_word(img, "めっ!", 700, 200, 6, "coral", t, 67.06 if t < 100 else 136.68)
    draw_events(img, t)
    draw_hud(img, t)
    draw_chat(img, t)
    draw_narration(img, t)
    draw_keycaps(img, t)
    return img


@lru_cache(1)
def snapshot():
    """The frame XIYIN 'screenshots' at 85.82 (for the polaroid gag)."""
    return compose(85.80, polaroid=False)


def compose(t, polaroid=True):
    hd = background(t).copy()
    if 44.14 <= t < 54.39:                                 # PAUSE: the world behind the game dims
        hd = S.dim(hd, 0.45)
    if zoomed(t):
        hd = S.plate_view("blush", 0.5).copy()
    draw_stickers(hd, t)
    hd.alpha_composite(pixel_layer(t).resize((OW, OH), Image.Resampling.NEAREST))
    if polaroid and 85.95 <= t < 88.6:                    # the screenshot shrinks into a polaroid, then gets tossed
        u = min(1, (t - 85.95) / 0.35)
        snap = snapshot().resize((480, 270), Image.Resampling.LANCZOS)
        card = Image.new("RGBA", (512, 340), (255, 255, 255, 255))
        card.paste(snap, (16, 16))
        k = 1 - 0.6 * (1 - (1 - u) ** 3)
        if t >= 87.19:
            v = t - 87.19
            card = card.rotate(-8 - 200 * v, expand=True, resample=Image.Resampling.BICUBIC)
            x, y = 1260 + v * 500, 520 - 600 * v + 1800 * v * v
        else:
            card = card.rotate(-8 * u, expand=True, resample=Image.Resampling.BICUBIC)
            x, y = 960 + 300 * u, 540 - 20 * u
        card = card.resize((int(card.width * k * 1.6), int(card.height * k * 1.6)), Image.Resampling.LANCZOS)
        hd.alpha_composite(card, (int(x - card.width / 2), int(y - card.height / 2)))
        if t >= 86.38:
            xi = B.icon("cross", 16)
            hd.alpha_composite(xi, (int(x - xi.width / 2), int(y - xi.height / 2)))
    draw_subtitle(hd, t)
    if t < 0.6 or t >= 176.6:                              # power on / off
        hd = power(hd, t)
    return hd


def power(hd, t):
    out = Image.new("RGBA", (OW, OH), (0, 0, 0, 255))
    if t < 0.6:
        u = max(0, (t - 0.1) / 0.5)
    else:
        u = max(0, 1 - (t - 176.6) / 0.6)
    if u <= 0:
        return out
    h = max(4, int(OH * u ** 2))
    w = OW if u > 0.15 else int(OW * u / 0.15)
    box = ((OW - w) // 2, (OH - h) // 2, (OW + w) // 2, (OH + h) // 2)
    if h <= 6:
        out.paste((255, 255, 255, 255), box)
    else:
        out.paste(hd.crop(box), box[:2])
    return out


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
                    "[s][2:a]amix=inputs=2:normalize=0,alimiter=limit=0.89:level=false[a]",
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
