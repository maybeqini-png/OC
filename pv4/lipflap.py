"""Lip flaps (口パク) on generated close-ups: the body plays at an even pace, the mouth shape follows the sung morae.

Owner review of block 64.4-84.6 s (2026-10-25): the よそ見 shot "stutters frame by frame". Cause, measured: lip-sync by
frame selection (pv4/mouth.sync_path) froze one drawing for up to 13 drawings (1.1 s) to hold an open mouth on a
held note, then jumped 3 source frames per drawing to catch up - the clip opens its mouth once, the vocal has ~10
morae. TV anime does this the other way round: the body is animated on its own and the mouth is a separate layer
swapped per mora (closed / half / open). Here:
- the body plays on 2s at an even pace (at most real time) through the QA-passed source range;
- per drawing, the wanted mouth shape comes from the sung morae (pv4/lyrics_block64.json): vowel a / o -> open,
  i / e / u -> half, っ / ん and gaps -> closed; the separated vocal gates it (no open mouth in a breath);
- if the body frame already shows that shape, its own mouth stays; otherwise its mouth is removed (plane-filled
  skin, pv4/mouthfix) and the shape is taken from the nearest source frame of the same clip that shows it (same
  lighting, nearly the same pose), placed with its upper lip on the body's upper lip, scaled by the face size;
  the half shape is always the nearest open shape closed from the bottom (60 % height), so closed / half / open
  read as one hand-drawn set.
"""
from functools import lru_cache

import cv2
import numpy as np

from mouthfix import disk, paste, plane_fill, removed

A_ROW, I_ROW, U_ROW = set("あかさたなはまやらわがざだばぱゃぁ"), set("いきしちにひみりぎじぢびぴぃ"), set("うくすつぬふむゆるぐずづぶぷゅぅ")
E_ROW, O_ROW = set("えけせてねへめれげぜでべぺぇ"), set("おこそとのほもよろをごぞどぼぽょぉ")
CLOSED, HALF, OPEN = 0, 1, 2


def hira(ch):
    return chr(ord(ch) - 0x60) if "ァ" <= ch <= "ヶ" else ch


def vowel_shape(kana):
    """Mouth shape for a mora: the vowel of its last kana (ちゃ -> a)."""
    ch = hira(kana[-1])
    if ch in "っん":
        return CLOSED
    if ch in A_ROW or ch in O_ROW:
        return OPEN
    if ch in I_ROW or ch in E_ROW or ch in U_ROW:
        return HALF
    return CLOSED


def wanted(t, morae, env_t, lead=1 / 24):
    """Shape at time t: the mora sounding at t (shown one frame early, like hand-timed flaps), gated by the vocal."""
    if env_t < 0.12:
        return CLOSED
    for m in morae:
        if m["t"] - lead <= t < m["end"]:
            return vowel_shape(m["kana"])
    return CLOSED


def even_plan(n_out, a, b):
    """Source frame per output frame: on 2s, even spacing, at most real time (2 source frames per drawing)."""
    n_draw = (n_out + 1) // 2
    span = min(b - a, 2 * (n_draw - 1))
    step = span / max(n_draw - 1, 1)
    d = [a + int(round(k * step)) for k in range(n_draw)]
    return [d[j // 2] for j in range(n_out)]


class LipFlap:
    def __init__(self, mf, openness, rng, thr=(0.3, 0.7)):
        """mf: MouthFix of the clip; openness: per-frame mouth openness (pv4/mouth.mouth_track); rng: QA range."""
        self.mf, (self.a, self.b) = mf, rng
        n = len(mf.frames)
        op = np.asarray(openness, np.float32)
        # shape per frame from the found mouth's height (a closed mouth is a thin line) and the measured openness
        self.cls = np.zeros(n, int)
        for i in range(n):
            m, bb, _ = mf.seg[i]
            if m is None:
                continue
            w, h = bb[2] / mf.boxes[i][2], bb[3] / mf.boxes[i][2]
            # a fragment of a closed smile line can be as tall as a small "o": the measured openness decides too; a
            # mouth found at full width is a (slightly) open grin, never a closed line
            closed = w < 0.1 and (h < 0.03 or op[i] < thr[0])
            self.cls[i] = CLOSED if closed else (HALF if (op[i] < thr[1] or h < 0.06) else OPEN)
        # mouth centre (x) and top (y) relative to the face box, from the segmentation where it found the mouth
        # (open / half: the whole mouth; closed: often a fragment of the line), smoothed over +-6 frames, interpolated
        # elsewhere - the window for the closed line and the place for pasted shapes
        # x only from whole (open / half) mouths: a fragment of a closed line is off-centre
        rel = np.full((n, 2), np.nan, np.float32)
        for i in range(n):
            m, bb, (ox, oy) = mf.seg[i]
            if m is not None:
                bx, by, bw, _ = mf.boxes[i]
                rel[i, 1] = (oy + bb[1] - by) / bw
                if self.cls[i] != CLOSED:
                    rel[i, 0] = (ox + bb[0] + bb[2] / 2 - bx) / bw
        sm = np.full((n, 2), np.nan, np.float32)
        for c, r in ((0, 20), (1, 6)):
            for i in range(n):
                w = rel[max(i - r, 0):i + r + 1, c]
                if not np.isnan(w).all():
                    sm[i, c] = np.nanmedian(w)
            idx, have = np.arange(n), ~np.isnan(sm[:, c])
            sm[~have, c] = np.interp(idx[~have], idx[have], sm[have, c])
        self.rel = sm

    def lip(self, i):
        bx, by, bw, _ = self.mf.boxes[i]
        return (bx + self.rel[i][0] * bw, by + self.rel[i][1] * bw)

    @lru_cache(maxsize=256)
    def layer(self, i):
        """Mouth layer of frame i: the shrunk open / half mouth (MouthFix) or the closed line; None if not found."""
        if self.cls[i] != CLOSED:
            lay = self.mf.layers(i)
        else:
            lay = self.closed_layer(i)
        if lay is None:
            return None
        rows, cols = np.where(lay["alpha"] > 0.5)
        if not len(rows):
            return None
        X0, Y0 = lay["roi"][:2]
        lay = dict(lay)
        lay["lip"] = (X0 + (cols.min() + cols.max()) / 2, Y0 + rows.min())
        return lay

    def closed_layer(self, i):
        """The closed mouth line (thin dark stroke under the nose), found by black-hat in a window at the expected
        position; the segmentation in pv4/mouthfix often finds only a fragment of a thin line."""
        f = self.mf.frames[i]
        bx, by, bw, _ = self.mf.boxes[i]
        cx, cy = self.lip(i)
        cy += 0.012 * bw  # the line's middle, just below the top of the mouth
        rw, rh = 0.14 * bw, max(0.055 * bw, 7.0)
        X0, Y0 = int(max(cx - 1.6 * rw, 0)), int(max(cy - 1.8 * rh, 0))
        X1, Y1 = int(min(cx + 1.6 * rw, f.shape[1])), int(min(cy + 2.2 * rh, f.shape[0]))
        roi = f[Y0:Y1, X0:X1]
        if roi.size == 0:
            return None
        lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB).astype(np.float32)
        L, A = lab[..., 0], lab[..., 1]
        win = np.zeros(L.shape, np.uint8)
        cv2.ellipse(win, (int(cx - X0), int(cy - Y0)), (int(rw), int(rh)), 0, 0, 360, 1, -1)
        L0, A0 = np.median(L[win == 0]), np.median(A[win == 0])
        hat = cv2.morphologyEx(L, cv2.MORPH_BLACKHAT, disk(max(2, int(0.012 * bw))))
        line = ((win > 0) & (hat > 10) & (L < L0 - 12)).astype(np.uint8)
        n, lab_c, st, _ = cv2.connectedComponentsWithStats(line, 8)
        if n < 2:
            return None
        inner = cv2.erode(win, disk(2 if bw > 200 else 1))  # strokes reaching the edge: jaw / hair, not the mouth
        keep = [k for k in range(1, n) if st[k, cv2.CC_STAT_AREA] >= 3 and not ((lab_c == k) & (inner == 0)).any()]
        if not keep:
            return None
        mask = np.isin(lab_c, keep).astype(np.uint8)
        ys, xs = np.where(mask > 0)
        mh, mw = ys.max() - ys.min() + 1, xs.max() - xs.min() + 1
        line_ok = mh <= 0.05 * bw and mw >= 2 * mh  # else not a clean closed line (a small "o", a grin): removed, never a donor
        mask = cv2.dilate(mask, disk(1))
        alpha = np.clip(cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 0.5), 0, 1)
        clean = plane_fill(roi, cv2.dilate(mask, disk(2)), L, A, L0, A0, win == 0)
        ys, xs = np.where(mask > 0)
        return dict(clean=np.clip(clean, 0, 255).astype(np.uint8), roi=(X0, Y0, X1, Y1), mouth=roi.astype(np.float32),
                    alpha=alpha, anchor=(X0 + (xs.min() + xs.max()) / 2, Y0 + ys.min()), face_w=float(bw), line_ok=line_ok)

    def donor(self, b, shape):
        """Nearest source frame in the QA range showing the shape (and a usable layer)."""
        order = sorted(range(self.a, self.b + 1), key=lambda i: abs(i - b))
        for i in order:
            lay = self.layer(i) if self.cls[i] == shape else None
            if lay is not None and lay.get("line_ok", True):
                return i
        return None

    def frame(self, b, shape):
        """Body frame b (BGR) with the mouth shape asked for."""
        if self.cls[b] == shape and shape != HALF:
            return self.mf.frame(b)
        if shape == HALF:  # half = the nearest open shape closed from the bottom, so the three shapes are one set
            d, sy = self.donor(b, OPEN), 0.6
        else:
            d, sy = self.donor(b, shape), 1.0
        if d is None:
            return self.mf.frame(b)
        own = self.layer(b)
        if own is None:
            return self.mf.frame(b)  # its own mouth could not be isolated: keep it rather than draw a second one
        base = removed(self.mf.frames[b], own)
        dl = self.layer(d)
        s = self.mf.boxes[b][2] / self.mf.boxes[d][2]
        # the donor is placed by its upper lip on the body's upper lip
        lip_b = own["lip"]
        ax, ay = dl["anchor"]
        lx, ly = dl["lip"]
        at = (lip_b[0] + s * (ax - lx), lip_b[1] + s * sy * (ay - ly))
        return paste(base, dl, at=at, scale=(s, s * sy))
