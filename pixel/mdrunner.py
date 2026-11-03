"""XIYIN's HD in-game runner (Muse Dash-like game layer at 1080p), facing right.

Colours are snapped to the owner's sheet first (pixel/mdrecolor.py), then the eyes are replaced by the one canonical
eye matching the sheet and the stream-cam portrait (pixel/mdeyes.py).
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
import mdface as FC
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


BACK_HAND = (150, 640, 201, 722)   # hand bounds; edits run in a padded window around it
   # the run drawing's back hand: a ragged pale smudge past the cuff; the sheet has
                                   # sleeves past the wrists, so the back sleeve simply ends at its cuff


@lru_cache(None)
def full_rgba(name):
    """Cut-out drawing on its original canvas (drawing coordinates kept)."""
    im = MD.cutout(FC.fix(name), holes=HOLES if name == BODY else (), crop=False, band_px=1)
    if name == BODY:
        a = np.asarray(im).copy()
        x0, y0, x1, y1 = BACK_HAND
        win = (slice(y0 - 30, y1 + 30), slice(x0 - 30, x1 + 30))
        sub = a[win].astype(int)
        inbox = np.zeros(sub.shape[:2], bool)
        inbox[30:-30, 30:-30] = True
        was = sub[..., 3] > 0
        sleeve = (sub[..., 2] > sub[..., 0] + 20) & (sub[..., :3].mean(-1) > 60) & was
        hand = inbox & was & ~ndimage.binary_dilation(sleeve, iterations=2)      # skin, its line art, white cuff
        keep = was & ~hand
        keep = ndimage.binary_opening(keep, iterations=1) | (was & ~inbox)
        # a 3 px dark outline where the hand was cut away, so the cuff end is closed like the rest of her
        edge = keep & ~ndimage.binary_erosion(keep, iterations=3, border_value=1) & \
            ndimage.binary_dilation(was & ~keep, iterations=4) & inbox
        patch = a[win].copy()
        patch[edge, :3] = LINE
        patch[..., 3] = np.where(keep, patch[..., 3], 0)
        a[win] = patch
        im = Image.fromarray(a, "RGBA")
    return im


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


# ---------------------------------------------------------------- loadout
# Like Muse Dash, her loadout changes through the PV (mdgame.LOADOUT): unarmed she fights with sleeve punches and
# kicks; armed she carries the one canonical paw mic (pixel/mdweapon.py) while running and jumping and every hit is
# one of the armed pose drawings. Sizes: the eye (pixel/mdeyes.py) is the scale key, so her head is the same size in
# every frame and the mic has one fixed length on screen.
HAND = (689.0, 752.0)          # run drawing: front fist (the body layer's arms do not move)
MIC_DEG = -38                  # carried mic: tilted forward, head up and ahead of her
AX = {}                        # id(sprite) -> anchor x (body only), read by mdgame so the mic never shifts her


def _scale():
    return HEIGHT / (GROUND - 18)


def eye_px():
    """Her eye height on screen (px) = the scale key for every drawing."""
    import mdeyes
    return mdeyes.eye_height(BODY) * _scale()


@lru_cache(None)
def mic_len():
    """Mic length on screen (px), from the armed pose drawings."""
    import mdeyes
    import mdweapon as WP
    WP.armed("v3_windup_49701")
    h = WP.INFO["v3_windup_49701"]["height"]
    return WP.LENGTH * h * eye_px() / mdeyes.eye_height("v3_windup_49701")


@lru_cache(None)
def carried_mic():
    """The paw mic as the armed poses draw it, sized for the run drawing (drawing px), rotated; (img, grip_xy)."""
    import mdeyes
    import mdweapon as WP
    WP.armed("v3_windup_49701")
    info = WP.INFO["v3_windup_49701"]
    k = eye_px() / mdeyes.eye_height("v3_windup_49701") / _scale()        # pose drawing px -> run drawing px
    im, pom = WP.mic_sprite(round(info["length"] * k), round(info["width"] * k))
    grip = (pom[0], pom[1] - 0.10 * info["length"] * k)                    # fist a little above the pommel
    pad = int(info["length"] * k)
    cv = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    cv.alpha_composite(im, (pad, pad))
    piv = (grip[0] + pad, grip[1] + pad)
    return cv.rotate(MIC_DEG, Image.Resampling.BICUBIC, center=piv), piv


def _with_mic(canvas, dy):
    """Wider canvas with the mic in her front fist (drawn under the body layer: her fist wraps the handle)."""
    mic, piv = carried_mic()
    extra = 420
    cv = Image.new("RGBA", (canvas.width + extra, canvas.height), (0, 0, 0, 0))
    cv.alpha_composite(canvas)
    cv.alpha_composite(mic, (int(round(HAND[0] - piv[0])), int(round(HAND[1] + dy - piv[1]))))
    return cv


def _body_anchor(canvas):
    a = np.asarray(canvas.getchannel("A"))
    rows = np.nonzero(a.any(1))[0]
    top, bot = rows.min(), rows.max()
    xs = np.nonzero(a[top: int(top + 0.55 * (bot - top))] > 128)[1]
    return float(xs.mean())


def _register(sprite, ax):
    AX[id(sprite)] = ax
    return sprite


@lru_cache(None)
def run_frame(i, stride=1.0, armed=False):
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
    if armed:
        plain = canvas.copy()
        plain.alpha_composite(body, (0, int(round(bob))))
        canvas = _with_mic(canvas, int(round(bob)))
    canvas.alpha_composite(body, (0, int(round(bob))))
    sp, feet = _finish(canvas, GROUND)
    if armed:
        _register(sp, _body_anchor(plain) * _scale())
    return sp, feet


def run_at(t, speed_scale=1.0, armed=False):
    i = int((t / BEAT) * N_PHASE) % N_PHASE      # one stride per beat
    return run_frame(i, round(speed_scale, 1), armed)


@lru_cache(None)
def jump_frame(kind="up", armed=False):
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
    body = warp_hair(body_layer(), 0.3 if kind == "up" else 0.8)
    if armed:
        plain = canvas.copy()
        plain.alpha_composite(body)
        canvas = _with_mic(canvas, 0)
    canvas.alpha_composite(body)
    sp, feet = _finish(canvas, GROUND)
    if armed:
        _register(sp, _body_anchor(plain) * _scale())
    return sp, feet


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
    src = FC.fix(name)      # sheet colours + canonical eye + N5-fitted face (pixel/mdface.py)
    if shadow:
        src = _drop_shadow(src, shadow)
    cut = MD.cutout(src, crop=False, band_px=1)
    a = np.asarray(cut.getchannel("A"))
    ground = float(np.nonzero(a.any(1))[0].max()) + 1
    scale = HEAD_RUN / head
    big = cut.resize((round(cut.width * scale), round(cut.height * scale)), Image.Resampling.LANCZOS)
    return _finish(big, ground * scale)


ARMED_GROUND = ("v3_smash_49702", "v3_upper_49701", "v3_upper_49702")   # armed hits cycle through these
ARMED_AIR = ("v3_airslam_49701", "v3_airslam_49702")
# measured ear-tip-to-chin on screen after the eye scale: these three came out ~10% larger than the run frame
HEAD_FIX = {"v3_upper_49702": 0.9, "v3_airslam_49701": 0.9, "v3_airslam_49702": 0.9}


@lru_cache(None)
def armed_strike(name):
    """(sprite, feet row): an armed pose drawing at the runner's scale (same eye = same head size)."""
    import mdeyes
    import mdweapon as WP
    im = WP.armed(name)
    info = WP.INFO[name]
    s = eye_px() / mdeyes.eye_height(name) * HEAD_FIX.get(name, 1.0)
    big = im.resize((round(im.width * s), round(im.height * s)), Image.Resampling.LANCZOS)
    bb = big.getbbox()
    sp = big.crop(bb)
    return _register(sp, info["ax"] * s - bb[0]), info["feet"] * s - bb[1]


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
