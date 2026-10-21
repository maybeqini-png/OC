"""Render the 「余裕だもん」 PV (1920x1080, 30 fps) from the prepared assets, shot by shot (README section 4).

usage:
  render.py preview <t1> <t2> ... --out sheet.jpg      contact sheet of single frames (QA)
  render.py segment <i> <n> --out seg_i.mp4            render the i-th of n equal segments (run n in parallel)
"""
import argparse
import json
import math
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
A = ROOT / "pv/assets"
FONTS = ROOT / "pv/fonts"
W, H, FPS, DUR = 1920, 1080, 30, 178.6
NAME = "（なまえ）"  # placeholder until the owner chooses the OC's name
INK, NAVY, COBALT, SKY = (27, 35, 64), (42, 58, 122), (60, 109, 240), (156, 196, 255)
WHITE, CORAL, LEMON, RED = (244, 246, 251), (255, 123, 138), (255, 214, 74), (255, 70, 90)

T = json.load(open(A / "timing.json"))
BEATS = np.array(T["beats"])
ENV = np.array(T["vocal_env"])
NF = int(DUR * FPS)

# ---------- lip-sync and blinks (precomputed so parallel segments agree) ----------
MOUTH = np.zeros(NF + 2, bool)
state = False
for f in range(NF):
    e = ENV[f] if f < len(ENV) else 0
    state = (e > 0.62) if not state else (e > 0.48)
    MOUTH[f] = state and f / FPS > 3.65
BLINK = np.zeros(NF + 2, bool)
rng = np.random.default_rng(11)
tb = 1.2
while tb < DUR:
    f0 = int(tb * FPS)
    BLINK[f0:f0 + 4] = True
    tb += rng.uniform(2.6, 4.8)

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
CHAT = [(7.8, "ねこ好き", "きた！"), (8.6, "J.D.", "here we go!"), (9.4, "もふ", "ふふんｗ"), (10.2, "Kai", "so smug lol"),
        (16.6, "リス", "大天才だ"), (17.4, "Mia", "genius!!"), (46.0, "審判", "ノーカン!?"), (46.7, "Leo", "it counts lol"),
        (47.4, "もふ", "カウントです"), (49.4, "A", "ニヤニヤ"), (49.8, "B", "ニヤニヤ"), (50.2, "C", "ニヤニヤ"),
        (50.6, "D", "ニヤニヤ"), (51.0, "E", "ニヤニヤ"), (51.4, "F", "ニヤニヤ"), (69.4, "ねこ好き", "見てるよ"),
        (70.1, "Kai", "watching!"), (85.0, "リス", "スクショ…"), (85.6, "Mia", "*screenshot*"), (104.6, "もふ", "www"),
        (105.1, "Leo", "LOL"), (105.6, "J.D.", "she broke"), (155.0, "ねこ好き", "余裕でしたね"), (155.8, "Kai", "gg")]
CHAT += [(139.6 + i * 0.9, n, "にゃ") for i, n in enumerate(["もふ", "Kai", "リス", "Mia", "J.D.", "Leo", "ねこ好き", "審判"])]


def ease(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def lerp(a, b, u):
    return a + (b - a) * u


@lru_cache(None)
def font(kind, size):
    return ImageFont.truetype(str(FONTS / f"MPLUSRounded1c-{kind}.ttf"), size)


@lru_cache(None)
def asset(name):
    return Image.open(A / f"{name}.png").convert("RGBA")


@lru_cache(None)
def asset_rgb(name):
    return Image.open(A / f"{name}.png").convert("RGB")


# ---------- text pieces ----------
@lru_cache(maxsize=256)
def sticker(text, size, fill, outline=INK, ow=10, kind="ExtraBold"):
    f = font(kind, size)
    l, t, r, b = f.getbbox(text, stroke_width=ow)
    pad = ow + 18
    im = Image.new("RGBA", (r - l + 2 * pad, b - t + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((pad - l + 6, pad - t + 8), text, font=f, fill=(0, 0, 0, 120), stroke_width=ow,
                            stroke_fill=(0, 0, 0, 120))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(4)))
    d = ImageDraw.Draw(im)
    d.text((pad - l, pad - t), text, font=f, fill=WHITE + (255,), stroke_width=ow + 6, stroke_fill=WHITE + (255,))
    d.text((pad - l, pad - t), text, font=f, fill=fill + (255,), stroke_width=ow, stroke_fill=outline + (255,))
    return im


@lru_cache(maxsize=128)
def caption_img(text, thin=False):
    f = font("Medium" if thin else "Bold", 50 if thin else 52)
    ow = 2 if thin else 6
    l, t, r, b = f.getbbox(text, stroke_width=ow)
    im = Image.new("RGBA", (r - l + 40, b - t + 30), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((20 - l, 15 - t), text, font=f, fill=WHITE + (255,), stroke_width=ow,
                            stroke_fill=INK + (230,))
    return im


@lru_cache(maxsize=32)
def bubble(text):
    f = font("Bold", 58)
    l, t, r, b = f.getbbox(text)
    w, h = r - l + 90, b - t + 60
    im = Image.new("RGBA", (w + 20, h + 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((6, 6, w + 6, h + 6), 40, fill=WHITE + (245,), outline=INK + (255,), width=6)
    d.polygon([(w * 0.25, h + 2), (w * 0.18, h + 52), (w * 0.38, h + 2)], fill=WHITE + (245,), outline=INK + (255,))
    d.line([(w * 0.25 + 4, h + 4), (w * 0.38 - 4, h + 4)], fill=WHITE + (255,), width=8)
    d.text((51 - l, 36 - t), text, font=f, fill=INK + (255,))
    return im


def paste(frame, im, cx, cy, scale=1.0, rot=0.0, alpha=1.0):
    if scale != 1.0:
        im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.BILINEAR)
    if rot:
        im = im.rotate(rot, resample=Image.BILINEAR, expand=True)
    if alpha < 1.0:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    frame.alpha_composite(im, (round(cx - im.width / 2), round(cy - im.height / 2)))


def pop(lt, dur=0.2):
    """scale for a pop-in that overshoots then settles; None before it starts"""
    if lt < 0:
        return None
    u = min(lt / dur, 1.0)
    return 1.0 + 0.35 * math.sin(u * math.pi) * (1 - u) + (1 - u) * 0.25


# ---------- layers ----------
def bg_view(name, z=1.0, px=0.0, py=0.0, bright=1.0):
    im = asset_rgb(name)
    ww, hh = 1920 / z, 1080 / z
    cx = min(max(1152 + px, ww / 2), 2304 - ww / 2)
    cy = min(max(648 + py, hh / 2), 1296 - hh / 2)
    v = im.crop((round(cx - ww / 2), round(cy - hh / 2), round(cx + ww / 2), round(cy + hh / 2))).resize((W, H), Image.BILINEAR)
    if bright != 1.0:
        v = ImageEnhance.Brightness(v).enhance(bright)
    return v.convert("RGBA")


@lru_cache(None)
def wall_img():
    f = font("ExtraBold", 120)
    im = Image.new("RGBA", (3200, 1500), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for row in range(8):
        off = (row % 2) * 300
        for col in range(-1, 6):
            d.text((col * 640 + off, row * 190), "余裕だもん", font=f, fill=SKY + (90,))
    glow = im.filter(ImageFilter.GaussianBlur(10))
    return Image.alpha_composite(glow, im)


def add_wall(frame, t, double=False):
    wall = wall_img()
    last = BEATS[BEATS <= t]
    k = math.exp(-(t - last[-1]) / 0.22) if len(last) else 0
    for i, (speed, yoff) in enumerate([(70, 0), (-50, 95)][: 2 if double else 1]):
        x = int((t * speed) % 640)
        crop = wall.crop((x, yoff, x + W, yoff + H))
        a = 0.55 + 0.45 * k
        crop.putalpha(crop.getchannel("A").point(lambda v: int(v * a)))
        frame.alpha_composite(crop)


@lru_cache(None)
def speedlines():
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = np.random.default_rng(3)
    for _ in range(90):
        ang = r.uniform(0, 2 * math.pi)
        r0, r1 = r.uniform(420, 620), 1400
        w = int(r.uniform(2, 7))
        d.line([(W / 2 + r0 * math.cos(ang), H / 2 + r0 * math.sin(ang)), (W / 2 + r1 * math.cos(ang), H / 2 + r1 * math.sin(ang))],
               fill=WHITE + (170,), width=w)
    return im


@lru_cache(None)
def vignette():
    y, x = np.mgrid[0:H, 0:W]
    r = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
    a = np.clip((r - 0.75) / 0.6, 0, 1) * 150
    im = np.zeros((H, W, 4), np.uint8)
    im[..., :3] = INK
    im[..., 3] = a.astype(np.uint8)
    return Image.fromarray(im, "RGBA")


@lru_cache(None)
def grain(i):
    r = np.random.default_rng(100 + i)
    n = np.clip(128 + r.normal(0, 14, (H // 2, W // 2)), 0, 255).astype(np.uint8)
    return Image.fromarray(n, "L").resize((W, H), Image.BILINEAR).convert("RGB")


def beam(frame, t, speed=0.18):
    ph = (t * speed) % 1.0
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x = -600 + ph * (W + 1200)
    ImageDraw.Draw(im).polygon([(x, 0), (x + 260, 0), (x - 200, H), (x - 460, H)], fill=SKY + (60,))
    frame.alpha_composite(im.filter(ImageFilter.GaussianBlur(40)))


def beat_bounce(t):
    last = BEATS[BEATS <= t]
    return 14 * math.exp(-(t - last[-1]) / 0.11) if len(last) else 0


def bust_name(t):
    f = min(int(t * FPS), NF)
    if BLINK[f]:
        return "bust_blink"
    return "bust_talk" if MOUTH[f] else "bust_base"


def draw_sprite(frame, t, name, cx, bottom, h, bounce=False, flip=False, breathe=True, alpha=1.0, tint=None):
    if name == "BUST":
        name = bust_name(t)
    im = asset(name)
    s = 1 + (0.006 * math.sin(2 * math.pi * t / 3.4) if breathe else 0)
    hh = h * s
    ww = im.width * h / im.height
    im = im.resize((max(1, round(ww)), max(1, round(hh))), Image.BILINEAR)
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    if tint is not None:
        solid = Image.new("RGBA", im.size, tint + (255,))
        solid.putalpha(im.getchannel("A"))
        im = solid
    if alpha < 1.0:
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    by = bottom - (beat_bounce(t) if bounce else 0)
    frame.alpha_composite(im, (round(cx - im.width / 2), round(by - im.height)))


# ---------- shots ----------
def stamp_all(frame, t, s):
    for (ts, text, color, x, y, size, rot) in s.get("stamps", []):
        sc = pop(t - ts)
        if sc is not None:
            paste(frame, sticker(text, size, color), W / 2 + x, H / 2 + y, scale=sc, rot=rot)


def scene(t, s):
    lt, dur = t - s["a"], s["b"] - s["a"]
    u = ease(lt / dur)
    z = lerp(s.get("z0", 1.0), s.get("z1", s.get("z0", 1.0)), u)
    px = lerp(s.get("px0", 0), s.get("px1", s.get("px0", 0)), u)
    frame = bg_view(s.get("bg", "b1_room") + ("_blur" if s.get("blur", True) else ""), 1 + (z - 1) * 0.4, px * 0.3, 0,
                    s.get("bright", 1.0))
    if s.get("wall"):
        add_wall(frame, t, s["wall"] == 2)
    if s.get("beam"):
        beam(frame, t)
    if s.get("lines"):
        frame.alpha_composite(speedlines().rotate((int(t * 12) % 4) * 3))
    spr = s.get("spr")
    if spr:
        h = s.get("h", 1100) * z
        cx = W / 2 + s.get("x", 0) * z - px
        bottom = s.get("bottom", H + 60) + (z - 1) * s.get("zy", 300)
        draw_sprite(frame, t, spr, cx, bottom, h, bounce=s.get("bounce", False), flip=s.get("flip", False))
    if s.get("check"):
        checklist(frame, t, s["a"])
    if s.get("logo") is not None:
        sc = pop(t - s["logo"], 0.25)
        if sc is not None:
            paste(frame, sticker("余裕だもん", 170, COBALT, ow=14), W / 2, 210, scale=sc, rot=-4)
    if s.get("bubbles"):
        for (ta, tb_, text) in s["bubbles"]:
            if ta <= t < tb_:
                paste(frame, bubble(text), W / 2 - 330, 230, scale=pop(t - ta) or 1)
    stamp_all(frame, t, s)
    return frame


def checklist(frame, t, a):
    items = [(20.4, "発声"), (22.4, "ステップ"), (24.4, "笑顔")]
    d = ImageDraw.Draw(frame)
    d.rounded_rectangle((120, 300, 620, 690), 34, fill=INK + (200,), outline=SKY + (255,), width=4)
    d.text((160, 325), "準備チェック", font=font("ExtraBold", 50), fill=WHITE)
    for i, (ti, lab) in enumerate(items):
        y = 420 + i * 88
        d.rounded_rectangle((160, y, 210, y + 50), 10, outline=WHITE, width=5)
        d.text((240, y - 4), lab, font=font("Bold", 46), fill=WHITE)
        if t >= ti:
            k = min((t - ti) / 0.15, 1)
            d.line([(168, y + 26), (182, y + 42)], fill=LEMON, width=9)
            d.line([(182, y + 42), (182 + 26 * k, y + 42 - 44 * k)], fill=LEMON, width=9)


@lru_cache(None)
def silhouette_img():
    im = asset("bust_base")
    a = im.getchannel("A")
    sil = Image.new("RGBA", im.size, (14, 18, 34, 255))
    sil.putalpha(a)
    rim = ImageChops.subtract(a, a.filter(ImageFilter.MinFilter(9))).filter(ImageFilter.GaussianBlur(3))
    glow = Image.new("RGBA", im.size, COBALT + (255,))
    glow.putalpha(rim)
    return Image.alpha_composite(sil, glow)


def shot_silhouette(t, s):
    frame = bg_view("b1_room_blur", 1.05, 0, 0, 0.45)
    im = silhouette_img()
    lit = 0.0 if t < 3.2 else ease((t - 3.2) / 0.5)
    h = 1150
    sil = im.resize((round(im.width * h / im.height), h), Image.BILINEAR)
    frame.alpha_composite(sil, (round(W / 2 - sil.width / 2), H + 60 - h))
    if lit > 0:
        draw_sprite(frame, t, "bust_base", W / 2, H + 60, h, alpha=lit, breathe=False)
    frame = Image.blend(frame.convert("RGB"), ImageEnhance.Brightness(frame.convert("RGB")).enhance(1.25), lit * 0.5).convert("RGBA")
    return frame


def shot_namecard(t, s):
    lt = t - s["a"]
    frame = Image.new("RGBA", (W, H), INK + (255,))
    d = ImageDraw.Draw(frame)
    k = ease(lt / 0.4)
    d.polygon([(0, 640 - 200 * k), (W, 380 - 200 * k), (W, 560), (0, 820)], fill=NAVY + (255,))
    d.polygon([(0, 700), (W * k, 700 - 260 * k), (W * k, 720 - 260 * k), (0, 720)], fill=COBALT + (255,))
    draw_sprite(frame, t, "bust_base", W * 0.70, H + 40, 1100, breathe=True)
    sc = pop(lt - 0.25, 0.25)
    if sc:
        paste(frame, sticker(NAME, 130, COBALT, ow=12), W * 0.30, H * 0.40, scale=sc, rot=-3)
    if lt > 0.6:
        d = ImageDraw.Draw(frame)
        d.text((200, 640), "Vocal & Music: AI (Google Gemini / Lyria)", font=font("Medium", 34), fill=SKY)
        d.text((200, 690), "Illustration: AI-assisted (NovelAI)", font=font("Medium", 34), fill=SKY)
    return frame


def shot_split(t, s):
    left = scene(t, dict(s, spr="BUST", bg="b2_stage", x=-420, h=1050))
    right = scene(t, dict(s, spr="e4_flustered", bg="b1_room", x=420, h=1050, stamps=[]))
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon([(W * 0.56, 0), (W, 0), (W, H), (W * 0.44, H)], fill=255)
    out = Image.composite(right, left, mask)
    ImageDraw.Draw(out).line([(W * 0.56, 0), (W * 0.44, H)], fill=WHITE + (255,), width=12)
    stamp_all(out, t, s)
    return out


def shot_reflection(t, s):
    frame = bg_view("b1_room_blur", 1.1, 0, 0, 0.35)
    draw_sprite(frame, t, "e7_honest", W / 2 + 40, H + 60, 1150, flip=True, alpha=0.45, tint=None)
    tintl = Image.new("RGBA", (W, H), NAVY + (70,))
    frame.alpha_composite(tintl)
    return frame


def shot_boots(t, s):
    frame = bg_view("b1_room_blur", 1.2, 0, 260, 0.8)
    im = asset("p2_referee_x")
    crop = im.crop((0, int(im.height * 0.70), im.width, im.height))
    h = 900
    crop = crop.resize((round(crop.width * h / crop.height), h), Image.BILINEAR)
    jitter = 0 if t > 121.6 else 5 * math.sin(t * 90)
    frame.alpha_composite(crop, (round(W / 2 - crop.width / 2 + jitter), H - h + 40))
    stamp_all(frame, t, s)
    return frame


def shot_spin(t, s):
    lt = t - s["a"]
    frame = bg_view("b3_bigstage_blur", 1.05, 0, 0, 1.0)
    frame.alpha_composite(speedlines())
    im = asset("p1_overcool")
    h = 980
    im = im.resize((round(im.width * h / im.height), h), Image.BILINEAR)
    ang = 360 * ease(min(lt / 1.1, 1))
    r = im.rotate(ang, resample=Image.BILINEAR, expand=True)
    frame.alpha_composite(r, (round(W / 2 - r.width / 2), round(H / 2 - r.height / 2 + 20)))
    stamp_all(frame, t, s)
    return frame


def shot_endcard(t, s):
    lt = t - s["a"]
    frame = Image.new("RGBA", (W, H), INK + (255,))
    sc = pop(lt - 0.2, 0.3)
    if sc:
        paste(frame, sticker("余裕だもん", 190, COBALT, ow=14), W / 2, 380, scale=sc, rot=-3)
    if lt > 0.8:
        paste(frame, sticker("ノーカン ×0", 64, LEMON, ow=8), W / 2, 590, scale=pop(lt - 0.8) or 1)
    if lt > 1.4:
        d = ImageDraw.Draw(frame)
        for i, line in enumerate(["Vocal & Music: AI-generated (Google Gemini / Lyria)", "Illustration: AI-assisted (NovelAI)",
                                  NAME]):
            f = font("Medium", 34)
            d.text((W / 2 - f.getlength(line) / 2, 720 + i * 52), line, font=f, fill=SKY)
    if t > DUR - 1.6:
        frame = Image.blend(frame.convert("RGB"), Image.new("RGB", (W, H), (0, 0, 0)), ease((t - (DUR - 1.6)) / 1.5)).convert("RGBA")
    return frame


ROOM, STAGE, BIG = "b1_room", "b2_stage", "b3_bigstage"
FULL = dict(h=1050, bottom=H - 20, zy=0)
SHOTS = [
    dict(a=0.0, b=3.7, fn=shot_silhouette, live=True),
    dict(a=3.7, b=7.5, spr="BUST", bg=ROOM, z0=1.15, z1=1.22, bubbles=[(3.7, 7.5, "ねえねえ　ちゃんと見ててよね")], nocap=True),
    dict(a=7.5, b=11.1, spr="BUST", bg=ROOM, z0=1.22, z1=1.0, bubbles=[(7.6, 11.1, "ふふん　そろそろ　いくよ")], nocap=True),
    dict(a=11.1, b=14.2, fn=shot_namecard, nolive=True, nocap=True, nochat=True),
    dict(a=14.2, b=19.8, spr="BUST", bg=STAGE, z0=1.0, z1=1.08, bounce=True, iris=True,
         stamps=[(16.4, "大天才", LEMON, -520, -250, 120, 8)]),
    dict(a=19.8, b=27.8, spr="BUST", bg=STAGE, x=330, bounce=True, check=True),
    dict(a=27.8, b=34.4, spr="BUST", bg=STAGE, z0=1.0, z1=1.1, bounce=True, logo=30.5),
    dict(a=34.4, b=42.6, spr="p1_overcool", bg=STAGE, z0=1.0, z1=1.25, beam=True, **FULL),
    dict(a=42.6, b=43.05, spr="e3_shocked", bg=ROOM, z0=1.15, shake=42.6, flash=42.6),
    dict(a=43.05, b=44.18, spr="c1_chibi_fallen", bg=ROOM, h=1150, bottom=H + 120, zy=0, lines=True, shake=43.05,
         stamps=[(43.05, "ドテッ", LEMON, 470, -230, 130, -10)]),
    dict(a=44.18, b=45.8, spr="e3_shocked", bg=ROOM, z0=1.15, z1=1.2),
    dict(a=45.8, b=49.2, spr="p2_referee_x", bg=ROOM, **FULL, stamps=[(46.0, "ノーカン", LEMON, 480, -120, 140, -8)]),
    dict(a=49.2, b=52.3, spr="e4_flustered", bg=ROOM, z0=1.2, z1=1.26),
    dict(a=52.3, b=55.6, spr="p4_crouch", bg=ROOM, z0=1.0, z1=1.1, bright_after=(55.07, 0.6), **FULL),
    dict(a=55.6, b=59.7, spr="BUST", bg=STAGE, wall=1, bounce=True, iris=True),
    dict(a=59.7, b=64.4, fn=shot_split),
    dict(a=64.4, b=66.82, spr="e5_meh_wink_closeup", bg=STAGE, h=1750, bottom=H + 760, zy=0, z0=1.0, z1=1.06),  # tight: keeps the off-model bow out of frame
    dict(a=66.82, b=68.8, spr="p7_pawboop", bg=STAGE, h=1150, z0=1.15, flash=66.82, flashc=CORAL,
         stamps=[(66.82, "めっ", CORAL, -480, -240, 170, 10)]),
    dict(a=68.8, b=73.0, spr="BUST", bg=STAGE, wall=1, bounce=True),
    dict(a=73.0, b=77.0, spr="e7_honest", bg=ROOM, z0=1.3, z1=1.36, bright=0.55, thin=True, nochat=True),
    dict(a=77.0, b=84.6, spr="BUST", bg=STAGE, z0=1.0, z1=1.15, beam=True, bounce=True),
    dict(a=84.6, b=87.9, spr="BUST", bg=ROOM, z0=1.15, flash=84.645,
         stamps=[(86.34, "禁止", LEMON, 470, -200, 150, -9), (86.7, "※冗談です", WHITE, 470, -40, 54, 0)]),
    dict(a=87.9, b=89.7, spr="e5_meh_wink_closeup", bg=ROOM, h=1750, bottom=H + 760, zy=0, z0=1.0, z1=1.04),
    dict(a=89.7, b=96.2, spr="p1_overcool", bg=STAGE, h=1700, bottom=H + 760, zy=0, z0=1.0, z1=1.08),
    dict(a=96.2, b=104.0, spr="p3_puitt", bg=ROOM, h=1100, z0=1.05, z1=1.12, stamps=[(96.3, "ぷいっ", LEMON, -520, -260, 130, 8)]),
    dict(a=104.0, b=110.0, spr="e6_laughing", bg=STAGE, bounce=True),
    dict(a=110.0, b=112.9, fn=shot_reflection, thin=True, nochat=True),
    dict(a=112.9, b=116.2, spr="c2_chibi_kick", bg=ROOM, h=860, bottom=H - 40, zy=0, kick=113.6),
    dict(a=116.2, b=122.8, fn=shot_boots, stamps=[(121.6, "ドンッ", LEMON, 420, -220, 120, -6)]),
    dict(a=122.8, b=125.8, spr="p1_overcool", bg=BIG, **FULL, iris=True),
    dict(a=125.8, b=130.2, spr="BUST", bg=BIG, wall=2, bounce=True),
    dict(a=130.2, b=133.5, fn=shot_spin, stamps=[(131.5, "+1 → ✕", LEMON, 520, -260, 110, -8)]),
    dict(a=133.5, b=137.36, spr="BUST", bg=BIG, z0=1.1, z1=1.15, wall=1),
    dict(a=137.36, b=139.0, spr="p7_pawboop", bg=BIG, h=1150, z0=1.15, flip=True, flash=137.36, flashc=CORAL,
         stamps=[(137.36, "めっ", CORAL, 480, -240, 170, -10)]),
    dict(a=139.0, b=147.0, spr="BUST", bg=BIG, wall=2, bounce=True),
    dict(a=147.0, b=153.96, spr="p1_overcool", bg=BIG, z0=1.2, z1=1.0, beam=True, **FULL),
    dict(a=153.96, b=158.5, spr="BUST", bg=ROOM, z0=1.1, z1=1.14),
    dict(a=158.5, b=163.0, spr="BUST", bg=ROOM, z0=1.15, z1=1.2),
    dict(a=163.0, b=172.5, spr="p5_wave", bg=ROOM, dim=(170.6, 0.25), **FULL),
    dict(a=172.5, b=DUR + 1, fn=shot_endcard, nolive=True, nocap=True, nochat=True),
]


def shot_at(t):
    for i, s in enumerate(SHOTS):
        if s["a"] <= t < s["b"]:
            return i, s
    return len(SHOTS) - 1, SHOTS[-1]


def base_frame(i, s, t):
    fr = s.get("fn", scene)(t, s)
    if s.get("bright_after") and t >= s["bright_after"][0]:
        fr = ImageEnhance.Brightness(fr.convert("RGB")).enhance(s["bright_after"][1]).convert("RGBA")
    if s.get("dim") and t >= s["dim"][0]:
        k = ease((t - s["dim"][0]) / 0.5)
        fr = ImageEnhance.Brightness(fr.convert("RGB")).enhance(lerp(1, s["dim"][1], k)).convert("RGBA")
    return fr


# ---------- HUD / overlays ----------
def counter_value(t):
    return 0 if t < 42.6 else 1 if t < 59.7 else 2 if t < 104.3 else 3


def hud(frame, t, s):
    d = ImageDraw.Draw(frame)
    if not s.get("nolive") and t < 171.0:
        d.ellipse((46, 44, 70, 68), fill=RED)
        d.text((82, 36), "LIVE", font=font("ExtraBold", 34), fill=WHITE)
    n = counter_value(t)
    if n and not s.get("nolive") and t < 113.9:
        k = 0 if t < 113.6 else ease((t - 113.6) / 0.3)
        changed = max([x for x in (42.6, 59.7, 104.3) if x <= t], default=0)
        sc = pop(t - changed) or 1
        paste(frame, sticker(f"ノーカン ×{n}", 46, LEMON, ow=6), 200 + 900 * k, 125 - 400 * k, scale=sc, rot=-720 * k * 0.1)


def chat(frame, t, s):
    if s.get("nochat"):
        return
    msgs = [m for m in CHAT if m[0] <= t and t - m[0] < 6.0]
    if not msgs:
        return
    msgs = msgs[-7:]
    x0, y = 1450, 980
    for (tm, name, text) in reversed(msgs):
        k = ease((t - tm) / 0.2)
        fade = 1 - ease((t - tm - 5.4) / 0.6)
        box = Image.new("RGBA", (420, 74), (0, 0, 0, 0))
        bd = ImageDraw.Draw(box)
        bd.rounded_rectangle((0, 0, 419, 73), 18, fill=INK + (int(190 * fade),))
        bd.text((18, 8), name, font=font("Bold", 24), fill=SKY + (int(255 * fade),))
        bd.text((18, 34), text, font=font("Bold", 30), fill=WHITE + (int(255 * fade),))
        frame.alpha_composite(box, (x0, round(y - 74 + (1 - k) * 40)))
        y -= 84


def captions(frame, t, s):
    if s.get("nocap"):
        return
    for (a, b, text) in LYRICS:
        if a <= t < b:
            im = caption_img(text, s.get("thin", False))
            al = min(1, (t - a) / 0.12, (b - t) / 0.12)
            paste(frame, im, W / 2, H - 70, alpha=max(0.0, al))


def render(t):
    i, s = shot_at(t)
    fr = base_frame(i, s, t)
    if s.get("iris") and t - s["a"] < 0.35:
        pi, ps = (i - 1, SHOTS[i - 1])
        prev = base_frame(pi, ps, t)
        r = ease((t - s["a"]) / 0.35) * 1150
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).ellipse((W / 2 - r, H / 2 - r, W / 2 + r, H / 2 + r), fill=255)
        fr = Image.composite(fr, prev, m)
    for key in ("shake",):
        if s.get(key) is not None and 0 <= t - s[key] < 0.35:
            amp = 22 * (1 - (t - s[key]) / 0.35)
            fr = ImageChops.offset(fr, int(amp * math.sin(t * 97)), int(amp * math.cos(t * 83)))
    fr.alpha_composite(vignette())
    hud(fr, t, s)
    chat(fr, t, s)
    captions(fr, t, s)
    if s.get("flash") is not None and 0 <= t - s["flash"] < 0.14:
        c = s.get("flashc", WHITE)
        fr.alpha_composite(Image.new("RGBA", (W, H), c + (int(130 * (1 - (t - s["flash"]) / 0.14)),)))
    rgb = fr.convert("RGB")
    rgb = ImageChops.soft_light(rgb, grain(int(t * FPS) % 6))
    return rgb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["preview", "segment"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.mode == "preview":
        ts = [float(x) for x in a.args]
        tiles = [render(t).resize((480, 270)) for t in ts]
        cols = 4
        sheet = Image.new("RGB", (cols * 480, math.ceil(len(tiles) / cols) * 290), (255, 255, 255))
        for k, (t, im) in enumerate(zip(ts, tiles)):
            sheet.paste(im, ((k % cols) * 480, (k // cols) * 290))
            ImageDraw.Draw(sheet).text(((k % cols) * 480 + 6, (k // cols) * 290 + 272), f"{t:.2f}s", fill=(0, 0, 0))
        sheet.save(a.out, quality=85)
        return
    i, n = int(a.args[0]), int(a.args[1])
    f0, f1 = NF * i // n, NF * (i + 1) // n
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                          "-pix_fmt", "yuv420p", a.out], stdin=subprocess.PIPE)
    for f in range(f0, f1):
        p.stdin.write(render(f / FPS).tobytes())
    p.stdin.close()
    p.wait()
    print("segment", i, "frames", f0, f1)


if __name__ == "__main__":
    main()
