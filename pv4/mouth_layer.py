"""Mouth layer for the generated clips: the body plays as generated, the mouth is timed to the sung morae.

Why (measured 2026-10-24 on mouth crop strips of every frame, docs/qa_block64_v42.md):
- H3 has no audio, so each clip opens and closes the mouth on its own clock: h3max_p07e holds one round "O" for 66
  frames (2.75 s) and is shut for its last 30 frames; h3_p04 is closed for 98 of 124 frames; h3max_p05d never opens.
- v4.0 re-ordered whole frames to match the vocal (pv4/mouth.py): the body then speeds up and stalls, and a frozen
  "O" still cannot follow the syllables.
Anime solves this with a separate mouth cel: the face keeps acting, the mouth changes on the sung syllables.

Pipeline
1. track   mouth centre per frame from a hand-marked frame-0 point (pv4/h3/mouth_marks.json): template matching of a
           mouth + chin patch against the previous frame.
2. measure openness = tallest column of mouth-interior pixels / face width, width, occlusion (sleeve or hand over the
           mouth), outline darkness -> shape class closed / half / open / round, normalised per clip; frames where the
           model dissolves between shapes (pale fill, no outline) are flagged and always replaced.
3. target  per drawing (on 2s, one frame ahead of the sound), like an animator's mouth chart: the mora's vowel
           (あ open, お round, え い う half), one step smaller on a consonant onset, lips shut at ま/ば/ぱ-row onsets, on っ
           and on ん before m/b/p or at a phrase end (otherwise ん is a half-open nasal), shut in rests (separated
           vocal below threshold) and after the phrase; one half-open drawing between shut and open.
4. donor   a frame of the same clip (or of a sister clip in the same light, rescaled) with the wanted shape, nearest in
           time (= nearest head pose), not occluded.
5. paste   donor mouth patch on the tracked centre, aligned by a small shift/rotation search on the skin ring,
           colour-matched on that ring, feathered mask covering both mouths. The base mouth is kept when it already
           has the wanted shape, so most drawings are untouched generated pixels.
"""
import json
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
CLIPS = HERE / "h3/clips"
CACHE = HERE / ".cache/mouth"
_M = json.load(open(HERE / "h3/mouth_marks.json"))
MARKS = {k: v for k, v in _M.items() if not k.startswith("_")}
CLOSED_ONLY = set(_M.get("_closed_only", []))

CLOSED, HALF, OPEN, ROUND = 0, 1, 2, 3
MAX_GAP = 60  # donor frames at most 2.5 s from the base frame; the ring check below rejects a pose mismatch
MAX_RING = 140.0  # mean squared ring difference (8-bit) above which a paste is refused
LIPS_SHUT = -1  # a designed closure (m/b/p onset): shown as CLOSED, never smoothed away
NAMES = ("closed", "half", "open", "round")
LIPS = set("まみむめもばびぶべぼぱぴぷぺぽ")
VOWELS = {"a": "あかさたなはまやらわがざだばぱぁゃ", "i": "いきしちにひみりぎじぢびぴぃ", "u": "うくすつぬふむゆるぐずづぶぷぅゅ",
          "e": "えけせてねへめれげぜでべぺぇ", "o": "おこそとのほもよろをごぞどぼぽぉょ"}
SHAPE = {"a": OPEN, "o": ROUND, "e": HALF, "i": HALF, "u": HALF}


def hira(s):
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def vowel(kana):
    k = hira(kana)
    if k in ("っ", "ん"):
        return k
    c = k[-1]
    for v, chars in VOWELS.items():
        if c in chars:
            return v
    return "a"


@lru_cache(maxsize=8)
def frames(name):
    cap = cv2.VideoCapture(str(CLIPS / f"{name}.mp4"))
    out = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        out.append(f)
    cap.release()
    return out


def _window(cx, cy, fw):
    w, h = int(fw * 0.5), int(fw * 0.34)
    return int(cx - w / 2), int(cy - h * 0.45), w, h


def _interior(patch):
    m = patch.astype(np.float32) / 255
    b, g, r = m[..., 0], m[..., 1], m[..., 2]
    lum = 0.11 * b + 0.59 * g + 0.3 * r
    return ((lum < 0.62) & (r > g + 0.05) & (r > b - 0.05)).astype(np.uint8)


def _track(fr, x, y, fw):
    pw, ph, oy = int(fw * 0.9), int(fw * 0.62), int(fw * 0.10)
    g = [cv2.GaussianBlur(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), (0, 0), 1.0) for f in fr]
    cx, cy = float(x), float(y)
    pts = [(cx, cy)]
    for k in range(1, len(fr)):
        px, py = int(cx - pw / 2), int(cy + oy - ph / 2)
        prev = g[k - 1][max(py, 0):py + ph, max(px, 0):px + pw]
        m = int(fw * 0.35)
        sx, sy = max(px - m, 0), max(py - m, 0)
        win = g[k][sy:py + ph + m, sx:px + pw + m]
        if prev.shape[0] >= ph // 2 and win.shape[0] > prev.shape[0] and win.shape[1] > prev.shape[1]:
            r = cv2.matchTemplate(win, prev, cv2.TM_CCOEFF_NORMED)
            _, mv, _, ml = cv2.minMaxLoc(r)
            if mv > 0.4:
                cx += sx + ml[0] + (px - max(px, 0)) - px
                cy += sy + ml[1] + (py - max(py, 0)) - py
        pts.append((cx, cy))
    return np.array(pts, np.float32)


def _measure(f, cx, cy, fw):
    """openness, width, round ratio, occlusion, ink (darkest outline luminance), area of non-skin pixels."""
    x0, y0, w, h = _window(cx, cy, fw)
    p = f[max(y0, 0):y0 + h, max(x0, 0):x0 + w]
    if p.size == 0:
        return 0.0, 0.0, 0.0, 1.0, 1.0, 0.0
    inter = _interior(p)
    lab = cv2.cvtColor(p, cv2.COLOR_BGR2LAB).astype(np.float32)
    border = np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])
    skin = np.median(border, axis=0)
    dist = np.linalg.norm(lab - skin, axis=2)
    # occlusion: pixels far from the skin colour (median of the window border) that are not mouth interior, or the
    # dark navy of a sleeve / hair lock over the mouth
    q = p.astype(np.float32) / 255
    navy = float(((0.11 * q[..., 0] + 0.59 * q[..., 1] + 0.3 * q[..., 2] < 0.45) & (q[..., 0] > q[..., 2] + 0.05)).mean())
    occ = max(float(((dist > 28) & (inter == 0)).mean()) / 0.12, navy / 0.08)  # >= 1 = occluded
    reg = dist > 16
    lum = cv2.GaussianBlur(lab[..., 0], (3, 3), 0) / 255
    ink = float(lum[reg].min()) if reg.any() else 1.0
    area = float(reg.mean())
    n, lab_, st, _ = cv2.connectedComponentsWithStats(inter, 8)
    if n < 2:
        return 0.0, 0.0, 0.0, occ, ink, area
    i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    hgt = float((lab_ == i).sum(axis=0).max())
    return hgt / fw, st[i, cv2.CC_STAT_WIDTH] / fw, hgt / max(st[i, cv2.CC_STAT_WIDTH], 1), occ, ink, area


@lru_cache(maxsize=8)
def track(name):
    """Per frame: centre (x, y), openness, width, round ratio, occlusion, class. Cached in pv4/.cache/mouth/."""
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"{name}.npz"
    if p.exists():
        d = np.load(p)
        return {k: d[k] for k in d.files}
    x, y, fw = MARKS[name]
    fr = frames(name)
    pts = _track(fr, x, y, fw)
    m = np.array([_measure(f, cx, cy, fw) for f, (cx, cy) in zip(fr, pts)], np.float32)
    o = m[:, 0]
    occ = m[:, 3] >= 1.0
    clear = o[~occ] if (~occ).sum() >= 8 else o
    lo, hi = np.percentile(clear, 10), np.percentile(clear, 95)
    if name in CLOSED_ONLY or hi - lo < 0.03:  # the clip never opens its mouth
        on = np.zeros_like(o)
    else:
        on = np.clip((o - lo) / (hi - lo), 0, 1.5)
    cls = np.where(on < 0.25, CLOSED, np.where(on < 0.65, HALF, np.where(m[:, 2] > 0.55, ROUND, OPEN)))
    # dissolve frames: the video model fades between mouth shapes (a pale fill with no outline, e.g. h3max_p07e
    # f106, f160), which no animator draws - never used as donors, always replaced when shown
    weak = (m[:, 5] > 0.05) & (m[:, 4] > 0.47)
    d = dict(pts=pts, open=o, width=m[:, 1], round=m[:, 2], occ=occ.astype(np.uint8), cls=cls.astype(np.int8),
             ink=m[:, 4], area=m[:, 5], weak=weak.astype(np.uint8), fw=np.float32(fw))
    np.savez(p, **d)
    return d


# ---------------- target shapes from the sung morae ----------------
SMALLER = {OPEN: HALF, ROUND: HALF, HALF: CLOSED, CLOSED: CLOSED}
PURE_VOWELS = set("あいうえおぁぃぅぇぉ")


class Timeline:
    def __init__(self, phrases, env, env_t0, fps=24, lead=1, rest=0.12):
        """phrases: [{"t", "end", "morae": [{"kana", "t", "end"}]}] (pv4/lyrics_block64.json phrases);
        env: separated-vocal loudness 0..1 per frame from env_t0."""
        self.ph = phrases
        self.env, self.t0, self.fps, self.lead, self.rest = env, env_t0, fps, lead, rest

    def loud(self, t):
        i = int(round((t - self.t0) * self.fps))
        return float(self.env[min(max(i, 0), len(self.env) - 1)])

    def mora(self, t):
        """(mora dict, its end, next mora dict or None) for time t, or None between phrases."""
        for p in self.ph:
            if p["t"] - 0.08 <= t < p["end"] + 0.04:
                ms = p["morae"]
                for k, m in enumerate(ms):
                    end = ms[k + 1]["t"] if k + 1 < len(ms) else p["end"]
                    if m["t"] - 0.08 <= t < end:
                        return m, end, (ms[k + 1] if k + 1 < len(ms) else None)
        return None

    def raw(self, t):
        """(class, reason) at sound time t."""
        hit = self.mora(t)
        if hit is None:
            return CLOSED, "out"
        m, end, nxt = hit
        nxt_lips = nxt is not None and hira(nxt["kana"])[0] in LIPS
        if nxt_lips and t >= nxt["t"] - 0.09:
            return LIPS_SHUT, "lips"  # lips meet just before the m/b/p of the next mora (catches one drawing on 2s)
        if hira(m["kana"])[0] in LIPS and t < m["t"] + 0.02:
            return LIPS_SHUT, "lips"
        v = vowel(m["kana"])
        if v == "っ":
            return CLOSED, "stop"
        if v == "ん":  # a sung nasal: lips closed only as [m] (before m/b/p) or at the end of the phrase
            return (CLOSED, "stop") if nxt is None or nxt_lips else (HALF, "nasal")
        if t >= m["t"] and self.loud(t) < self.rest:
            return CLOSED, "rest"  # breath or rest inside the phrase
        return SHAPE[v], "vowel"

    def at(self, t_draw):
        """Raw target class for a drawing shown at t_draw, one frame ahead of the sound."""
        c, _ = self.raw(t_draw + self.lead / self.fps)
        return CLOSED if c == LIPS_SHUT else c

    def plan(self, t_draws):
        """Targets for consecutive drawings (on 2s), like an animator's mouth chart:
        - each sung mora that starts with a consonant opens one step smaller on its first drawing (the jaw closes a
          little on the consonant), if the mora lasts at least two drawings so its vowel still shows;
        - a single shut drawing caused only by loudness flicker inside a line is removed;
        - one half-open drawing between shut and open, and before a phrase-final close."""
        dt = 2 / self.fps
        ts = [t + self.lead / self.fps for t in t_draws]
        raw = [self.raw(t) for t in ts]
        c = [r[0] for r in raw]
        n = len(c)
        for k in range(1, n - 1):
            if raw[k][1] == "rest" and c[k - 1] == c[k + 1] and c[k - 1] not in (CLOSED, LIPS_SHUT):
                c[k] = c[k - 1]
        for k in range(n):
            if raw[k][1] != "vowel" or c[k] == LIPS_SHUT:
                continue
            m, end, _ = self.mora(ts[k])
            first = ts[k] - dt < m["t"] <= ts[k] + 1e-6
            consonant = hira(m["kana"])[0] not in PURE_VOWELS and hira(m["kana"])[0] not in LIPS
            if first and consonant and end - m["t"] >= 2 * dt:
                c[k] = SMALLER[c[k]]
        out = [CLOSED if x == LIPS_SHUT else x for x in c]
        for k in range(n):
            if out[k] in (OPEN, ROUND):
                if k > 0 and out[k - 1] == CLOSED:
                    out[k] = HALF
                elif k + 2 < n and out[k + 1] == CLOSED and out[k + 2] == CLOSED:
                    out[k] = HALF
        return out


# ---------------- donors and paste ----------------
class MouthSwap:
    def __init__(self, name, donors=()):
        """donors: other clips (same light) allowed as mouth donors when the base clip lacks a shape."""
        self.name = name
        self.tr = track(name)
        self.fw = float(self.tr["fw"])
        self.pool = [(name, 1.0)] + [(d, self.fw / float(track(d)["fw"])) for d in donors]

    def base_class(self, i):
        return -2 if self.tr["weak"][i] else int(self.tr["cls"][i])

    def _pick(self, i, want):
        best = None
        for clip, sc in self.pool:
            tr = track(clip)
            ok = np.where((tr["cls"] == want) & (tr["occ"] == 0) & (tr["weak"] == 0))[0]
            if not len(ok):
                continue
            if clip == self.name:
                j = ok[np.argmin(np.abs(ok - i))]
                cost = abs(int(j) - i)
                if cost > MAX_GAP:  # too far from the current pose: keep her own mouth rather than paste a stranger
                    continue
            else:
                j, cost = ok[len(ok) // 2], 400
            if best is None or cost < best[0]:
                best = (cost, clip, int(j), sc)
        return best

    def _patch(self, clip, j, sc, size):
        """Donor patch (BGR float) of `size` x `size` base pixels centred on the donor mouth, rescaled."""
        tr = track(clip)
        cx, cy = tr["pts"][j]
        M = np.float32([[sc, 0, size / 2 - sc * cx], [0, sc, size / 2 - sc * cy]])
        return cv2.warpAffine(frames(clip)[j], M, (size, size), flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REFLECT).astype(np.float32)

    def apply(self, frame_bgr, i, want):
        """Return frame i (BGR uint8) with its mouth set to class `want`; unchanged when it already matches, when the
        mouth is occluded, or when no donor exists."""
        if self.tr["occ"][i] or self.base_class(i) == want:
            return frame_bgr, None
        pick = self._pick(i, want)
        if pick is None and want in (OPEN, ROUND):
            alt = ROUND if want == OPEN else OPEN
            if self.base_class(i) == alt:
                return frame_bgr, None
            pick = self._pick(i, alt)
        if pick is None:
            return frame_bgr, None
        _, clip, j, sc = pick
        fw = self.fw
        size = int(fw * 0.64) | 1
        bx, by = self.tr["pts"][i]
        x0, y0 = int(round(bx - size / 2)), int(round(by - size / 2))
        H_, W_ = frame_bgr.shape[:2]
        if x0 < 0 or y0 < 0 or x0 + size > W_ or y0 + size > H_:
            return frame_bgr, None
        base = frame_bgr[y0:y0 + size, x0:x0 + size].astype(np.float32)
        don = self._patch(clip, j, sc, size)
        # mask: everything that is not skin near the centre, in either mouth (lines, interior, tongue, teeth),
        # grown and feathered outward
        grow = max(2, int(round(fw * 0.045)))
        cm = np.zeros((size, size), np.uint8)
        cv2.ellipse(cm, (size // 2, size // 2), (int(size * 0.36), int(size * 0.26)), 0, 0, 360, 1, -1)
        lab_b = cv2.cvtColor(base.astype(np.uint8), cv2.COLOR_BGR2LAB).astype(np.float32)
        skin = np.median(np.concatenate([lab_b[0], lab_b[-1], lab_b[:, 0], lab_b[:, -1]]), axis=0)

        def mouth_px(patch):
            lab = cv2.cvtColor(np.clip(patch, 0, 255).astype(np.uint8), cv2.COLOR_BGR2LAB).astype(np.float32)
            darker = lab[..., 0] < skin[0] - 14
            redder = lab[..., 1] > skin[1] + 9
            teeth = (lab[..., 0] > skin[0] + 6) & (np.abs(lab[..., 1] - 128) < 6) & (lab[..., 2] < skin[2] - 4)
            m = ((darker | redder | teeth) & (cm > 0)).astype(np.uint8)
            n, lab_, st, _ = cv2.connectedComponentsWithStats(m, 8)
            keep = [j for j in range(1, n) if st[j, cv2.CC_STAT_AREA] >= 3]
            return np.isin(lab_, keep).astype(np.uint8)

        def grown(m, g):
            return cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * g + 1, 2 * g + 1)))

        mi = grown(mouth_px(base) | mouth_px(don), grow)
        if mi.sum() == 0:
            return frame_bgr, None
        ring = grown(mi, 2 * grow) - mi
        # align: small shift / rotation search on the skin ring (the chin and cheek lines anchor it)
        rb = ring.astype(bool)
        best = None
        for ang in (-4, -2, 0, 2, 4):
            R = cv2.getRotationMatrix2D((size / 2, size / 2), ang, 1.0)
            d_r = cv2.warpAffine(don, R, (size, size), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    d_s = np.roll(np.roll(d_r, dy, 0), dx, 1)
                    diff = d_s[rb] - base[rb]
                    e = float(np.mean((diff - diff.mean(axis=0)) ** 2))  # shape mismatch after brightness match
                    if best is None or e < best[0]:
                        best = (e, d_s)
        self.last_err = best[0]
        if best[0] > MAX_RING * (1.0 if clip == self.name else 2.0):  # the face around the mouth does not line up
            return frame_bgr, None
        don = best[1]
        mi = grown(mouth_px(base) | mouth_px(don), grow)
        ring = grown(mi, 2 * grow) - mi
        rb = ring.astype(bool)
        gain = np.clip((base[rb].mean(axis=0) + 1) / (don[rb].mean(axis=0) + 1), 0.85, 1.15)
        don = don * gain
        a = np.clip(cv2.GaussianBlur(mi.astype(np.float32), (0, 0), max(0.8, fw * 0.018)) * 2.2, 0, 1)
        a = np.maximum(a, cv2.erode(mi, np.ones((3, 3), np.uint8)).astype(np.float32))[..., None]
        out = frame_bgr.copy()
        out[y0:y0 + size, x0:x0 + size] = np.clip(base * (1 - a) + don * a, 0, 255).astype(np.uint8)
        return out, (clip, j)
