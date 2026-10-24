"""Lip-sync by frame selection: pick, for every output frame, the source frame of a generated clip whose mouth
matches the sung vocal, keeping time monotonic and within a speed range.

usage (library): mouth_track(clip_frames, face_box0) -> openness per source frame
                 sync_path(openness, vocal_env, out_frames, speed=(0.6, 1.6)) -> source index per output frame
- mouth openness: the face is tracked from the first frame's box with phase correlation; inside the lower face
  (the mouth window) dark-red / dark pixels are counted (open mouths show the dark interior and tongue).
- vocal envelope: RMS of the separated vocal, normalised, smoothed; > 0.35 = singing.
- path: dynamic programming over (output frame, source frame) with steps of 0, 1, 2 or 3 source frames per two
  output frames (drawings stay on 2s), cost = |openness - envelope| + speed penalty.
"""
import cv2
import numpy as np


def face_boxes(frames, cascade_xml, box0):
    """Per-frame face box from the anime-face cascade (needs an OpenCV build with CascadeClassifier), nearest to
    the previous box; missed frames keep the previous box; boxes are smoothed over 5 frames."""
    casc = cv2.CascadeClassifier(cascade_xml)
    prev = np.array(box0, np.float32)
    out = []
    for f in frames:
        g = cv2.equalizeHist(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY))
        r = casc.detectMultiScale(g, 1.05, 3, minSize=(int(prev[2] * 0.6), int(prev[2] * 0.6)))
        if len(r):
            c = prev[:2] + prev[2:] / 2
            best = min(r, key=lambda b: np.hypot(*(np.array(b[:2]) + np.array(b[2:]) / 2 - c)))
            if np.hypot(*(np.array(best[:2]) + np.array(best[2:]) / 2 - c)) < prev[2] * 0.6:
                prev = np.array(best, np.float32)
        out.append(prev.copy())
    out = np.array(out)
    k = np.ones(5) / 5
    sm = np.stack([np.convolve(np.pad(out[:, j], 2, mode="edge"), k, mode="valid") for j in range(4)], 1)
    return sm


def mouth_track(frames, box, boxes=None):
    """box = (x, y, w, h) of the face in frame 0 (clip pixels); boxes = per-frame boxes (face_boxes) if known."""
    if boxes is not None:
        out = []
        for f, (x, y, w, h) in zip(frames, boxes):
            mx0, mx1 = int(x + w * 0.30), int(x + w * 0.70)
            my0, my1 = int(y + h * 0.62), int(y + h * 0.95)
            m = f[max(my0, 0):my1, max(mx0, 0):mx1].astype(np.float32)
            b, gg, r = m[..., 0], m[..., 1], m[..., 2]
            lum = 0.11 * b + 0.59 * gg + 0.3 * r
            out.append(float(((lum < 150) & (r > gg + 15)).mean()) if m.size else 0.0)
        o = np.array(out)
        o = (o - np.percentile(o, 5)) / (np.percentile(o, 95) - np.percentile(o, 5) + 1e-6)
        return np.clip(o, 0, 1)
    x, y, w, h = box
    prev = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY).astype(np.float32)
    cx, cy = x, y
    out = []
    for k, f in enumerate(frames):
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32)
        if k:
            win = (slice(max(int(cy - h * 0.3), 0), int(cy + h * 1.3)), slice(max(int(cx - w * 0.3), 0), int(cx + w * 1.3)))
            (dx, dy), _ = cv2.phaseCorrelate(prev[win], g[win])
            cx, cy = cx + dx, cy + dy
        prev = g
        mx0, mx1 = int(cx + w * 0.30), int(cx + w * 0.70)
        my0, my1 = int(cy + h * 0.62), int(cy + h * 0.92)
        m = f[max(my0, 0):my1, max(mx0, 0):mx1].astype(np.float32)
        if m.size == 0:
            out.append(0.0)
            continue
        b, gg, r = m[..., 0], m[..., 1], m[..., 2]
        lum = 0.11 * b + 0.59 * gg + 0.3 * r
        interior = (lum < 110) & (r > gg + 12)  # dark warm pixels: mouth interior / tongue (hair is blue)
        out.append(float(interior.mean()))
    o = np.array(out)
    o = (o - np.percentile(o, 5)) / (np.percentile(o, 95) - np.percentile(o, 5) + 1e-6)
    return np.clip(o, 0, 1)


def sync_path(open_src, env_out, start=0, speed=(0.6, 1.6)):
    """Monotonic source index per output frame (24 fps both), drawings on 2s."""
    n_out, n_src = len(env_out), len(open_src)
    pairs = (n_out + 1) // 2
    steps = [s for s in (0, 1, 2, 3, 4) if speed[0] * 2 - 1e-6 <= s or s == 0]
    INF = 1e9
    cost = np.full((pairs, n_src), INF)
    back = np.zeros((pairs, n_src), int)
    cost[0, start] = abs(open_src[start] - env_out[0])
    for p in range(1, pairs):
        e = env_out[min(2 * p, n_out - 1)]
        for s in range(n_src):
            best, arg = INF, -1
            for st in steps:
                q = s - st
                if q < 0 or cost[p - 1, q] >= INF:
                    continue
                pen = 0.0 if 1 <= st <= 3 else (0.35 if st == 0 else 0.25)  # holds and skips cost a little
                c = cost[p - 1, q] + pen
                if c < best:
                    best, arg = c, q
            if arg >= 0:
                cost[p, s] = best + abs(open_src[s] - e) * 1.5
                back[p, s] = arg
    # end anywhere, but prefer having used the clip at a natural average speed
    tgt = min(n_src - 1, start + int(pairs * 2 * 1.0))
    endc = cost[-1] + 0.02 * np.abs(np.arange(n_src) - tgt)
    s = int(np.argmin(endc))
    path = [s]
    for p in range(pairs - 1, 0, -1):
        s = back[p, s]
        path.append(s)
    path = path[::-1]
    return [path[min(i // 2, pairs - 1)] for i in range(n_out)]


def vocal_env(y, sr, t0, t1, fps=24):
    hop = int(sr / fps)
    seg = y[int(t0 * sr):int(t1 * sr) + hop]
    rms = np.array([np.sqrt(np.mean(seg[i:i + hop] ** 2) + 1e-12) for i in range(0, len(seg) - hop + 1, hop)])
    db = 20 * np.log10(rms + 1e-5)
    e = np.clip((db + 42) / 30, 0, 1)
    e = np.convolve(e, np.ones(3) / 3, mode="same")
    return e[:int(round((t1 - t0) * fps))]
