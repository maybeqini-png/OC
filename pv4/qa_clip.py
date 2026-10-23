"""QA for generated video clips: does the OC stay on the reference sheet, and does the picture stay stable?

usage: qa_clip.py <clip.mp4> [<clip.mp4> ...] [--json out.json]

Per clip (analysed at 480x270):
- hair_drift: change of the hair colour (mean Lab of royal-blue pixels) against the first frame, as Delta E 2000-ish
  (CIE76 here; > 6 is visible). The first frame is our on-model frame, so drift = leaving the sheet.
- eye_drift: same for the iris blue (small saturated light-blue blobs in the face area).
- boil: temporal noise that motion cannot explain. Each frame is predicted from the previous one with dense optical
  flow; the residual on low-motion pixels is what flickers or "boils" (line wobble, texture crawl). Median and p95.
- bg_shift: for clips on a plain background, share of background pixels that stop being plain (objects appearing).
- jump: largest single-frame change (sudden morphs or pops).
"""
import json
import sys

import cv2
import numpy as np


def frames(path, size=(480, 270)):
    cap = cv2.VideoCapture(path)
    out = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        out.append(cv2.resize(f, size, interpolation=cv2.INTER_AREA))
    cap.release()
    return out


def lab(f):
    return cv2.cvtColor(f, cv2.COLOR_BGR2LAB).astype(np.float32) * np.array([100 / 255, 1, 1], np.float32) - [0, 128, 128]


def hair_mask(f):
    hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0].astype(int), hsv[..., 1].astype(int), hsv[..., 2].astype(int)
    return (h > 105) & (h < 128) & (s > 120) & (v > 60) & (v < 200)


def eye_mask(f):
    hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0].astype(int), hsv[..., 1].astype(int), hsv[..., 2].astype(int)
    return (h > 95) & (h < 115) & (s > 90) & (v > 170)


def mean_lab(f, m):
    if m.sum() < 30:
        return None
    return lab(f)[m].mean(axis=0)


def qa(path):
    fr = frames(path)
    g = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255 for f in fr]
    h0, e0 = mean_lab(fr[0], hair_mask(fr[0])), mean_lab(fr[0], eye_mask(fr[0]))
    hair, eye, boil, jump = [], [], [], []
    plain0 = (cv2.cvtColor(fr[0], cv2.COLOR_BGR2GRAY) > 245)
    bg = []
    for k in range(1, len(fr)):
        hk, ek = mean_lab(fr[k], hair_mask(fr[k])), mean_lab(fr[k], eye_mask(fr[k]))
        if h0 is not None and hk is not None:
            hair.append(float(np.linalg.norm(hk - h0)))
        if e0 is not None and ek is not None:
            eye.append(float(np.linalg.norm(ek - e0)))
        flow = cv2.calcOpticalFlowFarneback(g[k], g[k - 1], None, 0.5, 3, 15, 3, 5, 1.2, 0)
        hh, ww = g[k].shape
        yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
        pred = cv2.remap(g[k - 1], xx + flow[..., 0], yy + flow[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        mag = np.hypot(flow[..., 0], flow[..., 1])
        low = mag < 0.5
        if low.sum() > 100:
            boil.append(float(np.abs(pred - g[k])[low].mean() * 255))
        jump.append(float(np.abs(g[k] - g[k - 1]).mean() * 255))
        if plain0.mean() > 0.3:
            plain = cv2.cvtColor(fr[k], cv2.COLOR_BGR2GRAY) > 245
            bg.append(float((plain0 & ~plain).sum() / max(plain0.sum(), 1)))
    r = dict(clip=path, frames=len(fr),
             hair_drift_max=round(max(hair), 2) if hair else None, hair_drift_end=round(hair[-1], 2) if hair else None,
             eye_drift_max=round(max(eye), 2) if eye else None,
             boil_median=round(float(np.median(boil)), 3) if boil else None,
             boil_p95=round(float(np.percentile(boil, 95)), 3) if boil else None,
             jump_max=round(max(jump), 2), bg_shift_max=round(max(bg), 3) if bg else None)
    return r


if __name__ == "__main__":
    args = sys.argv[1:]
    out = None
    if "--json" in args:
        out = args[args.index("--json") + 1]
        args = args[:args.index("--json")]
    res = [qa(p) for p in args]
    for r in res:
        print(json.dumps(r, ensure_ascii=False))
    if out:
        json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
