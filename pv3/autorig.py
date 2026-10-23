"""Live2D-lite motion for a single drawing: the drawing is deformed, never slid around as a flat card.

From the face box (pv3/stickers/faces.json) the rig derives a neck pivot and three soft regions:
  head  - everything above the neck: tilts and nods on the beat
  hair  - hair-coloured pixels below the face: follows the head with lag and sways at the tips
  body  - below the neck: breathes (chest rises), settles after the entrance
All motion is one smooth displacement field applied with cv2.remap, so the drawing bends like a puppet.
"""
import json
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

ST = Path(__file__).resolve().parent / "stickers"
FACES = json.load(open(ST / "faces.json")) if (ST / "faces.json").exists() else {}


def smooth(e0, e1, x):
    u = np.clip((x - e0) / (e1 - e0), 0, 1)
    return u * u * (3 - 2 * u)


class Rig:
    def __init__(self, aid, rgba, src_h):
        """rgba: premultiplied float sticker at render size; src_h: height of the sticker file (face box units)."""
        self.rgba = rgba
        h, w = rgba.shape[:2]
        s = h / src_h
        a = rgba[..., 3]
        ys, xs = np.nonzero(a > 0.5)
        top, bot = ys.min(), ys.max()
        box = FACES.get(aid)
        if box is not None and box[2] * box[3] * s * s < 0.004 * w * h:
            box = None  # implausibly small (e.g. a hairclip in a profile view)
        if box is None:
            band = (ys < top + 0.25 * (bot - top))
            cx = xs[band].mean()
            fh = 0.2 * h
            box = [(cx - fh / 2) / s, (top + 0.04 * h) / s, fh / s, fh / s]
        fx, fy, fw, fh = [v * s for v in box]
        self.neck = (fx + fw / 2, fy + fh * 1.12)
        self.face = (fx, fy, fw, fh)
        self.bottom = bot
        gy, gx = np.mgrid[0:h, 0:w].astype(np.float32)
        self.gx, self.gy = gx, gy
        nx, ny = self.neck
        self.w_head = smooth(ny + 0.3 * fh, ny - 0.15 * fh, gy)
        rgb = rgba[..., :3] / np.maximum(rgba[..., 3:], 1e-4)
        R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        hair = ((B > R + 0.16) & (B > 0.4) & (G < 0.62) & (a > 0.5)).astype(np.float32)
        hair *= smooth(fy + 0.85 * fh, fy + 1.2 * fh, gy)  # strands below the face, not the bangs
        hair *= smooth(ny + 3.6 * fh, ny + 3.0 * fh, gy)    # hair ends around the waist: keeps socks/tail out
        hair *= smooth(fx - 1.6 * fw, fx - 1.1 * fw, gx) * smooth(fx + 2.6 * fw, fx + 2.1 * fw, gx)
        self.hair = cv2.GaussianBlur(hair, (0, 0), max(2.0, 0.004 * h))
        self.depth = np.clip((gy - (fy + fh)) / max(bot - (fy + fh), 1), 0, 1)
        self.body = smooth(ny, ny + 0.4 * fh, gy) * np.clip((bot - gy) / max(bot - ny, 1), 0, 1)
        self.h = h

    def render(self, t, energy=1.0, beat=0.441, beat_phase=0.0, tilt=0.0, settle=0.0):
        """t: seconds; beat_phase: time since the last beat (s); tilt: extra head tilt in degrees;
        settle: 0..1 recoil after the entrance (squash then relax)."""
        h = self.h
        nx, ny = self.neck
        gx, gy = self.gx, self.gy
        # head: slow sway + a nod on every beat
        th = np.deg2rad(tilt + energy * (2.2 * np.sin(2 * np.pi * t / (beat * 8)) + 0.8 * np.sin(2 * np.pi * t / (beat * 3))))
        nod = energy * 0.006 * h * np.exp(-beat_phase / 0.12) * (beat_phase >= 0)
        rx, ry = gx - nx, gy - ny
        hdx = (rx * np.cos(th) - ry * np.sin(th) - rx)
        hdy = (rx * np.sin(th) + ry * np.cos(th) - ry) + nod
        # breathing lifts chest and head together
        br = 0.005 * h * (0.5 + 0.5 * np.sin(2 * np.pi * t / 3.2))
        bdy = -br * self.body - br * self.w_head
        # hair follows the head with lag and swings at the tips
        lag = np.deg2rad(tilt + energy * (2.2 * np.sin(2 * np.pi * (t - 0.25) / (beat * 8)) + 0.8 * np.sin(2 * np.pi * (t - 0.2) / (beat * 3))))
        swing = energy * 0.012 * h * np.sin(2 * np.pi * t / 2.3 - 2.5 * self.depth) * self.depth ** 1.4
        hair_dx = (rx * np.cos(lag) - ry * np.sin(lag) - rx) * (1 - 0.5 * self.depth) + swing
        hair_dy = (rx * np.sin(lag) + ry * np.cos(lag) - ry) * (1 - 0.5 * self.depth)
        dx = hdx * self.w_head * (1 - self.hair) + hair_dx * self.hair
        dy = hdy * self.w_head * (1 - self.hair) + hair_dy * self.hair + bdy
        if settle > 0:  # entrance recoil: squash toward the feet, then relax
            k = 0.05 * settle
            dy += (self.bottom - gy) * k
            dx += (gx - nx) * -k * 0.5
        return cv2.remap(self.rgba, (gx - dx).astype(np.float32), (gy - dy).astype(np.float32), cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=0)
