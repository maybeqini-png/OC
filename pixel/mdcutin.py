"""Stage transitions as Muse Dash-style character cut-ins (owner 2026-11-03: "the transitions feel stiff").

Studied frame by frame on the official trailer (30 fps): a scene change never slides flat. The picture whips away
(zoom-in, a few degrees of roll, horizontal motion blur) while a tilted colour band with the character's big
close-up shoots in with speed lines and rings: fast in, a short slow drift, fast out. The next scene whips in the
same way, rolling back to level. Here, per transition (window p = 0..1):
  0.00-0.30  the old game picture zooms to 1.22 and rolls -7 deg with growing blur; the band sweeps in from the right
  0.22-0.80  band across the screen (tilted -12 deg, stage colour, dots, speed lines, white edges), rings pulse,
             XIYIN's approved bust (art/generated/vtuber3/final) zips in, drifts, zips out; the scene swaps at 0.5
  0.70-1.00  band exits left; the new picture rolls back from +7 deg and zooms 1.22 -> 1 as the blur clears.
The game HUD stays steady on top (it is drawn after the whip).
"""
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

import mdsprites as MD

BUSTS = Path(__file__).parent.parent / "art/generated/vtuber3/final"
BG = (238, 238, 244)


def ease_in(u):
    return u * u * u


def ease_out(u):
    return 1 - (1 - u) ** 3


FIST = (1537, 1248)            # her raised fist in the bust drawings (2048 px); every bust shares the pose
MIC_LEN, MIC_W, MIC_DEG = 980, 50, -22


@lru_cache(None)
def bust(name, h, armed=False):
    """The approved bust, cut out (its light grey background and the gaps between hair and arm), height h. armed:
    the paw mic in her raised fist (the same mic as in the game), drawn behind her so her fist closes over it - the
    close-up shows the loadout of the section that follows, as Muse Dash's character close-ups do."""
    src = Image.open(BUSTS / f"{name}.png").convert("RGB")
    a = np.asarray(src).astype(int)
    near = np.abs(a - np.array(BG)).sum(-1) < 14
    lab, n = ndimage.label(near)
    sizes = ndimage.sum(near, lab, range(1, n + 1))
    im = MD.cutout(src, crop=False)
    al = np.asarray(im).copy()
    al[ndimage.binary_dilation(np.isin(lab, [i + 1 for i, z in enumerate(sizes) if z > 800]), iterations=1), 3] = 0
    im = Image.fromarray(al, "RGBA")
    if armed:
        import mdweapon as WP
        mic, (px, py) = WP.mic_sprite(MIC_LEN, MIC_W)
        gy = py - 0.12 * MIC_LEN
        pad = MIC_LEN
        cv = Image.new("RGBA", (mic.width + 2 * pad, mic.height + 2 * pad), (0, 0, 0, 0))
        cv.alpha_composite(mic, (pad, pad))
        cv = cv.rotate(MIC_DEG, Image.Resampling.BICUBIC, center=(px + pad, gy + pad))
        big = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
        big.alpha_composite(cv, (int(FIST[0] - px), int(FIST[1] - gy)))
        big.alpha_composite(im, (pad, pad))
        im = big
    im = im.crop(im.getbbox())
    return im.resize((round(im.width * h / im.height), h), Image.Resampling.LANCZOS)


def whip(img, zoom, rot, blur):
    """Zoom about the centre, roll, and smear horizontally (motion blur) - the picture whipping past the camera."""
    W, H = img.size
    if zoom != 1 or rot:
        big = img.resize((round(W * zoom), round(H * zoom)), Image.Resampling.BICUBIC)
        big = big.rotate(rot, Image.Resampling.BICUBIC)
        x0, y0 = (big.width - W) // 2, (big.height - H) // 2
        img = big.crop((x0, y0, x0 + W, y0 + H))
    if blur > 0.5:
        a = np.asarray(img.convert("RGB")).astype(np.float32)
        k = int(blur)
        a = ndimage.uniform_filter1d(a, size=2 * k + 1, axis=1, mode="nearest")
        img = Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGB").convert("RGBA")
    return img


@lru_cache(None)
def _band_base(W, H, col):
    """Horizontal band (white edges, stage colour, polka dots) on an oversized canvas, tilted 12 deg."""
    BW, BH = int(W * 1.8), int(H * 1.8)
    lay = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    bh = int(H * 0.56)
    y0, y1 = BH // 2 - bh // 2, BH // 2 + bh // 2
    d.rectangle((0, y0 - 16, BW, y1 + 16), fill=(255, 255, 255, 255))
    d.rectangle((0, y0, BW, y1), fill=(*col, 255))
    light = tuple(min(255, c + 55) for c in col)
    for i in range(0, BW // 90 + 2):
        for j in range(0, bh // 70 + 1):
            x, y = i * 90 + (j % 2) * 45, y0 + 30 + j * 70
            d.ellipse((x - 13, y - 13, x + 13, y + 13), fill=(*light, 255))
    return lay.rotate(12, Image.Resampling.BICUBIC)


def _band(W, H, x_off, col, t):
    base = _band_base(W, H, col)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lay.alpha_composite(base, (int(x_off - (base.width - W) / 2), -(base.height - H) // 2))
    d = ImageDraw.Draw(lay)
    rng = np.random.default_rng(int(t * 30))
    slope = math.tan(math.radians(12))
    for _ in range(24):                                       # speed lines along the band
        x = rng.uniform(0, W)
        y = H / 2 + rng.uniform(-H * 0.25, H * 0.25) - (x - W / 2) * slope
        L = rng.uniform(140, 460)
        d.line((x, y, x + L, y - L * slope), fill=(255, 255, 255, 190), width=int(rng.uniform(3, 8)))
    return lay


def _rings(img, cx, cy, u, cols):
    d = ImageDraw.Draw(img)
    for k, c in enumerate(cols):
        r = 120 + 520 * ((u * 1.6 + k * 0.33) % 1)
        w = int(18 * (1 - ((u * 1.6 + k * 0.33) % 1)) + 4)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(*c, 220), width=w)


def cutin(old, new, p, portrait, col, armed=False):
    """Full game picture for transition progress p (old / new = finished game pictures without the HUD)."""
    W, H = old.size
    if p < 0.5:
        u = min(1.0, p / 0.3)
        pic = whip(old, 1 + 0.22 * ease_in(u), -7 * ease_in(u), 40 * ease_in(u))
    else:
        u = min(1.0, max(0.0, (1 - p) / 0.3))
        pic = whip(new, 1 + 0.22 * ease_in(u), 7 * ease_in(u), 40 * ease_in(u))
    pic = pic.convert("RGBA")
    # band: in 0.12-0.30 (from the right), across 0.30-0.70, out 0.70-0.88 (to the left)
    if 0.12 <= p < 0.88:
        if p < 0.30:
            x_off = W * (1 - ease_out((p - 0.12) / 0.18))
        elif p < 0.70:
            x_off = -40 * (p - 0.30) / 0.40
        else:
            x_off = -40 - (W + 400) * ease_in((p - 0.70) / 0.18)
        layer = _band(W, H, x_off, col, p)
        _rings(layer, W * 0.62 + x_off, H * 0.5, p, [(255, 255, 255), (255, 214, 74), (156, 196, 255)])
        # her close-up: zips in, drifts, zips out (slightly behind the band's motion so it reads as parallax)
        if 0.18 <= p < 0.84:
            b = bust(portrait, int(H * 0.86), armed)
            if p < 0.34:
                bx = W * 1.05 - (W * 1.05 - W * 0.40) * ease_out((p - 0.18) / 0.16)
            elif p < 0.66:
                bx = W * 0.40 - W * 0.06 * (p - 0.34) / 0.32
            else:
                bx = W * 0.34 - (W * 0.34 + b.width) * ease_in((p - 0.66) / 0.18)
            br = b.rotate(-6, Image.Resampling.BICUBIC, expand=True)
            if p < 0.34 or p >= 0.66:                          # smeared while zipping
                br = whip(br, 1.0, 0, 18).convert("RGBA")
                br.putalpha(Image.fromarray(ndimage.uniform_filter1d(
                    np.asarray(b.rotate(-6, Image.Resampling.BICUBIC, expand=True).getchannel("A")).astype(np.float32),
                    37, axis=1).astype(np.uint8)))
            layer.alpha_composite(br, (int(bx), int(H - br.height + H * 0.08)))
        pic.alpha_composite(layer)
    return pic
