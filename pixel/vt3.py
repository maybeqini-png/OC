"""VTuber model v3 (2026-11-02): a new bust-up drawn by NovelAI V5, 13 expression frames at 2048 px.

Why: the v2 model was the sheet crop itself (square-on, arms cut, waistband in frame, brows invisible and never
changing); see docs/vtuber_model_review.md.

Pipeline (generation commands and every round's notes in art/generated/vtuber3/prompts.sh):
1. pasteup(): the owner's sheet (Real-ESRGAN x2) re-framed to a mid-chest bust-up, head tilted 7 degrees, one
   sleeve raised to the face. It is only a V5 img2img input; V5 redraws everything.
2. V5 img2img takes; the chosen one (BASE_TAKE) is the body shared by every frame.
3. Expression takes are V5 img2img of that body (eyes / mouth painted over in skin tone, with closed-lid hint
   curves, for the closed-eye frames). compose() pastes only the brow/eye band, the mouth and the cheeks of a take
   onto the body: aligned on a ring, colour-matched separately for skin and the rest, cut along a seam where both
   images agree and merged with a multi-band blend (no ghost strands); blink also gets a skin correction.
4. upscale_all(): Real-ESRGAN x4plus-anime x4, Lanczos to 2048. model3(): cut-out RGBA.

usage:
  python3 pixel/vt3.py pasteup <tilt|sleeve> <out.png> --models DIR
  python3 pixel/vt3.py build                 # 1024 frames -> art/generated/vtuber3/frames1024/
  python3 pixel/vt3.py upscale --models DIR  # 2048 frames -> art/generated/vtuber3/final/
  python3 pixel/vt3.py sheet <out.png>       # contact sheet of the cut-out 2048 frames
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
SHEET = ROOT / "art/reference/oc_reference_sheet.webp"
V3 = ROOT / "art/generated/vtuber3"
BG = (238, 238, 241)
S = 2.0                                   # sheet -> canvas scale
WIN = (250, 10)                           # sheet point that lands on canvas (0, 0)
NECK = (511, 345)                         # sheet pivot for the head tilt (under the chin)
HEAD_CUT = 352                            # sheet rows above this belong to the head / hair on top
BROW = (35, 38, 92)                       # dark hair-outline navy
# brows: short strokes, inner end (towards the nose) first and thickest, about half an eye height above the lash line
# sheet coordinates (1024x1536 sheet)
OLD_BROWS = [((446, 225), (466, 225)), ((519, 222), (544, 208))]      # pale high lines (erased)
NEW_BROWS = [[(472, 250), (463, 248), (455, 248.5), (447, 251)],       # viewer-left eye (lash line y 260)
             [(533, 231), (541, 228.5), (550, 228), (559, 230)]]       # viewer-right eye (lash line y 240)


def sheet_x2(models):
    """Sheet upscaled x2 with Real-ESRGAN (animevideov3), white background made transparent."""
    p = V3 / "sheet_x2.png"
    if not p.exists():
        sys.path.insert(0, str(ROOT / "pixel"))
        from upscale import upscale
        upscale(Image.open(SHEET).convert("RGB"), models).save(p)
    im = Image.open(p).convert("RGBA")
    a = np.asarray(im).copy()
    lab, _ = ndimage.label(a[..., :3].min(-1) >= 244)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    a[np.isin(lab, list(border)), 3] = 0
    return Image.fromarray(a, "RGBA")


def to_canvas(x, y):
    return (x - WIN[0]) * S, (y - WIN[1]) * S


def place(canvas, piece, sheet_xy, angle=0.0, pivot=None):
    """Paste a piece of the x2 sheet (top-left at sheet_xy, sheet units), rotated by angle about pivot."""
    cx, cy = to_canvas(*sheet_xy)
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    layer.alpha_composite(piece, (round(cx), round(cy)))
    if angle:
        layer = layer.rotate(angle, resample=Image.Resampling.BICUBIC, center=to_canvas(*pivot))
    canvas.alpha_composite(layer)


def stroke_mask(size, pts, w0, w1, ss=4):
    """Anti-aliased tapered polyline mask: width w0 at the first point to w1 at the last (supersampled)."""
    m = Image.new("L", (size[0] * ss, size[1] * ss), 0)
    d = ImageDraw.Draw(m)
    n = len(pts) - 1
    for i in range(n):
        for j in range(8):
            f = (i + j / 8) / n
            x = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * j / 8
            y = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * j / 8
            r = (w0 + (w1 - w0) * f) / 2 * ss
            d.ellipse([x * ss - r, y * ss - r, x * ss + r, y * ss + r], fill=255)
    r = w1 / 2 * ss
    d.ellipse([pts[-1][0] * ss - r, pts[-1][1] * ss - r, pts[-1][0] * ss + r, pts[-1][1] * ss + r], fill=255)
    return m.resize(size, Image.Resampling.LANCZOS)


def paint(im, mask, colour):
    a = np.asarray(im).astype(np.float32)
    k = np.asarray(mask).astype(np.float32)[..., None] / 255
    a[..., :3] = a[..., :3] * (1 - k) + np.array(colour, np.float32) * k
    return Image.fromarray(a.clip(0, 255).astype(np.uint8), im.mode)


def fill_in(im, mask, iters=400):
    """Remove the masked pixels by diffusing the surrounding colours into them."""
    a = np.asarray(im).astype(np.float32)
    m = np.asarray(mask) > 127
    ys, xs = np.nonzero(m)
    y0, y1, x0, x1 = max(0, ys.min() - 4), ys.max() + 5, max(0, xs.min() - 4), xs.max() + 5
    c, mm = a[y0:y1, x0:x1, :3].copy(), m[y0:y1, x0:x1]
    c[mm] = c[~mm].mean(0)
    for _ in range(iters):
        avg = (np.roll(c, 1, 0) + np.roll(c, -1, 0) + np.roll(c, 1, 1) + np.roll(c, -1, 1)) / 4
        c[mm] = avg[mm]
    a[y0:y1, x0:x1, :3] = c
    return Image.fromarray(a.clip(0, 255).astype(np.uint8), im.mode)


def pasteup(models, variant="tilt", tilt=7.0, brows=None):
    sh = sheet_x2(models)
    k = int(S)
    canvas = Image.new("RGBA", (1024, 1024), BG + (255,))
    top = HEAD_CUT - 30
    place(canvas, sh.crop((0, top * k, sh.width, sh.height)), (0, top))
    head = sh.crop((0, 0, sh.width, HEAD_CUT * k)).copy()
    for a, b in OLD_BROWS:
        head = fill_in(head, stroke_mask(head.size, [(a[0] * k, a[1] * k), (b[0] * k, b[1] * k)], 9, 9))
    for pts in (brows or NEW_BROWS):
        p = [(x * k, y * k) for x, y in pts]
        head = paint(head, stroke_mask(head.size, p, 6.0, 2.5), BROW)
    m = Image.new("L", head.size, 255)               # soften the cut so the hair joins the body
    ImageDraw.Draw(m).rectangle([0, HEAD_CUT * k - 28, head.width, HEAD_CUT * k], fill=0)
    m = m.filter(ImageFilter.GaussianBlur(10))
    head.putalpha(Image.fromarray(np.minimum(np.asarray(head)[..., 3], np.asarray(m)), "L"))
    place(canvas, head, (0, 0), angle=tilt, pivot=NECK)
    if variant == "sleeve":
        cuff = sh.crop((640 * k, 690 * k, 772 * k, 892 * k)).rotate(165, resample=Image.Resampling.BICUBIC,
                                                                    expand=True)
        place(canvas, cuff, (515, 262))
    return canvas.convert("RGB")


# ---------------------------------------------------------------- base v3 (canvas coordinates, 1024 px)
# brow_points() / brow_guides(): painted short-brow guides (rounds 3, 3b, 6). V5 turned them into hair-clip bars or
# hid them under the bangs, so the final frames do not use them; the brows come from the expression prompts.
BASE_TAKE = V3 / "c_sleeve_0.62_33002.png"
# N5 drew faint brow lines high up, through the bangs (1-1.6 eye heights above the lash line)
HIGH_LINES = [[(363, 403), (401, 395)], [(507, 364), (595, 366)]]
# eyes: (centre of the upper lash line, eye height, axis angle in degrees; the head is tilted, axis rises to the right)
EYES3 = {"L": ((390, 494), 57, -17.5), "R": ((588, 430), 65, -17.5)}


def brow_points(eye, lift=0.45, half=30, tilt=0.0, arch=3.0, inner_dy=0.0, n=5):
    """Points of one brow, inner end first. lift: gap above the lash line in eye heights; tilt: extra rotation of the
    brow in degrees (+ = inner end down, つり眉 / angry; - = inner end up, 困り眉); inner_dy: extra drop of the inner
    end in px (+ = down); arch: bow of the middle in px."""
    (cx, cy), h, ang = EYES3[eye]
    t = math.radians(ang)
    ax, ay = math.cos(t), math.sin(t)                 # along the eye axis, towards viewer-right
    ux, uy = math.sin(t), -math.cos(t)               # up, perpendicular to the axis
    bx, by = cx + ux * lift * h, cy + uy * lift * h
    inward = 1 if eye == "L" else -1                  # the nose side is towards the face centre
    tt = math.radians(tilt) * inward
    pts = []
    for i in range(n):
        s = 1 - 2 * i / (n - 1)                       # +1 inner end ... -1 outer end
        along = s * half
        bow = arch * (1 - s * s)
        drop = math.tan(tt) * along * inward + (inner_dy * (s + 1) / 2)
        x = bx + ax * along * inward - ux * (bow - drop)
        y = by + ay * along * inward - uy * (bow - drop)
        pts.append((x, y))
    return pts


def brow_guides(im, brows, erase=HIGH_LINES, w=(5.5, 2.5), colour=BROW):
    """Erase the high faint lines (skin pixels only) and paint short brow strokes for img2img to redraw."""
    im = im.convert("RGB")
    for line in erase:
        im = fill_in(im, stroke_mask(im.size, line, 9, 9))     # thin lines: diffusing the neighbours is enough
    for pts in brows:
        im = paint(im, stroke_mask(im.size, pts, *w), colour)
    return im


# ---------------------------------------------------------------- expression frames (1024 units on BASE_TAKE)
# one tilted band for both eyes and brows (the brows sit on the bangs, so the band includes the bangs above the eyes),
# the mouth, and the cheeks (blush; skin only). (cx, cy, rx, ry, angle in degrees)
BAND = (488, 474, 182, 92, -17.5)
MOUTH3 = (512, 596, 60, 42, -10)
CHEEKS3 = ((362, 578, 46, 26, -17.5), (604, 536, 42, 24, -17.5))
EYES_ONLY = ((388, 520, 60, 42, -17.5), (590, 460, 62, 46, -17.5))      # erased for closed-eye sources
MOUTH_ONLY = ((512, 592, 34, 18, -10),)


def ell_mask(shape, ells, feather=0.0):
    H, W = shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    m = np.zeros((H, W), np.float32)
    for cx, cy, rx, ry, ang in ells:
        t = math.radians(ang)
        u = (xx - cx) * math.cos(t) + (yy - cy) * math.sin(t)
        v = -(xx - cx) * math.sin(t) + (yy - cy) * math.cos(t)
        m = np.maximum(m, (((u / rx) ** 2 + (v / ry) ** 2) <= 1).astype(np.float32))
    return ndimage.gaussian_filter(m, feather) if feather else m


def erased(regions, src=None):
    """The base with some regions painted over in her skin tone (source for closed-eye / new-mouth takes; a
    diffusion fill pulled hair blue into the face)."""
    im = Image.open(src or BASE_TAKE).convert("RGB")
    a = np.asarray(im)
    skin = a[(skin3(a.astype(np.float32)) > 0.9) & (a.min(-1) > 200)]
    tone = tuple(int(v) for v in np.median(skin, 0))
    m = Image.fromarray((ell_mask((im.height, im.width), regions, 2.5) * 255).astype(np.uint8), "L")
    return paint(im, m, tone)


def skin_fill(im, regions):
    """Regions replaced by a smooth fill from the surrounding skin only (normalised blur at growing scales), so blush
    and shading continue across them; source for closed-eye takes of the neutral frame."""
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    H, W = a.shape[:2]
    reg = ell_mask((H, W), regions) > 0.5
    w = ((skin3(a) > 0.9) & (a.min(-1) > 200) & ~reg).astype(np.float32)
    fill = a.copy()
    todo = reg.copy()
    for s in (4, 8, 16, 32):
        num = ndimage.gaussian_filter(a * w[..., None], (s, s, 0))
        den = ndimage.gaussian_filter(w, s)
        ok = todo & (den > 0.05)
        fill[ok] = num[ok] / den[ok][:, None]
        todo &= ~ok
    soft = ell_mask((H, W), regions, 2.0)[..., None]
    out = a * (1 - soft) + fill * soft
    return Image.fromarray(out.clip(0, 255).astype(np.uint8))


def skin3(a):
    s = (a[..., 0] > 225) & (a[..., 1] > 185) & (a[..., 2] > 165) & (a[..., 0] >= a[..., 2])
    s = ndimage.binary_opening(s, iterations=1)
    return ndimage.gaussian_filter(ndimage.binary_dilation(s, iterations=2).astype(np.float32), 1.5)


def skin_core(a):
    """Skin well clear of any line or strand (eroded, then softened): skin3's dilation reaches across a thin strand."""
    s = (a[..., 0] > 225) & (a[..., 1] > 185) & (a[..., 2] > 165) & (a[..., 0] >= a[..., 2])
    s = ndimage.binary_erosion(ndimage.binary_opening(s, iterations=1), iterations=3)
    return ndimage.gaussian_filter(s.astype(np.float32), 1.5)


def blend(B, R, m, sigmas=(1, 2, 4, 8)):
    """Multi-band blend (Burt-Adelson, as a Gaussian stack): each frequency band is mixed with the mask blurred at
    that band's scale, so line art switches within about a pixel while colour and shading blend over ~10 px. Coarser
    bands leaked the base's dark irises into closed-eye frames."""
    out = np.zeros_like(B)
    gB, gR = B, R
    for s in sigmas:
        nB = ndimage.gaussian_filter(B, (s, s, 0))
        nR = ndimage.gaussian_filter(R, (s, s, 0))
        mk = ndimage.gaussian_filter(m, s / 2)[..., None]
        out += (gB - nB) * (1 - mk) + (gR - nR) * mk
        gB, gR = nB, nR
    mk = ndimage.gaussian_filter(m, sigmas[-1] / 2)[..., None]
    return out + gB * (1 - mk) + gR * mk


def transplant3(base, raw, regions, cheeks=(), search=10, feather=6.0, seam=True, relight=False):
    """Paste regions of raw onto base: align raw on a ring around the regions, match its colours to the base on that
    ring (offsets per skin / non-skin class; V5 takes drift a little in hue), then cut each region along a seam where
    both images agree (seam_mask; a feathered cross-fade left ghost strands). Cheeks (blush) are feathered and only
    change skin."""
    B = np.asarray(base.convert("RGB")).astype(np.float32)
    R = np.asarray(raw.convert("RGB")).astype(np.float32)
    H, W = B.shape[:2]
    allr = list(regions) + list(cheeks)
    inner = ell_mask((H, W), allr) > 0.5
    grow = [(cx, cy, rx * 1.35 + 8, ry * 1.35 + 8, a) for cx, cy, rx, ry, a in allr]
    ring = (ell_mask((H, W), grow) > 0.5) & ~inner
    best, shift = None, (0, 0)
    for dy in range(-search, search + 1, 1):
        for dx in range(-search, search + 1, 1):
            Rs = np.roll(np.roll(R, dy, 0), dx, 1)
            err = float(np.mean((Rs[ring] - B[ring]) ** 2))
            if best is None or err < best:
                best, shift = err, (dx, dy)
    Rs = np.roll(np.roll(R, shift[1], 0), shift[0], 1)
    # colour match on the ring, separately for skin and for everything else (hair, lines, clothes): one linear fit
    # over both pulled the skin grey
    sk_b, sk_r = skin3(B) > 0.5, skin3(Rs)
    for cls_ring, w in ((ring & sk_b, sk_r), (ring & ~sk_b, 1 - sk_r)):
        if cls_ring.sum() < 50:
            continue
        off = (B[cls_ring] - Rs[cls_ring]).mean(0)
        Rs += w[..., None] * off[None, None, :]
    if relight:
        # closed eyes over open ones: V5 leaves a flat pale wash where the eyes were painted over, so the take's skin
        # is pulled towards the base's skin by a normalised blur of (base - take) over skin outside the eyes
        opening = ell_mask((H, W), [(cx, cy, rx * 1.05, ry * 1.1, a) for cx, cy, rx, ry, a in EYES_ONLY]) > 0.5
        w = ((skin3(B) > 0.9) & (skin3(Rs) > 0.9) & ~opening).astype(np.float32)
        corr = np.zeros_like(B)
        todo = np.ones((H, W), bool)
        for s in (12, 24, 48):                       # wider scales fill the middle of the eye region
            num = ndimage.gaussian_filter((B - Rs) * w[..., None], (s, s, 0))
            den = ndimage.gaussian_filter(w, s)
            ok = todo & (den > 0.05)
            corr[ok] = num[ok] / den[ok][:, None]
            todo &= ~ok
        corr = ndimage.gaussian_filter(corr, (4, 4, 0))
        Rs = Rs + corr * skin3(Rs)[..., None]
    m = np.zeros((H, W), np.float32)
    for e in regions:
        m = np.maximum(m, seam_mask(B, Rs, e) if seam else ell_mask((H, W), [e], feather))
    out = blend(B, Rs, m) if seam else B * (1 - m[..., None]) + Rs * m[..., None]
    if cheeks:
        # only where BOTH base and take are clear skin (owner 2026-11-05: weighting by the base's skin alone pasted
        # the take's hair tips at partial weight wherever the two strands did not line up - half-transparent strands
        # fading into the cheeks); the strands of whichever image is showing stay intact, only the blush changes
        mc = (ell_mask((H, W), cheeks, feather) * np.minimum(skin_core(B), skin_core(Rs)))[..., None]
        out = out * (1 - mc) + Rs * mc
    return Image.fromarray(out.clip(0, 255).astype(np.uint8)), shift, best


def seam_mask(B, Rs, ell, lo=0.72, hi=1.12, n_ang=720, n_rad=41, bias=6.0, step=4.0):
    """Hard-edged mask for one ellipse whose edge runs where base and take agree.

    A feathered cross-fade of two different sets of bangs leaves half-transparent ghost strands. Instead, the edge is
    a closed path around the ellipse (radius lo..hi of it, one radial step per angle step at most) with the least
    summed colour difference (dynamic programming over the angle, all start radii, closed by start == end); bias
    adds a small cost for larger radii so ties stay close to the core, step a cost per radial step so the path does
    not zig-zag. The result is anti-aliased over about 1 px (blend() then softens only the low frequencies)."""
    cx, cy, rx, ry, ang = ell
    H, W = B.shape[:2]
    t = math.radians(ang)
    diff = ndimage.gaussian_filter(np.abs(B - Rs).mean(-1), 1.0)
    phi = np.linspace(0, 2 * math.pi, n_ang, endpoint=False)
    sc = np.linspace(lo, hi, n_rad)
    u = sc[None, :] * rx * np.cos(phi)[:, None]
    v = sc[None, :] * ry * np.sin(phi)[:, None]
    xs = np.clip(cx + u * math.cos(t) - v * math.sin(t), 0, W - 1)
    ys = np.clip(cy + u * math.sin(t) + v * math.cos(t), 0, H - 1)
    C = ndimage.map_coordinates(diff, [ys, xs], order=1) + bias * (sc[None, :] - lo) / (hi - lo)
    R = n_rad
    big = 1e18
    D = np.full((R, R), big)                       # D[start, r]
    D[np.arange(R), np.arange(R)] = C[0]
    back = np.zeros((n_ang, R, R), np.int8)
    for i in range(1, n_ang):
        cand = np.stack([np.roll(D, 1, 1) + step, D, np.roll(D, -1, 1) + step])    # from r-1, r, r+1
        cand[0][:, 0] = big
        cand[2][:, -1] = big
        k = cand.argmin(0)
        D = cand.min(0) + C[i][None, :]
        back[i] = (k - 1).astype(np.int8)
    st = int(np.argmin(D[np.arange(R), np.arange(R)]))
    path = np.zeros(n_ang, int)
    r = st
    for i in range(n_ang - 1, -1, -1):
        path[i] = r
        if i:
            r = r + back[i, st, r]          # back = previous radius - this radius
    seam = sc[path]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    uu = (xx - cx) * math.cos(t) + (yy - cy) * math.sin(t)
    vv = -(xx - cx) * math.sin(t) + (yy - cy) * math.cos(t)
    rho = np.sqrt((uu / rx) ** 2 + (vv / ry) ** 2)
    a = np.mod(np.arctan2(vv / ry, uu / rx), 2 * math.pi) / (2 * math.pi) * n_ang
    i0 = np.floor(a).astype(int) % n_ang
    f = a - np.floor(a)
    s_at = seam[i0] * (1 - f) + seam[(i0 + 1) % n_ang] * f
    rad_px = np.sqrt((uu / rx) ** 2 * rx ** 2 + (vv / ry) ** 2 * ry ** 2) / np.maximum(rho, 1e-6)
    return np.clip((s_at - rho) * rad_px + 0.5, 0, 1).astype(np.float32)


LASH = (48, 36, 52)
EYE_W = {"L": 50, "R": 52}                  # half widths of the eyes along their axis
EYE_C = {"L": (388, 522), "R": (590, 461)}  # eye centres on the base


def closed_eye_guides(im, kind="calm", eyes=("L", "R")):
    """Closed-lid curves as hints for V5: calm = gently convex down (‿), happy = convex up (^)."""
    sag = {"calm": 7.0, "happy": -12.0, "tight": -6.0}[kind]
    for e in eyes:
        cx, cy = EYE_C[e]
        t = math.radians(-17.5)
        ax, ay, ux, uy = math.cos(t), math.sin(t), math.sin(t), -math.cos(t)
        pts = []
        for i in range(9):
            s = -1 + 2 * i / 8
            along = s * EYE_W[e] * 0.9
            off = -sag * (1 - s * s)                       # + = up
            pts.append((cx + ax * along + ux * off, cy + 6 + ay * along + uy * off))
        if e == "L":
            pts = pts[::-1]                                # thick end at the outer corner
        im = paint(im, stroke_mask(im.size, pts[::-1], 6.0, 3.0), LASH)
    return im


# ---------------------------------------------------------------- frame recipes
def take(name):
    p = V3 / f"{name}.png"
    return Image.open(p).convert("RGB")


def compose(layers):
    """layers: [(take name, regions, cheeks[, transplant3 options])] applied in order onto the base body."""
    im = Image.open(BASE_TAKE).convert("RGB")
    log = []
    for name, regions, cheeks, *opt in layers:
        opt = dict(opt[0]) if opt else {}
        closed = opt.pop("closed", None)
        im, shift, err = transplant3(im, take(name), regions, cheeks, **opt)
        if closed:
            im = clean_closed(im, [EYES_ONLY[i] for i in closed], [i for i in (0, 1) if i not in closed])
        log.append((name, shift, round(err, 1)))
    return im, log


def _skin_field(B, holes):
    """The base's skin colour everywhere, spread smoothly in from its skin outside `holes` (normalised blur)."""
    raw = (B[..., 0] > 225) & (B[..., 1] > 185) & (B[..., 2] > 165) & (B[..., 0] >= B[..., 2])
    w = (ndimage.binary_erosion(raw, iterations=2) & ~holes).astype(np.float32)
    out = np.zeros_like(B)
    todo = np.ones(w.shape, bool)
    for s in (6, 12, 24, 48, 96):
        num = ndimage.gaussian_filter(B * w[..., None], (s, s, 0))
        den = ndimage.gaussian_filter(w, s)
        ok = todo & (den > (0.2 if s < 48 else 0.005))
        out[ok] = num[ok] / den[ok][:, None]
        todo &= ~ok
    return out


def clean_closed(im, eyes, keep_open=()):
    """Closed eyes as lines on the base drawing (owner 2026-11-05: "smeared paint" around closed eyes).

    V5 paints the skin where the open eye was with grey airbrush washes, and its bangs never line up with the base's,
    so any cut through the eye band leaves steps and blurred patches in the hair. Anime cel faces are flat skin with
    the eye drawn as lines, so here the face is the base drawing everywhere in the band (bangs, brows, skin) and only
    the closed eye's own marks are taken from the composed frame: dark lines (lashes, > <) and tear highlights, inside
    each closed eye's area, not on the base's hair (hair stays in front) and not on the take's strands. Where the base
    has its open eye, the skin is the base's own skin spread in from around it. keep_open: indices of eyes left as
    composed (wink)."""
    B = np.asarray(Image.open(BASE_TAKE).convert("RGB")).astype(np.float32)
    F = np.asarray(im.convert("RGB")).astype(np.float32)
    H, W = B.shape[:2]
    holes = ell_mask((H, W), [(cx, cy, rx * 1.2, ry * 1.25, a) for cx, cy, rx, ry, a in EYES_ONLY]) > 0.5
    field = _skin_field(B, holes)

    def hair(a):
        return (a[..., 2] > a[..., 0] + 30) & (a.mean(-1) < 185)

    # base hair with its outlines; inside its eye openings only hair that runs in from outside them (its irises are
    # blue as well, but are enclosed by the lash and lid lines)
    eye_b = ell_mask((H, W), [(cx, cy, rx * 1.1, ry * 1.15, a) for cx, cy, rx, ry, a in EYES_ONLY]) > 0.5
    hb = hair(B)
    b_hair = ndimage.binary_propagation(hb & ~eye_b, mask=hb) | (hb & hair(F))
    b_hair = ndimage.binary_dilation(b_hair, iterations=2) & (~eye_b | b_hair)   # no dark caps on tips over the eye
    lumB = B.mean(-1)
    # the face without eyes: base pixels, but the base's own eyes (and the creases above them) become plain skin
    face = B.copy()
    z_open = ell_mask((H, W), [(cx, cy - ry * 0.1, rx * 1.35, ry * 1.6, a) for cx, cy, rx, ry, a in EYES_ONLY], 3)
    skin_b = (B[..., 0] > 225) & (B[..., 1] > 185) & (B[..., 2] > 165) & (B[..., 0] >= B[..., 2])
    # outside its eye only the base's eyelid creases change; its own skin shading and contour lines stay
    keep = ~eye_b & (skin_b | (lumB < 100))
    # specks of the base's iris that passed as hair
    lab, n = ndimage.label(b_hair & eye_b)
    small = np.isin(lab, [i + 1 for i, z in enumerate(ndimage.sum(b_hair & eye_b, lab, range(1, n + 1))) if z < 80])
    b_hair &= ~small
    wf = (z_open * ~b_hair * ~ndimage.binary_erosion(keep, iterations=1))[..., None]
    # at the outer eye corners the base's lash wings run out over the hair along the face's edge; what they cover
    # is unknown, so there the dark wing pixels touching the hair stay, in the face contour's colour (they continue
    # the contour line) instead of becoming skin notches
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    outer = np.zeros((H, W), bool)
    for (cx, cy, rx, ry, a), side in zip(EYES_ONLY, (-1, 1)):
        t = math.radians(a)
        u = (xx - cx) * math.cos(t) + (yy - cy) * math.sin(t)
        outer |= (side * u > 0.7 * rx) & (side * u < 1.6 * rx) & (np.abs(yy - cy) < 1.2 * ry)
    d_h = ndimage.distance_transform_edt(~b_hair)
    wing = outer & (d_h <= 4) & (lumB < 140)
    wing = ndimage.binary_opening(ndimage.binary_closing(wing, iterations=2), iterations=1) & outer & (d_h <= 5)
    core = b_hair & (lumB > 70)                       # hair fill, not its outlines
    hcol = np.zeros_like(B)
    todo = np.ones((H, W), bool)
    for s_ in (2, 4, 8):
        num = ndimage.gaussian_filter(B * core[..., None], (s_, s_, 0))
        den = ndimage.gaussian_filter(core.astype(np.float32), s_)
        ok = todo & (den > 0.05)
        hcol[ok] = num[ok] / den[ok][:, None]
        todo &= ~ok
    wing = ndimage.gaussian_filter(wing.astype(np.float32), 0.5)[..., None]
    fill = field * (1 - wing) + hcol * wing
    face = face * (1 - wf) + fill * wf
    # the closed eye's marks from the composed frame
    zone = ell_mask((H, W), [(cx, cy + ry * 0.2, rx * 1.3, ry * 1.25, a) for cx, cy, rx, ry, a in eyes], 2)
    lum = F.mean(-1)
    fh = hair(F) & (lum > 60)
    lab, n = ndimage.label(fh)
    big = np.isin(lab, [i + 1 for i, z in enumerate(ndimage.sum(fh, lab, range(1, n + 1))) if z > 400])
    f_hair = ndimage.binary_dilation(big, iterations=3)                # strands, not the gleam in a slit eye
    line = np.clip((185 - lum) / 70, 0, 1) * (F[..., 2] < F[..., 0] + 25)  # dark, not blue (lashes are brown/black)
    tear = ((F[..., 2] > F[..., 0] + 8) & (lum > 175)).astype(np.float32)
    tear = ndimage.binary_dilation(tear > 0, iterations=1) & (ndimage.gaussian_filter(line, 3) > 0.05)
    inside = ndimage.binary_fill_holes(ndimage.binary_closing(line > 0.5, iterations=2)).astype(np.float32)
    mark = np.maximum(np.maximum(line, tear), inside) * zone * ~b_hair * ~f_hair
    mark = ndimage.gaussian_filter(mark, 0.6)[..., None]
    out = face * (1 - mark) + F * mark
    # the band region becomes this face; everything else (mouth, open eyes kept for a wink) stays as composed
    cx, cy, rx, ry, a = BAND
    region = ell_mask((H, W), [(cx, cy, rx * 1.18, ry * 1.18, a)], 4)        # past the band's seam
    region *= 1 - ell_mask((H, W), [MOUTH3], 4)
    for i in keep_open:
        cx, cy, rx, ry, a = EYES_ONLY[i]
        region *= 1 - ell_mask((H, W), [(cx, cy, rx * 1.5, ry * 1.6, a)], 4)
    r = region[..., None]
    return Image.fromarray((F * (1 - r) + out * r).clip(0, 255).astype(np.uint8))


NEUTRAL = "x_neutral_0.45_36002"
_N = [(NEUTRAL, [BAND, MOUTH3], ())]
# cheeks: none transplanted (owner 2026-11-05: every pasted blush read as smeared over her cheeks); each face keeps
# the base drawing's cheeks, the takes' own blush still comes in with the eye band
FRAMES = {                                   # chosen takes (see art/generated/vtuber3/prompts.sh for each round)
    "neutral": _N,
    "blink": _N + [("f_blink_0.55_37002", list(EYES_ONLY), (), {"relight": True, "closed": (0, 1)})],   # eyes only: brows stay
    "talk_a": _N + [("f_talka_0.52_37001", [MOUTH3], ())],
    "talk_o": _N + [("f_talko_0.52_37002", [MOUTH3], ())],
    "smug": [("f_smug_37001", [BAND, MOUTH3], ())],
    "wink": [("f_wink_0.50_37012", [BAND, MOUTH3], (), {"closed": (1,)})],
    "happy": [("f_happy_37001", [BAND, MOUTH3], ())],
    "sing": [("f_sing_0.62_37001", [BAND, MOUTH3], (), {"closed": (0, 1)})],
    "shocked": [("f_shock_37001", [BAND, MOUTH3], ())],
    "angry": [("f_angry_37001", [BAND, MOUTH3], ())],
    "pout": [("f_pout_0.62_37001", [BAND, MOUTH3], (), {"closed": (0, 1)})],
    "flustered": [("f_flustered_37001", [BAND, MOUTH3], ())],
    "pain": [("f_pain_0.62_37004", [BAND, MOUTH3], (), {"closed": (0, 1)})],
}
FRAMES1024 = V3 / "frames1024"


def build1024(names=None):
    FRAMES1024.mkdir(exist_ok=True)
    for name in names or FRAMES:
        im, log = compose(FRAMES[name])
        im.save(FRAMES1024 / f"{name}.png")
        print(name, log)


def sheet3(out, folder=None, crop=(250, 280, 830, 800), w=420):
    from PIL import ImageFont
    folder = Path(folder or FRAMES1024)
    f = ImageFont.truetype(str(ROOT / "pv/fonts/MPLUSRounded1c-Bold.ttf"), 22)
    names = list(FRAMES)
    cols = 5
    h = round(w * (crop[3] - crop[1]) / (crop[2] - crop[0]))
    S = Image.new("RGB", (cols * w, ((len(names) + cols - 1) // cols) * (h + 30)), (232, 236, 248))
    d = ImageDraw.Draw(S)
    for i, n in enumerate(names):
        im = Image.open(folder / f"{n}.png").convert("RGB")
        k = im.width / 1024
        im = im.crop(tuple(round(v * k) for v in crop)).resize((w, h), Image.Resampling.LANCZOS)
        x, y = (i % cols) * w, (i // cols) * (h + 30)
        S.paste(im, (x, y + 30))
        d.text((x + 6, y + 3), f"{i + 1}. {n}", font=f, fill=(30, 40, 90))
    S.save(out)


# ---------------------------------------------------------------- 2048 px frames, cut-out
FINAL3 = V3 / "final"
FACE3 = (488, 520, 260, 230)      # face box (centre x, centre y, w, h) in 1024 units, for framing in the stream
BG3 = np.array([236, 237, 241], np.float32)


def upscale_all(models, names=None):
    sys.path.insert(0, str(ROOT / "pixel"))
    from vtmodel import anime_up
    FINAL3.mkdir(exist_ok=True)
    for n in names or FRAMES:
        anime_up(Image.open(FRAMES1024 / f"{n}.png").convert("RGB"), models).save(FINAL3 / f"{n}.png")
        print("up", n, flush=True)


_ALPHA = {}


def alpha3():
    """Cut-out at 2048 from the neutral frame (the body is the same in every frame). Background = V5's flat light
    grey connected to the border; grey gaps enclosed by hair strands are removed too, except inside the face (eye
    whites are close to that grey)."""
    if "a" in _ALPHA:
        return _ALPHA["a"]
    a = np.asarray(Image.open(FINAL3 / "neutral.png").convert("RGB")).astype(np.float32)
    H, W = a.shape[:2]
    near = np.sqrt(((a - BG3) ** 2).sum(-1)) < 11
    light = (a.min(-1) > 222) & (a.max(-1) - a.min(-1) < 18)      # V5's white rim around the outline
    # background seen through gaps between strands, tinted by the upscaler: light, low saturation and not reddish
    # (skin is redder than it is blue; the background grey is not)
    light |= (a.mean(-1) > 215) & (a.max(-1) - a.min(-1) < 35) & (a[..., 2] >= a[..., 0] - 2)
    lab, _ = ndimage.label(near | light)
    border = set(np.unique(np.concatenate([lab[0], lab[:, 0], lab[:, -1]]))) - {0}
    bg = np.isin(lab, list(border))
    k = W / 1024
    face = ell_mask((H, W), [(FACE3[0] * k, FACE3[1] * k, FACE3[2] * k * 0.75, FACE3[3] * k * 0.8, -17.5)]) > 0.5
    hair = ((a[..., 2] > a[..., 0] + 40) & (a[..., 2] > a[..., 1] + 20)) | (a.max(-1) < 110)   # hair or lines
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        if i in border or sl is None:
            continue
        comp = lab[sl] == i
        if comp.sum() < 12 or face[sl][comp].any():
            continue
        ys = slice(max(0, sl[0].start - 3), sl[0].stop + 3)
        xs = slice(max(0, sl[1].start - 3), sl[1].stop + 3)
        c2 = lab[ys, xs] == i
        ring = ndimage.binary_dilation(c2, iterations=2) & ~c2
        if (sl[0].start + sl[0].stop) / 2 < 0.35 * H:       # the white ear fur, up top (no strand gaps there)
            continue
        if ring.sum() and hair[ys, xs][ring].mean() > 0.3:
            bg[ys, xs] |= c2
    fg = ndimage.binary_opening(~bg, iterations=1)
    al = ndimage.gaussian_filter(fg.astype(np.float32), 0.8)
    _ALPHA["a"] = al
    return al


def model3(name):
    """2048 RGBA frame. Edge pixels are pulled towards the colour just inside so no grey fringe remains."""
    a = np.asarray(Image.open(FINAL3 / f"{name}.png").convert("RGB")).astype(np.float32)
    al = alpha3()
    fg = al > 0.5
    inner = ndimage.binary_erosion(fg, iterations=3)
    _, (iy, ix) = ndimage.distance_transform_edt(~inner, return_indices=True)
    band = fg & ~inner
    greyish = band & (np.sqrt(((a - BG3) ** 2).sum(-1)) < 40)
    a[greyish] = a[iy, ix][greyish]
    rgba = np.dstack([a.clip(0, 255), al * 255]).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def final_sheet(out):
    """The 13 cut-out 2048 frames on a light background, cropped to the bust."""
    from PIL import ImageFont
    f = ImageFont.truetype(str(ROOT / "pv/fonts/MPLUSRounded1c-Bold.ttf"), 26)
    names, cols, w = list(FRAMES), 5, 520
    crop = (360, 300, 1760, 1700)
    h = round(w * (crop[3] - crop[1]) / (crop[2] - crop[0]))
    S = Image.new("RGB", (cols * w, ((len(names) + cols - 1) // cols) * (h + 36)), (232, 236, 248))
    d = ImageDraw.Draw(S)
    for i, n in enumerate(names):
        c = Image.new("RGBA", (2048, 2048), (232, 236, 248, 255))
        c.alpha_composite(model3(n))
        x, y = (i % cols) * w, (i // cols) * (h + 36)
        S.paste(c.crop(crop).resize((w, h), Image.Resampling.LANCZOS).convert("RGB"), (x, y + 36))
        d.text((x + 8, y + 4), f"{i + 1}. {n}", font=f, fill=(30, 40, 90))
    S.save(out)


if __name__ == "__main__":
    models = sys.argv[sys.argv.index("--models") + 1] if "--models" in sys.argv else None
    cmd = sys.argv[1]
    if cmd == "pasteup":
        pasteup(models, sys.argv[2]).save(sys.argv[3])
    elif cmd == "build":
        build1024()
    elif cmd == "upscale":
        upscale_all(models)
    elif cmd == "sheet":
        final_sheet(sys.argv[2])
