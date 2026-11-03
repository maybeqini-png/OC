"""XIYIN's paw mic, identical in every pose.

N5 cannot keep a weapon's design or length consistent, so it does not draw the weapon: poses are drawn gripping a
plain light blue stick (art/generated/md_style/v3_*), and this module
- finds the stick (light, unsaturated blue, elongated, touching her hands; the pale ground shadow is excluded because
  it touches no skin), and its axis by PCA;
- takes the head end = the stick end farther from her body's centre, the grip = the other end;
- erases the drawn stick and lays the ONE canonical weapon sprite (w_pawmic_49502, cut out) along the axis, handle
  end at the grip, at a fixed length relative to her height;
- puts her fingers (skin pixels near the grip) back on top, so she visibly holds it.

usage: python3 mdweapon.py sheet out.png
"""
import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

import mdsprites as MD

SRC = Path(__file__).parent.parent / "art/generated/md_style"
WEAPON = "w_pawmic_49502"
HEAD_DIR = {"v3_upper_49702": (0, -1)}         # v3_windup_49702 rejected (stick across her face)
LENGTH = 0.46          # weapon length / character height (head of ears to soles)


@lru_cache(None)
def weapon_sprite():
    """Cut-out weapon, vertical (head up); returns (RGBA, handle_bottom_xy, head_top_xy)."""
    im = MD.cutout(Image.open(SRC / f"{WEAPON}.png"))
    a = np.asarray(im.getchannel("A")) > 128
    ys, xs = np.nonzero(a)
    bottom = (float(xs[ys > ys.max() - 6].mean()), float(ys.max()))
    top = (float(xs[ys < ys.min() + 6].mean()), float(ys.min()))
    return im, bottom, top


def skin_mask(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return (r > 205) & (g > 165) & (b > 140) & (r > b + 8) & (r >= g)


def find_stick(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    sat = a.max(-1) - a.min(-1)
    lum = a.mean(-1)
    m = (b > r + 25) & (g > r + 10) & (lum > 150) & (lum < 245) & (sat < 110) & (r > 110)
    m = ndimage.binary_opening(m, iterations=1)
    lab, n = ndimage.label(m)
    skin = ndimage.binary_dilation(skin_mask(a), iterations=12)
    best = None
    for i in range(1, n + 1):
        c = lab == i
        size = int(c.sum())
        if size < 1500 or not (c & skin).any():
            continue
        ys, xs = np.nonzero(c)
        pts = np.stack([xs, ys], 1).astype(np.float32)
        mu = pts.mean(0)
        u, s, vt = np.linalg.svd(pts - mu, full_matrices=False)
        elong = s[0] / max(1e-6, s[1])
        if best is None or elong * size > best[0]:
            proj = (pts - mu) @ vt[0]
            best = (elong * size, c, mu + vt[0] * proj.min(), mu + vt[0] * proj.max())
    if best is None:
        raise ValueError("no stick found")
    # the hands split the stick into pieces: take every stick-coloured pixel near the fitted line, beyond the ends too
    e1, e2 = best[2], best[3]
    d = (e2 - e1) / max(1e-6, np.linalg.norm(e2 - e1))
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]].astype(np.float32)
    rel = np.stack([xx - e1[0], yy - e1[1]], -1)
    t = rel @ d
    dist = np.abs(rel @ np.array([-d[1], d[0]]))
    line = (dist < 24) & (t > -1.2 * np.linalg.norm(e2 - e1)) & (t < 2.2 * np.linalg.norm(e2 - e1))
    full = ndimage.binary_dilation(m, iterations=1) & line            # erase mask (all pieces on the line)
    # ends: the longest piece plus pieces on the line that start within a hand's width of it (not the ground shadow)
    lab2, n2 = ndimage.label(full)
    keep = best[1].copy()
    L = np.linalg.norm(e2 - e1)
    for i in range(1, n2 + 1):
        c = lab2 == i
        if (c & best[1]).any() or c.sum() < 150:
            continue
        ys, xs = np.nonzero(c)
        tt = (np.stack([xs, ys], 1) - e1) @ d
        if (-0.35 * L < tt.max() < 0) or (L < tt.min() < 1.35 * L):
            keep |= c
    ys, xs = np.nonzero(keep)
    tt = (np.stack([xs, ys], 1) - e1) @ d
    return full, e1 + d * tt.min(), e1 + d * tt.max()


def armed(name, length=LENGTH):
    """RGBA drawing (drawing coordinates, cut out) with the canonical weapon in her hands."""
    src = Image.open(SRC / f"{name}.png").convert("RGB")
    a = np.asarray(src).astype(np.int16)
    stick, e1, e2 = find_stick(a)
    body = MD.cutout(src, crop=False)
    ba = np.asarray(body).copy()
    al = ba[..., 3] > 0
    ys, xs = np.nonzero(al & ~stick)
    centre = np.array([xs.mean(), ys.mean()])
    height = ys.max() - ys.min()
    # head = the stick end farther from her body centre, unless the pose says otherwise (HEAD_DIR: a direction the
    # weapon head points to, for poses where the stick crosses her body, e.g. a wind-up behind her back)
    head, grip = (e1, e2) if np.linalg.norm(e1 - centre) > np.linalg.norm(e2 - centre) else (e2, e1)
    if name in HEAD_DIR:
        v = np.array(HEAD_DIR[name], np.float32)
        head, grip = (e1, e2) if (e1 - e2) @ v > 0 else (e2, e1)
    # erase the drawn stick
    st = ndimage.binary_dilation(stick, iterations=3)
    ba[st, 3] = 0
    body = Image.fromarray(ba, "RGBA")
    # canonical weapon along grip -> head
    w, bottom, top = weapon_sprite()
    wl = math.hypot(top[0] - bottom[0], top[1] - bottom[1])
    k = length * height / wl
    wsc = w.resize((max(1, round(w.width * k)), max(1, round(w.height * k))), Image.Resampling.LANCZOS)
    bx, by = bottom[0] * k, bottom[1] * k
    d = head - grip
    ang = math.degrees(math.atan2(d[0], -d[1]))                # 0 = pointing up
    pad = int(max(wsc.size) * 1.2)
    canvas = Image.new("RGBA", (wsc.width + 2 * pad, wsc.height + 2 * pad), (0, 0, 0, 0))
    canvas.paste(wsc, (pad, pad))
    piv = (pad + bx, pad + by)
    rot = canvas.rotate(-ang, Image.Resampling.BICUBIC, center=piv)
    gx, gy = grip - d / np.linalg.norm(d) * 0.04 * height        # handle end a little past her hand
    P = 500                                                       # room for the weapon outside the drawing
    out = Image.new("RGBA", (body.width + 2 * P, body.height + 2 * P), (0, 0, 0, 0))
    out.alpha_composite(body, (P, P))
    out.alpha_composite(rot, (int(round(gx - piv[0])) + P, int(round(gy - piv[1])) + P))
    # fingers back on top (skin near the grip)
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    near = np.hypot(xx - grip[0], yy - grip[1]) < 0.09 * height
    fing = ndimage.binary_dilation(skin_mask(a) & near & al, iterations=2) & al & ~st
    top_layer = np.asarray(body).copy()
    top_layer[~fing, 3] = 0
    out.alpha_composite(Image.fromarray(top_layer, "RGBA"), (P, P))
    return out


if __name__ == "__main__" and sys.argv[1] == "sheet":
    names = sys.argv[3:] or sorted(p.stem for p in SRC.glob("v3_*.png"))
    W, H = 300, 440
    S = Image.new("RGB", (len(names) * W, H), (60, 50, 110))
    for i, n in enumerate(names):
        im = armed(n)
        im = im.crop(im.getbbox())
        s = min((W - 10) / im.width, (H - 10) / im.height)
        im = im.resize((int(im.width * s), int(im.height * s)), Image.Resampling.LANCZOS)
        S.paste(im, (i * W + (W - im.width) // 2, H - 5 - im.height), im)
    S.save(sys.argv[2])
