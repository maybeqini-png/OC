"""Puppet renderer for the OC rig (Live2D-style parameters on the owner's own drawing).

Every frame of the character comes from the same three layers built by rig_build.py, so her design can
not drift. Motion is deformation (head tilt/turn, lean, breathing, hair/ear/ahoge/tail follow-through,
blinks, lip-sync), never a whole-image slide. Expressions are drawn on the face in rest space so they
deform with it: blink squash, ^^ smile eyes, >< eyes, open mouths, blush lines, sweat drop, tears.

Coordinates in rig.json are 1x sheet pixels. A View is the rig resampled to one scale and crop.
"""
import json
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

LASH = np.array([46, 31, 42], np.float32)
MOUTH_LINE = np.array([150, 82, 92], np.float32)
MOUTH_IN = np.array([120, 46, 62], np.float32)
TONGUE = np.array([236, 132, 146], np.float32)
SKIN = np.array([254, 241, 236], np.float32)
BLUSH = np.array([247, 150, 160], np.float32)
SWEAT = np.array([150, 200, 255], np.float32)

DEFAULT = dict(angle_x=0.0, angle_y=0.0, angle_z=0.0, body_x=0.0, breath=0.0, hair_l=0.0, hair_r=0.0,
               ahoge=0.0, ear_l=0.0, ear_r=0.0, tail=0.0, eye_l=1.0, eye_r=1.0, eye_smile=0.0, eye_x=0.0,
               mouth_open=0.0, mouth_form=0.0, blush=0.0, sweat=0.0, tears=0.0, eye_x_mark=0.0)


def smooth(e0, e1, x):
    u = np.clip((x - e0) / (e1 - e0), 0, 1)
    return u * u * (3 - 2 * u)


class Rig:
    def __init__(self, rig_dir):
        d = Path(rig_dir)
        self.cfg = json.load(open(d / "rig.json"))
        self.K = self.cfg["K"]
        # body_fixed.png: the area the head uncovers when it tilts is painted flat neck-shadow skin / hair
        # (the LaMa fill under the jaw left a reddish smear and holes - the "jaw seam")
        files = {"tail": "tail", "body": "body_fixed" if (d / "body_fixed.png").exists() else "body", "upper": "upper",
                 "upper_lid": "upper_lid"}
        self.layers = {n: np.asarray(Image.open(d / f"{f}.png").convert("RGBA")) for n, f in files.items()}
        self.eyes = np.asarray(Image.open(d / "eyes.png").convert("RGB"))

    @lru_cache(maxsize=24)
    def view(self, scale, box):
        """box = (x0, y0, x1, y1) in 1x sheet px; the view is the rig at `scale` times the 1x size."""
        return View(self, scale, box)


class View:
    def __init__(self, rig, scale, box):
        self.rig, self.s, self.box = rig, scale, box
        x0, y0, x1, y1 = box
        K = rig.K
        self.w, self.h = int(round((x1 - x0) * scale)), int(round((y1 - y0) * scale))
        self.layers = {}
        for n, im in rig.layers.items():
            crop = im[int(y0 * K):int(y1 * K), int(x0 * K):int(x1 * K)].astype(np.float32) / 255
            crop[..., :3] *= crop[..., 3:]  # premultiply before resampling
            interp = cv2.INTER_AREA if scale < K else cv2.INTER_CUBIC
            self.layers[n] = np.clip(cv2.resize(crop, (self.w, self.h), interpolation=interp), 0, 1)
        eyes = rig.eyes[int(y0 * K):int(y1 * K), int(x0 * K):int(x1 * K), :2].astype(np.float32) / 255
        self.eyes = cv2.resize(eyes, (self.w, self.h), interpolation=cv2.INTER_AREA)
        up = self.layers["upper"]
        rgb = up[..., :3] / np.maximum(up[..., 3:], 1e-4)
        R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        self.hair = ((B > R + 0.16) & (B > 0.41) & (up[..., 3] > 0.5)).astype(np.float32)
        gy, gx = np.mgrid[0:self.h, 0:self.w].astype(np.float32)
        self.gx, self.gy = gx, gy
        self.X, self.Y = gx / scale + x0, gy / scale + y0  # 1x sheet coordinates of every view pixel

    def p(self, xy):
        """1x sheet point -> view pixel."""
        return ((xy[0] - self.box[0]) * self.s, (xy[1] - self.box[1]) * self.s)

    # ---------- face drawing in rest space ----------
    def _face(self, prm):
        up = self.layers["upper"].copy()
        c = self.rig.cfg
        for idx, side, key in ((0, "l", "eye_l"), (1, "r", "eye_r")):
            openness = float(np.clip(prm[key], 0, 1))
            if prm["eye_smile"] > 0.5 or prm["eye_x_mark"] > 0.5:
                self._eye_symbol(up, idx, side, "smile" if prm["eye_smile"] > 0.5 else "x")
            elif openness < 0.98:
                self._blink(up, idx, openness)
        if prm["mouth_open"] > 0.04 or abs(prm["mouth_form"]) > 0.05:
            self._mouth(up, c["mouth"], prm["mouth_open"], prm["mouth_form"])
        if prm["blush"] > 0.01:
            self._blush(up, prm["blush"])
        if prm["sweat"] > 0.01:
            self._sweat(up, prm["sweat"])
        if prm["tears"] > 0.01:
            self._tears(up, prm["tears"])
        return up

    def _region(self, box1x, pad=2):
        x0, y0 = self.p((box1x[0] - pad, box1x[1] - pad))
        x1, y1 = self.p((box1x[2] + pad, box1x[3] + pad))
        x0, y0 = max(int(x0), 0), max(int(y0), 0)
        return x0, y0, min(int(np.ceil(x1)), self.w), min(int(np.ceil(y1)), self.h)

    def _eye_box(self, idx, pad=3):
        m = self.eyes[..., idx]
        ys, xs = np.nonzero(m > 0.05)
        if not len(ys):
            return None
        p = int(pad * self.s)
        return max(xs.min() - p, 0), max(ys.min() - p, 0), min(xs.max() + p + 1, self.w), min(ys.max() + p + 1, self.h)

    def _blink(self, up, idx, openness):
        """Live2D-style eye close: the eye opening squashes toward its lower lid over the repainted eyelid skin."""
        bb = self._eye_box(idx)
        if bb is None:
            return
        x0, y0, x1, y1 = bb
        m = self.eyes[y0:y1, x0:x1, idx]
        patch = up[y0:y1, x0:x1].copy()
        lid_plate = self.layers["upper_lid"][y0:y1, x0:x1]
        hh, ww = m.shape
        rows = np.arange(hh, dtype=np.float32)[:, None]
        inside = m > 0.5
        lid = np.where(inside.any(0), hh - 1 - np.argmax(inside[::-1], axis=0), hh - 1).astype(np.float32)[None, :]
        f = max(1 - 0.9 * (1 - openness), 0.16)
        my = np.where(rows <= lid, lid - (lid - rows) / f, rows).astype(np.float32)
        mx = np.tile(np.arange(ww, dtype=np.float32), (hh, 1))
        sq = cv2.remap(patch, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        msq = cv2.remap(m, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)[..., None]
        base = lid_plate * m[..., None] + patch * (1 - m[..., None])
        up[y0:y1, x0:x1] = base * (1 - msq) + sq * msq

    def _eye_symbol(self, up, idx, side, kind):
        """^^ (laugh) or >< (flustered) eyes drawn on the repainted eyelid skin."""
        bb = self._eye_box(idx, pad=1)
        if bb is None:
            return
        x0, y0, x1, y1 = bb
        m = self.eyes[y0:y1, x0:x1, idx][..., None]
        up[y0:y1, x0:x1] = self.layers["upper_lid"][y0:y1, x0:x1] * m + up[y0:y1, x0:x1] * (1 - m)
        ss = 4
        cw, ch = (x1 - x0) * ss, (y1 - y0) * ss
        canvas = np.zeros((ch, cw), np.uint8)
        t = max(int(2.6 * self.s * ss), 2)
        if kind == "smile":
            pts = [(cw * (0.12 + 0.76 * u), ch * (0.78 - 0.5 * np.sin(np.pi * u))) for u in np.linspace(0, 1, 24)]
        else:
            a, b = (0.22, 0.78) if side == "l" else (0.78, 0.22)
            pts = [(cw * a, ch * 0.18), (cw * b, ch * 0.5), (cw * a, ch * 0.82)]
        cv2.polylines(canvas, [np.int32(pts)], False, 255, t, cv2.LINE_AA)
        k = cv2.resize(canvas, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA).astype(np.float32)[..., None] / 255
        lash = np.concatenate([LASH / 255, [1.0]]).astype(np.float32)
        up[y0:y1, x0:x1] = up[y0:y1, x0:x1] * (1 - k) + lash * k

    def _mouth(self, up, mouth, opn, form):
        cx, cy = self.p(mouth["center"])
        w = mouth["width"] * (1 + 0.35 * form) * self.s * (1 - 0.25 * max(opn - 0.6, 0))
        h = (2 + 13 * opn) * self.s
        ang = np.deg2rad(-10)
        ss = 4
        R = int(max(w, h) * 1.4) + 4
        n = 2 * R * ss
        inside, tongue, line = (np.zeros((n, n), np.uint8) for _ in range(3))
        top = [(u * w / 2, -0.12 * h + 1.6 * self.s * (1 - u * u) * (0.6 if form >= 0 else -0.6)) for u in np.linspace(-1, 1, 21)]
        bot = [(u * w / 2 * 0.86, top[i][1] + h * np.sqrt(max(1 - u * u, 0))) for i, u in enumerate(np.linspace(-1, 1, 21))]
        shape = top + bot[::-1]

        def tr(pts):
            out = []
            for x, y in pts:
                xr, yr = x * np.cos(ang) - y * np.sin(ang), x * np.sin(ang) + y * np.cos(ang)
                out.append(((xr + R) * ss, (yr + R) * ss))
            return np.int32(out)
        lw = max(int(1.1 * self.s * ss), 2)
        if opn > 0.04:
            cv2.fillPoly(inside, [tr(shape)], 255, cv2.LINE_AA)
            tc = [(u * w / 2 * 0.55, top[10][1] + h * (0.95 - 0.35 * np.sqrt(max(1 - u * u, 0)))) for u in np.linspace(-1, 1, 15)]
            cv2.fillPoly(tongue, [tr(bot[4:17][::-1] + tc)], 255, cv2.LINE_AA)
            tongue = cv2.bitwise_and(tongue, inside)
            cv2.polylines(line, [tr(shape)], True, 255, lw, cv2.LINE_AA)
        else:
            cv2.polylines(line, [tr(top)], False, 255, lw, cv2.LINE_AA)
        canvas = np.dstack([inside, tongue, line])  # ch0 inside, ch1 tongue, ch2 line
        small = cv2.resize(canvas, (2 * R, 2 * R), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        x0, y0 = int(cx) - R, int(cy) - R
        x0c, y0c, x1c, y1c = max(x0, 0), max(y0, 0), min(x0 + 2 * R, self.w), min(y0 + 2 * R, self.h)
        if x1c <= x0c or y1c <= y0c:
            return
        sm = small[y0c - y0:y1c - y0, x0c - x0:x1c - x0]
        reg = up[y0c:y1c, x0c:x1c]
        if form != 0 or opn > 0.04:  # cover the drawn smile line so the new mouth replaces it
            cover = cv2.dilate(sm[..., 0] + sm[..., 2], np.ones((3, 3), np.uint8))
            near = cv2.GaussianBlur((cover > 0.05).astype(np.float32), (0, 0), self.s * 1.2)
            lineish = (reg[..., :3].sum(-1) < 2.4).astype(np.float32) * np.clip(near * 3, 0, 1)
            skin = np.concatenate([SKIN / 255, [1.0]]).astype(np.float32)
            reg[:] = reg * (1 - lineish[..., None]) + skin * lineish[..., None]
        for mask, col in ((sm[..., 0], MOUTH_IN), (sm[..., 1], TONGUE), (sm[..., 2], MOUTH_LINE)):
            m = mask[..., None]
            reg[:] = reg * (1 - m) + np.concatenate([col / 255, [1.0]]).astype(np.float32) * m

    def _blush(self, up, k):
        for cx, cy in ((455, 292), (553, 279)):
            px, py = self.p((cx, cy))
            g = np.exp(-(((self.gx - px) / (14 * self.s)) ** 2 + ((self.gy - py) / (6 * self.s)) ** 2))
            canvas = np.zeros((self.h, self.w), np.float32)
            for i in range(3):
                x = px + (i - 1) * 6 * self.s
                cv2.line(canvas, (int(x + 2.5 * self.s), int(py - 3.5 * self.s)), (int(x - 2.5 * self.s), int(py + 3.5 * self.s)),
                         1.0, max(int(1.3 * self.s), 1), cv2.LINE_AA)
            m = np.clip(0.55 * g + 0.8 * canvas * (g > 0.2), 0, 1)[..., None] * k * up[..., 3:]
            m *= 1 - self.hair[..., None]
            up[:] = up * (1 - m) + np.concatenate([BLUSH / 255, [1.0]]).astype(np.float32) * m * up[..., 3:]

    def _sweat(self, up, k):
        px, py = self.p((588, 250 + 12 * (1 - k)))
        canvas = np.zeros((self.h, self.w), np.uint8)
        r = int(6 * self.s)
        cv2.circle(canvas, (int(px), int(py + r)), r, 255, -1, cv2.LINE_AA)
        cv2.fillPoly(canvas, [np.int32([(px - r * 0.95, py + r * 0.7), (px, py - r * 1.6), (px + r * 0.95, py + r * 0.7)])], 255, cv2.LINE_AA)
        m = (canvas.astype(np.float32) / 255)[..., None] * k
        col = np.concatenate([SWEAT / 255, [1.0]]).astype(np.float32)
        edge = cv2.morphologyEx(canvas, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)).astype(np.float32)[..., None] / 255 * k
        up[:] = up * (1 - m) + col * m
        up[:] = up * (1 - edge) + np.array([0.35, 0.5, 0.8, 1], np.float32) * edge

    def _tears(self, up, k):
        for cx, cy in ((470, 286), (552, 270)):
            px, py = self.p((cx, cy))
            m = np.exp(-(((self.gx - px) / (5 * self.s)) ** 2 + ((self.gy - py) / (2.5 * self.s)) ** 2)) * k
            m = m[..., None] * (1 - self.hair[..., None])
            up[:] = up * (1 - m * 0.8) + np.array([0.85, 0.95, 1, 1], np.float32) * m * 0.8

    # ---------- deformation ----------
    def render(self, prm):
        P = dict(DEFAULT)
        P.update(prm)
        c = self.rig.cfg
        X, Y = self.X, self.Y
        s = self.s
        # body: lean pivots at the hips (legs fixed), breathing lifts chest and shoulders
        w_up = smooth(910, 380, Y)
        bdx = P["body_x"] * 7 * w_up
        bdy = -P["breath"] * 2.6 * smooth(720, 420, Y)
        body_d = (bdx, bdy)
        nx, ny = c["neck_pivot"]
        t_head = (P["body_x"] * 7 * smooth(910, 380, ny), -P["breath"] * 2.6 * smooth(720, 420, ny))
        # head: tilt about the neck, turn/nod by face parallax; hair below the head follows with lag + sway
        th = np.deg2rad(P["angle_z"])
        rx, ry = X - nx, Y - ny
        hdx = rx * np.cos(th) - ry * np.sin(th) - rx
        hdy = rx * np.sin(th) + ry * np.cos(th) - ry
        fcx, fcy = c["face_center"]
        r2 = ((X - fcx) ** 2 + (Y - fcy) ** 2) / c["head_radius"] ** 2
        fall = np.clip(1 - r2, 0, 1) ** 2
        hdx += P["angle_x"] * 9 * fall
        hdy += P["angle_y"] * 6 * fall
        below = np.clip((Y - 300) / 320, 0, 1)
        follow = 1 - 0.6 * below
        side = np.where(X < fcx, P["hair_l"], P["hair_r"])
        sway = side * below ** 1.6 * 14
        udx = hdx * follow + t_head[0] + sway
        udy = hdy * follow + t_head[1] - np.abs(sway) * 0.15 * below
        for key, pk in (("ear_l", "ear_l"), ("ear_r", "ear_r")):
            if abs(P[pk]) > 1e-3:
                ex, ey = c[key]["pivot"]
                a = np.deg2rad(P[pk])
                ox, oy = X - ex, Y - ey
                m = np.exp(-((ox ** 2 + oy ** 2) / 42 ** 2)) * (oy < 12)
                udx += (ox * np.cos(a) - oy * np.sin(a) - ox) * m
                udy += (ox * np.sin(a) + oy * np.cos(a) - oy) * m
        if abs(P["ahoge"]) > 1e-3:
            ax_, ay_ = c["ahoge"]["pivot"]
            a = np.deg2rad(P["ahoge"])
            ox, oy = X - ax_, Y - ay_
            bx0, by0, bx1, by1 = c["ahoge"]["box"]
            m = smooth(0, 70, -oy) * smooth(bx0 - 12, bx0 + 8, X) * smooth(bx1 + 12, bx1 - 8, X)
            udx += (ox * np.cos(a) - oy * np.sin(a) - ox) * m
            udy += (ox * np.sin(a) + oy * np.cos(a) - oy) * m
        # tail swings from its root, bending more toward the tip
        tx, ty = c["tail_root"]
        a = np.deg2rad(P["tail"]) * np.clip(np.hypot(X - tx, Y - ty) / 90, 0, 1)
        ox, oy = X - tx, Y - ty
        tdx = ox * np.cos(a) - oy * np.sin(a) - ox + bdx * 0
        tdy = ox * np.sin(a) + oy * np.cos(a) - oy

        up = self._face(P)
        out = np.zeros((self.h, self.w, 4), np.float32)
        for layer, (dx, dy) in (("tail", (tdx, tdy)), ("body", body_d), ("upper", (udx, udy))):
            src = up if layer == "upper" else self.layers[layer]
            mx = (self.gx - dx * s).astype(np.float32)  # forward displacement -> backward lookup (small, smooth fields)
            my = (self.gy - dy * s).astype(np.float32)
            im = cv2.remap(src, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
            out = im + out * (1 - im[..., 3:])
        return out  # premultiplied RGBA, float32 0..1


class Motion:
    """Idle motion generator: breathing, blinks with random gaps, ear twitches, hair/tail follow-through.

    All randomness comes from a fixed seed so every render of a shot is identical."""

    def __init__(self, seed=7, duration=200.0, fps=30):
        rng = np.random.default_rng(seed)
        t, blinks = 0.6, []
        while t < duration:
            blinks.append(t)
            t += rng.uniform(2.2, 4.8) if rng.random() > 0.15 else 0.35  # occasional double blink
        self.blinks = np.array(blinks)
        t, twitch = 1.0, []
        while t < duration:
            twitch.append((t, rng.choice([-1, 1]), rng.uniform(0.6, 1)))
            t += rng.uniform(1.8, 5.0)
        self.twitch = twitch
        self.phase = rng.uniform(0, 2 * np.pi, 8)

    def eye(self, t):
        d = t - self.blinks
        d = d[(d > -0.01) & (d < 0.3)]
        if not len(d):
            return 1.0
        u = d[0]
        return float(np.clip(abs(u - 0.07) / 0.07, 0, 1) if u < 0.14 else np.clip((u - 0.07) / 0.16, 0, 1))

    def ear(self, t, which):
        v = 0.0
        for t0, sgn, amp in self.twitch:
            u = t - t0
            if 0 <= u < 0.5 and ((sgn > 0) == (which == "l") or amp > 0.85):
                v += amp * np.exp(-u / 0.12) * np.sin(u * 38) * 9
        return v

    def params(self, t, energy=1.0, head_from=None):
        ph = self.phase
        breath = 0.5 + 0.5 * np.sin(2 * np.pi * t / 3.4 + ph[0])
        angle_z = energy * (2.2 * np.sin(2 * np.pi * t / 5.3 + ph[1]) + 0.8 * np.sin(2 * np.pi * t / 2.1 + ph[2]))
        angle_x = energy * 0.35 * np.sin(2 * np.pi * t / 6.1 + ph[3])
        angle_y = energy * 0.25 * np.sin(2 * np.pi * t / 4.3 + ph[4])
        body_x = energy * 0.5 * np.sin(2 * np.pi * t / 5.3 + ph[1] - 0.6)
        # hair lags the head (second-order follow-through)
        lag = 0.32
        hair = -0.55 * (angle_z - energy * (2.2 * np.sin(2 * np.pi * (t - lag) / 5.3 + ph[1])
                                            + 0.8 * np.sin(2 * np.pi * (t - lag) / 2.1 + ph[2]))) \
            + 0.35 * np.sin(2 * np.pi * t / 2.7 + ph[5])
        e = self.eye(t)
        return dict(breath=breath, angle_z=angle_z, angle_x=angle_x, angle_y=angle_y, body_x=body_x,
                    hair_l=hair, hair_r=hair * 0.9, ahoge=-angle_z * 2.2 + 6 * np.sin(2 * np.pi * t / 1.9 + ph[6]),
                    ear_l=self.ear(t, "l"), ear_r=self.ear(t, "r"), tail=14 * np.sin(2 * np.pi * t / 2.6 + ph[7]),
                    eye_l=e, eye_r=e)
