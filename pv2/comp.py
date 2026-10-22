"""Compositing (撮影) for the PV: puts the rig inside the scene instead of on top of it.

All images are float32 0..1; character layers are premultiplied RGBA from rig.View.render().
Operations follow anime 撮影 practice: gradation over the character in the scene's light colours, rim
(back) light from the scene's light side, light wrap from the blurred background, contact shadow, diffusion
glow over the whole frame, depth of field on the background, foreground bokeh/particles, grain.
"""
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONTS = Path(__file__).resolve().parent.parent / "pv" / "fonts"
INK = (0.106, 0.137, 0.251)
COBALT = (0.235, 0.427, 0.941)
SKY = (0.612, 0.769, 1.0)
WHITE = (0.957, 0.965, 0.984)
CORAL = (1.0, 0.482, 0.541)
LEMON = (1.0, 0.839, 0.290)


def load_rgb(path, size=None):
    im = Image.open(path).convert("RGB")
    if size:
        im = im.resize(size, Image.LANCZOS)
    return np.asarray(im).astype(np.float32) / 255


def over(dst, src, x, y):
    """Composite premultiplied RGBA `src` onto RGB `dst` at integer position (x, y), clipped."""
    H, W = dst.shape[:2]
    h, w = src.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0:
        return dst
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]
    dst[y0:y1, x0:x1] = s[..., :3] + dst[y0:y1, x0:x1] * (1 - s[..., 3:])
    return dst


def light_char(ch, bg_patch, light):
    """Grade a premultiplied character with the scene light so she belongs to the plate.

    light: top/bottom (gradation colours, multiplied), grade (strength, kept low so her colours stay on-model),
    rim (colour), rim_dir (+1 light from the right, -1 from the left), rim_k, wrap_k."""
    a = ch[..., 3:]
    h, w = a.shape[:2]
    rgb = ch[..., :3].copy()
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    grad = np.array(light["top"], np.float32) * (1 - yy) + np.array(light["bottom"], np.float32) * yy
    g = light.get("grade", 0.15)
    rgb *= (1 - g) + g * grad
    a2 = a[..., 0]
    width = max(int(light.get("rim_w", 6)), 1)
    for d in ([light.get("rim_dir", 1)] if light.get("rim_dir", 1) != 0 else [-1, 1]):
        shifted = np.zeros_like(a2)
        if d > 0:
            shifted[:, :-width] = a2[:, width:]
        else:
            shifted[:, width:] = a2[:, :-width]
        edge = np.clip(a2 - shifted, 0, 1)
        edge = cv2.GaussianBlur(edge, (0, 0), width * 0.6)[..., None] * a
        rgb += np.array(light["rim"], np.float32) * edge * light.get("rim_k", 0.55)
    if bg_patch is not None and light.get("wrap_k", 0.25) > 0:
        er = cv2.erode(a2, np.ones((7, 7), np.uint8), iterations=1)
        band = cv2.GaussianBlur(np.clip(a2 - er, 0, 1), (0, 0), 4)[..., None] * a
        wrap = cv2.GaussianBlur(bg_patch, (0, 0), 12)
        rgb = rgb * (1 - band * light["wrap_k"]) + wrap * band * light["wrap_k"]
    return np.concatenate([np.clip(rgb, 0, None), a], axis=-1)


def contact_shadow(frame, cx, cy, rx, ry, k=0.35, color=(0.25, 0.22, 0.42)):
    H, W = frame.shape[:2]
    yy, xx = np.ogrid[:H, :W]
    m = np.exp(-(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2) * 2.2) * k
    frame[:] = frame * (1 - m[..., None]) + np.array(color, np.float32) * frame * m[..., None]
    return frame


def diffusion(frame, k=0.22, sigma=14, thresh=0.62):
    hi = np.clip((frame - thresh) / (1 - thresh), 0, 1)
    glow = cv2.GaussianBlur(hi, (0, 0), sigma)
    return 1 - (1 - frame) * (1 - glow * k)


def beams(frame, t, origins, color=(0.85, 0.93, 1.0), k=0.35, spread=0.10, speed=0.6, seed=0):
    """Additive stage light beams sweeping from given origins (fractions of the frame)."""
    H, W = frame.shape[:2]
    acc = np.zeros((H // 4, W // 4), np.float32)
    for i, (ox, oy) in enumerate(origins):
        ang = np.pi / 2 + 0.45 * np.sin(t * speed * 2 * np.pi * (0.7 + 0.13 * i) + i * 1.7 + seed)
        yy, xx = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32)
        dx, dy = xx - ox * W / 4, yy - oy * H / 4
        a = np.arctan2(dy, dx)
        d = np.abs(np.angle(np.exp(1j * (a - ang))))
        acc += np.clip(1 - d / spread, 0, 1) ** 2 * np.clip(np.hypot(dx, dy) / (H / 4), 0, 1)
    acc = cv2.resize(cv2.GaussianBlur(acc, (0, 0), 3), (W, H))[..., None]
    return 1 - (1 - frame) * (1 - acc * k * np.array(color, np.float32))


def particles(frame, t, seed, n=40, color=WHITE, size=(3, 14), speed=(20, 60), k=0.7, bokeh=True, drift=(0, -1)):
    """Floating bokeh / confetti: deterministic per seed, positions depend only on t."""
    H, W = frame.shape[:2]
    rng = np.random.default_rng(seed)
    x0, y0 = rng.uniform(0, W, n), rng.uniform(0, H, n)
    r = rng.uniform(*size, n)
    v = rng.uniform(*speed, n)
    ph = rng.uniform(0, 6.28, n)
    layer = np.zeros((H, W), np.float32)
    for i in range(n):
        x = (x0[i] + drift[0] * v[i] * t + 18 * np.sin(t * 0.9 + ph[i])) % W
        y = (y0[i] + drift[1] * v[i] * t) % H
        cv2.circle(layer, (int(x), int(y)), int(r[i]), float(0.5 + 0.5 * np.sin(t * 2.1 + ph[i]) ** 2), -1, cv2.LINE_AA)
    if bokeh:
        layer = cv2.GaussianBlur(layer, (0, 0), 2.5)
    layer = layer[..., None] * k
    return 1 - (1 - frame) * (1 - layer * np.array(color, np.float32))


def sparkle(frame, x, y, r, k=1.0, color=WHITE, rot=0.0):
    """Four-point anime sparkle (キラッ)."""
    s = int(r * 2.4)
    canvas = np.zeros((2 * s, 2 * s), np.uint8)
    pts = []
    for i in range(8):
        ang = rot + i * np.pi / 4
        rr = r if i % 2 == 0 else r * 0.18
        pts.append((s + rr * np.cos(ang) * 2, s + rr * np.sin(ang) * 2))
    cv2.fillPoly(canvas, [np.int32(pts)], 255, cv2.LINE_AA)
    m = cv2.resize(canvas, (s, s), interpolation=cv2.INTER_AREA).astype(np.float32)[..., None] / 255 * k
    patch = np.concatenate([m * np.array(color, np.float32), m], axis=-1)
    return over(frame, patch, int(x - s / 2), int(y - s / 2))


def vignette(frame, k=0.22, color=INK):
    H, W = frame.shape[:2]
    yy, xx = np.ogrid[:H, :W]
    d = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
    m = np.clip((d - 0.45) / 1.2, 0, 1)[..., None] * k
    return frame * (1 - m) + np.array(color, np.float32) * m


def grain(frame, frame_idx, k=0.018):
    rng = np.random.default_rng(frame_idx)
    n = rng.normal(0, 1, frame.shape[:2]).astype(np.float32)[..., None]
    return frame + n * k


@lru_cache(None)
def font(size, kind="ExtraBold"):
    return ImageFont.truetype(str(FONTS / f"MPLUSRounded1c-{kind}.ttf"), size)


@lru_cache(maxsize=256)
def text_rgba(text, size, fill=WHITE, stroke=COBALT, stroke_w=None, kind="ExtraBold", shadow=True, vertical=False):
    """Rendered label as premultiplied RGBA (white fill, coloured outline, soft drop shadow)."""
    f = font(size, kind)
    sw = stroke_w if stroke_w is not None else max(size // 9, 2)
    chars = list(text) if vertical else [text]
    boxes = [f.getbbox(c, stroke_width=sw) for c in chars]
    if vertical:
        w = max(b[2] - b[0] for b in boxes) + 2 * sw + 16
        h = int(sum(size * 1.02 for _ in chars)) + 2 * sw + 16
    else:
        b = boxes[0]
        w, h = b[2] - b[0] + 2 * sw + 16, b[3] - b[1] + 2 * sw + 16
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = tuple(int(c * 255) for c in fill)
    scol = tuple(int(c * 255) for c in stroke)
    if vertical:
        y = 8
        for c in chars:
            cb = f.getbbox(c, stroke_width=sw)
            d.text(((w - (cb[2] - cb[0])) / 2 - cb[0], y - cb[1] + sw), c, font=f, fill=col, stroke_width=sw, stroke_fill=scol)
            y += size * 1.02
    else:
        d.text((8 + sw - boxes[0][0], 8 + sw - boxes[0][1]), text, font=f, fill=col, stroke_width=sw, stroke_fill=scol)
    a = np.asarray(im).astype(np.float32) / 255
    rgba = np.concatenate([a[..., :3] * a[..., 3:], a[..., 3:]], axis=-1)
    if shadow:
        sh = cv2.GaussianBlur(a[..., 3], (0, 0), max(size / 18, 1.5))
        sh = np.roll(np.roll(sh, int(size * 0.06), 0), int(size * 0.04), 1)[..., None] * 0.45
        shadow_rgba = np.concatenate([np.array(INK, np.float32) * sh, sh], axis=-1)
        rgba = rgba + shadow_rgba * (1 - rgba[..., 3:])
    return rgba


def transform_rgba(rgba, scale=1.0, angle=0.0, alpha=1.0):
    h, w = rgba.shape[:2]
    if scale != 1.0 or angle != 0.0:
        M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, scale)
        nw, nh = int(w * scale * 1.3) + 4, int(h * scale * 1.3) + 4
        M[0, 2] += (nw - w) / 2
        M[1, 2] += (nh - h) / 2
        rgba = cv2.warpAffine(rgba, M, (nw, nh), flags=cv2.INTER_LINEAR, borderValue=0)
    return rgba * alpha


def put(frame, rgba, cx, cy, scale=1.0, angle=0.0, alpha=1.0):
    """Place an RGBA element centred at (cx, cy)."""
    if alpha <= 0.002 or scale <= 0.01:
        return frame
    r = transform_rgba(rgba, scale, angle, alpha)
    return over(frame, r, int(cx - r.shape[1] / 2), int(cy - r.shape[0] / 2))


def camera(canvas, out_size, zoom=1.0, cx=0.5, cy=0.5, angle=0.0, shake=(0.0, 0.0)):
    """Final camera: zoom/rotate around a point of the canvas and crop to out_size (no upsampling beyond 1/zoom)."""
    H, W = canvas.shape[:2]
    ow, oh = out_size
    base = min(W / ow, H / oh)
    s = 1 / base * zoom
    M = cv2.getRotationMatrix2D((cx * W, cy * H), angle, s)
    M[0, 2] += ow / 2 - cx * W + shake[0]
    M[1, 2] += oh / 2 - cy * H + shake[1]
    return cv2.warpAffine(canvas, M, (ow, oh), flags=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


def ease(u):
    u = float(np.clip(u, 0, 1))
    return u * u * (3 - 2 * u)


def ease_out_back(u, k=1.7):
    u = float(np.clip(u, 0, 1)) - 1
    return 1 + u * u * ((k + 1) * u + k)
