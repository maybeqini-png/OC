"""PV v4 look toolkit: the OC taken pixel-exact from the reference sheet, integrated into scenes by light
(ambient grade, directional rim light, contact shadow, water reflection) instead of being pasted as a sticker,
plus the v4 typographic system (Mincho / heavy gothic / thin Latin, vertical setting, depth-sorted words).

Images are float32 in [0, 1]; RGBA layers are premultiplied.
"""
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "pv4/fonts"
CACHE = ROOT / "pv4/.cache"
W, H = 1920, 1080

# palette (README section 3) + light colours for the night scenes
INK, NAVY = (0.075, 0.09, 0.17), (0.106, 0.137, 0.251)
COBALT, SKY, WHITE = (0.235, 0.427, 0.941), (0.612, 0.769, 1.0), (0.957, 0.965, 0.984)
CORAL, LEMON = (1.0, 0.482, 0.541), (1.0, 0.839, 0.290)
MOON = (0.80, 0.90, 1.0)

FACE = {"mincho": "ZenOldMincho-Bold.ttf", "mincho_r": "ZenOldMincho-Regular.ttf", "heavy": "DelaGothicOne-Regular.ttf",
        "gothic": "ZenKakuGothicNew-Bold.ttf", "gothic_b": "ZenKakuGothicNew-Black.ttf", "latin": "CormorantGaramond-wght.ttf"}


# ---------------- the OC, exactly as drawn on the reference sheet ----------------
def _cutout(rgb):
    """White-background sheet -> premultiplied RGBA. Background = near-white regions connected to the border,
    plus large enclosed white pockets (gaps between tail and leg); small whites (eyes, highlights) stay."""
    u8 = (rgb * 255).astype(np.uint8)
    h, w = u8.shape[:2]
    near = (u8.min(axis=2) >= 236).astype(np.uint8)
    n, lab = cv2.connectedComponents(near, connectivity=4)
    border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    bg = np.isin(lab, border[border > 0]).astype(np.uint8)
    # enclosed pockets (between hair and sleeves, tail and leg) are paper white; skin highlights are warm, so
    # only neutral near-pure white counts, and the face (eye whites) is excluded
    pure = ((u8.min(axis=2) >= 248) & (u8.max(axis=2).astype(int) - u8.min(axis=2) <= 5)).astype(np.uint8)
    n2, lab2, stats, cent = cv2.connectedComponentsWithStats(pure, connectivity=4)
    for i in range(1, n2):
        cx, cy = cent[i] / (w, h)
        if stats[i, cv2.CC_STAT_AREA] > 4e-5 * h * w and not (0.40 < cx < 0.60 and 0.09 < cy < 0.23):
            bg[lab2 == i] = 1
    a = 1.0 - bg.astype(np.float32)
    a = cv2.erode(a, np.ones((3, 3), np.uint8), iterations=1)
    a = cv2.GaussianBlur(a, (0, 0), 1.1)
    a = np.clip(a, 0, 1)
    # remove the white fringe: un-composite from white where alpha is partial
    am = np.maximum(a, 1e-3)[..., None]
    col = np.clip((rgb - (1 - a[..., None]) * 1.0) / am, 0, 1)
    col = np.where(a[..., None] > 0.02, col, 0)
    return np.concatenate([col * a[..., None], a[..., None]], axis=-1).astype(np.float32)


@lru_cache(maxsize=1)
def sheet_master():
    """4x master of the reference sheet (pv2/rig/master_x4.png, Real-ESRGAN of the owner's sheet), cut out."""
    CACHE.mkdir(exist_ok=True)
    p = CACHE / "sheet_x4_rgba.npy"
    if p.exists():
        return np.load(p)
    rgb = np.asarray(Image.open(ROOT / "pv2/rig/master_x4.png").convert("RGB")).astype(np.float32) / 255
    rgba = _cutout(rgb)
    ys, xs = np.where(rgba[..., 3] > 0.02)
    rgba = rgba[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    np.save(p, rgba)
    return rgba


def figure(height, crop=None):
    """The full figure (or a crop given as fractions x0,y0,x1,y1 of the figure box) scaled to `height` px."""
    m = sheet_master()
    if crop:
        h, w = m.shape[:2]
        x0, y0, x1, y1 = crop
        m = m[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]
    s = height / m.shape[0]
    return cv2.resize(m, (max(int(m.shape[1] * s), 1), height), interpolation=cv2.INTER_AREA)


# head-and-shoulders box on the figure (fractions of the cut-out figure box)
HEAD = (0.18, 0.0, 0.82, 0.30)


# ---------------- integration by light ----------------
def relight(rgba, ambient=NAVY, amb_k=0.28, key=1.0, rim_dir=(-0.4, -1.0), rim_color=MOON, rim_k=0.9, rim_px=6,
            fill_color=None, fill_k=0.0):
    """Grade the drawing into the scene: ambient tint, exposure, directional rim light on the silhouette edge
    facing the light, optional coloured fill (screen glow, spotlight)."""
    a = rgba[..., 3]
    col = rgba[..., :3] / np.maximum(a, 1e-4)[..., None]
    amb = np.array(ambient, np.float32)
    # ambient: shadows take the scene colour, lights keep the design colour
    lum = col @ np.array([0.3, 0.59, 0.11], np.float32)
    tint = amb_k * (1 - lum)[..., None]
    col = col * (1 - tint) + (col * amb * 2.2) * tint
    col = col * key
    if fill_color is not None and fill_k:
        col = col + np.array(fill_color, np.float32) * fill_k * (0.35 + 0.65 * lum[..., None])
    # rim: silhouette band, weighted by how much the edge normal faces the light
    band = np.clip(a - cv2.erode(a, np.ones((rim_px * 2 + 1, rim_px * 2 + 1), np.uint8)), 0, 1)
    sm = cv2.GaussianBlur(a, (0, 0), rim_px * 0.8)
    gx, gy = cv2.Sobel(sm, cv2.CV_32F, 1, 0, ksize=5), cv2.Sobel(sm, cv2.CV_32F, 0, 1, ksize=5)
    nrm = np.sqrt(gx ** 2 + gy ** 2) + 1e-6
    d = np.array(rim_dir, np.float32) / np.linalg.norm(rim_dir)
    facing = np.clip(-(gx * d[0] + gy * d[1]) / nrm, 0, 1)
    rim = cv2.GaussianBlur(band * facing, (0, 0), 1.2) * rim_k
    col = col + np.array(rim_color, np.float32) * rim[..., None]
    col = np.clip(col, 0, 1.4)
    return np.concatenate([col * a[..., None], a[..., None]], axis=-1)


def over(dst, src, x, y, alpha=1.0):
    """Premultiplied src over dst at integer offset (clipped)."""
    h, w = src.shape[:2]
    H_, W_ = dst.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W_), min(y + h, H_)
    if x0 >= x1 or y0 >= y1:
        return dst
    s = src[y0 - y:y1 - y, x0 - x:x1 - x] * alpha
    dst[y0:y1, x0:x1, :3] = dst[y0:y1, x0:x1, :3] * (1 - s[..., 3:]) + s[..., :3]
    return dst


def add(dst, light, x=0, y=0):
    """Additive light layer (RGB) at offset."""
    h, w = light.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, dst.shape[1]), min(y + h, dst.shape[0])
    dst[y0:y1, x0:x1, :3] += light[y0 - y:y1 - y, x0 - x:x1 - x, :3]
    return dst


def reflection(rgba, fade=(0.55, 0.0), blur=2.5, ripple=(5.0, 0.045), t=0.0, tint=(0.55, 0.68, 0.95), squash=0.96):
    """Mirror image for a water/glass floor: flipped, rippled, blurred, faded with distance, tinted."""
    r = rgba[::-1].copy()
    h, w = r.shape[:2]
    r = cv2.resize(r, (w, int(h * squash)), interpolation=cv2.INTER_AREA)
    h = r.shape[0]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    amp = ripple[0] * (0.3 + yy / h)
    mapx = xx + amp * np.sin(yy * ripple[1] * 6.283 / 6 + t * 3.0)
    r = cv2.remap(r, mapx, yy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    r = cv2.GaussianBlur(r, (0, 0), blur)
    f = np.linspace(fade[0], fade[1], h, dtype=np.float32)[:, None, None]
    r = r * f
    r[..., :3] *= np.array(tint, np.float32)
    return r


def contact_glow(frame, cx, cy, rx, ry, color=MOON, k=0.35):
    """Soft light pool where she stands on a lit floor/water."""
    yy, xx = np.mgrid[0:frame.shape[0], 0:frame.shape[1]].astype(np.float32)
    g = np.exp(-(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2))
    frame[..., :3] += np.array(color, np.float32) * g[..., None] * k
    return frame


def shadow_pool(frame, cx, cy, rx, ry, k=0.45):
    yy, xx = np.mgrid[0:frame.shape[0], 0:frame.shape[1]].astype(np.float32)
    g = np.exp(-(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2))
    frame[..., :3] *= (1 - k * g)[..., None]
    return frame


# ---------------- typography ----------------
@lru_cache(maxsize=64)
def font(face, size):
    f = ImageFont.truetype(str(FONTS / FACE[face]), size)
    if face == "latin":
        try:
            f.set_variation_by_axes([300])
        except Exception:
            pass
    return f


ROTATE_V = set("ー〜～…ｰ—-")  # glyphs rotated 90 degrees in vertical setting
SMALL_V = set("ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮ")


def type_rgba(text, face, size, fill=WHITE, stroke=None, stroke_w=0, tracking=0.0, vertical=False, outline_only=False,
              glow=0.0, glow_color=None, line_gap=0.25):
    """Text as premultiplied RGBA. tracking = extra space in em; vertical = tategaki (top to bottom, columns right
    to left for '\\n'); outline_only draws just the stroke (for big background words)."""
    f = font(face, size)
    pad = int(stroke_w + size * 0.3 + glow * 3)
    lines = text.split("\n")
    adv = size * (1 + tracking)
    if vertical:
        cols = len(lines)
        hmax = max(len(l) for l in lines)
        cw, ch = int(cols * size * (1 + line_gap)) + 2 * pad, int(hmax * adv) + 2 * pad
    else:
        widths = [sum(f.getlength(c) + size * tracking for c in l) for l in lines]
        cw, ch = int(max(widths)) + 2 * pad, int(len(lines) * size * (1 + line_gap)) + 2 * pad
    img = Image.new("L", (cw, ch), 0)
    edge = Image.new("L", (cw, ch), 0)
    d, de = ImageDraw.Draw(img), ImageDraw.Draw(edge)

    def glyph(c, x, y, rot=False):
        if rot:
            g = Image.new("L", (size * 2, size * 2), 0)
            ge = Image.new("L", (size * 2, size * 2), 0)
            ImageDraw.Draw(g).text((size // 2, size // 2), c, font=f, fill=255)
            if stroke_w:
                ImageDraw.Draw(ge).text((size // 2, size // 2), c, font=f, fill=255, stroke_width=stroke_w, stroke_fill=255)
            g, ge = g.rotate(-90, center=(size, size)), ge.rotate(-90, center=(size, size))
            img.paste(255, (int(x - size / 2), int(y - size / 2)), g)
            edge.paste(255, (int(x - size / 2), int(y - size / 2)), ge)
            return
        d.text((x, y), c, font=f, fill=255)
        if stroke_w:
            de.text((x, y), c, font=f, fill=255, stroke_width=stroke_w, stroke_fill=255)

    for li, l in enumerate(lines):
        if vertical:
            x = cw - pad - (li + 1) * size * (1 + line_gap) + size * line_gap / 2
            y = pad
            for c in l:
                if c in SMALL_V:
                    glyph(c, x + size * 0.12, y - size * 0.12)
                else:
                    glyph(c, x, y, rot=c in ROTATE_V)
                y += adv
        else:
            x, y = pad, pad + li * size * (1 + line_gap)
            for c in l:
                glyph(c, x, y)
                x += f.getlength(c) + size * tracking
    fill_a = np.asarray(img).astype(np.float32) / 255
    edge_a = np.asarray(edge).astype(np.float32) / 255 if stroke_w else np.zeros_like(fill_a)
    out = np.zeros((ch, cw, 4), np.float32)
    if stroke_w:
        sa = np.clip(edge_a - (fill_a if outline_only else 0), 0, 1) if outline_only else edge_a
        sc = np.array(stroke or fill, np.float32)
        out[..., :3] = sc * sa[..., None]
        out[..., 3] = sa
    if not outline_only:
        fc = np.array(fill, np.float32)
        out[..., :3] = out[..., :3] * (1 - fill_a[..., None]) + fc * fill_a[..., None]
        out[..., 3] = np.maximum(out[..., 3], fill_a)
    if glow:
        gc = np.array(glow_color or fill, np.float32)
        g = cv2.GaussianBlur(out[..., 3], (0, 0), glow)
        out[..., :3] += gc * g[..., None] * 0.8
        out[..., 3] = np.clip(out[..., 3] + g * 0.6, 0, 1)
    return out


def bbox_trim(rgba, pad=4):
    ys, xs = np.where(rgba[..., 3] > 0.01)
    if len(xs) == 0:
        return rgba
    return rgba[max(ys.min() - pad, 0):ys.max() + pad + 1, max(xs.min() - pad, 0):xs.max() + pad + 1]


def put(frame, rgba, cx, cy, scale=1.0, angle=0.0, alpha=1.0, anchor=(0.5, 0.5)):
    if scale != 1.0 or angle:
        h, w = rgba.shape[:2]
        M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, scale)
        c, s = abs(M[0, 0]), abs(M[0, 1])
        nw, nh = int(h * s + w * c) + 2, int(h * c + w * s) + 2
        M[0, 2] += nw / 2 - w / 2
        M[1, 2] += nh / 2 - h / 2
        rgba = cv2.warpAffine(rgba, M, (nw, nh), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
    h, w = rgba.shape[:2]
    return over(frame, rgba, int(cx - w * anchor[0]), int(cy - h * anchor[1]), alpha)


# ---------------- plates and finishing ----------------
def plate(path, blur=0.0, zoom=1.0, cx=0.5, cy=0.5, flip_v=False):
    im = np.asarray(Image.open(path).convert("RGB")).astype(np.float32) / 255
    h, w = im.shape[:2]
    s = max(W / w, H / h) * zoom
    im = cv2.resize(im, (int(w * s) + 1, int(h * s) + 1), interpolation=cv2.INTER_CUBIC)
    h, w = im.shape[:2]
    x0, y0 = int((w - W) * cx), int((h - H) * cy)
    im = im[y0:y0 + H, x0:x0 + W]
    if flip_v:
        im = im[::-1]
    if blur:
        im = cv2.GaussianBlur(im, (0, 0), blur)
    return np.ascontiguousarray(im)


def grade(img, k=0.6, stops=((0.0, INK), (0.32, NAVY), (0.62, COBALT), (0.85, SKY), (1.0, WHITE)), contrast=1.0):
    """Gradient-map a generated plate onto the PV palette (mixed by k): one colour world for every asset and
    no stray generator hues or texture noise competing with the character."""
    lum = np.clip((img[..., :3] @ np.array([0.3, 0.59, 0.11], np.float32) - 0.5) * contrast + 0.5, 0, 1)
    xs = np.array([s[0] for s in stops], np.float32)
    out = np.stack([np.interp(lum, xs, np.array([s[1][c] for s in stops], np.float32)) for c in range(3)], -1)
    img = img.copy()
    img[..., :3] = img[..., :3] * (1 - k) + out * k
    return img


def bloom(frame, thresh=0.72, k=0.45, sigmas=(6, 18, 48)):
    lum = frame[..., :3].max(axis=2, keepdims=True)
    hi = frame[..., :3] * np.clip((lum - thresh) / (1 - thresh), 0, 1)
    acc = sum(cv2.GaussianBlur(hi, (0, 0), s) for s in sigmas) / len(sigmas)
    frame[..., :3] += acc * k
    return frame


def chroma(frame, px=2.0):
    """Lateral chromatic aberration growing toward the frame edge."""
    h, w = frame.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dx, dy = (xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2)
    out = frame.copy()
    for ch, sgn in ((0, 1), (2, -1)):
        mx = xx + sgn * px * dx * np.abs(dx)
        my = yy + sgn * px * dy * np.abs(dy) * 0.6
        out[..., ch] = cv2.remap(frame[..., ch], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return out


def vignette(frame, k=0.35, color=INK):
    h, w = frame.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    v = np.clip((r - 0.55) / 0.9, 0, 1) ** 1.6 * k
    frame[..., :3] = frame[..., :3] * (1 - v[..., None]) + np.array(color, np.float32) * v[..., None]
    return frame


def grain(frame, seed=0, k=0.022):
    rng = np.random.default_rng(seed)
    n = rng.standard_normal(frame.shape[:2]).astype(np.float32)
    n = cv2.GaussianBlur(n, (0, 0), 0.7)
    frame[..., :3] += n[..., None] * k
    return frame


def tonemap(frame):
    """Soft shoulder so bloom and rim light roll off instead of clipping."""
    x = np.maximum(frame[..., :3], 0)
    frame[..., :3] = np.where(x < 0.8, x, 0.8 + 0.2 * np.tanh((x - 0.8) / 0.2))
    return frame


def finish(frame, seed=0, bloom_k=0.12, chroma_px=1.2, vig=0.32, grain_k=0.018):
    """Bloom here only catches real light sources (high threshold); plates get their own bloom before the
    character is placed, so line art and skin never glow."""
    f = bloom(frame, thresh=0.93, k=bloom_k)
    f = chroma(f, chroma_px) if chroma_px else f
    f = vignette(f, vig)
    f = grain(f, seed, grain_k)
    return np.clip(tonemap(f), 0, 1)


def save(frame, path, q=92):
    Image.fromarray((np.clip(frame[..., :3], 0, 1) * 255 + 0.5).astype(np.uint8)).save(path, quality=q)
