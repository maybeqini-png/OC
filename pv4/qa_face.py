"""Face / jawline QA for generated clips: tracked face crops of every on-screen drawing + jaw-contour wobble.

usage: qa_face.py <block module> <out_dir>
For each shot of the block, the face box (pv4/h3/faces.json, anime-face cascade on the clip's first frame) is
tracked with phase correlation. In each tracked crop:
- skin mask (light, warm, low-saturation pixels), cleaned;
- jaw profile = lowest skin row per column across the middle 70 % of the face width (the chin/cheek line);
- wobble = change of the jaw profile against the previous on-screen drawing after removing a global shift and a
  linear tilt (so head motion and tilt do not count), in % of the face height. Sudden local warps of the jaw,
  cheeks or chin (the typical generated-video distortion) show up as wobble spikes;
- asym = difference between the left and right halves' change against the shot's first drawing (one side of the
  face deforming while the other does not).
Flags: wobble > 2.0 % or asym > 3.0 %. Sheets: face crops of every on-screen drawing, flagged ones framed red.
"""
import importlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def skin(c, face_thr=150):
    """Skin mask; with face_thr set between the lit face and the neck shadow it keeps the face only, so the
    lower edge is the jaw line (anime necks are drawn in the shadow tone)."""
    lab = cv2.cvtColor(c, cv2.COLOR_BGR2LAB).astype(np.int16)
    l, a, b = lab[..., 0], lab[..., 1] - 128, lab[..., 2] - 128
    m = ((l > face_thr) & (a > 1) & (a < 30) & (b > -2) & (b < 30)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))


def face_threshold(c):
    """Two-cluster split of the skin lightness in the first crop: lit face vs neck shadow."""
    lab = cv2.cvtColor(c, cv2.COLOR_BGR2LAB)
    L = lab[..., 0][skin(c).astype(bool)].astype(np.float32).reshape(-1, 1)
    if len(L) < 50:
        return 150
    _, lab_, cen = cv2.kmeans(L, 2, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5), 3,
                              cv2.KMEANS_PP_CENTERS)
    return int(cen.mean())


def jaw_profile(m):
    """Lowest face-skin row per column, from the largest face blob only (hands and neck are other blobs)."""
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=4)
    if n > 1:
        big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        m = (lab == big).astype(np.uint8)
    h, w = m.shape
    cols = range(int(w * 0.15), int(w * 0.85))
    prof = []
    for x in cols:
        ys = np.where(m[:, x])[0]
        prof.append(ys.max() if len(ys) else np.nan)
    return np.array(prof, np.float32)


def detrend(d):
    x = np.arange(len(d), dtype=np.float32)
    ok = np.isfinite(d)
    if ok.sum() < 5:
        return np.full_like(d, np.nan)
    A = np.stack([x[ok], np.ones(ok.sum())], 1)
    c, *_ = np.linalg.lstsq(A, d[ok], rcond=None)
    return d - (c[0] * x + c[1])


def track(frames, box):
    x, y, w, h = box
    prev = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY).astype(np.float32)
    cx, cy = float(x), float(y)
    pos = [(cx, cy)]
    for f in frames[1:]:
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32)
        win = (slice(max(int(cy - h * 0.3), 0), int(cy + h * 1.3)), slice(max(int(cx - w * 0.3), 0), int(cx + w * 1.3)))
        (dx, dy), _ = cv2.phaseCorrelate(prev[win], g[win])
        cx, cy = cx + dx, cy + dy
        prev = g
        pos.append((cx, cy))
    return pos


def main():
    B = importlib.import_module(sys.argv[1])
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    faces = json.load(open(HERE / "h3/faces.json"))
    report = {}
    for k, shot in enumerate(B.SHOTS):
        name = shot[2]
        box = faces.get(name)
        if not box:
            continue
        fr = B.clip(name)
        pos = track(fr, box)
        used = sorted(set(B.plan(k)))
        x0, y0, w, h = box
        crops, rec = [], []
        prev_prof, first_prof = None, None
        thr = None
        for i in used:
            cx, cy = pos[i]
            ex0, ey0 = int(cx - w * 0.25), int(cy - h * 0.15)
            ex1, ey1 = int(cx + w * 1.25), int(cy + h * 1.25)
            c = fr[i][max(ey0, 0):ey1, max(ex0, 0):ex1]
            c = cv2.resize(c, (300, int(300 * c.shape[0] / max(c.shape[1], 1))), interpolation=cv2.INTER_CUBIC)
            if thr is None:
                thr = face_threshold(c)
            m = skin(c, thr)
            prof = jaw_profile(m)
            hh = c.shape[0]
            wob = asym = 0.0
            if prev_prof is not None:
                d = detrend(prof - prev_prof)
                wob = float(np.nanmean(np.abs(d)) / hh * 100) if np.isfinite(d).any() else 0.0
            if first_prof is not None:
                d0 = detrend(prof - first_prof)
                half = len(d0) // 2
                l, r = np.nanmean(np.abs(d0[:half])), np.nanmean(np.abs(d0[half:]))
                asym = float(abs(l - r) / hh * 100) if np.isfinite(l) and np.isfinite(r) else 0.0
            else:
                first_prof = prof
            prev_prof = prof
            flag = wob > 2.0 or asym > 3.0
            rec.append(dict(frame=int(i), wobble=round(wob, 2), asym=round(asym, 2), flag=bool(flag)))
            vis = c.copy()
            for xi, yv in zip(range(int(300 * 0.15), int(300 * 0.85)), prof):
                if np.isfinite(yv):
                    cv2.circle(vis, (xi, int(yv)), 1, (0, 255, 0), -1)
            if flag:
                cv2.rectangle(vis, (0, 0), (vis.shape[1] - 1, vis.shape[0] - 1), (0, 0, 255), 4)
            cv2.putText(vis, f"f{i} w{wob:.1f} a{asym:.1f}", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 230, 255), 1,
                        cv2.LINE_AA)
            crops.append(vis)
        th = max(c.shape[0] for c in crops)
        crops = [np.pad(c, ((0, th - c.shape[0]), (0, 0), (0, 0))) for c in crops]
        cols = 8
        crops += [np.zeros_like(crops[0])] * (-len(crops) % cols)
        rows = [np.concatenate(crops[j:j + cols], 1) for j in range(0, len(crops), cols)]
        for p in range(0, len(rows), 3):
            cv2.imwrite(str(out / f"face_{name}_{p // 3 + 1:02d}.jpg"), np.concatenate(rows[p:p + 3], 0),
                        [cv2.IMWRITE_JPEG_QUALITY, 90])
        report[name] = dict(drawings=len(used), flagged=[r["frame"] for r in rec if r["flag"]],
                            wobble_max=max(r["wobble"] for r in rec), asym_max=max(r["asym"] for r in rec), frames=rec)
        print(name, "drawings", len(used), "flagged", report[name]["flagged"], "wobble max",
              report[name]["wobble_max"], "asym max", report[name]["asym_max"])
    json.dump(report, open(out / "face_qa.json", "w"), indent=1)


if __name__ == "__main__":
    main()
