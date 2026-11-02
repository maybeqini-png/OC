"""XIYIN's HD in-game runner (Muse Dash-like game layer at 1080p), facing right.

Colours are snapped to the owner's sheet first (pixel/mdrecolor.py).
Run cycle = one V5 body drawing (art/generated/md_style/z_run_49102) on rigged legs, like the approved pixel avatar
(pixel/avatar.py + legs.py), so every frame is the same drawing and nothing flickers between frames:
- the drawing is cut out of its white background (pixel/mdsprites.cutout, plus the background trapped between two
  hair strands), its drawn legs and boots are removed below the shorts;
- each leg is a thigh and a shin (two-bone IK, the knee bends forward) drawn as smooth tapered capsules in the
  drawing's colours with its dark line, plus the drawn boot (with its sock band) as a rigid foot;
- the far leg uses shadow tones; the hip bobs twice per stride; back hair and tail follow through (smooth warp);
- everything is drawn at the drawing's own scale (about 4.5x the final size) and downscaled once, so edges stay
  anti-aliased and never pick up white.
Strike frames are separate V5 drawings in the same style (shown for a few frames, as in Muse Dash).

usage: python3 mdrunner.py sheet out.png
"""
import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

import legs
import mdrecolor as RC
import mdsprites as MD

HERE = Path(__file__).parent
SRC = HERE.parent / "art/generated/md_style"
BEAT = 60 / 136
HEIGHT = 290                      # final sprite height (head to sole) at 1080p
N_PHASE = 16

BODY = "z_run_49102"
HOLES = ((280, 370),)            # trapped background between hair strands (drawing pixels)
LINE = (22, 26, 52)
SKIN, SKIN_SH = (255, 242, 235), (247, 206, 194)
SKIN_FAR, SKIN_FAR_SH = (246, 200, 188), (228, 176, 166)
HIP_N, HIP_F = (508.0, 838.0), (445.0, 846.0)
L1, L2 = 128.0, 104.0            # thigh, shin (drawing px)
R_HIP, R_KNEE, R_ANKLE = 40.0, 29.0, 25.0
LW = 5.5                          # line width (drawing px)
GROUND = 1212.0                   # sole line of the drawing
SOCK_TOP = ((548, 1023), (628, 996))   # line across the front sock top: the boot piece is everything below it
ANKLE_D = (600.0, 1046.0)         # ankle joint in the drawing (pivot of the boot piece)
SHIN_D = math.atan2(1046 - 955, 600 - 555)   # shin direction in the drawing
SX, SY = 6.2, 4.2                 # legs.PATH (pixel avatar units) -> drawing px


@lru_cache(None)
def full_rgba(name):
    """Cut-out drawing on its original canvas (drawing coordinates kept)."""
    return MD.cutout(RC.recolor(name), holes=HOLES if name == BODY else (), crop=False)


@lru_cache(None)
def body_layer():
    """The run drawing without its legs: keep everything above the shorts hem plus the shorts themselves."""
    im = full_rgba(BODY)
    a = np.asarray(im).copy()
    H, W = a.shape[:2]
    rgb = a[..., :3].astype(int)
    lum, sat = rgb.mean(-1), rgb.max(-1) - rgb.min(-1)
    grey = (lum < 120) & (sat < 40) & (a[..., 3] > 0)
    lab, _ = ndimage.label(grey)
    shorts = np.isin(lab, [lab[805, 380], lab[830, 500]])
    shorts = ndimage.binary_fill_holes(ndimage.binary_closing(shorts, iterations=4))
    yy, xx = np.mgrid[0:H, 0:W]
    hem = np.where(shorts.any(0), H - 1 - np.argmax(shorts[::-1], 0), 0)        # lowest shorts row per column
    near = ndimage.binary_dilation(shorts, iterations=7) & (yy <= hem[None, :] + 6)   # its outline, not the legs'
    keep = (yy < 812) | (near & (yy < 885) & (xx > 290) & (xx < 575))
    skin = (rgb[..., 0] > 190) & (rgb[..., 0] - rgb[..., 2] > 8) & (rgb[..., 0] >= rgb[..., 1])
    keep &= ~((yy >= 800) & ndimage.binary_dilation(skin, iterations=3))        # old leg tops under the hem
    # the back hand's pale fingers would read as white specks at game size: give them the skin shadow tone
    pale = (lum > 225) & (sat < 40) & (yy > 640) & (yy < 720) & (xx > 150) & (xx < 200)
    a[pale, :3] = SKIN_SH
    a[..., 3] = np.where(keep, a[..., 3], 0)
    return Image.fromarray(a, "RGBA")


@lru_cache(None)
def boot_piece(far=False):
    """The front boot with its sock band, below the sock-top line; pivot = ANKLE_D. Far boot in shadow tones."""
    a = np.asarray(full_rgba(BODY)).copy()
    H, W = a.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    (x0, y0), (x1, y1) = SOCK_TOP
    below = (xx - x0) * (y1 - y0) - (yy - y0) * (x1 - x0) < 0
    rgb = a[..., :3].astype(int)
    skin = (rgb[..., 0] > 190) & (rgb[..., 0] - rgb[..., 2] > 8) & (rgb[..., 0] >= rgb[..., 1])
    skin = ndimage.binary_dilation(skin, iterations=2) & (rgb.mean(-1) > 120)      # incl. their soft edge
    m = below & (xx > 535) & (yy > 985) & ~skin
    lab, n = ndimage.label(m & (a[..., 3] > 0))                                   # keep the boot, drop slivers
    if n > 1:
        sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
        m &= lab == (1 + int(np.argmax(sizes)))
    a[..., 3] = np.where(m, a[..., 3], 0)
    if far:
        a[..., :3] = (a[..., :3] * 0.72).astype(np.uint8)
    return Image.fromarray(a, "RGBA")


def _capsule(shape, p0, p1, r0, r1, origin):
    H, W = shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    xx += origin[0] + 0.5
    yy += origin[1] + 0.5
    vx, vy = p1[0] - p0[0], p1[1] - p0[1]
    L2_ = max(1e-6, vx * vx + vy * vy)
    t = np.clip(((xx - p0[0]) * vx + (yy - p0[1]) * vy) / L2_, 0, 1)
    dx, dy = xx - (p0[0] + t * vx), yy - (p0[1] + t * vy)
    d = np.hypot(dx, dy)
    r = r0 + (r1 - r0) * t
    side = (dx * -vy + dy * vx) / math.sqrt(L2_)          # >0 on the left of the bone direction
    return d - r, side / np.maximum(r, 1)


def draw_leg(canvas, hip, knee, ankle, far):
    """Thigh + shin as one smooth silhouette with the drawing's line; shadow on the back of the leg."""
    xs = [hip[0], knee[0], ankle[0]]
    ys = [hip[1], knee[1], ankle[1]]
    pad = R_HIP + 12
    x0, y0 = int(min(xs) - pad), int(min(ys) - pad)
    x1, y1 = int(max(xs) + pad), int(max(ys) + pad)
    shape = (y1 - y0, x1 - x0)
    d1, s1 = _capsule(shape, hip, knee, R_HIP, R_KNEE, (x0, y0))
    d2, s2 = _capsule(shape, knee, ankle, R_KNEE, R_ANKLE, (x0, y0))
    d = np.minimum(d1, d2)
    side = np.where(d1 < d2, s1, s2)
    fill = np.clip(0.5 - d, 0, 1)                         # 1-px anti-aliased edges
    line = np.clip(0.5 - (d - LW), 0, 1)
    base, sh = (SKIN_FAR, SKIN_FAR_SH) if far else (SKIN, SKIN_SH)
    # the back of the leg (left of the bone when it points down) gets the shadow tone, a soft-edged band
    shadow = np.clip((side - 0.35) * 6, 0, 1)
    col = np.array(base, np.float32) * (1 - shadow[..., None]) + np.array(sh, np.float32) * shadow[..., None]
    rgb = np.array(LINE, np.float32) * (1 - fill[..., None]) + col * fill[..., None]
    rgba = np.dstack([rgb, line * 255]).clip(0, 255).astype(np.uint8)
    canvas.alpha_composite(Image.fromarray(rgba, "RGBA"), (x0, y0))


def place_boot(canvas, ankle, shin_ang, far):
    """Boot rigid with the shin, damped (chunky boots flex a little at the ankle)."""
    rot = math.degrees(shin_ang - SHIN_D) * 0.75
    b = boot_piece(far)
    box = (520, 980, 830, 1216)
    piece = b.crop(box)
    piv = (ANKLE_D[0] - box[0], ANKLE_D[1] - box[1])
    big = Image.new("RGBA", (piece.width * 2, piece.height * 2), (0, 0, 0, 0))
    off = (piece.width - int(piv[0]), piece.height - int(piv[1]))
    big.paste(piece, off)
    big = big.rotate(-rot, Image.Resampling.BICUBIC, center=(piece.width, piece.height))
    canvas.alpha_composite(big, (int(round(ankle[0] - piece.width)), int(round(ankle[1] - piece.height))))


def leg_pose(phase, stride=1.0):
    """Ankle target (drawing px) for one leg at a cycle phase, from the pixel avatar's foot path."""
    dx, dy = legs.catmull(legs.PATH, phase)
    return dx * SX * stride, dy * SY


def warp_hair(im, phase):
    """Follow-through on the back hair (x < 360, rows 250-700) and the tail (rows 690-800, x < 330)."""
    a = np.asarray(im).astype(np.float32)
    H, W = a.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    w_h = np.clip((360 - xx) / 220, 0, 1) * np.clip((yy - 250) / 200, 0, 1) * np.clip((760 - yy) / 60, 0, 1)
    dx = 9.0 * w_h * np.sin(2 * math.pi * phase - (yy - 250) / 90 - (360 - xx) / 140)
    dy0 = 5.0 * w_h * np.sin(2 * math.pi * phase + 0.8 - (360 - xx) / 120)
    w_t = np.clip((330 - xx) / 260, 0, 1) * ((yy >= 680) & (yy < 805))
    dy = dy0 + 11.0 * w_t * np.sin(2 * math.pi * phase + 1.4 - (330 - xx) / 70)
    out = np.empty_like(a)
    for c in range(4):
        out[..., c] = ndimage.map_coordinates(a[..., c] * (a[..., 3] / 255 if c < 3 else 1), [yy - dy, xx - dx],
                                              order=1, mode="constant")
    al = np.maximum(out[..., 3], 1e-3) / 255
    out[..., :3] = np.where(out[..., 3:4] > 0, out[..., :3] / al[..., None], 0)
    return Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGBA")


def _finish(canvas, feet_y):
    """Downscale to the game size: (sprite, feet row in the sprite)."""
    s = HEIGHT / (GROUND - 18)
    w, h = round(canvas.width * s), round(canvas.height * s)
    small = canvas.resize((w, h), Image.Resampling.LANCZOS)
    bb = small.getbbox()
    small = small.crop((0, bb[1], w, bb[3]))
    return small, feet_y * s - bb[1]


@lru_cache(None)
def run_frame(i, stride=1.0):
    phase = i / N_PHASE
    bob = 9.0 * math.cos(4 * math.pi * (phase - 0.25))     # lowest at mid-stance, highest in flight
    W, H = 832, 1300
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hips = {}
    for far, ph, hip in ((True, (phase + 0.5) % 1, HIP_F), (False, phase, HIP_N)):
        hx, hy = hip[0], hip[1] + bob
        dx, dy = leg_pose(ph, stride)
        ank = (hx + dx, GROUND - 166 + dy)
        kx, ky, ank = legs.ik((hx, hy), ank, L1, L2)
        hips[far] = ((hx, hy), (kx, ky), ank)
    for far in (True, False):
        (h, k, a) = hips[far]
        draw_leg(canvas, h, k, a, far)
        place_boot(canvas, a, math.atan2(a[1] - k[1], a[0] - k[0]), far)
    body = warp_hair(body_layer(), phase)
    canvas.alpha_composite(body, (0, int(round(bob))))
    return _finish(canvas, GROUND)


def run_at(t, speed_scale=1.0):
    i = int((t / BEAT) * N_PHASE) % N_PHASE      # one stride per beat
    return run_frame(i, round(speed_scale, 1))


@lru_cache(None)
def jump_frame(kind="up"):
    """Knees tucked (rising) or legs reaching down (falling)."""
    W, H = 832, 1300
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if kind == "up":
        tg = {True: (-40, -150), False: (70, -120)}
    else:
        tg = {True: (-60, -40), False: (40, -20)}
    for far, hip in ((True, HIP_F), (False, HIP_N)):
        dx, dy = tg[far]
        ank = (hip[0] + dx, GROUND - 166 + dy)
        kx, ky, ank = legs.ik(hip, ank, L1, L2)
        draw_leg(canvas, hip, (kx, ky), ank, far)
        place_boot(canvas, ank, math.atan2(ank[1] - ky, ank[0] - kx), far)
    canvas.alpha_composite(warp_hair(body_layer(), 0.3 if kind == "up" else 0.8))
    return _finish(canvas, GROUND)


# strike / air drawings: (take, head height in drawing px measured ear tip to chin, ground shadow colour or None)
STRIKES = {"punch": ("z_punch_49113", 322, (131, 171, 223)), "air": ("z_air_49123", 405, None)}
HEAD_RUN = 355


def _drop_shadow(im, col):
    """Paint a flat ground shadow (and its blend into white) white, so the cut-out removes it."""
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    c, w = np.array(col, np.float32), np.array([255, 255, 255], np.float32)
    d = w - c
    t = np.clip(((a - c) * d).sum(-1) / (d * d).sum(), 0, 1)
    off = np.linalg.norm(a - (c + t[..., None] * d), axis=-1)
    a[(off < 14) & (t < 0.98)] = 255
    return Image.fromarray(a.astype(np.uint8), "RGB")


@lru_cache(None)
def strike_frame(kind):
    """(sprite, feet row): a whole strike drawing at the run body's head size."""
    name, head, shadow = STRIKES[kind]
    src = RC.recolor(name)
    if shadow:
        src = _drop_shadow(src, shadow)
    cut = MD.cutout(src, crop=False)
    a = np.asarray(cut.getchannel("A"))
    ground = float(np.nonzero(a.any(1))[0].max()) + 1
    scale = HEAD_RUN / head
    big = cut.resize((round(cut.width * scale), round(cut.height * scale)), Image.Resampling.LANCZOS)
    return _finish(big, ground * scale)


if __name__ == "__main__" and sys.argv[1] == "sheet":
    frames = [run_frame(i) for i in range(0, N_PHASE, 4)] + [jump_frame("up"), jump_frame("down"), strike_frame("punch"), strike_frame("air")]
    th = max(f[0].height for f in frames) + 20
    bgs = [(30, 24, 60), (255, 150, 210), (150, 210, 255)]
    S = Image.new("RGB", (sum(f[0].width + 10 for f in frames), th * 3))
    for r, c in enumerate(bgs):
        S.paste(Image.new("RGB", (S.width, th), c), (0, r * th))
        x = 0
        for im, feet in frames:
            S.paste(im, (x, r * th + int(th - 10 - feet)), im)
            x += im.width + 10
    S.save(sys.argv[2])
