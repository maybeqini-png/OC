"""The OC as the owner's sheet itself, animated without generation and without layer seams.

Why: generated footage keeps an AI look that no post-filter removes (a palette/cel pass made it worse, see
docs/research_pv_language.md §7), and the pv2 layer rig shows seams at the jaw when the head turns (the sheet is
one flat drawing, not a layered PSD). Here every pixel comes from the sheet (4x master), and motion is:
- ONE smooth displacement field (no cut layers -> nothing can open up): head tilt/nod about the neck pivot with
  soft falloff, hair-end follow-through and swing, breathing, ear twitches (pv3/autorig.py idea, sheet geometry
  from pv2/rig/rig.json);
- face changes drawn in rest space with the pv2 rig's eye masks / repainted lids and mouth shapes: blink, ^^ eyes,
  wink, 3-shape lip flap (closed / half / open, as in TV-anime 口パク), "e" mouth for めっ, blush;
- the sheet's tail drawn separately (pv4/look.figure_parts) and swung about its root.
Timing helpers keep drawings on 2s and put accents on beats.
"""
import json
import sys
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "pv2"))
import look as L  # noqa: E402
from rig import Rig as LayerRig  # noqa: E402

CFG = json.load(open(HERE.parent / "pv2/rig/rig.json"))
K = CFG["K"]


def smooth(e0, e1, x):
    u = np.clip((x - e0) / (e1 - e0), 0, 1)
    return u * u * (3 - 2 * u)


@lru_cache(maxsize=1)
def layer_rig():
    return LayerRig(HERE.parent / "pv2/rig")


class Puppet:
    """A view of the sheet: box = (x0, y0, x1, y1) in 1x sheet px, scale = output px per 1x px."""

    def __init__(self, box, scale):
        self.box, self.s = box, scale
        lr = layer_rig()
        self.view = lr.view(scale, box)  # gives eye masks, repainted lids and the face drawing helpers
        # the full sheet figure without tail, premultiplied, in the same crop and scale
        body, tail, root = L.rig_parts_master()
        ox, oy = L.sheet_offset()
        x0, y0, x1, y1 = box

        def crop4(a):
            out = np.zeros((int((y1 - y0) * K), int((x1 - x0) * K), 4), np.float32)
            sx0, sy0 = int(x0 * K - ox), int(y0 * K - oy)
            hh, ww = a.shape[:2]
            ax0, ay0 = max(sx0, 0), max(sy0, 0)
            ax1, ay1 = min(sx0 + out.shape[1], ww), min(sy0 + out.shape[0], hh)
            if ax1 > ax0 and ay1 > ay0:
                out[ay0 - sy0:ay1 - sy0, ax0 - sx0:ax1 - sx0] = a[ay0:ay1, ax0:ax1]
            return cv2.resize(out, (self.view.w, self.view.h), interpolation=cv2.INTER_AREA if scale < K else cv2.INTER_CUBIC)
        self.body = np.clip(crop4(body), 0, 1)
        self.tail = np.clip(crop4(tail), 0, 1)
        self.tail_root = self.p(((root[0] + ox) / K, (root[1] + oy) / K))
        h, w = self.body.shape[:2]
        gy, gx = np.mgrid[0:h, 0:w].astype(np.float32)
        self.gx, self.gy = gx, gy
        X, Y = gx / scale + x0, gy / scale + y0  # 1x sheet coordinates
        nx, ny = CFG["neck_pivot"]
        fcx, fcy = CFG["face_center"]
        self.neck = self.p((nx, ny))
        # soft weights in 1x sheet space
        self.w_head = smooth(ny + 18, ny - 22, Y)  # 1 above the neck, 0 below
        rgb = self.body[..., :3] / np.maximum(self.body[..., 3:], 1e-4)
        R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        hair = ((B > R + 0.16) & (B > 0.4) & (G < 0.62) & (self.body[..., 3] > 0.5)).astype(np.float32)
        hair *= smooth(300, 340, Y) * smooth(1000, 880, Y)
        self.hair = cv2.GaussianBlur(hair, (0, 0), max(2.0, 3 * scale))
        self.depth = np.clip((Y - 300) / 600, 0, 1)
        self.w_body = smooth(ny - 10, ny + 40, Y) * smooth(1010, 700, Y)  # chest/shoulders breathe, legs do not
        r2 = ((X - fcx) ** 2 + (Y - fcy) ** 2) / CFG["head_radius"] ** 2
        self.face_fall = np.clip(1 - r2, 0, 1) ** 2
        self.ears = []
        for key in ("ear_l", "ear_r"):
            ex, ey = CFG[key]["pivot"]
            m = np.exp(-(((X - ex) ** 2 + (Y - ey) ** 2) / 42 ** 2)) * (Y - ey < 12)
            self.ears.append((self.p((ex, ey)), m.astype(np.float32)))
        self.X, self.Y = X, Y

    def p(self, xy):
        return ((xy[0] - self.box[0]) * self.s, (xy[1] - self.box[1]) * self.s)

    def face(self, prm):
        """Draw blink / eyes / mouth / blush on the full figure (the pv2 helpers draw on view.layers['upper'])."""
        v = self.view
        keep = v.layers["upper"]
        v.layers["upper"] = self.body
        try:
            P = dict(eye_l=1.0, eye_r=1.0, eye_smile=0.0, eye_x_mark=0.0, mouth_open=0.0, mouth_form=0.0, blush=0.0,
                     sweat=0.0, tears=0.0)
            P.update(prm)
            out = v._face(P)
        finally:
            v.layers["upper"] = keep
        return out

    def render(self, prm):
        """prm: tilt (deg), nod (1x px), turn (-1..1 face parallax), breath (0..1), hair_lag (deg), swing (0..1 phase
        amplitude), ear_l / ear_r (deg), tail (deg) + face params (eye_l, eye_r, eye_smile, mouth_open, mouth_form,
        blush). Returns premultiplied RGBA."""
        img = self.face(prm)
        s = self.s
        nx, ny = self.neck
        gx, gy = self.gx, self.gy
        th = np.deg2rad(prm.get("tilt", 0.0))
        rx, ry = gx - nx, gy - ny
        hdx = rx * np.cos(th) - ry * np.sin(th) - rx + prm.get("turn", 0.0) * 9 * s * self.face_fall
        hdy = rx * np.sin(th) + ry * np.cos(th) - ry + prm.get("nod", 0.0) * s + prm.get("look_y", 0.0) * 6 * s * self.face_fall
        lag = np.deg2rad(prm.get("hair_lag", prm.get("tilt", 0.0)))
        sw = prm.get("swing", 0.0) * 12 * s * self.depth ** 1.5
        hair_dx = (rx * np.cos(lag) - ry * np.sin(lag) - rx) * (1 - 0.6 * self.depth) + sw
        hair_dy = (rx * np.sin(lag) + ry * np.cos(lag) - ry) * (1 - 0.6 * self.depth)
        br = prm.get("breath", 0.0) * 2.4 * s
        dx = hdx * self.w_head * (1 - self.hair) + hair_dx * self.hair
        dy = hdy * self.w_head * (1 - self.hair) + hair_dy * self.hair - br * (self.w_body + self.w_head)
        for (pivot, m), key in zip(self.ears, ("ear_l", "ear_r")):
            a = np.deg2rad(prm.get(key, 0.0))
            if abs(a) > 1e-4:
                ox, oy = gx - pivot[0], gy - pivot[1]
                dx += (ox * np.cos(a) - oy * np.sin(a) - ox) * m
                dy += (ox * np.sin(a) + oy * np.cos(a) - oy) * m
        out = cv2.remap(img, (gx - dx).astype(np.float32), (gy - dy).astype(np.float32), cv2.INTER_LINEAR,
                        borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        if self.tail[..., 3].max() > 0.01:
            tl = L.swing_tail(self.tail, self.tail_root, prm.get("tail", 0.0))
            tl = cv2.remap(tl, (gx).astype(np.float32), (gy + br * 0).astype(np.float32), cv2.INTER_LINEAR)
            out = out + tl * (1 - out[..., 3:])  # the tail is behind her
        return np.clip(out, 0, 1)


# ---------------- performance helpers ----------------
class Performance:
    """Deterministic acting curves: blinks with natural gaps, idle sway, beat accents, mouth flaps on 2s."""

    def __init__(self, beats, seed=3, t0=0.0, t1=200.0):
        rng = np.random.default_rng(seed)
        self.beats = np.asarray(beats)
        t, bl = t0 + 0.8, []
        while t < t1:
            bl.append(t)
            t += rng.uniform(2.4, 4.6) if rng.random() > 0.15 else 0.32
        self.blinks = np.array(bl)
        self.ph = rng.uniform(0, 6.28, 6)

    def eye(self, t):
        d = t - self.blinks
        d = d[(d >= 0) & (d < 0.22)]
        if not len(d):
            return 1.0
        u = d[0]
        # anime blink: open -> half (1 drawing) -> closed (1-2) -> half -> open, on 2s
        seq = [0.5, 0.0, 0.0, 0.5]
        return seq[min(int(u / (2 / 24)), 3)]

    def beat_phase(self, t):
        i = np.searchsorted(self.beats, t) - 1
        return t - self.beats[i] if i >= 0 else 1.0

    def idle(self, t, energy=1.0):
        ph = self.ph
        bp = self.beat_phase(t)
        nod = energy * 2.2 * np.exp(-bp / 0.11) if bp < 0.4 else 0.0
        tilt = energy * (1.6 * np.sin(2 * np.pi * t / 5.3 + ph[0]) + 0.5 * np.sin(2 * np.pi * t / 2.2 + ph[1]))
        lag = energy * (1.6 * np.sin(2 * np.pi * (t - 0.3) / 5.3 + ph[0]) + 0.5 * np.sin(2 * np.pi * (t - 0.25) / 2.2 + ph[1]))
        return dict(tilt=tilt, hair_lag=lag, nod=nod, breath=0.5 + 0.5 * np.sin(2 * np.pi * t / 3.4 + ph[2]),
                    swing=energy * 0.5 * np.sin(2 * np.pi * t / 2.6 + ph[3]), tail=12 * np.sin(2 * np.pi * t / 2.9 + ph[4]),
                    eye_l=self.eye(t), eye_r=self.eye(t))


def mouth_shape(env_value):
    """3-shape lip flap: closed / half / open (+ the width form for a smile)."""
    if env_value < 0.28:
        return 0.0
    if env_value < 0.6:
        return 0.38
    return 0.75


def on2s(t, fps=24):
    """Quantise a time to the drawing grid of animation on 2s."""
    return np.floor(t * fps / 2) * 2 / fps
