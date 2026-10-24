"""Put the sheet's own tail back onto a generated clip whose first frame had the tail removed.

Video models lose or detach a thin tail (measured in pv4/h3: detached tail, side-swapping, vanishing). The
tail is therefore a deterministic layer: the pv2 rig's tail drawing (cut from the owner's sheet), rotated about its
root with a slow sway held on 2s, anchored to her hips by tracking the shorts in the clip, relit like the first
frame, drawn BEHIND her (the per-frame matte restores her pixels in front) and mirrored into the water.

usage (library): TailComp(placement, clip_frames, alpha_frames, scale).frame(i, frame_bgr) -> composited frame
"""
import cv2
import numpy as np

import look as L


class TailComp:
    def __init__(self, place, frames, alphas, scale=0.7, seed=3):
        """place: placements.json entry of the clean first frame (1920x1080 px); scale = clip px / first-frame px."""
        self.s = scale
        body, tail, root = L.figure_parts(int(place["fig_h"] * scale))
        rl = dict(place["relight"])
        rl["rim_px"] = max(2, int(rl.get("rim_px", 4) * scale))
        self.tail = L.relight(tail, **{k: tuple(v) if isinstance(v, list) else v for k, v in rl.items()})
        self.root_local = root
        self.root0 = (place["root"][0] * scale, place["root"][1] * scale)
        self.feet_y = place["feet"] * scale
        self.frames, self.alphas = frames, alphas
        self.track = self._track()
        rng = np.random.default_rng(seed)
        self.phase = rng.uniform(0, 6.28, 2)

    def _track(self):
        """Hip anchor per frame: template of the shorts just above-right of the tail root, matched in a window."""
        x, y = int(self.root0[0]), int(self.root0[1])
        g0 = cv2.cvtColor(self.frames[0], cv2.COLOR_BGR2GRAY)
        k = self.s / 0.7
        tw, th = int(46 * k), int(34 * k)
        tx0, ty0 = x + int(4 * k), y - th - int(6 * k)
        tmpl = g0[ty0:ty0 + th, tx0:tx0 + tw]
        out = [(0.0, 0.0)]
        prev = (0.0, 0.0)
        for f in self.frames[1:]:
            g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
            m = int(30 * k)
            sx0, sy0 = max(tx0 - m + int(prev[0]), 0), max(ty0 - m + int(prev[1]), 0)
            win = g[sy0:sy0 + th + 2 * m, sx0:sx0 + tw + 2 * m]
            r = cv2.matchTemplate(win, tmpl, cv2.TM_CCOEFF_NORMED)
            _, mv, _, ml = cv2.minMaxLoc(r)
            d = (sx0 + ml[0] - tx0, sy0 + ml[1] - ty0) if mv > 0.5 else prev
            prev = (0.7 * prev[0] + 0.3 * d[0], 0.7 * prev[1] + 0.3 * d[1])  # smooth (no jitter)
            out.append(prev)
        return out

    def angle(self, t):
        """Slow, lazy sway (a cat tail at rest), plus a small secondary wave."""
        return 9 * np.sin(2 * np.pi * t / 3.1 + self.phase[0]) + 3 * np.sin(2 * np.pi * t / 1.3 + self.phase[1])

    def frame(self, i, f_bgr, t_draw):
        """t_draw: time of the drawing (already quantised to 2s by the caller)."""
        f = cv2.cvtColor(f_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255
        tl = L.swing_tail(self.tail, self.root_local, self.angle(t_draw))
        dx, dy = self.track[min(i, len(self.track) - 1)]
        ox = int(round(self.root0[0] + dx - self.root_local[0]))
        oy = int(round(self.root0[1] + dy - self.root_local[1]))
        out = f.copy()
        # reflection first (under everything), then the tail, then her pixels back on top through the matte
        refl = tl[::-1].copy()
        ry = int(round(2 * (self.feet_y + dy) - (oy + tl.shape[0])))
        refl = cv2.GaussianBlur(refl, (0, 0), 1.6) * 0.45
        refl[..., :3] *= np.array((0.6, 0.72, 1.0), np.float32)
        L.over(out, refl, ox, ry)
        L.over(out, tl, ox, oy)
        a = self.alphas[min(i, len(self.alphas) - 1)].astype(np.float32) / 255
        a = np.clip((a - 0.2) / 0.6, 0, 1)
        # the tail must not be hidden by her matte where it is in front of the background only: restore only
        # pixels the matte calls "her" (legs, shorts, sweater), which are in front of the tail
        out = out * (1 - a[..., None]) + f * a[..., None]
        return out
