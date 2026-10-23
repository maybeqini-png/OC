"""Find the face box in every sticker with the lbpcascade_animeface detector (OpenCV 4 CascadeClassifier).

usage: PYTHONPATH=<opencv4 dir> detect_faces.py <cascade.xml>    -> pv3/stickers/faces.json {id: [x, y, w, h] | null}
The motion rig uses the box to place the neck pivot and to tell head from hair."""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ST = Path(__file__).resolve().parent / "stickers"
casc = cv2.CascadeClassifier(sys.argv[1])
out = {}
for p in sorted(ST.glob("*.png")):
    im = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
    a = im[..., 3:4].astype(np.float32) / 255
    rgb = (im[..., :3] * a + 255 * (1 - a)).astype(np.uint8)
    g = cv2.equalizeHist(cv2.cvtColor(rgb, cv2.COLOR_BGR2GRAY))
    best = None
    for sf, mn in ((1.05, 3), (1.08, 2), (1.1, 1)):
        f = casc.detectMultiScale(g, scaleFactor=sf, minNeighbors=mn, minSize=(60, 60))
        if len(f):
            best = max(f, key=lambda r: r[2] * r[3])
            break
    out[p.stem] = [int(v) for v in best] if best is not None else None
json.dump(out, open(ST / "faces.json", "w"), indent=1)
print(sum(v is not None for v in out.values()), "/", len(out), "faces found; missing:", [k for k, v in out.items() if v is None])
