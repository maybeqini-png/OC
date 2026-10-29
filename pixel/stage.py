"""XIYIN pixel PV: the rhythm-stage renderer (one 384x216 pixel screen, scaled x5 to 1920x1080).

Every frame is a pure function of the song time t. The game layer is drawn at native pixel size with fixed
palettes and pixel fonts (no anti-aliasing), then enlarged with nearest-neighbour, so all elements share one grid.

usage:
  stage.py preview <t> [<t> ...] --out sheet.png      contact sheet of single frames (fast check)
  stage.py render --t0 41.6 --t1 69.0 --out clip.mp4   full render with the song (and synthesized blips)
"""
import argparse
import json
import math
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).parent
ROOT = HERE.parent
W, H, SCALE, FPS = 384, 216, 5, 30
AUDIO = ROOT / "audio" / "t2_optimized_full.mp3"

# colours (README section 3 palette roles: navy / cobalt / sky / white; coral = feelings; lemon = gags)
NAVY = (27, 35, 64)
INK = (20, 24, 52)
COBALT = (60, 109, 240)
SKY = (156, 196, 255)
WHITE = (244, 246, 251)
CORAL = (255, 123, 138)
LEMON = (255, 214, 74)
BG_TOP, BG_BOT = (214, 225, 255), (246, 247, 252)
GRID = (205, 218, 252)
FLOOR, FLOOR_EDGE, FLOOR_MARK = (27, 35, 64), (60, 109, 240), (44, 56, 104)

GROUND_Y = 196                     # feet line
LANES = {"air": 138, "ground": 184}  # note centre y
JUDGE_X = 100
LEAD = 1.6                         # seconds a note is on screen before its hit time
SPEED = (W - JUDGE_X) / LEAD       # px per second
SPRITE_X = 34


# ---------------------------------------------------------------- fonts and pixel text
@lru_cache(None)
def font(name):
    f = {"jp": ("fonts/fusion-pixel-12px-proportional-jp-latin-400-normal.woff2", 12),
         "ps": ("fonts/PressStart2P.ttf", 8),
         "mi": ("fonts/misaki_gothic.ttf", 8)}[name]
    return ImageFont.truetype(str(HERE / f[0]), f[1])


@lru_cache(None)
def text_mask(text, fname):
    """1-bit glyph mask at native pixel size, cropped to the ink."""
    f = font(fname)
    im = Image.new("L", (len(text) * 16 + 16, 32), 0)
    d = ImageDraw.Draw(im)
    d.fontmode = "1"
    d.text((4, 4), text, font=f, fill=255)
    ref = Image.new("L", im.size, 0)
    ImageDraw.Draw(ref).text((4, 4), "国gyｗ", font=f, fill=255)
    rb = ref.getbbox()
    box = im.getbbox() or (4, rb[1], 5, rb[3])
    return im.crop((box[0], min(box[1], rb[1]), box[2], max(box[3], rb[3])))


def put_text(img, text, fname, xy, color, outline=None, scale=1, anchor="lt"):
    m = text_mask(text, fname)
    if scale > 1:
        m = m.resize((m.width * scale, m.height * scale), Image.Resampling.NEAREST)
    x, y = xy
    if anchor[0] == "m":
        x -= m.width // 2
    if anchor[1] == "m":
        y -= m.height // 2
    if outline:
        o = Image.new("L", (m.width + 2, m.height + 2), 0)
        o.paste(m, (1, 1))
        o = o.filter(ImageFilter.MaxFilter(3))
        img.paste(outline, (x - 1, y - 1, x - 1 + o.width, y - 1 + o.height), o)
    img.paste(color, (x, y, x + m.width, y + m.height), m)
    return m.width, m.height


def block_word(img, text, cx, cy, base, light, dark, tile=3, outline=INK):
    """Alice-MV-style word built from beveled tiles: every glyph pixel becomes a tile x tile block."""
    m = np.asarray(text_mask(text, "jp")) > 0
    m = m[np.any(m, 1)]                          # vertical ink only (block words are centred on cy)
    M = np.kron(m, np.ones((tile, tile), bool))
    h, w = M.shape
    top = M & ~np.vstack([np.zeros((1, w), bool), M[:-1]])   # glyph pixels with nothing above: highlight
    rgb = np.zeros((h, w, 3), np.uint8)
    rgb[:] = base
    rgb[top] = light
    layer = Image.fromarray(rgb)
    mask = Image.fromarray((M * 255).astype(np.uint8))
    x, y = cx - w // 2, cy - h // 2
    sh = Image.new("L", (w + 2, h + tile + 2), 0)          # drop shadow, one tile down
    sh.paste(mask, (1, tile + 1))
    full = Image.new("L", sh.size, 0)
    full.paste(mask, (1, 1))
    full.paste(sh, (0, 0), sh)
    o = full.filter(ImageFilter.MaxFilter(3))
    img.paste(outline, (x - 1, y - 1, x - 1 + o.width, y - 1 + o.height), o)
    img.paste(dark, (x - 1, y - 1, x - 1 + sh.width, y - 1 + sh.height), sh)
    img.paste(layer, (x, y), mask)


# ---------------------------------------------------------------- small pixel icons (char grids)
ICON_COLORS = {"K": INK, "C": COBALT, "W": WHITE, "Y": SKY, "R": CORAL, "L": LEMON, "N": NAVY}
PAW = ["...KKKKK...", "..KCCCCCK..", ".KCWCCCWCK.", "KCCCWCWCCCK", "KCCCCCCCCCK", "KCCCWWWCCCK",
       "KCCWWWWWCCK", "KCCCWWWCCCK", ".KCCCCCCCK.", "..KCCCCCK..", "...KKKKK..."]
CAT = [".K.......K.", "KYK.....KYK", "KYYKKKKKYYK", "KYYYYYYYYYK", "KYKKYYYKKYK", "KYYYYYYYYYK",
       "KYYYYRYYYYK", ".KYYYYYYYK.", "..KKKKKKK.."]
PAWHAND = ["..KK.KK..", ".KWWKWWK.", ".KWWKWWK.", "KKKKKKKKK", "KWWWWWWWK", "KWWWRWWWK", "KWWRRRWWK",
           ".KWWWWWK.", "..KKKKK.."]


@lru_cache(None)
def icon(rows):
    im = Image.new("RGBA", (len(rows[0]), len(rows)), (0, 0, 0, 0))
    px = im.load()
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c != ".":
                px[x, y] = ICON_COLORS[c] + (255,)
    return im


@lru_cache(None)
def sprite(name):
    return Image.open(HERE / "sprites" / f"{name}.png").convert("RGBA")


# ---------------------------------------------------------------- timeline
@lru_cache(None)
def lyrics():
    return json.loads((ROOT / "pv3" / "lyrics_timed.json").read_text(encoding="utf-8"))


def lyric_at(t):
    """(line text, list of (char, sung)) for the line on screen at t."""
    cur = None
    for ln in lyrics():
        if ln["start"] - 0.3 <= t < ln["end"] + 0.4:
            cur = ln
    if not cur:
        return None
    chars = []
    for ph in cur["phrases"]:
        for ch, ct in zip(ph["text"], ph["chars"]):
            chars.append((ch, t >= ct))
        chars.append(("　", t >= ph["t"]))
    return chars[:-1]


MISS_TIMES = [42.61, 61.0]   # えっ, and the second (ignored) note during ふふん


@lru_cache(None)
def notes():
    """(time, lane, miss) from the sung syllables in the playing sections; the stumble section has no notes."""
    out = []
    playing = [(41.0, 42.62), (55.6, 61.7), (64.4, 66.4)]   # notes pause while she argues
    k = 0
    for ln in lyrics():
        for ph in ln["phrases"]:
            for ct in sorted(set(ph["chars"])):
                if any(a <= ct < b for a, b in playing):
                    lane = "air" if (k // 3) % 2 else "ground"
                    out.append((round(ct, 3), lane, any(abs(ct - m) < 0.08 for m in MISS_TIMES)))
                    k += 1
    for m in MISS_TIMES:
        if not any(abs(n[0] - m) < 0.08 for n in out):
            out.append((m, "ground", True))
    return tuple(sorted(out))


def hits_before(t):
    return [n for n in notes() if n[0] <= t]


def combo_at(t):
    c = 99 - sum(1 for nt, _, miss in notes() if nt < MISS_TIMES[0] and not miss)
    for nt, _, miss in hits_before(t):
        c = 0 if miss else c + 1
    return c


def miss_count(t):
    """The running gag: each MISS is scratched off again ("NO COUNT")."""
    n = sum(1 for m in MISS_TIMES if t >= m)
    n -= (t >= 48.3) + (t >= 63.4)
    return max(0, n)


def running(t):
    return not (42.61 <= t < 55.6)


def zoomed(t):
    return 66.6 <= t < 67.5


SPRITES = [  # (t0, t1, sprite)
    (0, 42.61, "s01_idle_smug"), (42.61, 45.8, "s03_trip"), (45.8, 51.2, "s04_nocount_x"),
    (51.2, 52.3, "s06_akanbe"), (52.3, 59.41, "s01_idle_smug"), (59.41, 62.2, "s07_pupu_laugh"),
    (62.2, 64.46, "s04_nocount_x"), (64.46, 67.5, "s05_me_boop"), (67.5, 99, "s01_idle_smug")]

CHAT = [(42.75, "えっ"), (43.0, "こけたｗ"), (43.4, "だいじょうぶ？"), (44.4, "ポーズｗｗ"), (46.6, "ノーカン？"),
        (47.3, "それはずるいｗ"), (48.1, "ノーカンｗｗ"), (49.8, "ニヤニヤ"), (50.0, "ｗｗｗ"), (50.3, "ニヤニヤ"),
        (50.6, "かわいい"), (50.9, "ｗｗｗｗ"), (51.5, "べーされたｗ"), (53.3, "がんばれー"), (55.8, "きた！"),
        (57.2, "うまい"), (58.6, "よゆうｗ"), (61.2, "いまミスった？"), (62.6, "またノーカンｗ"), (64.7, "わらってないよ"),
        (67.0, "めっ されたｗ"), (67.9, "もういっかい！")]

NARRATION = [(44.25, 45.75, "＊ XIYINは ポーズボタンを おした。"),
             (46.35, 48.9, "＊ いまのは ノーカン らしい。"),
             (62.3, 63.4, "＊ また ノーカン らしい。")]
TYPE_CPS = 16   # typewriter characters per second


def typed(t):
    for a, b, text in NARRATION:
        if a <= t < b:
            return text[:max(0, int((t - a) * TYPE_CPS))]
    return None


# ---------------------------------------------------------------- drawing
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16


@lru_cache(None)
def background():
    """Light dithered gradient (4 shades) - kept static; the grid on top scrolls."""
    y = np.linspace(0, 1, GROUND_Y)[:, None] * np.ones((1, W))
    levels = np.floor(y * 3 + BAYER[np.arange(GROUND_Y)[:, None] % 4, np.arange(W)[None] % 4]) / 3
    a, b = np.array(BG_TOP), np.array(BG_BOT)
    rgb = (a + (b - a) * levels[..., None]).astype(np.uint8)
    return Image.fromarray(rgb)


def scroll(t):
    """World offset in px: moves while the game runs, stops during the stumble."""
    stop0, stop1 = 42.61, 55.6
    if t < stop0:
        return t * SPEED
    if t < stop1:
        return stop0 * SPEED
    return (stop0 + (t - stop1)) * SPEED


def draw_world(img, t):
    img.paste(background(), (0, 0))
    d = ImageDraw.Draw(img)
    off = scroll(t)
    g = int(off / 4) % 16                       # far grid scrolls slower (parallax)
    for x in range(-g, W, 16):
        d.line([(x, 0), (x, GROUND_Y - 1)], fill=GRID)
    for y in range(8, GROUND_Y, 16):
        d.line([(0, y), (W, y)], fill=GRID)
    d.rectangle([0, GROUND_Y, W, H], fill=FLOOR)
    d.line([(0, GROUND_Y), (W, GROUND_Y)], fill=FLOOR_EDGE)
    f = int(off) % 24
    for x in range(-f, W, 24):                  # floor marks scroll at note speed
        d.rectangle([x, GROUND_Y + 6, x + 10, GROUND_Y + 8], fill=FLOOR_MARK)
        d.rectangle([x + 12, GROUND_Y + 13, x + 16, GROUND_Y + 15], fill=FLOOR_MARK)
    for lane, y in LANES.items():               # judgement rings
        beat_pulse = 1 if running(t) and (t * 136 / 60) % 1 < 0.15 else 0
        r = 7 + beat_pulse
        d.ellipse([JUDGE_X - r, y - r, JUDGE_X + r, y + r], outline=COBALT)
        d.ellipse([JUDGE_X - r + 2, y - r + 2, JUDGE_X + r - 2, y + r - 2], outline=SKY)


def draw_notes(img, t):
    for nt, lane, miss in notes():
        dt = nt - t
        y = LANES[lane]
        if dt > LEAD or dt < -1.2:
            continue
        if dt >= 0 or miss:
            x = int(JUDGE_X + dt * SPEED)
            ic = icon(tuple(PAW if lane == "ground" else CAT))
            if miss and dt < 0:                  # the missed note keeps sliding past her, blinking
                if int(-dt * 15) % 2:
                    continue
            img.alpha_composite(ic, (x - ic.width // 2, y - ic.height // 2))
        elif dt > -0.3:                          # hit burst + PERFECT
            k = int(-dt * FPS)
            d = ImageDraw.Draw(img)
            r = 6 + 3 * k
            for a in range(8):
                ang = a * math.pi / 4
                px, py = JUDGE_X + int(r * math.cos(ang)), y + int(r * math.sin(ang))
                d.rectangle([px, py, px + 1, py + 1], fill=LEMON if a % 2 else COBALT)
            put_text(img, "PERFECT", "ps", (JUDGE_X, y - 16 - k), COBALT, outline=WHITE, anchor="mt")


def draw_xiyin(img, t):
    name = next(s for a, b, s in SPRITES if a <= t < b)
    sp = sprite(name)
    y = GROUND_Y - sp.height
    if running(t) and any(0 <= t - nt < 0.07 for nt, _, m in notes() if not m):
        y -= 2                                   # hop on each hit
    if 42.61 <= t < 43.05:                       # trip: lifted, then lands on the thud
        y -= int(10 * math.sin((t - 42.61) / 0.44 * math.pi))
    img.alpha_composite(sp, (SPRITE_X, y))


def draw_hud(img, t):
    d = ImageDraw.Draw(img)
    # LIVE badge
    d.rectangle([4, 4, 40, 15], fill=CORAL)
    put_text(img, "LIVE", "ps", (12, 6), WHITE)
    d.rectangle([7, 8, 9, 10], fill=WHITE)
    put_text(img, f"{1204 + int(t * 7) % 37:,} watching", "mi", (44, 6), NAVY)
    # score / miss (top right)
    hit_n = sum(1 for n in hits_before(t) if not n[2])
    put_text(img, "SCORE", "ps", (W - 104, 6), COBALT)
    put_text(img, f"{1834500 + hit_n * 1000:07d}", "ps", (W - 62, 6), NAVY)
    mc = miss_count(t)
    put_text(img, f"MISS {mc}", "ps", (W - 62, 18), CORAL if mc else NAVY)
    for a in (48.0, 63.1):                       # a paw swipes the miss count back down
        if a <= t < a + 0.5:
            p = icon(tuple(PAWHAND))
            img.alpha_composite(p, (W - 30 + int((t - a) * -30), 16))
    # combo (centre)
    c = combo_at(t)
    if c >= 2 and running(t) and not zoomed(t):
        put_text(img, str(c), "ps", (W // 2, 40), NAVY, outline=WHITE, scale=2, anchor="mt")
        put_text(img, "COMBO", "ps", (W // 2, 60), COBALT, outline=WHITE, anchor="mt")
        if 96 <= c <= 100 and c == 100:
            put_text(img, "100 COMBO!", "ps", (W // 2, 72), LEMON, outline=INK, anchor="mt")
    # lyric line (karaoke fill)
    ly = lyric_at(t)
    if ly:
        f = font("jp")
        total = sum(int(f.getlength(ch)) for ch, _ in ly)
        x = W // 2 - total // 2
        for ch, sung in ly:
            if ch.strip("　"):
                put_text(img, ch, "jp", (x, 22), NAVY if sung else (150, 162, 205), outline=WHITE)
            x += int(f.getlength(ch))


def draw_chat(img, t):
    if zoomed(t):
        return
    d = ImageDraw.Draw(img)
    ceiling = 140                                # newest bubble sits lowest; older ones are pushed up
    for ct, text in sorted(CHAT, reverse=True):
        age = t - ct
        if not 0 <= age < 2.4:
            continue
        m = text_mask(text, "jp")
        y = min(136 - int(age * 24), ceiling - m.height - 8)
        ceiling = y - 3
        if y < 74:
            break
        x = W - 8 - m.width - 8
        d.rectangle([x - 4, y - 3, x + m.width + 4, y + m.height + 3], fill=WHITE, outline=SKY)
        put_text(img, text, "jp", (x, y), NAVY)


def draw_events(img, t):
    d = ImageDraw.Draw(img)
    if 42.61 <= t < 43.6:
        put_text(img, "MISS", "ps", (JUDGE_X + 30, 96), CORAL, outline=INK, scale=3, anchor="mt")
    if 43.05 <= t < 43.9:
        block_word(img, "ドテッ", 120, 168, LEMON, (255, 236, 160), (214, 160, 30), tile=2)
    if 44.18 <= t < 45.8:                        # pause overlay (50% dither) + PAUSE
        a = np.asarray(img).copy()
        yy, xx = np.mgrid[0:H, 0:W]
        m = (yy + xx) % 2 == 0
        a[m, :3] = (a[m, :3] * 0.35 + np.array(NAVY) * 0.65).astype(np.uint8)
        img.paste(Image.fromarray(a))
        put_text(img, "II PAUSE", "ps", (W // 2, 70), WHITE, outline=INK, scale=2, anchor="mt")
    if 46.95 <= t < 49.4:
        tile = 4 if t < 47.02 else 3            # stamp: lands one size bigger, then settles
        block_word(img, "ノーカン", W // 2 + 6, 104, COBALT, SKY, NAVY, tile=tile)
        put_text(img, "NO COUNT!", "ps", (W // 2 + 6, 128), CORAL, outline=WHITE, anchor="mt")
    if 51.25 <= t < 52.3:
        block_word(img, "べー", 120, 118, LEMON, (255, 236, 160), (214, 160, 30), tile=2)
    if 53.1 <= t < 54.4:
        put_text(img, "READY?", "ps", (W // 2, 96), NAVY, outline=WHITE, scale=2, anchor="mt")
    if 54.5 <= t < 55.5:
        put_text(img, "GO!", "ps", (W // 2, 92), COBALT, outline=WHITE, scale=3, anchor="mt")
    for a in (55.64, 57.55):
        if a <= t < a + 1.4:
            block_word(img, "余裕", W // 2 + 40, 100, COBALT, SKY, NAVY, tile=3)
            put_text(img, "EASY!", "ps", (W // 2 + 40, 124), LEMON, outline=INK, anchor="mt")
    if 61.0 <= t < 61.6:
        put_text(img, "MISS", "ps", (JUDGE_X + 30, 160), CORAL, outline=INK, scale=2, anchor="mt")
    if 62.2 <= t < 63.0:
        block_word(img, "ノーカン", W // 2 + 30, 104, COBALT, SKY, NAVY, tile=2)
    if 66.82 <= t < 67.5:
        block_word(img, "めっ!", W // 2 + 70, 92, CORAL, (255, 190, 198), (200, 70, 90), tile=4)
        put_text(img, "NO-NO!", "ps", (W // 2 + 70, 128), NAVY, outline=WHITE, anchor="mt")
    if 67.6 <= t:                                # RETRY? menu
        x0, y0 = W // 2 - 10, 70
        d.rectangle([x0, y0, x0 + 120, y0 + 52], fill=INK, outline=WHITE)
        put_text(img, "RETRY?", "ps", (x0 + 10, y0 + 8), WHITE)
        sel = t >= 68.3
        if not sel or int(t * 10) % 2:
            put_text(img, "▶ もういっかい", "jp", (x0 + 10, y0 + 20), LEMON if sel else WHITE)
        put_text(img, "  やめる", "jp", (x0 + 10, y0 + 35), (150, 162, 205))
    txt = typed(t)
    if txt is not None:
        bx0, by0, bx1, by1 = 92, 150, W - 8, 206
        d.rectangle([bx0, by0, bx1, by1], fill=(0, 0, 0), outline=WHITE)
        d.rectangle([bx0 + 2, by0 + 2, bx1 - 2, by1 - 2], outline=WHITE)
        if txt:
            put_text(img, txt, "jp", (bx0 + 10, by0 + 10), WHITE)


def frame(t):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    draw_world(img, t)
    draw_notes(img, t)
    draw_xiyin(img, t)
    if zoomed(t):                                # めっ: integer zoom (x2) on her
        img = img.crop((0, 108, 192, 216)).resize((W, H), Image.Resampling.NEAREST)
    draw_hud(img, t)
    draw_chat(img, t)
    draw_events(img, t)
    sx = sy = 0
    if 42.61 <= t < 42.9 or 66.82 <= t < 67.0:  # screen shake (whole pixels)
        sx = 2 if int(t * FPS) % 2 else -2
    out = Image.new("RGBA", (W, H), INK + (255,))
    out.paste(img, (sx, sy))
    return out.convert("RGB")


def big(im):
    return im.resize((W * SCALE, H * SCALE), Image.Resampling.NEAREST)


# ---------------------------------------------------------------- audio (song segment + typewriter blips)
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
                wave = np.sign(np.sin(2 * np.pi * 700 * tt)) * np.exp(-tt * 60) * 0.12
                out[k:k + L] += wave[: max(0, min(L, n - k))]
    import wave
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(out, -1, 1) * 32767).astype(np.int16).tobytes())


def render(t0, t1, out):
    tmp = Path(out).with_suffix(".blips.wav")
    blips_wav(t0, t1, tmp)
    nframes = round((t1 - t0) * FPS)
    cmd = ["ffmpeg", "-v", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W * SCALE}x{H * SCALE}", "-framerate", str(FPS), "-i", "-",
           "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", str(AUDIO), "-i", str(tmp),
           "-filter_complex", f"[1:a]afade=t=in:d=0.15,afade=t=out:st={t1 - t0 - 0.5:.3f}:d=0.5[s];"
                              "[s][2:a]amix=inputs=2:normalize=0,alimiter=limit=0.85:level=false[a]",
           "-map", "0:v", "-map", "[a]",
           "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
           "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-tune", "animation",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
           "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(nframes):
        p.stdin.write(big(frame(t0 + i / FPS)).tobytes())
    p.stdin.close()
    p.wait()
    tmp.unlink(missing_ok=True)
    print(out, nframes, "frames")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    pv = sub.add_parser("preview")
    pv.add_argument("times", type=float, nargs="+")
    pv.add_argument("--out", required=True)
    rd = sub.add_parser("render")
    rd.add_argument("--t0", type=float, default=41.6)
    rd.add_argument("--t1", type=float, default=69.0)
    rd.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "preview":
        tiles = [frame(t).resize((W * 2, H * 2), Image.Resampling.NEAREST) for t in a.times]
        cols = 3
        rows = (len(tiles) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * W * 2, rows * (H * 2 + 14)), (0, 0, 0))
        dd = ImageDraw.Draw(sheet)
        for i, (t, tile) in enumerate(zip(a.times, tiles)):
            x, y = (i % cols) * W * 2, (i // cols) * (H * 2 + 14)
            sheet.paste(tile, (x, y + 14))
            dd.text((x + 4, y + 1), f"t={t:.2f}", fill=(255, 220, 80))
        sheet.save(a.out)
    else:
        render(a.t0, a.t1, a.out)


if __name__ == "__main__":
    main()
