"""Hit and speed effects for the HD game layer, from a frame-by-frame study of the official Muse Dash trailer
(Steam, 1080p30) and game-feel write-ups (see docs/rhythm_game_style_reference.md, "Hit and speed effects").

Hit (age in seconds since the strike, 30 fps):
  f0-2   big asymmetric impact star (core + light rim, random tilt), squash/hit-stop on the struck monster,
         white swoosh crescent from her strike, short vertical shake, radial spark dashes start;
  f3-4   white-core flash star inside a pink rim;
  f5-9   the star shrinks to a small spike star and vanishes;
  f0-27  confetti: filled stars thrown in a forward-up cone with drag, slow spin, fading over their last third;
  f0-9   white smoke puffs where the monster was (ground) / dust at her feet;
  PERFECT: chunky banded letters, white outline, dark extrusion, -8 deg tilt, pop-in with smeared ghost copies
         for 3 frames, hold, rise and fade by 0.55 s.
Speed (Fever): thin tapered streaks across the screen (each lives 4 frames, re-seeded per frame so they flicker),
  translucent diagonal bands sweeping the background, three tinted afterimages behind her, and a radial
  speed-line burst with a 2-frame flash when Fever starts.
All shapes are drawn 3x supersampled; nothing is drawn on white, so there are no fringes.
"""
import math
import random
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

ROOT = Path(__file__).parent.parent
OW, OH = 1920, 1080
FPS = 30
WHITE = (255, 255, 255)

PALETTES = {   # per stage: impact core, impact rim, confetti colours, PERFECT bands (top, mid, bottom), extrusion
    "pink": dict(core=(255, 60, 160), rim=(255, 190, 230), conf=[(190, 80, 255), (140, 90, 255), (90, 120, 255),
                                                                   (255, 90, 200), (230, 120, 255)],
                 bands=[(255, 186, 225), (255, 110, 185), (236, 50, 150)], ext=(120, 20, 90), edge=(255, 70, 170)),
    "gold": dict(core=(255, 200, 40), rim=(255, 250, 200), conf=[(255, 170, 40), (255, 210, 60), (255, 120, 60),
                                                                   (255, 240, 120), (250, 140, 200)],
                 bands=[(255, 250, 140), (255, 214, 40), (255, 150, 30)], ext=(110, 40, 90), edge=(255, 80, 180)),
    "blue": dict(core=(70, 150, 255), rim=(200, 235, 255), conf=[(90, 160, 255), (120, 220, 255), (190, 140, 255),
                                                                   (255, 150, 220), (110, 120, 255)],
                 bands=[(190, 240, 255), (90, 180, 255), (60, 110, 240)], ext=(30, 40, 120), edge=(255, 255, 255)),
}
PALETTES["pass"] = dict(core=(255, 150, 30), rim=(255, 236, 170), conf=[(255, 170, 40), (255, 210, 80), (255, 120, 60)],
                        bands=[(255, 226, 120), (255, 170, 40), (255, 110, 20)], ext=(120, 50, 40), edge=(255, 255, 255))
STAGE_PAL = {"sky": "pink", "sunset": "pink", "pop": "pink", "night": "gold", "pinkpop": "pink",
             "twilight": "gold", "climb": "gold", "festival": "gold"}


def _ss(w, h, draw, k=3):
    big = Image.new("RGBA", (w * k, h * k), (0, 0, 0, 0))
    draw(ImageDraw.Draw(big), k)
    return big.resize((w, h), Image.Resampling.LANCZOS)


def put(img, sp, cx, cy, alpha=1.0):
    if alpha < 0.999:
        a = np.asarray(sp).copy()
        a[..., 3] = (a[..., 3] * max(0.0, alpha)).astype(np.uint8)
        sp = Image.fromarray(a, "RGBA")
    img.alpha_composite(sp, (int(round(cx - sp.width / 2)), int(round(cy - sp.height / 2))))


# ---------------------------------------------------------------- shapes
def _star_pts(c, r_out, r_in, n, rot, spikes=None):
    pts = []
    for i in range(2 * n):
        r = r_out * (spikes[i // 2] if spikes and i % 2 == 0 else 1.0) if i % 2 == 0 else r_in
        a = rot + i * math.pi / n - math.pi / 2
        pts.append((c + r * math.cos(a), c + r * math.sin(a)))
    return pts


@lru_cache(None)
def impact_star(size, seed, core, rim, white_core=False):
    """Asymmetric 5-point impact star: one long spike, uneven others (as drawn in the reference)."""
    rng = random.Random(seed)
    spikes = [1.0, 0.72 + rng.random() * 0.2, 0.62 + rng.random() * 0.2, 0.8 + rng.random() * 0.15,
              0.66 + rng.random() * 0.2]
    rng.shuffle(spikes)
    rot = rng.uniform(0, 2 * math.pi / 5)

    def dr(d, k):
        c = size * k / 2
        d.polygon(_star_pts(c, c * 0.98, c * 0.42, 5, rot, spikes), fill=rim)
        d.polygon(_star_pts(c, c * 0.84, c * 0.35, 5, rot, spikes), fill=WHITE if white_core else core)
        if not white_core:                               # layered as in play: hot core, lighter inner star
            d.polygon(_star_pts(c, c * 0.5, c * 0.21, 5, rot + 0.2, spikes),
                      fill=tuple(min(255, int(v * 0.55 + 255 * 0.45)) for v in core))
        if white_core:
            d.polygon(_star_pts(c, c * 0.52, c * 0.22, 5, rot, spikes), fill=(255, 255, 255))
    return _ss(size, size, dr)


@lru_cache(None)
def solid_star(size, col, rot_step):
    def dr(d, k):
        c = size * k / 2
        d.polygon(_star_pts(c, c * 0.96, c * 0.46, 5, rot_step * math.pi / 18), fill=col)
    return _ss(size, size, dr)


@lru_cache(None)
def puff(size):
    """Cartoon smoke puff: three overlapping white circles with a pale lilac underside."""
    def dr(d, k):
        s = size * k
        for (x, y, r), col in [((0.5, 0.58, 0.34), (230, 225, 250)), ((0.32, 0.5, 0.26), WHITE),
                               ((0.62, 0.42, 0.3), WHITE), ((0.5, 0.52, 0.3), WHITE)]:
            d.ellipse([s * (x - r), s * (y - r), s * (x + r), s * (y + r)], fill=col)
    return _ss(size, size, dr)


def taper_line(d, x0, y0, x1, y1, w0, w1, col):
    """Tapered quad from (x0,y0) width w0 to (x1,y1) width w1."""
    dx, dy = x1 - x0, y1 - y0
    L = max(1e-6, math.hypot(dx, dy))
    nx, ny = -dy / L, dx / L
    d.polygon([(x0 + nx * w0 / 2, y0 + ny * w0 / 2), (x1 + nx * w1 / 2, y1 + ny * w1 / 2),
               (x1 - nx * w1 / 2, y1 - ny * w1 / 2), (x0 - nx * w0 / 2, y0 - ny * w0 / 2)], fill=col)


# ---------------------------------------------------------------- hit
def impact(img, x, y, age, seed, pal="pink", scale=1.0):
    """Impact star sequence + spark dashes (age in s)."""
    P = PALETTES[pal]
    f = age * FPS
    if f < 3:
        sz = int(250 * scale * (0.85 + 0.15 * min(1, f)))
        put(img, impact_star(sz, seed, P["core"], P["rim"]), x, y)
    elif f < 5:
        put(img, impact_star(int(210 * scale), seed, P["core"], P["edge"] if pal != "blue" else P["rim"], True), x, y)
    elif f < 10:
        u = (f - 5) / 5
        sz = max(8, int(150 * scale * (1 - u) ** 1.3))
        put(img, impact_star(sz, seed + 1, P["core"], P["rim"]), x, y, alpha=1 - u * 0.5)
    if f < 7:                                                   # spark dashes radiating out
        rng = random.Random(seed * 7)
        lay = Image.new("RGBA", (520, 520), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        for i in range(10):
            a = rng.uniform(0, 2 * math.pi)
            r0 = 70 + f * 26 + rng.uniform(0, 30)
            ln = (34 + rng.uniform(0, 30)) * (1 - f / 7)
            taper_line(d, 260 + r0 * math.cos(a), 260 + r0 * math.sin(a), 260 + (r0 + ln) * math.cos(a),
                       260 + (r0 + ln) * math.sin(a), 7, 1, (255, 255, 255, 235))
        img.alpha_composite(lay, (int(x - 260), int(y - 260)))


def confetti(img, x, y, age, seed, pal="pink", n=34):
    """Dense star confetti as in play: dozens of filled stars burst forward and up, slow down quickly, then hang
    and drift right for up to 1.6 s (on a fast run they pile up into a star field in front of her)."""
    if age > 1.6:
        return
    P = PALETTES[pal]
    rng = random.Random(seed * 13 + 5)
    for i in range(n):
        ang = math.radians(rng.uniform(-110, 50))               # 0 = forward (right), negative = up
        v = rng.uniform(250, 950)
        life = rng.uniform(0.8, 1.6)
        if age > life:
            continue
        k = 4.0                                                 # strong drag: burst, then hang
        dist = v / k * (1 - math.exp(-k * age))
        px = x + dist * math.cos(ang) + 70 * age
        py = y + dist * math.sin(ang) - 25 * age
        size = int(rng.uniform(14, 62))
        rot = int(rng.uniform(0, 36) + age * rng.uniform(-40, 40)) % 36
        alpha = 1.0 if age < life * 0.6 else 1 - (age - life * 0.6) / (life * 0.4)
        put(img, solid_star(size, P["conf"][i % len(P["conf"])], rot), px, py, alpha)


def grind(img, x, y, g, seed):
    """A saw grinding along the floor: a few short sparks thrown back from the contact point every frame."""
    rng = random.Random(int(g * 30) * 31 + seed)
    lay = Image.new("RGBA", (300, 160), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(5):
        a = math.radians(rng.uniform(195, 245))
        r0 = rng.uniform(4, 30)
        ln = rng.uniform(20, 55)
        col = (255, 236, 150, 230) if i % 2 else (255, 255, 255, 230)
        taper_line(d, 200 + r0 * math.cos(a), 140 + r0 * math.sin(a), 200 + (r0 + ln) * math.cos(a),
                   140 + (r0 + ln) * math.sin(a), 5, 1, col)
    img.alpha_composite(lay, (int(x - 200), int(y - 140)))


def puffs(img, x, y, age, seed, n=4, size=90):
    if age > 0.34:
        return
    rng = random.Random(seed * 3 + 1)
    u = age / 0.34
    for i in range(n):
        a = rng.uniform(-math.pi, 0.3)
        d = 30 + 90 * (1 - (1 - u) ** 2)
        s = int(size * rng.uniform(0.6, 1.0) * (0.6 + 0.6 * u))
        put(img, puff(max(8, s)), x + d * math.cos(a), y + d * math.sin(a) * 0.6, alpha=1 - u ** 2)


@lru_cache(None)
def swoosh_img(w, h, up):
    """White crescent swoosh (strike smear), a pale blue inner edge."""
    def dr(d, k):
        W, H = w * k, h * k
        d.ellipse([0, 0, W, H], fill=(200, 230, 255, 255))
        d.ellipse([W * 0.05, H * 0.02, W * 0.97, H * 0.94], fill=WHITE)
        d.ellipse([-W * 0.1, H * 0.24, W * 0.8, H * 1.06], fill=(0, 0, 0, 0))
    im = _ss(w, h, dr)
    return im.transpose(Image.Transpose.FLIP_TOP_BOTTOM) if up else im


def swoosh(img, x, y, age, up=False):
    f = age * FPS
    if f >= 3:
        return
    im = swoosh_img(230, 210, up)
    put(img, im, x, y, alpha=1.0 if f < 2 else 0.5)


@lru_cache(None)
def _font(size):
    return ImageFont.truetype(str(ROOT / "pv" / "fonts" / "MPLUSRounded1c-ExtraBold.ttf"), size)


@lru_cache(None)
def banded_text(s, size, pal):
    """Chunky judgement letters: three horizontal colour bands, white outline, thin coloured edge, dark extrusion,
    tilted -8 deg."""
    P = PALETTES[pal]
    f = _font(size)
    bb = f.getbbox(s)
    pad = 26
    w, h = bb[2] - bb[0] + 2 * pad + 12, bb[3] - bb[1] + 2 * pad + 12
    org = (pad - bb[0], pad - bb[1])

    def mask(stroke, off=(0, 0)):
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).text((org[0] + off[0], org[1] + off[1]), s, font=f, fill=255, stroke_width=stroke,
                               stroke_fill=255)
        return np.asarray(m).astype(np.float32) / 255

    edge = mask(12)
    outline = mask(9)
    ext = np.maximum(mask(9, (7, 9)), mask(9, (4, 5)))
    body = mask(0)
    ys = np.arange(h)[:, None].astype(np.float32)
    top, bot = org[1] + bb[1], org[1] + bb[3]
    u = np.clip((ys - top) / max(1, bot - top), 0, 1)
    bands = np.where(u < 0.36, 0, np.where(u < 0.68, 1, 2))
    col = np.array(P["bands"], np.float32)[bands][:, 0, :]
    col = np.broadcast_to(col[:, None, :], (h, w, 3))
    out = np.zeros((h, w, 4), np.float32)

    def over(rgb, a):
        a = a[..., None]
        out[..., :3] = rgb * a + out[..., :3] * (1 - a)
        out[..., 3:] = a + out[..., 3:] * (1 - a)
    over(np.array(P["ext"], np.float32), np.maximum(ext, 0) * 1.0)
    over(np.array(P["edge"], np.float32), edge)
    over(np.array(WHITE, np.float32), outline)
    over(col, body)
    im = Image.fromarray((np.dstack([out[..., :3], out[..., 3] * 255])).clip(0, 255).astype(np.uint8), "RGBA")
    return im.rotate(8, Image.Resampling.BICUBIC, expand=True)


@lru_cache(None)
def _scaled(s, size, pal, sc_step):
    im = banded_text(s, size, pal)
    sc = sc_step / 100
    return im.resize((max(1, round(im.width * sc)), max(1, round(im.height * sc))), Image.Resampling.LANCZOS)


def judgement(img, x, y, age, pal="pink", word="PERFECT", size=78):
    """Pop-in with smeared ghosts for 3 frames, hold, rise and fade out by 0.55 s."""
    if age > 0.55:
        return
    f = age * FPS
    sc = [150, 126, 110, 104, 100][min(4, int(f))]
    im = _scaled(word, size, pal, sc)
    yy = y - max(0.0, age - 0.12) * 70
    alpha = 1.0 if age < 0.42 else 1 - (age - 0.42) / 0.13
    if f < 3:
        for k, a in ((2, 0.22), (1, 0.45)):
            put(img, im, x + k * (46 - 14 * f), yy - k * 4, alpha * a)
    put(img, im, x, yy, alpha)


# ---------------------------------------------------------------- speed (Fever)
def speed_streaks(img, g, n=44, y0=110, y1=880, col=(255, 255, 255)):
    """Thin tapered streaks across the screen, each living 4 frames and moving left fast; re-seeded per frame
    window so the field flickers like drawn speed lines."""
    fr = int(g * FPS)
    lay = Image.new("RGBA", (OW * 2, OH * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(n):
        birth = fr - ((fr + i * 3) % 4)
        rng = random.Random(birth * 131 + i * 7919)
        age = fr - birth
        y = rng.uniform(y0, y1)
        ln = rng.uniform(220, 760)
        x = rng.uniform(0, OW + 400) - age * 110
        th = rng.uniform(4, 10)
        a = int(rng.uniform(170, 245) * (1 - age / 5))
        c = col if i % 3 else (255, 170, 230)
        taper_line(d, 2 * x, 2 * y, 2 * (x + ln), 2 * y, 2 * th, 0.5, (*c, a))
    img.alpha_composite(lay.resize((OW, OH), Image.Resampling.BILINEAR))


def fever_bands(img, g, cols=((255, 90, 200), (150, 90, 255), (90, 200, 255))):
    """Translucent diagonal colour bands sweeping left across the background (Fever backdrop)."""
    yy, xx = np.mgrid[0:OH // 4, 0:OW // 4].astype(np.float32) * 4
    ph = (xx + yy * 0.45 + g * 1600) / 300
    k = np.floor(ph).astype(int) % len(cols)
    inband = (ph % 1) < 0.42
    a = np.zeros((OH // 4, OW // 4, 4), np.uint8)
    c = np.array(cols, np.uint8)[k]
    a[..., :3] = c
    a[..., 3] = np.where(inband, 70, 0).astype(np.uint8)
    img.alpha_composite(Image.fromarray(a, "RGBA").resize((OW, OH), Image.Resampling.BILINEAR))


@lru_cache(None)
def tinted(sp_id, col, alpha):
    sp = _TINT_SRC[sp_id]
    a = np.asarray(sp).astype(np.float32)
    rgb = np.broadcast_to(np.array(col, np.float32), a[..., :3].shape)          # flat silhouette
    return Image.fromarray(np.dstack([rgb, a[..., 3] * alpha]).clip(0, 255).astype(np.uint8), "RGBA")


_TINT_SRC = {}


def afterimages(img, sp, x, y, g):
    """Three tinted ghosts of her current frame trailing behind (pulse: spacing breathes with the beat)."""
    _TINT_SRC[id(sp)] = sp
    pulse = 1 + 0.25 * math.sin(g * 2 * math.pi * 136 / 60)
    for kk, col, al in ((3, (110, 220, 255), 0.22), (2, (255, 110, 210), 0.36), (1, (170, 120, 255), 0.55)):
        img.alpha_composite(tinted(id(sp), col, al), (int(x - kk * 95 * pulse), int(y)))


def radial_burst(img, cx, cy, age, seed=3):
    """Fever start: concentrated speed lines toward the centre (centre masked), 2-frame white flash first."""
    if age > 0.6:
        return
    f = age * FPS
    if f < 2:
        img.alpha_composite(Image.new("RGBA", (OW, OH), (255, 255, 255, 150 if f < 1 else 70)))
    lay = Image.new("RGBA", (OW, OH), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rng = random.Random(seed + int(f))
    R = math.hypot(OW, OH)
    for i in range(70):
        a = rng.uniform(0, 2 * math.pi)
        r0 = rng.uniform(330, 520)
        w = rng.uniform(6, 20)
        taper_line(d, cx + R * math.cos(a), cy + R * math.sin(a), cx + r0 * math.cos(a), cy + r0 * math.sin(a), w,
                   0.5, (255, 255, 255, int(200 * (1 - age / 0.6))))
    img.alpha_composite(lay)


# ---------------------------------------------------------------- dodge (jumping a saw)
def dodge_trail(img, frames):
    """Jump smear: her last frames as pale cyan / white silhouettes (oldest faintest), like the hit ghosts."""
    for k, (sp, x, y) in enumerate(frames):
        _TINT_SRC[id(sp)] = sp
        col = (200, 240, 255) if k % 2 else (255, 255, 255)
        img.alpha_composite(tinted(id(sp), col, [0.12, 0.2, 0.3][k % 3]), (int(x), int(y)))


def clear_spark(img, x, y, age, seed):
    """The saw passing under her: a short fan of sparks thrown backward off its teeth (f0-6)."""
    f = age * FPS
    if f >= 7:
        return
    rng = random.Random(seed * 17)
    lay = Image.new("RGBA", (600, 400), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(12):
        a = math.radians(rng.uniform(190, 260))
        r0 = 20 + f * 34 + rng.uniform(0, 20)
        ln = rng.uniform(30, 70) * (1 - f / 7)
        col = (255, 230, 120, 240) if i % 2 else (255, 255, 255, 240)
        taper_line(d, 300 + r0 * math.cos(a), 300 + r0 * math.sin(a), 300 + (r0 + ln) * math.cos(a),
                   300 + (r0 + ln) * math.sin(a), 6, 1, col)
    img.alpha_composite(lay, (int(x - 300), int(y - 300)))


def ring_flash(img, x, y, age, col=(255, 255, 255)):
    """Flat ellipse shock ring on the floor (take-off / landing), 6 frames."""
    if age > 0.2:
        return
    u = age / 0.2
    w, h = int(120 + 220 * u), int(26 + 30 * u)
    lay = Image.new("RGBA", (w + 20, h + 20), (0, 0, 0, 0))
    ImageDraw.Draw(lay).ellipse([10, 10, 10 + w, 10 + h], outline=(*col, int(230 * (1 - u))), width=7)
    img.alpha_composite(lay, (int(x - w / 2 - 10), int(y - h / 2 - 10)))
