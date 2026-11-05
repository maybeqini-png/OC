"""Clean the stream-cam faces' skin (owner 2026-11-05: many frames have cheek problems - grey / blue smudges, airbrush
streaks - "do not alter the original character design").

Only skin is touched; line art, eyes, mouth, brows, hair and outfit stay exactly as drawn:
1. skin mask = warm light pixels in the face box, minus everything within 3 px of line art, hair, eyes or mouth;
2. tint: the smudges are mauve / grey (blue at or above green, where the drawing's skin keeps blue a few levels
   under green); only their blue channel is brought back to the frame's own skin balance;
(No smoothing: it softened the nose dot and the blush, which belong to the design.)
Originals are kept in art/generated/vtuber3/final_orig/ (first run copies them); every run starts from those.

usage: python3 vtclean.py [names...]
"""
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).parent.parent
FINAL = ROOT / "art/generated/vtuber3/final"
ORIG = ROOT / "art/generated/vtuber3/final_orig"
FACE_BOX = (600, 700, 1450, 1330)        # x0, y0, x1, y1 in the 2048 frames (all share the pose)


def clean(im):
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    x0, y0, x1, y1 = FACE_BOX
    A = a[y0:y1, x0:x1]
    r, g, b = A[..., 0], A[..., 1], A[..., 2]
    lum = A.mean(-1)
    skin = (r > 200) & (lum > 185) & (r >= g) & (r >= b)
    other = ~skin
    keep_out = ndimage.binary_dilation(other & (lum < 200), iterations=3)    # lines, hair, eyes, mouth
    sk = skin & ~keep_out
    ref = A[sk & (r - b > 24)]
    if len(ref) < 100:
        return im
    # the drawing's skin and blush always have blue a few levels under green (warm); the smudges are mauve / grey,
    # blue at or above green. Only those pixels change, and only their blue (graded), so shapes, blush and lines stay.
    off = float(np.median((ref[:, 1] - ref[:, 2])))
    excess = (b - (g - off))
    mauve = sk & (excess > 2)
    out = A.copy()
    out[..., 2] = np.where(mauve, b - excess, b)
    out = solid_tips(out)
    a[y0:y1, x0:x1] = out
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


NECK_Y = 1250 - 700                       # box px: below this the skin / hair mix is the neck shadow (drawn)


def solid_tips(A):
    """Hair tips over the cheeks were drawn half-transparent (a faded blue smear over the skin, on both sides). Where
    a pixel is a blend of the nearby hair and skin over a wide area (not a 1-2 px anti-aliased edge), it is redrawn as
    solid hair or clean skin, with a narrow soft edge (about 2 px) like the drawing's other strand edges."""
    lum = A.mean(-1)
    hair_m = (A[..., 2] > A[..., 0] + 40) & (lum < 150)
    skin_m = (A[..., 0] > 235) & (A[..., 0] > A[..., 2] + 12) & (lum > 200)
    def local(m):
        w = m.astype(np.float32)
        num = np.stack([ndimage.gaussian_filter(A[..., c] * w, 12) for c in range(3)], -1)
        return num / np.maximum(ndimage.gaussian_filter(w, 12)[..., None], 1e-3)
    H_, S_ = local(hair_m), local(skin_m)
    d = H_ - S_
    t = ((A - S_) * d).sum(-1) / np.maximum((d * d).sum(-1), 1.0)
    resid = np.linalg.norm(A - (S_ + t[..., None] * d), axis=-1)
    blend = (t > 0.1) & (t < 0.9) & (resid < 30)
    blend[NECK_Y:] = False
    sat = A.max(-1) - A.min(-1)
    eye = ((lum > 236) & (sat < 30)) | ((A[..., 2] > A[..., 0] + 60) & (lum > 135))   # whites and light irises
    lab, n = ndimage.label(eye)
    if n:                                          # only sizeable eye parts (not single bright pixels in hair)
        sizes = ndimage.sum(eye, lab, range(1, n + 1))
        eye = np.isin(lab, [i + 1 for i, z in enumerate(sizes) if z > 300])
    blend &= ~ndimage.binary_dilation(eye, iterations=8)   # never inside the eyes
    wide = ndimage.binary_dilation(ndimage.binary_opening(blend, iterations=2), iterations=3)
    if not wide.any():
        return A
    ts = ndimage.gaussian_filter(t, 1.0)
    al = np.clip((ts - 0.42) / 0.16, 0, 1)[..., None]
    snapped = H_ * al + S_ * (1 - al)
    k = ndimage.gaussian_filter(wide.astype(np.float32), 1.5)[..., None]
    return A * (1 - k) + snapped * k


def main(names):
    ORIG.mkdir(exist_ok=True)
    for p in sorted(FINAL.glob("*.png")):
        if names and p.stem not in names:
            continue
        o = ORIG / p.name
        if not o.exists():
            shutil.copy(p, o)
        clean(Image.open(o)).save(p)
        print(p.name)


if __name__ == "__main__":
    main(sys.argv[1:])
