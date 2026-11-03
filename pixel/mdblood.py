"""Climb stage (the build-up before Fever): the weeping cat-eye backdrop made menacing in motion.

Layers over the stage plate (pixel/plates/climb.png, plate coordinates; y0 = top of the current view):
- grade: the stage sinks toward black-crimson with a heavy vignette that tightens as the climb goes on;
- the drawn red rivers flow: inside the plate's red mask a scrolling ripple texture (dark clots and wet highlights)
  runs downward, so the blood visibly pours;
- fresh tears: tapered streams from the lower lids of both eyes, swelling bulges travelling down them, each ending
  in a heavy drip that stretches, detaches and falls;
- glowing pupils: a red glow behind each eye that pulses with a heartbeat (lub-dub on every beat);
- blood drops falling through the whole view, and a red heartbeat flash at the screen edges.
Everything is drawn in code (flat shapes, anti-aliased), timed to the song's beat.
"""
import math
import random
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import scene as S

OW, OH = 1920, 1080
BLOOD = (128, 0, 16)
BLOOD_D = (52, 0, 8)
BLOOD_HI = (236, 56, 72)
EYES = ((653, 225, 241, 135), (1310, 225, 241, 135))      # centre x, y, half width, half height (plate px)
LIDS = [(530, 330), (640, 352), (760, 345), (850, 318),     # tear sources on the lower lids
        (1110, 318), (1205, 345), (1330, 352), (1450, 330)]
T0, T1 = 116.55, 125.8


@lru_cache(1)
def red_mask():
    a = np.asarray(S.plate("climb").convert("RGB")).astype(np.int16)
    m = (a[..., 0] > 150) & (a[..., 1] < 120) & (a[..., 2] < 120) & (a[..., 0] - a[..., 1] > 70)
    return Image.fromarray((m * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(1.2))


@lru_cache(1)
def eye_mask():
    """Eye whites on the plate (cream, top of the plate)."""
    a = np.asarray(S.plate("climb").convert("RGB")).astype(np.int16)
    m = (a.min(-1) > 190) & (a[..., 0] >= a[..., 2])
    m[700:] = False
    return Image.fromarray((m * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(1.0))


@lru_cache(1)
def veins():
    """Bloodshot veins: branching thin red lines from each eye's rim toward the pupil (plate coords, top 700 px)."""
    rng = random.Random(11)
    big = Image.new("RGBA", (OW * 2, 1400), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    for cx, cy, hw, hh in EYES:
        for i in range(34):
            a = rng.uniform(0, 2 * math.pi)
            x, y = cx + hw * 1.02 * math.cos(a), cy + hh * 1.02 * math.sin(a)
            w = rng.uniform(5, 9)
            for step in range(rng.randint(5, 9)):
                tx, ty = cx + (x - cx) * 0.78, cy + (y - cy) * 0.78
                tx += rng.uniform(-22, 22)
                ty += rng.uniform(-14, 14)
                d.line([(2 * x, 2 * y), (2 * tx, 2 * ty)], fill=(200, 10, 30, 235), width=max(2, int(2 * w)))
                if rng.random() < 0.35:
                    bx, by = tx + rng.uniform(-40, 40), ty + rng.uniform(-30, 30)
                    d.line([(2 * tx, 2 * ty), (2 * bx, 2 * by)], fill=(200, 10, 30, 200), width=max(2, int(w)))
                x, y, w = tx, ty, w * 0.75
    return big.resize((OW, 700), Image.Resampling.LANCZOS)


@lru_cache(1)
def ripple():
    """Tileable 256 x 512 flow texture: vertical streaks of clots and wet highlights (values 0..1)."""
    rng = np.random.default_rng(7)
    h, w = 512, 256
    base = rng.random((h // 16, w // 4))
    base = np.kron(base, np.ones((16, 4)))
    img = Image.fromarray((base * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur((3, 22)))
    a = np.asarray(img).astype(np.float32) / 255
    a = (a - a.min()) / (a.max() - a.min() + 1e-6)
    return np.tile(a, (1, 8))[:, :OW] if a.shape[1] * 8 >= OW else a


def heartbeat(t, beat, ph0):
    """Lub-dub envelope on every beat: strong at the beat, a softer second thump 0.18 beat later."""
    p = ((t - ph0) / beat) % 1.0
    lub = math.exp(-((p) / 0.06) ** 2) + math.exp(-((p - 1) / 0.06) ** 2)
    dub = 0.6 * math.exp(-((p - 0.18) / 0.05) ** 2)
    return min(1.0, lub + dub)


def _stream_poly(x0, y_top, y_bot, w0, t, seed):
    """Tapered wavy stream with bulges running down it (plate coords)."""
    rng = random.Random(seed)
    amp, per, ph = rng.uniform(6, 16), rng.uniform(140, 260), rng.uniform(0, 6.28)
    left, right = [], []
    y = y_top
    while y <= y_bot:
        u = (y - y_top) / max(1.0, y_bot - y_top)
        bulge = 0.55 + 0.45 * math.sin(y / 46.0 - t * 9.0 + ph) ** 2      # swellings flowing downward
        w = w0 * (1.0 - 0.45 * u) * bulge
        x = x0 + amp * math.sin(y / per + ph) * min(1.0, (y - y_top) / 80)
        left.append((x - w / 2, y))
        right.append((x + w / 2, y))
        y += 8
    return left + right[::-1], (left[-1][0] + right[-1][0]) / 2 if left else x0


def overlay(plate_view, t, y0, beat, ph0):
    """plate_view: RGBA 1920x1080 crop of the climb plate whose top is plate y0. Returns the menacing view."""
    if not (T0 - 1.0 <= t < T1 + 0.2):
        return plate_view
    k = min(1.0, max(0.0, (t - T0 + 0.6) / 1.2))                         # fades in with the wipe
    hb = heartbeat(t, beat, ph0)
    img = plate_view.convert("RGB")
    a = np.asarray(img).astype(np.float32)
    # 1) grade toward black-crimson
    grade = np.array([70, 6, 18], np.float32)
    a = a * (1 - 0.42 * k) + grade * 0.42 * k * (a.mean(-1, keepdims=True) / 255)
    # 2) the drawn rivers flow
    m = np.asarray(red_mask().crop((0, int(y0), OW, int(y0) + OH))).astype(np.float32) / 255
    rp = ripple()
    sh = int((t * 520) % rp.shape[0])
    tex = np.roll(rp, sh, axis=0)
    tex = np.tile(tex, (OH // tex.shape[0] + 2, OW // tex.shape[1] + 2))[:OH, :OW]
    tex = np.roll(tex, -int(y0) % rp.shape[0], axis=0)                   # texture fixed to the plate, not the view
    col = (np.array(BLOOD_D, np.float32) * (1 - tex[..., None]) + np.array(BLOOD, np.float32) * tex[..., None])
    hi = np.clip((tex - 0.78) / 0.22, 0, 1)[..., None]
    col = col * (1 - hi) + np.array(BLOOD_HI, np.float32) * hi
    mk = (m * k)[..., None]
    a = a * (1 - mk) + col * mk
    # 2b) bloodshot eyes: whites go sickly and red-veined, redder on each heartbeat
    if y0 < 700:
        h = int(min(OH, 700 - y0))
        em = np.asarray(eye_mask().crop((0, int(y0), OW, int(y0) + h))).astype(np.float32)[..., None] / 255 * k
        sick = np.array([214, 168, 150], np.float32) * (1 - 0.25 * hb) + np.array([230, 60, 70], np.float32) * 0.25 * hb
        a[:h] = a[:h] * (1 - em) + sick * em
        vn = np.asarray(veins().crop((0, int(y0), OW, int(y0) + h))).astype(np.float32)
        va = vn[..., 3:4] / 255 * em
        a[:h] = a[:h] * (1 - va) + vn[..., :3] * va
    out = Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGB").convert("RGBA")
    # 3) glowing pupils (heartbeat)
    glow = Image.new("RGBA", (OW, OH), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for cx, cy, hw, hh in EYES:
        sy = cy - y0
        if -300 < sy < OH + 300:
            r = 95 + 45 * hb
            gd.ellipse([cx - r * 0.5, sy - r, cx + r * 0.5, sy + r], fill=(255, 0, 30, int((170 + 85 * hb) * k)))
    out.alpha_composite(glow.filter(ImageFilter.GaussianBlur(30)))
    core = Image.new("RGBA", (OW, OH), (0, 0, 0, 0))
    cd = ImageDraw.Draw(core)
    for cx, cy, hw, hh in EYES:                                         # slit pupils glow hot in the middle
        sy = cy - y0
        if -300 < sy < OH + 300:
            cd.ellipse([cx - 10, sy - hh * 0.75, cx + 10, sy + hh * 0.75], fill=(255, 60, 60, int((120 + 120 * hb) * k)))
    out.alpha_composite(core.filter(ImageFilter.GaussianBlur(6)))
    # 4) fresh tears from the lids, with drips that stretch and fall
    lay = Image.new("RGBA", (OW * 2, OH * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    grow = max(0.0, t - T0 + 0.4)
    for i, (lx, ly) in enumerate(LIDS):
        rng = random.Random(i * 31 + 5)
        speed = rng.uniform(330, 520)
        length = min(3900 - ly, 120 + grow * speed)
        y_top, y_bot = ly, ly + length
        if y_bot - y0 < -20 or y_top - y0 > OH + 20:
            pass
        else:
            poly, tipx = _stream_poly(lx, y_top, y_bot, rng.uniform(18, 34), t, i)
            pts = [(2 * x, 2 * (y - y0)) for x, y in poly]
            d.polygon(pts, fill=(*BLOOD_D, int(255 * k)))
            inner = [(2 * (x + (lx - x) * 0.35), 2 * (y - y0)) for x, y in poly]
            d.polygon(inner, fill=(*BLOOD, int(255 * k)))
        # drips: every ~0.9 s a drop swells at the stream tip, detaches and falls
        per = rng.uniform(0.7, 1.1)
        for n in range(3):
            phase = (t - T0) / per + n / 3 + i * 0.37
            u = phase % 1.0
            dy = y_bot + 30 + (0 if u < 0.35 else 2600 * (u - 0.35) ** 2)
            r = 10 + 10 * min(1.0, u / 0.35)
            sy = dy - y0
            if -40 < sy < OH + 40:
                stretch = 1.0 + (2.2 * (u - 0.35) if u > 0.35 else 0.0)
                d.ellipse([2 * (lx - r), 2 * (sy - r * stretch), 2 * (lx + r), 2 * (sy + r)],
                          fill=(*BLOOD, int(255 * k)))
                d.ellipse([2 * (lx - r * 0.35), 2 * (sy - r * 0.2), 2 * (lx - r * 0.05), 2 * (sy + r * 0.25)],
                          fill=(*BLOOD_HI, int(200 * k)))
    out.alpha_composite(lay.resize((OW, OH), Image.Resampling.LANCZOS))
    # 5) blood rain across the view (screen space, slanted, flickering)
    rain = Image.new("RGBA", (OW, OH), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rain)
    fr = int(t * 30)
    for j in range(46):
        rng = random.Random(j * 977 + (fr // 3) * 13)
        x = rng.uniform(0, OW)
        yy = (rng.uniform(0, OH) + (t * 1500 + j * 97) % OH) % OH
        ln = rng.uniform(18, 46)
        rd.line([(x, yy), (x - ln * 0.12, yy + ln)], fill=(*BLOOD, int(rng.uniform(120, 220) * k)), width=3)
    out.alpha_composite(rain)
    # 6) heartbeat vignette: dark edges that flash red on every beat
    vig = _vignette()
    v = np.asarray(vig).astype(np.float32) / 255
    alpha = (v * (150 + 90 * hb) * k).clip(0, 255).astype(np.uint8)
    rgb = np.zeros((OH, OW, 3), np.uint8)
    rgb[...] = (int(20 + 120 * hb), 0, 6)
    out.alpha_composite(Image.fromarray(np.dstack([rgb, alpha]), "RGBA"))
    return out


@lru_cache(1)
def _vignette():
    yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
    r = np.hypot((xx - OW / 2) / (OW / 2), (yy - OH / 2) / (OH / 2))
    return Image.fromarray((np.clip((r - 0.55) / 0.6, 0, 1) ** 1.6 * 255).astype(np.uint8), "L")
