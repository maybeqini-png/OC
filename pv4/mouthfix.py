"""Mouth proportion fix for generated clips: shrink each generated mouth back to the sheet's mouth size.

Owner review of the fal block (2026-10-25): "the only issue is the mouth being out of proper proportion". Measured
(targets below): the open H3 mouths are 1.2-1.8x as wide as the sheet's smile and about twice the size of hand-drawn
small-girl mouths while talking.

Per source frame (face box from the anime-face cascade, pv4/mouth.face_boxes, cached in .cache/faceboxes_<clip>.npy):
1. segment the mouth inside the lower-middle of the face box (see segment);
2. measure its size relative to the face box against the targets below - larger mouths are scaled down, about the
   top-centre of the mouth (it stays under the nose), never enlarged; the scale is smoothed over time so it cannot pop;
3. the original mouth and its lip shading are filled with a plane fit of the surrounding skin; the mouth's ink line
   is thickened by what the shrink will thin it, and the scaled mouth (with its own anti-aliased mask) is put back.
"""
import cv2
import numpy as np

# Targets, measured with this module's own detector (face-box widths; scratchpad qa/mfix/ref_mouths.py):
# - the sheet's closed smile: 0.103 wide (25 px over a 242 px face box), 0.645 down the box;
# - hand-drawn small-girl references while talking: UTOPIA (天使うと) 0.06-0.08 wide x 0.06-0.08 high,
#   NGNL ED (Shiro) 0.09 x 0.06; only shouts reach 0.15 (Ryuuou OP). Other designs draw wider smiles (the
#   可愛くてごめん girl: 0.20-0.29, docs/research_xiyin_refs.md §2) - width belongs to each design, so the target is
#   this sheet;
# - the H3 clips: median open 0.12-0.14 wide, up to 0.18 x 0.12 - the oversized mouths the owner saw.
# Sizes up to (W0, H0) stay as drawn; above, the excess is compressed (SLOPE), so the mouth still opens and closes
# with the voice but a wide grin ends near the sheet's smile width and a held "o" near the references' size.
W0, H0, SLOPE = 0.07, 0.05, 0.35


def segment(face):
    """face: BGR crop of the face box. Returns (mask uint8, bbox) of the mouth or (None, None).

    The mouth is the largest non-skin hole enclosed by skin in the lower-middle of the face (open interior, teeth,
    tongue, or the closed mouth's line); hair, collar and neck touch the search window's border and are not holes."""
    h, w = face.shape[:2]
    x0, x1, y0, y1 = int(0.22 * w), int(0.78 * w), int(0.48 * h), int(min(h, 0.92 * h))
    reg = face[y0:y1, x0:x1].astype(np.float32)
    if reg.size == 0:
        return None, None
    b, g, r = reg[..., 0], reg[..., 1], reg[..., 2]
    lum = 0.11 * b + 0.59 * g + 0.3 * r
    warm = (r > b + 4) & (lum > 120)
    if warm.sum() < 0.1 * warm.size:
        return None, None
    skin_l = np.median(lum[warm])
    skin = (warm & (lum > skin_l - 38)).astype(np.uint8)
    skin = cv2.morphologyEx(skin, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    non = (1 - skin).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(non, 4)
    rh, rw = non.shape
    best, score = None, 0
    for k in range(1, n):
        x, y, ww, hh, a = st[k]
        if x == 0 or y == 0 or x + ww >= rw or y + hh >= rh or a < 3:
            continue  # touches the window: hair, collar, neck
        off = abs(cen[k][0] - rw / 2) / rw
        if off > 0.2 or ww > 0.6 * rw:
            continue
        dark = skin_l - lum[lab == k].mean()
        s = a * max(dark, 1.0) * (1 - off * 3)
        if s > score:
            best, score = k, s
    if best is None:
        return None, None
    full = np.zeros((h, w), np.uint8)
    full[y0:y1, x0:x1] = (lab == best).astype(np.uint8)
    full = cv2.dilate(full, np.ones((3, 3), np.uint8))  # anti-aliased edge of the line art
    ys, xs = np.where(full > 0)
    return full, (xs.min(), ys.min(), xs.max() - xs.min() + 1, ys.max() - ys.min() + 1)


def scale_for(face_w, bbox):
    _, _, mw, mh = bbox
    w, h = mw / face_w, mh / face_w
    kw = 1.0 if w <= W0 else (W0 + (w - W0) * SLOPE) / w
    kh = 1.0 if h <= H0 else (H0 + (h - H0) * SLOPE) / h
    return float(min(kw, kh))


class MouthFix:
    def __init__(self, frames, boxes):
        """frames: list of BGR source frames; boxes: per-frame face boxes (x, y, w, h)."""
        self.frames, self.boxes = frames, boxes
        self.seg = []
        for f, b in zip(frames, boxes):
            x, y, w, h = [int(round(v)) for v in b]
            face = f[max(y, 0):y + h, max(x, 0):x + w]
            m, bb = segment(face)
            self.seg.append((m, bb, (max(x, 0), max(y, 0))))
        # a found "mouth" away from where this clip's mouth sits in the neighbouring frames (relative to the face box)
        # is something else - e.g. the gap between jaw and hair above the neck (h3_p02b f100, owner review
        # 2026-10-25: "the neck is wrong"): it is dropped, so nothing there is touched
        n = len(frames)
        pos = np.full((n, 2), np.nan, np.float32)
        for i, (m, bb, (ox, oy)) in enumerate(self.seg):
            if m is not None:
                bx, by, bw, _ = boxes[i]
                pos[i] = ((ox + bb[0] + bb[2] / 2 - bx) / bw, (oy + bb[1] - by) / bw)
        self.ok = np.zeros(n, bool)
        for i in range(n):
            if not np.isnan(pos[i, 0]):
                ref = np.nanmedian(pos[max(i - 8, 0):i + 9], 0)
                self.ok[i] = np.abs(pos[i] - ref).max() < 0.05
            if not self.ok[i]:
                self.seg[i] = (None, None, self.seg[i][2])
        raw = np.array([scale_for(boxes[i][2], self.seg[i][1]) if self.seg[i][1] is not None else 1.0 for i in range(n)])
        # temporal smoothing: median over +-2 frames, so a single mis-segmented frame cannot pop
        pad = np.pad(raw, 2, mode="edge")
        self.k = np.array([np.median(pad[i:i + 5]) for i in range(len(raw))])
        self.raw = raw

    def frame(self, i):
        lay = self.layers(i)
        if lay is None or self.k[i] > 0.97:
            return self.frames[i].copy()
        return paste(removed(self.frames[i], lay), lay)

    def layers(self, i, k=None):
        """The mouth of source frame i as layers: the roi with the mouth removed (clean), the mouth scaled by k
        (default: this frame's proportion fix) as colour + alpha in a roi, and its anchor (the scaling centre, just
        below the top of the mouth) in frame pixels. None where no mouth was found (closed lines are often missed)."""
        f = self.frames[i]
        m, bb, (ox, oy) = self.seg[i]
        if m is None:
            return None
        k = self.k[i] if k is None else k
        bx, by, bw, bh = bb
        pad = int(max(bw, bh) * 0.9) + 8
        X0, Y0 = max(ox + bx - pad, 0), max(oy + by - pad, 0)
        X1, Y1 = min(ox + bx + bw + pad, f.shape[1]), min(oy + by + bh + pad, f.shape[0])
        roi = f[Y0:Y1, X0:X1].copy()
        mm = np.zeros(roi.shape[:2], np.uint8)
        sub = m[max(Y0 - oy, 0):Y1 - oy, max(X0 - ox, 0):X1 - ox]
        mm[(oy + max(Y0 - oy, 0)) - Y0:(oy + max(Y0 - oy, 0)) - Y0 + sub.shape[0],
           (ox + max(X0 - ox, 0)) - X0:(ox + max(X0 - ox, 0)) - X0 + sub.shape[1]] = sub
        lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB).astype(np.float32)
        L, A = lab[..., 0], lab[..., 1]
        near = cv2.dilate(mm, disk(int(0.5 * bh) + 3))
        far = cv2.dilate(mm, disk(int(1.1 * bh) + 8))
        out_near = (far > 0) & (near == 0)
        bright = out_near & (L > np.percentile(L[out_near], 35))
        L0, A0 = np.median(L[bright]), np.median(A[bright])
        # 1. remove the mouth with its lip shading (pinker or darker than the skin, next to the mouth), then fill it
        #    with the surrounding skin as a plane fit (inpainting from the border smeared the pink shading back in)
        shade = ((near > 0) & ((A > A0 + 4) | (L < L0 - 10))).astype(np.uint8) | mm
        n, lab_c = cv2.connectedComponents(shade, connectivity=8)
        keep = np.unique(lab_c[mm > 0])
        grown = np.isin(lab_c, keep[keep > 0]).astype(np.uint8)
        grown = cv2.dilate(grown, disk(3))  # the outline of an open mouth is part of it
        clean = plane_fill(roi, grown, L, A, L0, A0, bright)
        # 2. keep the ink weight: thicken the mouth's line art by the amount the shrink will thin it
        src = roi.copy()
        keep_a = mm.copy()
        # ink = very dark, or a thin dark stroke (black-hat) - the faint centre of a thin grin line counts too
        hat = cv2.morphologyEx(L, cv2.MORPH_BLACKHAT, disk(2))
        line = ((mm > 0) & ((L < L0 - 60) | (hat > 18))).astype(np.uint8)
        grow = int(round((1 / k - 1) * 1.6))
        if grow > 0 and line.any():
            thick = cv2.dilate(line, disk(grow))
            er = cv2.erode(roi, disk(grow))
            add = (thick > 0) & (line == 0)
            src[add] = er[add]
            keep_a = np.maximum(keep_a, thick)
        # 3. the mouth, scaled about its top-centre (it stays under the nose)
        ys, xs = np.where(mm > 0)
        ax, ay = (xs.min() + xs.max()) / 2, ys.min() + 0.25 * (ys.max() - ys.min())
        small = cv2.resize(src, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        small_a = cv2.resize(keep_a.astype(np.float32), None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        T = np.float32([[1, 0, ax * (1 - k)], [0, 1, ay * (1 - k)]])
        size = (roi.shape[1], roi.shape[0])
        sm = cv2.warpAffine(small, T, size, flags=cv2.INTER_LINEAR).astype(np.float32)
        sa = cv2.warpAffine(small_a, T, size, flags=cv2.INTER_LINEAR)
        sa = np.clip(cv2.GaussianBlur(sa, (0, 0), 0.5), 0, 1)
        return dict(clean=np.clip(clean, 0, 255).astype(np.uint8), roi=(X0, Y0, X1, Y1), mouth=sm, alpha=sa,
                    anchor=(X0 + ax, Y0 + ay), face_w=float(self.boxes[i][2]))


def disk(r):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def plane_fill(roi, region, L, A, L0, A0, fallback):
    """Fill region (uint8 mask) of a BGR roi with a plane fitted to the skin ring around it, feathered."""
    ring = (cv2.dilate(region, disk(6)) > 0) & (region == 0) & (np.abs(L - L0) < 10) & (np.abs(A - A0) < 5)
    yy, xx = np.mgrid[0:roi.shape[0], 0:roi.shape[1]].astype(np.float32)
    if ring.sum() >= 12:
        P = np.stack([np.ones(ring.sum()), xx[ring], yy[ring]], 1)
        coef, *_ = np.linalg.lstsq(P, roi[ring].astype(np.float32), rcond=None)
        fill = np.stack([np.ones_like(xx), xx, yy], -1) @ coef
    else:
        fill = np.broadcast_to(np.median(roi[fallback], 0), roi.shape).astype(np.float32)
    ga = cv2.GaussianBlur(region.astype(np.float32), (0, 0), 1.0)[..., None]
    return roi.astype(np.float32) * (1 - ga) + fill * ga


def removed(frame, lay):
    """frame (BGR uint8) with the layer's mouth removed (its plane-filled roi put back)."""
    X0, Y0, X1, Y1 = lay["roi"]
    out = frame.copy()
    out[Y0:Y1, X0:X1] = lay["clean"]
    return out


def paste(frame, lay, at=None, scale=(1.0, 1.0)):
    """Put a mouth layer (from MouthFix.layers) onto frame (BGR uint8), its anchor moved to at, scaled (sx, sy)."""
    X0, Y0, X1, Y1 = lay["roi"]
    ax, ay = lay["anchor"]
    tx, ty = (ax, ay) if at is None else at
    sx, sy = scale
    # roi pixel (u, v) -> frame (tx + sx * (X0 + u - ax), ty + sy * (Y0 + v - ay))
    M = np.float32([[sx, 0, tx + sx * (X0 - ax)], [0, sy, ty + sy * (Y0 - ay)]])
    size = (frame.shape[1], frame.shape[0])
    col = cv2.warpAffine(lay["mouth"], M, size, flags=cv2.INTER_LINEAR)
    a = cv2.warpAffine(lay["alpha"], M, size, flags=cv2.INTER_LINEAR)[..., None]
    out = frame.astype(np.float32) * (1 - a) + col * a
    return np.clip(out, 0, 255).astype(np.uint8)


def build_boxes(name, cascade_xml, save=True):
    """Face boxes for a clip in pv4/h3/clips -> pv4/.cache/faceboxes_<name>.npy (needs OpenCV 4: CascadeClassifier).
    The largest face in the first frame where one is found is the start box."""
    from pathlib import Path
    from mouth import face_boxes
    here = Path(__file__).resolve().parent
    cap = cv2.VideoCapture(str(here / f"h3/clips/{name}.mp4"))
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    casc = cv2.CascadeClassifier(cascade_xml)
    for f in frames:  # the first frame where the cascade finds her face
        g = cv2.equalizeHist(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY))
        r = casc.detectMultiScale(g, 1.05, 3, minSize=(60, 60))
        if len(r):
            box0 = max(r, key=lambda b: b[2] * b[3])
            break
    boxes = face_boxes(frames, cascade_xml, box0)
    if save:
        np.save(here / f".cache/faceboxes_{name}.npy", boxes)
    return boxes


if __name__ == "__main__":
    # usage: PYTHONPATH=<opencv4> mouthfix.py <lbpcascade_animeface.xml> <clip name>...
    import sys
    for nm in sys.argv[2:]:
        print(nm, build_boxes(nm, sys.argv[1])[0].round(1))
