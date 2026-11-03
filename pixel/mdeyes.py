"""XIYIN's eyes, one canonical design pasted onto every game drawing.

Owner 2026-11-03: "the eyes are flawed" - the game drawings (V5 takes) have flat, heavy-lidded slit eyes, while the
owner's sheet and the stream-cam portrait of the same PV have big round blue eyes: dark lash line with a flick at the
outer corner, deep blue iris fading to light blue at the bottom, dark pupil, a four-point star sparkle and a small round
highlight. Japanese drawing guides give the standard fix for keeping a character on-model across many drawings: decide
one eye (with its brow) and reuse it - copy the good eye rather than redraw it each time - and keep eye size and height
constant relative to the head. So:
- each drawing gets an eye spec (drawing px): old-eye box to clear to skin, eye centre, height, width (narrower when
  the head turns toward profile), tilt, upper-lid cover (0 = round open eye as on the cam, 0.25 = cheeky smug lid);
- the old eye is cleared to the face's skin colour, the canonical eye is drawn at 4x and downsampled into place, and the
  drawing's own bangs (hair pixels) are put back over it, as on the sheet where strands cross the eyes.
The face always looks right (screen right), so the outer corner with the lash flick is on the left.

usage: python3 mdeyes.py check out.png
"""
import math
import sys
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SKIN = (255, 243, 236)
LASH = (38, 28, 52)
IRIS_TOP, IRIS_MID, IRIS_LOW = (26, 34, 96), (48, 88, 196), (128, 186, 246)
IRIS_LINE = (22, 26, 68)
PUPIL = (18, 22, 64)
SPARK = (255, 250, 222)

# drawing px. clear = ellipse box of the old eye (x0, y0, x1, y1); c = new eye centre; h, w = eye height / width;
# tilt = degrees (positive = outer corner lower); lid = fraction of the eye covered by the upper lid
EYES = {   # clear: one or more ellipse boxes (old eye, its stray lash strokes, the old lid crease that read as a frown)
    "z_run_49102": dict(clear=[(538, 282, 628, 354), (578, 248, 626, 282)], c=(579, 319), h=62, w=44, tilt=-4,
                        lid=0.10),
    "z_punch_49113": dict(clear=[(444, 292, 528, 350), (468, 260, 522, 292)], c=(487, 321), h=56, w=40, tilt=-4,
                          lid=0.22),
    "z_air_49123": dict(clear=[(438, 312, 528, 370)], c=(490, 346), h=66, w=46, tilt=-4, lid=0.12),
    # armed paw-mic poses (v3_*): head about 230 px, eye 0.18 of the head as in the runner; faces tilted with the
    # action, the far eye (smaller, narrower) where the face turns toward the viewer
    "v3_windup_49701": dict(clear=[(398, 383, 472, 434)], c=(436, 410), h=42, w=30, tilt=-6, lid=0.18),
    "v3_smash_49702": dict(clear=[(563, 638, 637, 714)], c=(604, 684), h=42, w=30, tilt=25, lid=0.25),
    "v3_upper_49701": dict(clear=[(383, 373, 454, 422)], c=(424, 400), h=40, w=29, tilt=-4, lid=0.15),
    "v3_upper_49702": dict(clear=[(403, 443, 487, 502)], c=(450, 473), h=44, w=32, tilt=-4, lid=0.12),
    "v3_airslam_49701": dict(clear=[(370, 468, 434, 527), (448, 438, 490, 477)],
                             eyes=[dict(c=(406, 498), h=40, w=29, tilt=-25, lid=0.15),
                                   dict(c=(469, 458), h=32, w=18, tilt=-25, lid=0.15)]),
    "v3_airslam_49702": dict(clear=[(383, 518, 460, 572), (488, 493, 524, 532)],
                             eyes=[dict(c=(427, 545), h=40, w=29, tilt=-20, lid=0.12),
                                   dict(c=(506, 512), h=32, w=18, tilt=-20, lid=0.12)]),
}


def _hair(a):
    r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
    return (b > r + 45) & (b > 110) & (r + g + b < 520)


@lru_cache(None)
def eye_sprite(h, w, lid, k=4):
    """RGBA canonical eye (outer corner left), drawn at k x and downsampled; returns the image (centred)."""
    H, W = int(h * k * 1.5), int(w * k * 1.9)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cx, cy = W / 2, H / 2
    eh, ew = h * k, w * k
    # sclera (white), iris and pupil are clipped to the eye opening
    opening = Image.new("L", (W, H), 0)
    do = ImageDraw.Draw(opening)
    do.ellipse((cx - ew * 0.62, cy - eh * 0.50, cx + ew * 0.55, cy + eh * 0.50), fill=255)
    top_cut = cy - eh * 0.50 + eh * lid
    do.rectangle((0, 0, W, top_cut), fill=0)
    layer = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    d = ImageDraw.Draw(layer)
    d.rectangle((0, 0, W, cy - eh * 0.25), fill=(226, 232, 248, 255))       # lid shadow on the white
    # iris: vertical gradient in an ellipse, shifted toward the nose (right)
    ix0, ix1 = cx - ew * 0.40, cx + ew * 0.46
    iy0, iy1 = cy - eh * 0.48, cy + eh * 0.50
    ga = np.zeros((H, W, 4), np.uint8)
    t = np.clip((np.arange(H) - iy0) / (iy1 - iy0), 0, 1)[:, None]
    c1, c2, c3 = (np.array(c, np.float32) for c in (IRIS_TOP, IRIS_MID, IRIS_LOW))
    col = np.where(t < 0.45, c1 + (c2 - c1) * (t / 0.45), c2 + (c3 - c2) * ((t - 0.45) / 0.55))
    ga[..., :3] = np.repeat(col[:, None, :], W, 1).astype(np.uint8)
    ga[..., 3] = 255
    grad = Image.fromarray(ga, "RGBA")
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).ellipse((ix0, iy0, ix1, iy1), fill=255)
    layer.paste(grad, (0, 0), m)
    d.ellipse((ix0, iy0, ix1, iy1), outline=IRIS_LINE, width=max(2, int(k * 1.6)))
    # pupil, upper-centre
    pw, ph = ew * 0.30, eh * 0.36
    pcx, pcy = (ix0 + ix1) / 2 + ew * 0.02, cy - eh * 0.04
    d.ellipse((pcx - pw / 2, pcy - ph / 2, pcx + pw / 2, pcy + ph / 2), fill=PUPIL)
    # light ring at the bottom of the iris
    d.arc((ix0 + ew * 0.10, iy0 + eh * 0.35, ix1 - ew * 0.10, iy1 - eh * 0.06), 20, 160,
          fill=(170, 214, 255), width=max(2, int(k * 1.4)))
    # sparkle: four-point star upper-left of the pupil, plus a small round highlight lower right
    sx, sy, r = (ix0 + ix1) / 2 - ew * 0.10, cy - eh * 0.16, eh * 0.19
    star = []
    for i in range(8):
        a_ = math.pi / 2 * (i // 2) + (math.pi / 4 if i % 2 else 0) - math.pi / 2
        rr = r if i % 2 == 0 else r * 0.28
        star.append((sx + rr * math.cos(a_), sy + rr * math.sin(a_)))
    d.polygon(star, fill=SPARK)
    q = eh * 0.07
    d.ellipse((ix1 - ew * 0.30 - q, cy + eh * 0.20 - q, ix1 - ew * 0.30 + q, cy + eh * 0.20 + q), fill=(255, 255, 255))
    im.paste(layer, (0, 0), opening)
    # upper lash: thick dark arc along the top of the opening, flick at the outer (left) corner
    dl = ImageDraw.Draw(im)
    lw = eh * 0.13
    pts = []
    for i in range(25):
        u = i / 24
        x = cx - ew * 0.66 + u * ew * 1.24
        e = ((x - (cx - ew * 0.035)) / (ew * 0.585))
        y = max(top_cut, cy - eh * 0.50 * math.sqrt(max(0.0, 1 - e * e)))
        pts.append((x, y))
    # thick at the outer corner, tapering to a thin point at the inner corner
    fine = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        for j in range(6):
            fine.append((x0 + (x1 - x0) * j / 6, y0 + (y1 - y0) * j / 6))
    fine.append(pts[-1])
    for i, (x, y) in enumerate(fine):
        u = i / (len(fine) - 1)
        r = lw / 2 * (1.0 if u < 0.55 else max(0.15, 1 - (u - 0.55) / 0.45 * 0.85))
        dl.ellipse((x - r, y - r, x + r, y + r), fill=LASH)
    fx, fy = pts[0]
    dl.polygon([(fx + lw * 0.3, fy - lw * 0.5), (fx - ew * 0.28, fy - eh * 0.06), (fx + lw * 0.2, fy + lw * 0.6)],
               fill=LASH)
    # lower lash: short thin line at the outer bottom
    dl.arc((cx - ew * 0.60, cy - eh * 0.46, cx + ew * 0.50, cy + eh * 0.52), 105, 150, fill=LASH,
           width=max(2, int(k * 1.5)))
    return im.resize((round(W / k), round(H / k)), Image.Resampling.LANCZOS)


def fix(name, img):
    """RGB drawing with its eye replaced by the canonical one (unchanged if the drawing has no spec)."""
    if name not in EYES:
        return img
    e = EYES[name]
    a = np.asarray(img.convert("RGB")).copy()
    m = Image.new("L", img.size, 0)
    for box in e["clear"]:
        ImageDraw.Draw(m).ellipse(box, fill=255)
    from scipy import ndimage
    inside = np.asarray(m) > 0
    # hair = hair-blue pieces that reach outside the old eye (bangs crossing it); blue pieces wholly inside the old
    # eye are its iris and are cleared
    hb = _hair(a)
    hl, hn = ndimage.label(hb)
    out_ids = np.unique(hl[hb & ~inside])
    hair = np.isin(hl, out_ids[out_ids > 0])
    # the hair's own outline (dark line pixels along the hair) is kept, so clearing never opens the face edge
    outline = (a.astype(int).mean(-1) < 110) & ndimage.binary_dilation(hair, iterations=4)
    clear = (np.asarray(m.filter(ImageFilter.MaxFilter(5))) > 0) & ~hair & ~outline
    a[clear] = SKIN
    out = Image.fromarray(a, "RGB").convert("RGBA")
    for q in e.get("eyes", [e]):
        eye = eye_sprite(q["h"], q["w"], q["lid"]).rotate(-q["tilt"], Image.Resampling.BICUBIC, expand=True)
        out.alpha_composite(eye, (int(round(q["c"][0] - eye.width / 2)), int(round(q["c"][1] - eye.height / 2))))
    o = np.asarray(out).copy()
    o[hair, :3] = np.asarray(img.convert("RGB"))[hair]                 # bangs back over the eye
    return Image.fromarray(o[..., :3], "RGB")


if __name__ == "__main__" and sys.argv[1] == "check":
    import mdrecolor as RC
    tiles = []
    names = sys.argv[3:] or list(EYES)
    for n in names:
        e = EYES[n]
        e = dict(e, c=e.get("c") or e["eyes"][0]["c"])
        src = RC.recolor_pose(n) if n in RC.POSE_SEEDS else RC.recolor(n)
        cx, cy = e["c"]
        r = 2.4 * (e.get("h") or e["eyes"][0]["h"])
        box = (int(cx - r), int(cy - 1.1 * r), int(cx + r), int(cy + 0.9 * r))
        tiles += [src.crop(box).resize((450, 450)), fix(n, src).crop(box).resize((450, 450))]
    S = Image.new("RGB", (450 * len(tiles), 450), "white")
    for i, t in enumerate(tiles):
        S.paste(t, (450 * i, 0))
    S.save(sys.argv[2])


def eye_height(name):
    """Eye height in drawing px: the scale key that keeps her the same size in every frame (same eye = same head)."""
    e = EYES[name]
    return e.get("h") or e["eyes"][0]["h"]
