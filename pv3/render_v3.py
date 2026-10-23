"""「余裕だもん」 PV v3: phrase-synced storyboard, moving characters, one typographic system.

Fixes over v2 (owner review 2026-10-23):
- sync: every cut lands on the first sung syllable of its phrase (pv3/lyrics_timed.json, ASR-aligned); accent
  words appear on their exact syllable; heads nod on the beat.
- motion: every drawing is deformed by pv3/autorig.py (head tilt/nod, hair follow-through, breathing, entrance
  recoil) and every shot has a camera move; chorus shots pulse on the beat.
- typography: one lyric track (bottom centre, whole line, karaoke fill as sung) + at most one accent word per
  shot in a fixed zone opposite the character. No duplicate or vertical lyric blocks, no random stamps.
- repetition: one drawing per phrase (75 drawings); repeats only as chorus/hook motifs.
usage: render_v3.py preview <t...> --out sheet.jpg | segment <i> <n> --out seg.mp4
"""
import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render as R  # noqa: E402  (v2 backgrounds, stream UI, palette)
from autorig import Rig  # noqa: E402

C = R.C
W, H, FPS, DUR = R.W, R.H, R.FPS, R.DUR
NAVY, COBALT, SKY = R.NAVY, R.COBALT, R.SKY

TIMED = json.load(open(HERE / "lyrics_timed.json"))
PH = [p for l in TIMED for p in l["phrases"]]
# known exact hits (SFX were placed on these syllables)
FIX = {32: 66.82, 65: 137.36, 66: 137.8, 14: 42.6, 40: 84.645}
for i, t in FIX.items():
    d = t - PH[i]["t"]
    PH[i]["t"] = t
    PH[i]["chars"] = [c + d for c in PH[i]["chars"]]


def P(i, lead=0.06):
    return PH[i]["t"] - lead


# shot: (start, layout, args). accent=(text, phrase index) -> appears on that phrase's first syllable.
SHOTS = [
    (0.0, "pattern", dict(ids=["c01_sleep", "c08_dance", "c06_boop"], theme="sky", hold="c01_sleep", energy=0.4)),
    (2.55, "close", dict(st="d01_wake", theme="cream", zoom=(1.0, 1.08))),
    (P(0), "scrap", dict(st="n01_peek", side="r", theme="sky", accent=("ねえねえ", 0))),
    (P(1), "close", dict(st="d02_lookhere", theme="mint", zoom=(1.05, 1.15), accent=("見ててよね", 1, 5))),
    (P(2), "scrap", dict(st="n02_fufun", side="l", theme="cream", accent=("ふふん", 2))),
    (P(3), "scrap", dict(st="d03_stretch", side="r", theme="sky")),
    (P(4), "burst", dict(st="n03_ikuyo", wall="いくよ", pal="cool", accent=("いくよ!", 4), energy=1.2)),
    (11.05, "card", dict(kind="title", st="d04_jump")),
    (P(5), "scrap", dict(st="d05_proud", side="r", theme="mint")),
    (P(6), "burst", dict(st="n04_tensai", wall="大天才", pal="cool", accent=("大天才", 6), energy=1.2)),
    (P(7), "stream", dict(st="n05_batchiri", theme="sky")),
    (P(8), "burst", dict(st="n06_kanpeki", wall="完璧", pal="pop", accent=("完璧じゃん", 8), energy=1.2)),
    (25.4, "pattern", dict(ids=["c08_dance", "c06_boop", "c05_sign"], theme="mint", energy=0.8)),
    (P(9), "scrap", dict(st="n07_zannen", side="l", theme="pink", accent=("ざんねん", 9))),
    (P(10), "burst", dict(st="n08_yoyuu", wall="余裕", pal="pop", accent=("余裕だもん", 10), energy=1.3)),
    (33.6, "stage", dict(st="d25_skypoint", energy=1.0, zoom=(1.12, 1.0))),
    (P(11), "burst", dict(st="n09_smart", wall="ほら", pal="cool", energy=1.2)),
    (P(12), "close", dict(st="d06_hairflip", theme="cool", zoom=(1.0, 1.1), accent=("スマートに", 12))),
    (P(13), "stage", dict(st="n10_kimeru", energy=1.4, zoom=(1.0, 1.08), accent=("キメちゃうよ", 13))),
    (P(14), "comic", dict()),
    (P(17), "stream", dict(st="n14_nocount", theme="mint", counter=1, accent=("ノーカン", 17))),
    (P(20), "stream", dict(st="n15_niyake", theme="pink", nyaa=True)),
    (P(22), "close", dict(st="d07_hotcheeks", theme="pink", zoom=(1.0, 1.12))),
    (P(23), "scrap", dict(st="n16_shinkokyu", side="r", theme="sky", energy=0.4)),
    (P(24), "close", dict(st="d08_seeno", theme="cool", zoom=(1.0, 1.25), accent=("せーの", 24))),
    (P(25), "burst", dict(st="n17_sing", wall="余裕だもん", pal="neon", energy=1.6, accent=("余裕だもん", 25))),
    (P(26), "burst", dict(st="d09_singpoint", wall="ほら", pal="pop", energy=1.6)),
    (P(27), "stage", dict(st="n08_yoyuu", energy=1.6, zoom=(1.0, 1.1), accent=("余裕だもん", 27))),
    (P(28), "scrap", dict(st="n18_fufun2", side="r", theme="cream", accent=("ふふん", 28))),
    (P(29), "scrap", dict(st="d10_turnaway", side="l", theme="sky")),
    (P(30), "sign", dict(st="c05_sign", text="ノーカン", theme="pink")),
    (P(31), "sym", dict(sts=["n29_warauna", "n26_fukidasu"], energy=1.2)),
    (P(32), "boop", dict(st="n19_me")),
    (P(33), "scrap", dict(st="n20_mouikkai", side="l", theme="mint", accent=("もういっかい", 33))),
    (P(34), "scrap", dict(st="n21_yosomi", side="r", theme="sky")),
    (P(35), "close", dict(st="d11_gentle", theme="cream", zoom=(1.0, 1.15))),
    (P(36), "dark", dict(st="n22_tsuyogari")),
    (P(37), "close", dict(st="d12_serious", theme="cool", zoom=(1.0, 1.15), accent=("本気だもん", 37))),
    (P(38), "close", dict(st="d13_singclose", theme="cool", zoom=(1.0, 1.12))),
    (P(39), "stage", dict(st="d14_jumpmic", energy=1.5, zoom=(1.0, 1.1), accent=("キメちゃうよ", 39))),
    (83.0, "pattern", dict(ids=["c03_dizzy", "c06_boop", "c08_dance"], theme="cream", energy=0.8)),
    (P(40, 0.03), "stream", dict(st="n23_screenshot", theme="cream", shutter=84.645)),
    (P(41), "polaroid", dict(st="n13_matta", accent=("きんし!", 41))),
    (P(42), "scrap", dict(st="d15_flustered", side="r", theme="pink")),
    (P(43), "scrap", dict(st="n24_namaiki", side="l", theme="pink", accent=("なまいき", 43))),
    (P(44), "burst", dict(st="c04_stomp", wall="もん!", pal="pop", energy=1.3)),
    (95.6, "pattern", dict(ids=["c03_dizzy", "c07_cry", "c04_stomp"], theme="pink", energy=0.8)),
    (P(45), "scrap", dict(st="n25_pui", side="r", theme="mint", accent=("ぷいっ", 45))),
    (P(46), "scrap", dict(st="d16_back", side="l", theme="sky")),
    (P(47), "close", dict(st="d17_peek", theme="mint", zoom=(1.0, 1.1))),
    (P(48), "close", dict(st="d18_eyes", theme="cream", zoom=(1.0, 1.2))),
    (P(49), "stream", dict(st="n26_fukidasu", theme="sky")),
    (P(50), "dark", dict(st="n27_kuyashii")),
    (P(51), "close", dict(st="d19_wipetear", theme="cool", zoom=(1.0, 1.1))),
    (P(52), "scrap", dict(st="d20_angel", side="r", theme="cream", accent=("いいこちゃん", 52))),
    (P(53), "scrap", dict(st="d21_devil", side="l", theme="pink", accent=("つまんない", 53))),
    (P(54), "detail", dict(st="d22_tiptoe")),
    (P(55), "stage", dict(st="n28_step", energy=1.3, zoom=(1.08, 1.0))),
    (P(56), "close", dict(st="d23_shout", theme="pop", zoom=(1.1, 1.0), accent=("わらうな", 56))),
    (P(57), "scrap", dict(st="d24_sleeves", side="r", theme="cream")),
    (P(58), "stage", dict(st="d25_skypoint", energy=1.4, zoom=(1.0, 1.12), accent=("ほんばん", 58))),
    (P(59), "burst", dict(st="n08_yoyuu", wall="余裕だもん", pal="neon", energy=1.7, accent=("余裕だもん", 59))),
    (P(60), "burst", dict(st="n32_honene", wall="もっと", pal="pop", energy=1.7)),
    (P(61), "stage", dict(st="n17_sing", energy=1.7, zoom=(1.12, 1.0), accent=("余裕だもん", 61))),
    (P(62), "comic2", dict()),
    (P(63), "scrap", dict(st="n30_misebajan", side="r", theme="cream", accent=("見せ場じゃん", 63))),
    (P(64), "sym", dict(sts=["d26_tease", "n26_fukidasu"], energy=1.3)),
    (P(65, 0.5), "boop", dict(st="n19_me")),
    (P(66), "scrap", dict(st="c06_boop", side="l", theme="mint")),
    (P(67), "close", dict(st="d27_frame", theme="sky", zoom=(1.0, 1.12))),
    (P(68), "close", dict(st="d28_shh", theme="cream", zoom=(1.0, 1.1))),
    (P(69), "stream", dict(st="c08_dance", theme="pink", nyan=True)),
    (P(70), "close", dict(st="d29_reach", theme="sky", zoom=(1.15, 1.0))),
    (P(71), "dark", dict(st="n31_utaikiru", light=True)),
    (P(72), "stage", dict(st="d30_powersing", energy=1.4, zoom=(1.0, 1.15), accent=("歌いきるよ", 72))),
    (P(73), "scrap", dict(st="d31_wink", side="l", theme="cream")),
    (P(74), "scrap", dict(st="d32_nod", side="r", theme="sky")),
    (P(75), "burst", dict(st="n06_kanpeki", wall="余裕でしょ", pal="cool", energy=1.3, accent=("余裕でしょ", 75))),
    (P(76), "close", dict(st="d33_chin", theme="cream", zoom=(1.0, 1.08))),
    (P(77), "scrap", dict(st="d34_shy", side="l", theme="pink")),
    (P(78), "scrap", dict(st="n33_matakite", side="r", theme="sky", accent=("また来てよね", 78))),
    (166.0, "stream", dict(st="n33_matakite", theme="cream", ending=True)),
    (170.0, "pattern", dict(ids=["c01_sleep", "c08_dance", "c06_boop"], theme="sky", hold="c01_sleep", energy=0.3)),
    (172.5, "card", dict(kind="end", st="n33_matakite")),
]
SHOTS.sort(key=lambda s: s[0])


# ---------------- character ----------------
@lru_cache(maxsize=48)
def rig(aid, height):
    im = Image.open(R.ST / f"{aid}.png").convert("RGBA")
    src_h = im.height
    im = im.resize((max(int(im.width * height / src_h), 1), height), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32) / 255
    return Rig(aid, np.concatenate([a[..., :3] * a[..., 3:], a[..., 3:]], axis=-1), src_h)


def char(frame, aid, cx, base_y, height, t, u, energy=1.0, tilt=0.0, pop=True, flip=False):
    """Deformed (living) drawing with soft shadow; enters with an overshoot pop and a recoil."""
    r = rig(aid, height)
    phase = t - R.last_beat(t)
    rgba = r.render(t, energy=energy, beat_phase=phase, tilt=tilt, settle=max(0.0, 1 - u / 0.3) if pop else 0.0)
    if flip:
        rgba = rgba[:, ::-1]
    rgba = R.shadowed(rgba)
    s = (0.86 + 0.14 * C.ease_out_back(min(u / 0.2, 1))) if pop else 1.0
    if abs(s - 1.0) > 1e-3:
        rgba = cv2.resize(rgba, (max(int(rgba.shape[1] * s), 1), max(int(rgba.shape[0] * s), 1)), interpolation=cv2.INTER_LINEAR)
    return C.over(frame, rgba, int(cx - rgba.shape[1] / 2), int(base_y - rgba.shape[0]))


# ---------------- typography ----------------
LYR_SIZE, LYR_Y = 66, H - 100


@lru_cache(maxsize=64)
def line_imgs(text):
    base = C.text_rgba(text, LYR_SIZE, fill=(1, 1, 1), stroke=NAVY, stroke_w=7)
    sung = C.text_rgba(text, LYR_SIZE, fill=COBALT, stroke=(1, 1, 1), stroke_w=7)
    f = C.font(LYR_SIZE)
    sw = 7
    x0 = 8 + sw - f.getbbox(text, stroke_width=sw)[0]
    edges = [x0 + f.getlength(text[:k]) for k in range(len(text) + 1)]
    return base, sung, edges


def current_line(t):
    for k, l in enumerate(TIMED):
        nxt = TIMED[k + 1]["start"] if k + 1 < len(TIMED) else 1e9
        if l["start"] - 0.3 <= t < min(nxt - 0.08, l["end"] + 0.7):
            return l
    return None


def lyric_track(frame, t):
    l = current_line(t)
    if l is None:
        return frame
    text = l["line"]
    chars = [c for p in l["phrases"] for c in p["chars"] + [None]][:-1]
    base, sung, edges = line_imgs(text)
    # progress in px: the current character fills over its own duration
    x = edges[0]
    for k, ct in enumerate(chars):
        if ct is None:
            continue
        nt = next((c for c in chars[k + 1:] if c is not None), ct + 0.35)
        if t >= ct:
            x = edges[k] + (edges[k + 1] - edges[k]) * min((t - ct) / max(nt - ct, 0.08), 1.0)
    img = base.copy()
    xi = int(x)
    img[:, :xi] = sung[:, :xi]
    fade = min((t - l["start"] + 0.3) / 0.18, 1.0, (min(l["end"] + 0.7, 999) - t) / 0.2)
    dy = int(14 * (1 - min((t - l["start"] + 0.3) / 0.18, 1.0)))
    return C.put(frame, img, W / 2, LYR_Y + dy, alpha=max(min(fade, 1.0), 0.0))


def accent(frame, t, spec, side):
    """One big word per shot, landing on its syllable, in the zone opposite the character."""
    if not spec:
        return frame
    text, pi = spec[0], spec[1]
    k = spec[2] if len(spec) > 2 else 0
    at = PH[pi]["chars"][min(k, len(PH[pi]["chars"]) - 1)]
    u = t - at
    if u < 0:
        return frame
    size = 160 if len(text) <= 4 else 120 if len(text) <= 6 else 100
    img = C.text_rgba(text, size, fill=(1, 1, 1), stroke=COBALT, stroke_w=14)
    s = 1.0 + 0.45 * np.exp(-u / 0.07)
    # zone opposite the character, kept clear of the head and of the lyric track
    cx = W * (0.25 if side == "r" else 0.75) if side in ("l", "r") else W / 2
    cy = H * 0.36
    shake = 6 * np.exp(-u / 0.08) * np.sin(u * 90)
    return C.put(frame, img, cx + shake, cy, scale=min(s, 1.45), angle=-4 if side != "l" else 4)


# ---------------- backgrounds / layouts ----------------
@lru_cache(maxsize=4)
def stage_plate(blur):
    im = C.load_rgb(HERE.parent / "pv2/bg/stage_dream_blue_x2.png")
    h, w = im.shape[:2]
    crop = im[int(h * 0.06):int(h * 0.06) + int(w * 9 / 16), :]
    crop = cv2.resize(crop, (W, H), interpolation=cv2.INTER_AREA)
    return cv2.GaussianBlur(crop, (0, 0), blur) if blur else crop


def soft_bg(theme):
    if theme in ("cool", "pop"):
        return R.burst_bg(0.0, "cool" if theme == "cool" else "pop") * 0.85 + 0.15 * np.array(SKY, np.float32)
    base, light = R.THEMES[theme]
    return R.fill(base, light)


def L_scrap(t, u, d, a):
    f = R.scrap_bg(t, a["theme"])
    side = a.get("side", "r")
    f = char(f, a["st"], W * (0.66 if side == "r" else 0.34), H + 30, 1020, t, u, a.get("energy", 0.9))
    return accent(f, t, a.get("accent"), side), (1.0, 1.04)


def L_burst(t, u, d, a):
    f = R.burst_bg(t, a["pal"])
    if not a.get("accent"):  # one big word at a time: the wall only when there is no accent word
        f = R.text_wall(f, a["wall"], t, col=(1, 1, 1), k=0.35 if a["pal"] != "pop" else 0.5)
    cx = W * (0.64 if a.get("accent") else 0.5)
    f = char(f, a["st"], cx, H + 40, 1060, t, u, a.get("energy", 1.3))
    f = C.particles(f, t, 11, n=30, color=(1, 1, 1), size=(3, 9), k=0.6)
    return accent(f, t, a.get("accent"), "r"), (1.06, 1.0)


def L_stage(t, u, d, a):
    f = stage_plate(5).copy()
    f = C.beams(f, t, [(0.2, -0.05), (0.8, -0.05), (0.5, -0.1)], color=(0.85, 0.93, 1.0), k=0.35, speed=0.35)
    f = C.contact_shadow(f, W / 2, H - 70, 260, 34, k=0.4)
    f = char(f, a["st"], W / 2, H + 10, 1040, t, u, a.get("energy", 1.3))
    f = C.particles(f, t, 23, n=40, color=(1, 1, 1), size=(3, 10), k=0.6)
    return accent(f, t, a.get("accent"), "r"), a.get("zoom", (1.0, 1.06))


def L_close(t, u, d, a):
    f = soft_bg(a["theme"]).copy()
    f = R.pattern_dots(f, t, (1, 1, 1), k=0.25) if a["theme"] not in ("cool", "pop") else f
    r = rig(a["st"], 1900)
    fx, fy, fw, fh = r.face
    x = int(W / 2 - (fx + fw / 2))
    y = int(H * 0.46 - (fy + fh / 2))
    rgba = r.render(t, energy=0.8, beat_phase=t - R.last_beat(t), settle=0)
    f = C.over(f, R.shadowed(rgba, off=(14, 18)), x, y)
    return accent(f, t, a.get("accent"), "r"), a.get("zoom", (1.0, 1.1))


def L_stream(t, u, d, a):
    f = R.scrap_bg(t, a["theme"])
    f = char(f, a["st"], 700, H + 20, 960, t, u, 1.0)
    f = R.stream_ui(f, t, a.get("counter"), a.get("ending", False))
    if a.get("shutter") is not None and 0 <= t - a["shutter"] < 0.25:
        f = f * 0 + 1.0 - (t - a["shutter"]) / 0.25 * 0.6
    if a.get("nyaa"):  # ニヤニヤ flood inside the chat panel's column only
        for j in range(5):
            f = R.stamp(f, "ニヤニヤ", u, 0.3 + j * 0.35, 1615, 230 + j * 130, col=(1.0, 0.6, 0.66), size=64, rot=-6)
    return accent(f, t, a.get("accent"), "l"), (1.0, 1.03)


def L_dark(t, u, d, a):
    top = (0.16, 0.2, 0.36) if not a.get("light") else (0.3, 0.42, 0.75)
    f = R.fill(R.INK if not a.get("light") else NAVY, top)
    f = C.particles(f, t, 5, n=50, color=SKY, size=(2, 6), k=0.5, drift=(0, -1))
    if a.get("light"):
        f = C.beams(f, t, [(0.55, -0.1)], color=SKY, k=0.3, spread=0.18, speed=0.15)
    f = char(f, a["st"], W * 0.55, H + 30, 1100, t, u, 0.6, pop=False)
    return f, (1.0, 1.08)


def L_comic(t, u, d, a, ids=("n11_trip", "c02_fall", "n12_aitata", "n13_matta"), times=None):
    f = R.fill(R.CREAM)
    times = times or [PH[14]["t"], PH[15]["t"], PH[15]["chars"][3], PH[16]["t"]]
    boxes = [(70, 70, 1010, 600), (1040, 70, 1850, 600), (70, 630, 1100, 990), (1130, 630, 1850, 990)]
    for (x0, y0, x1, y1), aid, ta in zip(boxes, ids, times):
        if t < ta:
            continue
        sub = np.empty((y1 - y0, x1 - x0, 3), np.float32)
        sub[:] = (0.86, 0.92, 1.0) if aid != "c02_fall" else (1.0, 0.95, 0.75)
        sub = char(sub, aid, sub.shape[1] / 2, sub.shape[0] + int((y1 - y0) * 0.25), int((y1 - y0) * 1.25), t, t - ta, 1.0)
        f[y0:y1, x0:x1] = sub
        cv2.rectangle(f, (x0, y0), (x1, y1), NAVY, 8)
    f = R.stamp(f, "えっ", t, times[0], 760, 180, col=(1, 1, 1), size=120)
    f = R.stamp(f, "ドテッ", t, times[1], 1500, 470, size=150)
    if times[1] < t < times[1] + 0.4:
        k = (times[1] + 0.4 - t) / 0.4
        f = np.roll(f, (int(14 * k * np.sin(t * 90)), int(12 * k * np.cos(t * 70))), (0, 1))
    return f, (1.0, 1.0)


def L_comic2(t, u, d, a):
    return L_comic(t, u, d, a, ids=("c02_fall", "n12_aitata", "d19_wipetear", "n30_misebajan"),
                   times=[PH[62]["t"], PH[62]["chars"][2], PH[62]["chars"][4], PH[62]["chars"][5] + 0.3])


def L_sym(t, u, d, a):
    bi = R.beat_index(t)
    cols = [COBALT, SKY, NAVY, (1, 1, 1)]
    f = R.fill(cols[bi % 4])
    side = np.array(cols[(bi + 2) % 4], np.float32)
    f[:, :560] = side
    f[:, W - 560:] = side
    sts = a["sts"]
    f = char(f, sts[bi % 2], 280, H + 20, 860, t, 1, a.get("energy", 1.2), pop=False)
    f = char(f, sts[(bi + 1) % 2], W - 280, H + 20, 860, t, 1, a.get("energy", 1.2), pop=False, flip=True)
    m = np.zeros((H, W), np.uint8)
    R.paw(m, W / 2, H / 2 - 60, 150 + 30 * np.exp(-(t - R.last_beat(t)) / 0.1))
    al = (m.astype(np.float32) / 255)[..., None]
    f = f * (1 - al) + np.array(C.LEMON if bi % 2 else (1, 1, 1), np.float32) * al
    return f, (1.0, 1.0)


def L_boop(t, u, d, a):
    f = R.burst_bg(t, "pop")
    r = rig(a["st"], 1500)
    rgba = r.render(t, energy=0.6, beat_phase=t - R.last_beat(t))
    hit = PH[32]["t"] if t < 100 else PH[65]["t"]
    k = C.ease(min(max((t - hit + 0.25) / 0.25, 0), 1))
    f = C.put(f, R.shadowed(rgba), W / 2, H / 2 + 300, scale=0.85 + 0.2 * k)
    f = R.stamp(f, "めっ", t, hit, W * 0.76, H * 0.3, col=(1.0, 0.48, 0.54), size=230, rot=10)
    if 0 <= t - hit < 0.1:
        f = f * 0.5 + 0.5
    return f, (1.0, 1.0)


def L_sign(t, u, d, a):
    f = R.scrap_bg(t, a["theme"])
    f = char(f, a["st"], W / 2, H + 20, 1000, t, u, 1.0)
    at = PH[30]["chars"][0]
    if t >= at:
        f = C.put(f, C.text_rgba(a["text"], 92, fill=NAVY, stroke=(1, 1, 1), stroke_w=4, shadow=False), W / 2 + 4, H * 0.52,
                  scale=1 + 0.3 * np.exp(-(t - at) / 0.08), angle=-3)
    return f, (1.0, 1.06)


def L_polaroid(t, u, d, a):
    f = R.scrap_bg(t, "cream")
    pw, ph = 760, 900
    card = np.ones((ph, pw, 3), np.float32)
    inner = np.empty((640, 680, 3), np.float32)
    inner[:] = SKY
    inner = char(inner, a["st"], 340, 640 + 170, 820, t, u, 0.8)
    card[40:680, 40:720] = inner
    rgba = np.concatenate([card, np.ones((ph, pw, 1), np.float32)], -1)
    f = C.put(f, R.shadowed(rgba), W * 0.64, H * 0.47, scale=0.9 + 0.1 * C.ease_out_back(min(u / 0.25, 1)), angle=-6 + 2 * np.sin(t))
    return accent(f, t, a.get("accent"), "r"), (1.0, 1.04)


def L_detail(t, u, d, a):
    f = R.scrap_bg(t, "sky")
    tremble = 3 * np.sin(t * 60)
    f = char(f, a["st"], W / 2 + tremble, H + 380, 1700, t, u, 0.3)
    return f, (1.0, 1.06)


def L_pattern(t, u, d, a):
    f = R.fill(R.THEMES[a["theme"]][0], R.THEMES[a["theme"]][1])
    ids = a["ids"]
    for j in range(4):
        for i in range(6):
            aid = ids[(i + j) % len(ids)]
            x = (i * 360 + t * 70 + (180 if j % 2 else 0)) % (W + 360) - 180
            y = (j * 320 - t * 36) % (H + 320) - 160
            f = C.put(f, R.sticker(aid, 300), x, y, angle=(i * 13 + j * 7) % 20 - 10, alpha=0.85)
    if a.get("hold"):
        f = f * 0.5 + np.array(R.THEMES[a["theme"]][1], np.float32) * 0.5
        f = char(f, a["hold"], W / 2, H * 0.86, 620, t, u, a.get("energy", 0.4))
    return f, (1.0, 1.04)


def L_card(t, u, d, a):
    f = R.fill(SKY, (1, 1, 1))
    f = R.pattern_dots(f, t, (1, 1, 1), k=0.6)
    if a["kind"] == "title":
        f = char(f, a["st"], W * 0.72, H + 20, 1080, t, u, 1.2)
        f = C.put(f, C.text_rgba("余裕だもん", 190, fill=(1, 1, 1), stroke=COBALT, stroke_w=16), W * 0.34, H * 0.42,
                  scale=0.6 + 0.4 * C.ease_out_back(min(u / 0.35, 1)))
        f = C.put(f, C.text_rgba(R.NAME, 80, fill=NAVY, stroke=(1, 1, 1)), W * 0.34, H * 0.64, alpha=min(max((u - 0.6) / 0.4, 0), 1))
    else:
        f = char(f, a["st"], W * 0.3, H + 20, 1000, t, u, 0.6)
        f = C.put(f, C.text_rgba("余裕だもん", 150, fill=(1, 1, 1), stroke=COBALT, stroke_w=14), W * 0.68, H * 0.38)
        f = C.put(f, C.text_rgba("Vocal: AI (Gemini)  /  Art: NovelAI", 34, fill=NAVY, stroke=(1, 1, 1), kind="Bold"), W * 0.68, H * 0.58)
        f = f * (1 - np.clip((u - d + 1.2) / 1.2, 0, 1))
    return f, (1.0, 1.03)


NO_LYRIC = {"card", "pattern", "comic", "comic2"}


def render(t, i):
    k = max(j for j, s in enumerate(SHOTS) if s[0] <= t)
    t0, kind, a = SHOTS[k]
    d = (SHOTS[k + 1][0] if k + 1 < len(SHOTS) else DUR) - t0
    u = t - t0
    f, (z0, z1) = globals()[f"L_{kind}"](t, u, d, a)
    # camera: every shot moves; loud sections pulse on the beat
    z = z0 + (z1 - z0) * C.ease(u / max(d, 0.1))
    energy = a.get("energy", 1.0)
    if energy >= 1.3:
        z += 0.018 * np.exp(-(t - R.last_beat(t)) / 0.09)
    f = C.camera(f, (W, H), zoom=z, cx=0.5, cy=0.5)
    if kind not in NO_LYRIC:
        f = lyric_track(f, t)
    if u < 0.07 and energy >= 1.3:  # flash cut on high-energy shots
        f = f + 0.4 * (1 - u / 0.07)
    return R.finish(f, t, i)


def main():
    if sys.argv[1] == "preview":
        ts = [float(x) for x in sys.argv[2:sys.argv.index("--out")]]
        tiles = [Image.fromarray(R.to8(render(t, int(t * FPS)))).resize((480, 270)) for t in ts]
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
        p.stdin.write(R.to8(render(i / FPS, i)).tobytes())
    p.stdin.close()
    p.wait()


if __name__ == "__main__":
    main()
