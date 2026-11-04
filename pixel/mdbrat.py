"""XIYIN's cheeky-brat acting pack in the game layer (owner 2026-11-04: "make her more captivating").

Poses (art/generated/md_style/brat, V4.5 Precise Reference on her approved game drawing; see prompts.sh there):
akanbe (finger pulls the lower eyelid, tongue out), finger wag (smug doyagao, chin up), fluster (the miss), peace
(victory, wink), boop (the めっ scold toward the viewer), and the armed paw-mic poses at her run proportions.
Every pose is checked against the owner's sheet (art/reference/oc_reference_sheet.webp):
- colours: mdrecolor.snap_v45 (hair to the sheet's royal blue by region, irises to the canonical eye's blues);
- the sheet's small details the image model leaves out are drawn on: the black cat-face emblem on the tie and the
  light-blue smug cat-face patch on the chest, at the emblem's height to the viewer's right of the tie;
- one scale: every pose is sized by her head (hair top to chin, HEAD below, drawing px) against the run drawing.
"""
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

import mdrecolor as RC
import mdsprites as MD

SRC = Path(__file__).parent.parent / "art/generated/md_style"
POSES = {"akanbe": "brat/t_akanbe_65001", "wag": "brat/t_wag_65001", "fluster": "brat/m_fluster_65001",
         "peace": "brat/v_peace_65003", "boop": "brat/b_boop_65003"}
ARMED = {"windup": "brat/a_windup_65002", "smash": "brat/a_smash_65001", "upper": "brat/a_upper_65001",
         "airslam": "brat/a_airslam_65001"}
ARMED_GROUND = ("smash", "upper", "windup")   # armed hits cycle through these (a different drawing each hit)
ARMED_AIR = ("airslam", "upper")
# head height, hair top to chin (drawing px), measured on a 25 px grid; z_run_49102 = the run drawing
HEAD = {"z_run_49102": 322, "brat/t_akanbe_65001": 346, "brat/t_wag_65001": 373, "brat/m_fluster_65001": 367,
        "brat/v_peace_65003": 319, "brat/b_boop_65003": 355, "brat/a_windup_65002": 344,
        "brat/a_smash_65001": 374, "brat/a_upper_65001": 274, "brat/a_airslam_65001": 250}
# tie boxes read on a grid where the automatic finder caught hair; None = tie hidden (back / arms over it): no details
TIES = {"brat/t_wag_65001": (283, 583, 400, 783), "brat/v_peace_65003": (283, 550, 358, 783),
        "brat/b_boop_65003": (317, 583, 383, 800), "brat/a_airslam_65001": (308, 733, 375, 917),
        "brat/a_windup_65002": None, "brat/a_smash_65001": None, "brat/a_upper_65001": None}
PATCH = (120, 170, 235)
PATCH_D = (40, 60, 120)


def _tie(orig):
    """The necktie in the original take (light steel blue, vertical, in the torso band): bbox or None."""
    a = np.asarray(orig.convert("RGB")).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = a.mean(-1)
    fg = lum < 240
    ys = np.nonzero(fg.any(1))[0]
    top, bot = ys.min(), ys.max()
    band = np.zeros(fg.shape, bool)
    band[int(top + 0.28 * (bot - top)): int(top + 0.72 * (bot - top))] = True
    m = band & (lum > 85) & (lum < 190) & (b > r + 40) & (g > r + 8) & ~((g > 140) & (b > 200))
    lab, n = ndimage.label(ndimage.binary_opening(m, iterations=1))
    best = None
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        z = int((lab[sl] == i).sum())
        if z > 400 and h > 0.9 * w and (best is None or z > best[0]):
            best = (z, (sl[1].start, sl[0].start, sl[1].stop, sl[0].stop))
    return best[1] if best else None


def _cat_face(d, cx, cy, r, fill, line, eyes_closed=True, whiskers=True, w=3):
    """Small cat face (round head, two ears) like the sheet's patch / emblem."""
    d.polygon([(cx - r * 0.95, cy - r * 0.2), (cx - r * 0.75, cy - r * 1.25), (cx - r * 0.2, cy - r * 0.8)],
              fill=fill, outline=line)
    d.polygon([(cx + r * 0.95, cy - r * 0.2), (cx + r * 0.75, cy - r * 1.25), (cx + r * 0.2, cy - r * 0.8)],
              fill=fill, outline=line)
    d.ellipse((cx - r, cy - r * 0.85, cx + r, cy + r * 0.8), fill=fill, outline=line, width=w)
    if eyes_closed:
        for sx in (-1, 1):                                 # smug half-closed eyes
            d.arc((cx + sx * r * 0.42 - r * 0.22, cy - r * 0.2, cx + sx * r * 0.42 + r * 0.22, cy + r * 0.16),
                  200, 340, fill=line, width=w)
        d.arc((cx - r * 0.18, cy + r * 0.12, cx + r * 0.18, cy + r * 0.38), 20, 160, fill=line, width=w)
    if whiskers:
        for sx in (-1, 1):
            for dy in (-0.05, 0.12):
                d.line((cx + sx * r * 0.75, cy + r * dy, cx + sx * r * 1.25, cy + r * (dy - 0.06)), fill=line, width=2)


def decorate(img, orig, name=None):
    """Tie emblem + chest patch from the sheet, placed from the tie (TIES, else found in the original take)."""
    box = TIES[name] if name in TIES else _tie(orig)
    if box is None:
        return img
    x0, y0, x1, y1 = box
    tw, th = x1 - x0, y1 - y0
    S2 = 4
    W, H = img.size
    lay = Image.new("RGBA", (W * S2, H * S2), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    ex, ey = (x0 + x1) / 2, y0 + 0.42 * th                  # black cat on the tie
    _cat_face(d, ex * S2, ey * S2, 0.24 * tw * S2, (20, 18, 30), (20, 18, 30), False, False)
    px, py = x1 + 0.9 * tw, ey                             # light-blue smug cat on the chest
    _cat_face(d, px * S2, py * S2, 0.34 * tw * S2, PATCH, PATCH_D, True, True, w=S2 * 2)
    out = img.convert("RGBA")
    out.alpha_composite(lay.resize((W, H), Image.Resampling.LANCZOS))
    return out.convert("RGB")


@lru_cache(None)
def colour(name):
    """The take in the sheet's colours with the sheet's tie emblem and chest patch (RGB, on white)."""
    orig = Image.open(SRC / f"{name}.png").convert("RGB")
    return decorate(RC.snap_v45(orig), orig, name)


def _drop_shadow(a):
    """Remove a drawn ground shadow / impact splash under her feet (flat pale shapes in the bottom 14 %)."""
    H = a.shape[0]
    low = np.zeros(a.shape[:2], bool)
    low[int(H * 0.86):] = True
    pale = low & (a[..., :3].astype(int).mean(-1) > 120) & (a[..., 2].astype(int) > a[..., 0].astype(int) + 20)
    a[pale, 3] = 0
    return a


def scale(name):
    """Drawing px -> screen px, by head size against the run drawing."""
    import mdrunner as MR
    return MR._scale() * HEAD["z_run_49102"] / HEAD[name]


@lru_cache(None)
def pose(key):
    """(sprite, feet row) for an acting pose at game scale; the anchor (her upper-body centre) is registered."""
    import mdrunner as MR
    name = POSES[key]
    im = MD.cutout(colour(name), crop=False, band_px=1)
    a = _drop_shadow(np.asarray(im).copy())
    im = Image.fromarray(a, "RGBA")
    s = scale(name)
    big = im.resize((round(im.width * s), round(im.height * s)), Image.Resampling.LANCZOS)
    bb = big.getbbox()
    sp = big.crop(bb)
    al = np.asarray(sp.getchannel("A")) > 128
    ys, xs = np.nonzero(al)
    up = ys < ys.min() + 0.55 * (ys.max() - ys.min())
    MR._register(sp, float(xs[up].mean()))
    return sp, float(ys.max() + 1)


@lru_cache(None)
def armed(key):
    """(sprite, feet row): an armed pose at her run proportions, with the one paw mic at its one screen length."""
    import mdrunner as MR
    import mdweapon as WP
    name = ARMED[key]
    WP.armed(name)                                        # first pass: her body height in the drawing
    h = WP.INFO[name]["height"]
    s = scale(name)
    frac = MR.mic_len() / (s * h)
    im = WP.armed(name, frac)
    info = WP.INFO[name]
    big = im.resize((round(im.width * s), round(im.height * s)), Image.Resampling.LANCZOS)
    bb = big.getbbox()
    sp = big.crop(bb)
    MR._register(sp, info["ax"] * s - bb[0])
    return sp, info["feet"] * s - bb[1]
