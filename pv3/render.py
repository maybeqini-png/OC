"""「余裕だもん」 PV renderer: a designed motion-graphics system built from the reference-MV breakdown
(docs/reference_breakdown.md). Layout families:
  scrap  - pastel scrapbook frame, sticker character, big rounded lyric typography        (うみゃうにゃ)
  burst  - radial burst + giant text wall behind the sticker, colour flips per beat         (ロリ神)
  dark   - navy field, vertical lyric text, soft particles for serious lines
  scene  - full illustration with camera move, light and particles
  stream - her stream window: LIVE badge, chat, ノーカン counter                            (story device)
  sym    - symmetric 3-panel beat layout, poses alternate per beat                           (メズマライザー)
  comic  - comic panels with SFX words for the stumble gag
  pattern- scrolling pattern of chibi stickers for breaks and transitions
  card   - title / end cards
usage: render.py preview <t> [<t> ...] --out sheet.jpg | segment <i> <n> --out seg.mp4
"""
import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pv2"))
import comp as C  # noqa: E402

W, H, FPS, DUR = 1920, 1080, 30, 178.6
ST = ROOT / "pv3/stickers"
TIM = json.load(open(ROOT / "pv/assets/timing.json"))
BEATS = np.array(TIM["beats"])
NAME = "（なまえ）"

NAVY, INK = (0.106, 0.137, 0.251), (0.075, 0.09, 0.17)
COBALT, SKY, CREAM = (0.235, 0.427, 0.941), (0.612, 0.769, 1.0), (1.0, 0.976, 0.93)
PINK, MINT = (1.0, 0.86, 0.9), (0.80, 0.95, 0.93)
THEMES = {"sky": (SKY, (0.86, 0.93, 1.0)), "cream": (CREAM, (0.93, 0.95, 1.0)), "pink": (PINK, (1.0, 0.95, 0.97)),
          "mint": (MINT, (0.93, 0.98, 1.0))}

LYRICS = [
    (3.7, 6.7, "ねえねえ　ちゃんと見ててよね"), (7.6, 11.1, "ふふん　そろそろ　いくよ"),
    (14.15, 19.6, "今日の私は　だいてんさい"), (19.8, 25.4, "準備もバッチリ　完璧じゃん"),
    (27.8, 33.4, "ざんねんでした　余裕だもん"), (34.4, 42.3, "ほら　スマートに　キメちゃうよ"),
    (42.6, 45.3, "えっ　あいたたた　ちょっと待った"), (45.8, 48.9, "いまのは　カウントに　はいりません"),
    (49.2, 52.2, "あーもう　にやけないでよ"), (52.3, 55.2, "ほっぺが熱いけど　深呼吸　せーの"),
    (55.6, 59.6, "余裕だもん　ほら　余裕だもん"), (59.7, 64.2, "ふふん　いまのは　ノーカンじゃん"),
    (64.4, 68.8, "笑ったでしょ　めっ　もういっかい"), (69.0, 72.9, "よそ見しないで　見ててよね"),
    (73.0, 76.9, "強がりだって　本気だもん"), (77.0, 83.0, "この声で　キメちゃうよ"),
    (84.6, 89.7, "スクショは　きんし　忘れてよね"), (90.2, 95.6, "なまいきなんて　言わせないもん"),
    (96.2, 103.8, "ぷいって　そっぽ　向いてみても"), (104.0, 109.8, "きみと目があえば　吹き出しちゃうな"),
    (110.0, 112.8, "悔しいままで　終わりたくない"), (112.9, 116.0, "いいこちゃんなんて　つまんないでしょ"),
    (116.2, 122.5, "震えるつま先で　ステップ踏んで"), (122.8, 125.4, "わらうな　こっからが　ほんばんだもん"),
    (125.8, 130.0, "余裕だもん　もっと　余裕だもん"), (130.2, 133.4, "転んだあとが　見せ場じゃん"),
    (133.5, 138.7, "笑ったでしょ　めっ　もういっかい"), (139.0, 142.9, "よそ見しないで　見ててよね"),
    (143.0, 146.9, "笑ったきみも　巻き込んで"), (147.0, 153.6, "最後まで　歌いきるよ"),
    (154.0, 158.4, "ほらね　やっぱり　余裕でしょ"), (158.5, 172.5, "ふふん　たぶんね　また来てよね"),
]
CHAT = [(7.8, "ねこ好き", "きた！"), (8.6, "J.D.", "here we go!"), (9.4, "もふ", "ふふんｗ"), (16.6, "リス", "大天才だ"),
        (17.4, "Mia", "genius!!"), (18.3, "Kai", "so smug lol"), (46.0, "審判", "ノーカン!?"), (46.7, "Leo", "it counts lol"),
        (47.4, "もふ", "カウントです"), (48.1, "Kai", "ｗｗｗ"), (85.0, "リス", "スクショ…"), (85.6, "Mia", "*screenshot*"),
        (86.4, "J.D.", "saved"), (104.6, "もふ", "www"), (105.1, "Leo", "LOL"), (105.6, "J.D.", "she broke"),
        (155.0, "ねこ好き", "余裕でしたね"), (155.8, "Kai", "gg"), (166.4, "もふ", "おつにゃ"), (167.0, "Mia", "otsu!"),
        (167.6, "リス", "また来るね"), (168.2, "J.D.", "see you!")]
CHAT += [(143.2 + i * 0.45, n, "にゃ") for i, n in enumerate(["もふ", "Kai", "リス", "Mia", "J.D.", "Leo", "ねこ好き", "審判"])]

# (start, layout, args); a shot ends where the next starts
SHOTS = [
    (0.0, "pattern", dict(ids=["c01_sleep", "c08_dance", "c06_boop"], theme="sky", hold="c01_sleep")),
    (3.6, "scrap", dict(st="n01_peek", side="r", theme="sky")),
    (5.2, "scrap", dict(st="n01_peek", side="l", theme="cream", zoom=2.3, focus=(0.5, 0.2))),
    (6.75, "burst", dict(st="n02_fufun", wall="ふふん", pal="cool")),
    (7.6, "scrap", dict(st="n02_fufun", side="l", theme="mint")),
    (9.4, "burst", dict(st="n03_ikuyo", wall="いくよ", pal="cool")),
    (11.1, "card", dict(kind="title")),
    (14.15, "burst", dict(st="n04_tensai", wall="大天才", pal="cool")),
    (16.9, "stream", dict(st="n06_kanpeki", theme="sky")),
    (19.8, "scrap", dict(st="n05_batchiri", side="r", theme="cream")),
    (22.6, "burst", dict(st="n06_kanpeki", wall="完璧", pal="pop")),
    (25.4, "pattern", dict(ids=["c08_dance", "c06_boop", "c05_sign"], theme="mint")),
    (27.8, "scrap", dict(st="n07_zannen", side="l", theme="pink")),
    (30.6, "burst", dict(st="n08_yoyuu", wall="余裕", pal="pop")),
    (33.4, "flash", dict()),
    (34.4, "scene", dict(img="art/generated/proof/c1_stage_hero_s6102_v5.png", z=(1.0, 1.12), c=(0.5, 0.45))),
    (37.0, "burst", dict(st="n09_smart", wall="スマート", pal="cool")),
    (39.6, "burst", dict(st="n10_kimeru", wall="キメ", pal="neon")),
    (42.55, "comic", dict()),
    (45.6, "stream", dict(st="n14_nocount", theme="mint", counter=1)),
    (49.1, "scrap", dict(st="n15_niyake", side="r", theme="pink", stamps="ニヤニヤ")),
    (52.25, "scene", dict(img="art/generated/proof/c4_flustered_s6102_v5.png", z=(1.08, 1.0), c=(0.5, 0.4))),
    (53.7, "scrap", dict(st="n16_shinkokyu", side="l", theme="sky")),
    (54.5, "seeno", dict()),
    (55.6, "burst", dict(st="n08_yoyuu", wall="余裕だもん", pal="neon")),
    (56.49, "burst", dict(st="n17_sing", wall="余裕だもん", pal="pop")),
    (57.37, "burst", dict(st="n06_kanpeki", wall="ほら", pal="cool")),
    (58.25, "scene", dict(img="art/generated/proof/c5_chorus_s6101_v5.png", z=(1.0, 1.1), c=(0.45, 0.4))),
    (59.7, "scrap", dict(st="n18_fufun2", side="r", theme="cream")),
    (61.9, "stream", dict(st="c05_sign", theme="pink", counter=2, stamp="ノーカン!")),
    (64.4, "sym", dict(sts=["n29_warauna", "n26_fukidasu"])),
    (66.6, "boop", dict(st="n19_me")),
    (67.6, "scrap", dict(st="n20_mouikkai", side="l", theme="mint")),
    (69.0, "scrap", dict(st="n21_yosomi", side="r", theme="sky")),
    (71.0, "eyes", dict(st="n21_yosomi")),
    (73.0, "dark", dict(st="n22_tsuyogari")),
    (77.0, "burst", dict(st="n17_sing", wall="この声で", pal="cool")),
    (80.0, "scene", dict(img="art/generated/proof/c1_stage_hero_s6102_v5.png", z=(1.25, 1.05), c=(0.5, 0.35))),
    (83.0, "flash", dict()),
    (84.6, "stream", dict(st="n23_screenshot", theme="cream", shutter=84.645)),
    (87.2, "polaroid", dict(st="n13_matta")),
    (90.2, "scrap", dict(st="n24_namaiki", side="l", theme="pink")),
    (92.9, "burst", dict(st="c04_stomp", wall="なまいき", pal="pop")),
    (96.2, "scrap", dict(st="n25_pui", side="r", theme="mint")),
    (99.0, "pattern", dict(ids=["c03_dizzy", "c07_cry", "c04_stomp"], theme="pink")),
    (101.4, "scrap", dict(st="n24_namaiki", side="r", theme="sky", zoom=1.9, focus=(0.5, 0.25))),
    (104.0, "eyes", dict(st="n06_kanpeki")),
    (105.8, "stream", dict(st="n26_fukidasu", theme="sky")),
    (110.0, "dark", dict(st="n27_kuyashii")),
    (112.9, "sym", dict(sts=["n24_namaiki", "n25_pui"])),
    (116.2, "burst", dict(st="n28_step", wall="ステップ", pal="neon")),
    (119.4, "pattern", dict(ids=["c08_dance", "c06_boop", "c03_dizzy"], theme="sky")),
    (122.8, "burst", dict(st="n29_warauna", wall="わらうな", pal="pop")),
    (124.1, "burst", dict(st="n10_kimeru", wall="ほんばん", pal="neon")),
    (125.8, "burst", dict(st="n08_yoyuu", wall="余裕だもん", pal="neon")),
    (126.69, "burst", dict(st="n32_honene", wall="もっと", pal="pop")),
    (127.57, "burst", dict(st="n17_sing", wall="余裕だもん", pal="cool")),
    (128.45, "scene", dict(img="art/generated/proof/c5_chorus_s6101_v5.png", z=(1.15, 1.0), c=(0.4, 0.4))),
    (130.2, "scrap", dict(st="n30_misebajan", side="r", theme="cream", inset="c02_fall")),
    (133.5, "sym", dict(sts=["n29_warauna", "n26_fukidasu"])),
    (136.3, "boop", dict(st="n19_me")),
    (138.0, "scrap", dict(st="n20_mouikkai", side="r", theme="sky")),
    (139.0, "scene", dict(img="art/generated/proof/c6_wink_s6101_v5.png", z=(1.0, 1.12), c=(0.5, 0.35))),
    (141.0, "scrap", dict(st="n01_peek", side="l", theme="mint")),
    (143.0, "stream", dict(st="n17_sing", theme="pink")),
    (147.0, "dark", dict(st="n31_utaikiru", light=True)),
    (150.3, "scene", dict(img="art/generated/proof/c5_chorus_s6101_v5.png", z=(1.0, 1.18), c=(0.5, 0.45))),
    (154.0, "scrap", dict(st="n32_honene", side="l", theme="cream")),
    (156.2, "burst", dict(st="n06_kanpeki", wall="余裕でしょ", pal="cool")),
    (158.5, "scrap", dict(st="n02_fufun", side="r", theme="sky")),
    (161.8, "scrap", dict(st="n33_matakite", side="l", theme="pink")),
    (166.0, "stream", dict(st="n33_matakite", theme="cream", ending=True)),
    (170.0, "pattern", dict(ids=["c01_sleep", "c08_dance", "c06_boop"], theme="sky", hold="c01_sleep")),
    (172.5, "card", dict(kind="end")),
]


def beat_index(t):
    return int(np.searchsorted(BEATS, t, side="right"))


def last_beat(t):
    i = beat_index(t) - 1
    return BEATS[i] if i >= 0 else -1.0


@lru_cache(maxsize=64)
def sticker(aid, height):
    im = Image.open(ST / f"{aid}.png").convert("RGBA")
    s = height / im.height
    im = im.resize((max(int(im.width * s), 1), height), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32) / 255
    return np.concatenate([a[..., :3] * a[..., 3:], a[..., 3:]], axis=-1)


@lru_cache(maxsize=16)
def scene_img(path):
    return C.load_rgb(ROOT / path)


def shadowed(rgba, off=(10, 14), k=0.35, blur=8):
    a = rgba[..., 3]
    sh = cv2.GaussianBlur(a, (0, 0), blur) * k
    sh = np.roll(np.roll(sh, off[1], 0), off[0], 1)[..., None]
    base = np.concatenate([np.array(NAVY, np.float32) * sh, sh], axis=-1)
    return rgba + base * (1 - rgba[..., 3:])


def place_sticker(frame, aid, cx, base_y, height, u, t, rot=0.0, pop=True, sway=True):
    """Sticker enters with an overshoot pop, then drifts and sways gently (no beat bouncing)."""
    s = C.ease_out_back(u / 0.22) if pop else 1.0
    s = 0.6 + 0.4 * s if pop else 1.0
    ang = rot + (1.3 * np.sin(t * 1.7) if sway else 0)
    dy = 5 * np.sin(t * 1.3)
    st = shadowed(sticker(aid, height))
    r = C.transform_rgba(st, s, ang)
    return C.over(frame, r, int(cx - r.shape[1] / 2), int(base_y - r.shape[0] + (r.shape[0] - st.shape[0] * s) / 2 + dy))


# ---------------- backgrounds ----------------
def fill(col, top=None):
    f = np.empty((H, W, 3), np.float32)
    if top is None:
        f[:] = col
    else:
        yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        f[:] = np.array(top, np.float32) * (1 - yy) + np.array(col, np.float32) * yy
    return f


def pattern_dots(frame, t, col, step=96, r=10, speed=(18, 10), k=0.55):
    ox, oy = (t * speed[0]) % step, (t * speed[1]) % step
    m = np.zeros((H, W), np.uint8)
    for j, y in enumerate(np.arange(-step, H + step, step) + oy):
        for x in np.arange(-step, W + step, step) + ox + (step / 2 if j % 2 else 0):
            cv2.circle(m, (int(x), int(y)), r, 255, -1, cv2.LINE_AA)
    a = (m.astype(np.float32) / 255 * k)[..., None]
    return frame * (1 - a) + np.array(col, np.float32) * a


def paw(canvas, x, y, s, val=255):
    cv2.ellipse(canvas, (int(x), int(y + s * 0.35)), (int(s * 0.5), int(s * 0.42)), 0, 0, 360, val, -1, cv2.LINE_AA)
    for dx, dy in ((-0.55, -0.25), (-0.2, -0.6), (0.2, -0.6), (0.55, -0.25)):
        cv2.circle(canvas, (int(x + dx * s), int(y + dy * s)), int(s * 0.2), val, -1, cv2.LINE_AA)


def scrap_bg(t, theme):
    base, light = THEMES[theme]
    f = fill(base, light)
    f = pattern_dots(f, t, (1, 1, 1), k=0.45)
    m = np.zeros((H, W), np.uint8)
    for i in range(7):
        x = (i * 311 + t * 22) % (W + 200) - 100
        y = 120 + (i * 173) % (H - 240)
        paw(m, x, y, 34 + (i % 3) * 8)
    a = (m.astype(np.float32) / 255 * 0.35)[..., None]
    f = f * (1 - a) + np.array(COBALT, np.float32) * a
    # scalloped lace frame
    fr = np.zeros((H, W), np.uint8)
    cv2.rectangle(fr, (40, 40), (W - 40, H - 40), 255, 22)
    for x in range(40, W - 40, 44):
        cv2.circle(fr, (x, 40), 18, 255, -1, cv2.LINE_AA)
        cv2.circle(fr, (x, H - 40), 18, 255, -1, cv2.LINE_AA)
    for y in range(40, H - 40, 44):
        cv2.circle(fr, (40, y), 18, 255, -1, cv2.LINE_AA)
        cv2.circle(fr, (W - 40, y), 18, 255, -1, cv2.LINE_AA)
    a = (fr.astype(np.float32) / 255)[..., None]
    f = f * (1 - a) + np.array((1, 1, 1), np.float32) * a
    inner = np.zeros((H, W), np.uint8)
    cv2.rectangle(inner, (64, 64), (W - 64, H - 64), 255, 3, cv2.LINE_AA)
    a = (inner.astype(np.float32) / 255 * 0.8)[..., None]
    return f * (1 - a) + np.array(COBALT, np.float32) * a


PALS = {"cool": [NAVY, (0.12, 0.2, 0.55), COBALT, (0.08, 0.1, 0.3)], "pop": [COBALT, SKY, (1, 1, 1), (0.98, 0.84, 0.29)],
        "neon": [(0.06, 0.08, 0.25), (0.18, 0.12, 0.55), COBALT, (0.05, 0.3, 0.6)]}


@lru_cache(None)
def _burst_grid():
    yy, xx = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32)
    ang = np.arctan2(yy - H / 4, xx - W / 4)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    glow = (np.clip(1 - np.hypot(yy - H / 2, xx - W / 2) / (W / 2), 0, 1) ** 2)[..., None]
    return ang, glow


def burst_bg(t, pal):
    cols = PALS[pal]
    bi = beat_index(t)
    c1, c2 = cols[bi % len(cols)], cols[(bi + 1) % len(cols)]
    ang, glow = _burst_grid()
    rays = (np.sin((ang + t * 0.25) * 18) > 0).astype(np.float32)
    rays = cv2.resize(cv2.GaussianBlur(rays, (0, 0), 0.8), (W, H))[..., None]
    f = np.array(c1, np.float32) * (1 - rays * 0.55) + np.array(c2, np.float32) * rays * 0.55
    return f * (1 - glow * 0.35) + np.array((1, 1, 1), np.float32) * glow * 0.35


def text_wall(frame, text, t, col=(1, 1, 1), k=0.85):
    size = 520 if len(text) <= 2 else 380 if len(text) <= 4 else 300
    rgba = C.text_rgba(text, size, fill=col, stroke=COBALT, stroke_w=14, shadow=False)
    sc = min(1.0, (W * 1.15) / rgba.shape[1])
    x = W / 2 + 40 * np.sin(t * 0.6)
    return C.put(frame, rgba, x, H / 2, scale=sc, alpha=k)


def lyric_at(t):
    for a, b, s in LYRICS:
        if a <= t < b:
            return a, b, s
    return None


def lyric_block(frame, t, x, y, size=78, vertical=False, fill=(1, 1, 1), stroke=COBALT, max_lines=3):
    """Current lyric, one phrase per line, characters popping in (kinetic typography)."""
    ly = lyric_at(t)
    if not ly:
        return frame
    a, b, text = ly
    parts = text.split("　")[:max_lines]
    n_all = sum(len(p) for p in parts)
    reveal = (t - a) / max((b - a) * 0.6, 0.3) * n_all
    k = 0
    for li, p in enumerate(parts):
        for ci, ch in enumerate(p):
            u = (reveal - k) / 1.5
            k += 1
            if u <= 0:
                continue
            rgba = C.text_rgba(ch, size, fill=fill, stroke=stroke)
            s = 0.5 + 0.5 * C.ease_out_back(min(u, 1))
            if vertical:
                cx, cy = x - li * size * 1.15, y + ci * size * 1.02
            else:
                cx, cy = x + ci * size * 1.0, y + li * size * 1.25
            frame = C.put(frame, rgba, cx, cy, scale=s)
    return frame


def small_caption_at(frame, t, y):
    ly = lyric_at(t)
    return frame if not ly else C.put(frame, C.text_rgba(ly[2], 50, fill=(1, 1, 1), stroke=NAVY, stroke_w=6), W / 2, y)


def small_caption(frame, t):
    ly = lyric_at(t)
    if not ly:
        return frame
    rgba = C.text_rgba(ly[2], 46, fill=(1, 1, 1), stroke=NAVY, stroke_w=6)
    return C.put(frame, rgba, W / 2, H - 92)


def chat_panel(frame, t, x0=1380, y0=150, w=470, h=760):
    panel = frame[y0:y0 + h, x0:x0 + w]
    panel[:] = panel * 0.25 + np.array((1, 1, 1), np.float32) * 0.75
    msgs = [c for c in CHAT if t - 9 < c[0] <= t][-9:]
    for i, (tm, name, msg) in enumerate(reversed(msgs)):
        y = y0 + h - 60 - i * 78
        u = min((t - tm) / 0.2, 1)
        nr = C.text_rgba(name, 26, fill=COBALT, stroke=(1, 1, 1), stroke_w=2, kind="Bold", shadow=False)
        mr = C.text_rgba(msg, 34, fill=NAVY, stroke=(1, 1, 1), stroke_w=2, kind="Bold", shadow=False)
        frame = C.over(frame, nr * u, x0 + 20, int(y - 30))
        frame = C.over(frame, mr * u, x0 + 20 + int(30 * (1 - u)), int(y))
    return frame


def stream_ui(frame, t, counter=None, ending=False):
    bar = np.zeros((H, W), np.uint8)
    cv2.rectangle(bar, (60, 60), (W - 60, H - 60), 255, 6, cv2.LINE_AA)
    a = (bar.astype(np.float32) / 255)[..., None]
    frame = frame * (1 - a) + np.array(NAVY, np.float32) * a
    frame[60:122, 60:W - 60] = frame[60:122, 60:W - 60] * 0.2 + np.array(NAVY, np.float32) * 0.8
    blink = 0.6 + 0.4 * (np.sin(t * 6) > 0)
    cv2.circle(frame, (100, 91), 12, (1.0 * blink, 0.48 * blink, 0.54 * blink), -1, cv2.LINE_AA)
    frame = C.over(frame, C.text_rgba("配信終了" if ending else "LIVE", 34, fill=(1, 1, 1), stroke=NAVY, stroke_w=2, shadow=False), 124, 66)
    frame = C.over(frame, C.text_rgba(f"{NAME}ちゃんねる", 30, fill=SKY, stroke=NAVY, stroke_w=2, kind="Bold", shadow=False), 300, 70)
    if counter is not None:
        frame = C.put(frame, C.text_rgba(f"ノーカン ×{counter}", 44, fill=C.LEMON, stroke=NAVY), 1600, 92)
    return chat_panel(frame, t)


def stamp(frame, text, t, t0, x, y, col=C.LEMON, size=150, rot=-8):
    u = (t - t0) / 0.18
    if u <= 0:
        return frame
    s = 1.6 - 0.6 * C.ease(min(u, 1))
    return C.put(frame, C.text_rgba(text, size, fill=col, stroke=NAVY, stroke_w=12), x, y, scale=s, angle=rot)


def finish(frame, t, i, k_grain=0.012):
    frame = C.diffusion(frame, k=0.12)
    frame = C.vignette(frame, k=0.12)
    return np.clip(C.grain(frame, i, k_grain), 0, 1)


# ---------------- layouts ----------------
def L_scrap(t, u, a):
    f = scrap_bg(t, a["theme"])
    side = a.get("side", "r")
    if a.get("zoom"):
        z, (fx, fy) = a["zoom"], a.get("focus", (0.5, 0.3))
        st = sticker(a["st"], int(1000 * z))
        x = int(W / 2 - st.shape[1] * fx)
        y = int(H / 2 - st.shape[0] * fy + 30 * np.sin(t * 0.8))
        f = C.over(f, shadowed(st), x, y)
        f = lyric_block(f, t, 170, 720, size=86)
    else:
        cx = W * (0.68 if side == "r" else 0.32)
        f = place_sticker(f, a["st"], cx, H - 40, 1000, u, t)
        f = lyric_block(f, t, 1500 if side == "l" else 420, 200, size=96, vertical=True)
    if a.get("stamps"):  # chat voices pile up around her, away from the lyric column
        x0 = W * (0.5 if side == "r" else 0.06)
        for j in range(6):
            t0 = 0.4 + j * 0.45
            f = stamp(f, a["stamps"], u, t0, x0 + (j * 211) % 760, 180 + (j * 263) % 700, col=(1.0, 0.6, 0.66),
                      size=86, rot=(-12 + 9 * j) % 24 - 12)
    if a.get("inset"):
        f = place_sticker(f, a["inset"], W * 0.47, H * 0.9, 380, u - 0.4, t, rot=-10)
    return f


def L_burst(t, u, a):
    f = burst_bg(t, a["pal"])
    f = text_wall(f, a["wall"], t, col=(1, 1, 1), k=0.8 if a["pal"] != "pop" else 0.95)
    f = place_sticker(f, a["st"], W / 2, H + 20, 1060, u, t, sway=False)
    f = C.particles(f, t, 11, n=30, color=(1, 1, 1), size=(3, 9), k=0.6)
    if u < 0.12:
        f = f + (1 - u / 0.12) * 0.35
    return small_caption(f, t)


def L_dark(t, u, a):
    top = (0.16, 0.2, 0.36) if not a.get("light") else (0.3, 0.42, 0.75)
    f = fill(INK if not a.get("light") else NAVY, top)
    f = C.particles(f, t, 5, n=50, color=SKY, size=(2, 6), k=0.5, drift=(0, -1))
    f = place_sticker(f, a["st"], W * 0.62, H + 20, 1100, u, t, pop=False)
    f = C.beams(f, t, [(0.62, -0.1)], color=SKY, k=0.25, spread=0.18, speed=0.15) if a.get("light") else f
    return lyric_block(f, t, 470, 160, size=92, vertical=True, fill=(1, 1, 1), stroke=COBALT)


def L_scene(t, u, a, d):
    img = scene_img(a["img"])
    z = a["z"][0] + (a["z"][1] - a["z"][0]) * C.ease(u / max(d, 0.1))
    h0, w0 = img.shape[:2]
    canvas = cv2.resize(img, (int(w0 * 1920 / w0 * 1.15), int(h0 * 1920 / w0 * 1.15)), interpolation=cv2.INTER_CUBIC)
    f = C.camera(canvas, (W, H), zoom=z, cx=a["c"][0], cy=a["c"][1])
    f = C.particles(f, t, 21, n=35, color=(1, 1, 1), size=(3, 10), k=0.55)
    return small_caption(f, t)


def L_stream(t, u, a):
    f = scrap_bg(t, a["theme"])
    f = place_sticker(f, a["st"], 720, H - 60, 900, u, t)
    f = stream_ui(f, t, a.get("counter"), a.get("ending", False))
    if a.get("stamp"):
        f = stamp(f, a["stamp"], u, 0.9, 760, 300, size=170)
    if a.get("shutter") is not None and 0 <= t - a["shutter"] < 0.25:
        f = f * 0 + 1.0 - (t - a["shutter"]) / 0.25 * 0.6
    return lyric_block(f, t, 160, 260, size=72, vertical=False)


def L_sym(t, u, a):
    bi = beat_index(t)
    cols = [COBALT, SKY, NAVY, (1, 1, 1)]
    f = fill(cols[bi % 4])
    side = np.array(cols[(bi + 2) % 4], np.float32)
    f[:, :560] = side
    f[:, W - 560:] = side
    sts = a["sts"]
    f = place_sticker(f, sts[bi % 2], 280, H - 30, 820, 1, t, pop=False, sway=False)
    f = place_sticker(f, sts[(bi + 1) % 2], W - 280, H - 30, 820, 1, t, pop=False, sway=False)
    m = np.zeros((H, W), np.uint8)
    paw(m, W / 2, H / 2 - 40, 150 + 20 * np.exp(-(t - last_beat(t)) / 0.1))
    al = (m.astype(np.float32) / 255)[..., None]
    f = f * (1 - al) + np.array(C.LEMON if bi % 2 else (1, 1, 1), np.float32) * al
    return small_caption(f, t)


def L_boop(t, u, a):
    f = burst_bg(t, "pop")
    st = sticker(a["st"], 1500)
    s = 1.0 + 0.25 * C.ease(min(u / 0.25, 1))
    f = C.put(f, shadowed(st), W / 2, H / 2 + 260, scale=s * 0.9)
    f = stamp(f, "めっ", u, 0.2, W * 0.76, H * 0.3, col=(1.0, 0.48, 0.54), size=220, rot=10)
    return small_caption(f, t)


def L_eyes(t, u, a):
    st = sticker(a["st"], 3600)
    f = fill(NAVY)
    f = C.over(f, st, int(W / 2 - st.shape[1] * 0.5), int(-st.shape[0] * 0.115 + 20 * np.sin(t)))
    f[:170] = np.array(INK, np.float32)
    f[H - 170:] = np.array(INK, np.float32)
    return lyric_block(f, t, 200, 85, size=60, max_lines=2) if False else small_caption_at(f, t, H - 85)


def L_comic(t, u, a):
    f = fill(CREAM)
    panels = [((70, 70, 1010, 600), "n11_trip", 0.0), ((1040, 70, 1850, 600), "c02_fall", 0.5),
              ((70, 630, 1100, 1010), "n12_aitata", 1.2), ((1130, 630, 1850, 1010), "n13_matta", 1.9)]
    for (x0, y0, x1, y1), aid, t0 in panels:
        if u < t0:
            continue
        sub = np.empty((y1 - y0, x1 - x0, 3), np.float32)
        sub[:] = (0.86, 0.92, 1.0) if aid != "c02_fall" else (1.0, 0.95, 0.75)
        st = sticker(aid, int((y1 - y0) * 1.25))
        sub = C.over(sub, st, (sub.shape[1] - st.shape[1]) // 2, sub.shape[0] - st.shape[0] + int(st.shape[0] * 0.2))
        f[y0:y1, x0:x1] = sub
        cv2.rectangle(f, (x0, y0), (x1, y1), NAVY, 8)
    f = stamp(f, "えっ", u, 0.0, 760, 180, col=(1, 1, 1), size=120)
    f = stamp(f, "ドテッ", u, 0.5, 1500, 470, size=150)
    shake = (0, 0)
    if 0.45 < u < 0.9:
        shake = (12 * np.sin(u * 90), 10 * np.cos(u * 70))
    f = np.roll(f, (int(shake[1]), int(shake[0])), (0, 1))
    return small_caption(f, t)


def L_polaroid(t, u, a):
    f = scrap_bg(t, "cream")
    pw, ph = 760, 900
    card = np.ones((ph, pw, 3), np.float32)
    inner = np.empty((640, 680, 3), np.float32)
    inner[:] = SKY
    st = sticker(a["st"], 800)
    inner = C.over(inner, st, (680 - st.shape[1]) // 2, 640 - st.shape[0] + 160)
    card[40:680, 40:720] = inner
    rgba = np.concatenate([card, np.ones((ph, pw, 1), np.float32)], -1)
    f = C.put(f, rgba, W * 0.5, H * 0.5, scale=0.95, angle=-6 + 2 * np.sin(t))
    f = stamp(f, "きんし!", u, 0.5, W * 0.5, H * 0.78, col=(1.0, 0.48, 0.54), size=140, rot=-4)
    return lyric_block(f, t, 230, 220, size=70, vertical=True)


def L_pattern(t, u, a):
    f = fill(THEMES[a["theme"]][0], THEMES[a["theme"]][1])
    ids = a["ids"]
    for j in range(5):
        for i in range(7):
            aid = ids[(i + j) % len(ids)]
            x = (i * 300 + t * 60 + (150 if j % 2 else 0)) % (W + 300) - 150
            y = (j * 260 - t * 30) % (H + 260) - 130
            f = C.put(f, sticker(aid, 300), x, y, angle=(i * 13 + j * 7) % 20 - 10, alpha=0.9)
    if a.get("hold"):
        f = f * 0.55 + np.array(THEMES[a["theme"]][1], np.float32) * 0.45
        f = place_sticker(f, a["hold"], W / 2, H * 0.78, 560, u, t)
    return f


def L_card(t, u, a, d):
    f = fill(SKY, (1, 1, 1))
    f = pattern_dots(f, t, (1, 1, 1), k=0.6)
    if a["kind"] == "title":
        f = place_sticker(f, "n08_yoyuu", W * 0.72, H + 10, 1050, u, t)
        f = C.put(f, C.text_rgba("余裕だもん", 190, fill=(1, 1, 1), stroke=COBALT, stroke_w=16), W * 0.34, H * 0.42,
                  scale=0.6 + 0.4 * C.ease_out_back(min(u / 0.35, 1)))
        f = C.put(f, C.text_rgba(f"{NAME}", 80, fill=NAVY, stroke=(1, 1, 1)), W * 0.34, H * 0.64, alpha=min(max((u - 0.6) / 0.4, 0), 1))
        f = C.put(f, C.text_rgba("Vocal: AI (Gemini)  /  Art: NovelAI", 34, fill=NAVY, stroke=(1, 1, 1), kind="Bold"),
                  W * 0.34, H * 0.76, alpha=min(max((u - 0.9) / 0.4, 0), 1))
    else:
        f = place_sticker(f, "n33_matakite", W * 0.3, H + 10, 1000, u, t)
        f = C.put(f, C.text_rgba("余裕だもん", 150, fill=(1, 1, 1), stroke=COBALT, stroke_w=14), W * 0.68, H * 0.38)
        f = C.put(f, C.text_rgba("また来てよね", 80, fill=NAVY, stroke=(1, 1, 1)), W * 0.68, H * 0.58)
        f = f * (1 - np.clip((u - d + 1.2) / 1.2, 0, 1))
    return f


def L_flash(t, u, a, d):
    f = burst_bg(t, "pop")
    return f * (1 - np.clip(u / d, 0, 1)) + np.clip(u / d, 0, 1)


def L_seeno(t, u, a, d):
    f = burst_bg(t, "neon")
    f = C.put(f, C.text_rgba("せーの", 260, fill=(1, 1, 1), stroke=COBALT, stroke_w=18), W / 2, H / 2,
              scale=0.7 + 0.5 * C.ease(u / d))
    return f + np.clip((u - d + 0.3) / 0.3, 0, 1)


def render(t, i):
    k = max(j for j, s in enumerate(SHOTS) if s[0] <= t)
    t0, kind, a = SHOTS[k]
    d = (SHOTS[k + 1][0] if k + 1 < len(SHOTS) else DUR) - t0
    u = t - t0
    if kind in ("scene", "card", "flash", "seeno"):
        f = globals()[f"L_{kind}"](t, u, a, d)
    else:
        f = globals()[f"L_{kind}"](t, u, a)
    return finish(f, t, i)


def to8(f):
    return (np.clip(f, 0, 1) * 255 + 0.5).astype(np.uint8)


def main():
    if sys.argv[1] == "preview":
        ts = [float(x) for x in sys.argv[2:sys.argv.index("--out")]]
        tiles = [Image.fromarray(to8(render(t, int(t * FPS)))).resize((480, 270)) for t in ts]
        cols = 4
        sheet = Image.new("RGB", (480 * cols, 270 * ((len(tiles) + cols - 1) // cols)))
        for j, tl in enumerate(tiles):
            sheet.paste(tl, ((j % cols) * 480, (j // cols) * 270))
        sheet.save(sys.argv[-1], quality=88)
        return
    seg, n, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[-1]
    total = int(DUR * FPS)
    a, b = total * seg // n, total * (seg + 1) // n
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt",
                          "yuv420p", out], stdin=subprocess.PIPE)
    for i in range(a, b):
        p.stdin.write(to8(render(i / FPS, i)).tobytes())
    p.stdin.close()
    p.wait()


if __name__ == "__main__":
    main()
