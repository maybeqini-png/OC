"""v4 motion test (72.2-78.5 s): 「強がりだって　本気だもん」 → flip into the reflection world for 「この声で」.

Shows the v4 rules in motion:
- the character is the owner's sheet, moved only by the deterministic rig (pv2/rig.py: breathing, blinks, head
  tilt, hair/ear/ahoge/tail follow-through); no generated video, so nothing can morph or flicker;
- depth: plate, reflection, figure and type move at different parallax rates under one slow camera push;
- type: each character fades, rises and sharpens on its sung time (pv3/lyrics_timed.json), staggered;
- transition: a whip-tilt down through the waterline into the inverted world below it (the two worlds meet
  seamlessly at the water), motivated by the lyric: the bluff above the water, the truth below.

usage: motion_test.py preview <t...> --out sheet.jpg | render <out.mp4> [workers]
"""
import json
import subprocess
import sys
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "pv2"))
import look as L  # noqa: E402
from rig import Motion, Rig  # noqa: E402

W, H, FPS = L.W, L.H, 30
T0, T1 = 72.2, 78.5
FLIP = (76.3, 76.8)
TIMED = json.load(open(HERE.parent / "pv3/lyrics_timed.json"))
LINE = next(l for l in TIMED if l["line"].startswith("強がり"))
NEXT = next(l for l in TIMED if l["line"].startswith("この声で"))
HORIZON = int(H * 0.585)
BOX, FIG_H = (250, 10, 770, 1500), 640
MOTION = Motion(seed=11)


@lru_cache(maxsize=1)
def rig_view():
    return Rig(HERE.parent / "pv2/rig").view(FIG_H / (BOX[3] - BOX[1]), BOX)


@lru_cache(maxsize=1)
def plate_big():
    """Graded, bloomed plate rendered 6% larger than the frame so the camera can drift inside it."""
    p = L.grade(L.plate(L.ROOT / "art/generated/pv4/plates/p1_mirror_moon.png", zoom=1.12 * 1.06, cx=0.62, cy=0.42), k=0.45)
    return L.bloom(p, thresh=0.7, k=0.35)


@lru_cache(maxsize=16)
def glyph(ch, face, size, color):
    return L.bbox_trim(L.type_rgba(ch, face, size, fill=color), pad=2)


def type_reveal(f, text, chars, t, x, y, size, color, face="mincho", step=1.28, ripple=False, out_t=None):
    """Vertical line, one glyph per sung character: fade 0.22 s, rise 14 px, blur 6 -> 0 px."""
    for k, (ch, ct) in enumerate(zip(text, chars)):
        u = (t - ct) / 0.22
        if u <= 0:
            continue
        a = min(u, 1.0)
        if out_t is not None:
            a *= np.clip((out_t - t) / 0.25, 0, 1)
        if a <= 0:
            continue
        g = glyph(ch, face, size, color)
        e = 1 - (1 - min(u, 1)) ** 3
        b = 6 * (1 - e)
        if b > 0.3:
            g = cv2.GaussianBlur(g, (0, 0), b)
        if ripple:
            hh, ww = g.shape[:2]
            yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
            g = cv2.remap(g, xx + 2.2 * np.sin(yy * 0.09 + t * 4), yy, cv2.INTER_LINEAR)
        cy = y + k * size * step + 14 * (1 - e)
        L.over(f, g, int(x - g.shape[1] / 2), int(cy), a)
    return f


def chars_of(line, text, step=0.11):
    """Glyph times for a phrase: its onset plus an even stagger. The per-character times in lyrics_timed.json
    are not reliable (e.g. 強 72.70 -> が 74.18), so only phrase onsets are used until the lyrics are re-timed."""
    p = next(p for p in line["phrases"] if p["text"] == text)
    return [p["t"] + k * step for k in range(len(text))]


def scene(t, mirror_world=False):
    u = (t - T0) / (T1 - T0)
    z = 1.0 + 0.045 * L_ease(u)  # slow push-in for the whole shot
    big = plate_big()
    # plate drifts least (far), figure and type at full rate (near)
    ox = int((big.shape[1] - W) * (0.5 - 0.10 * u))
    oy = int((big.shape[0] - H) * 0.5)
    f = big[oy:oy + H, ox:ox + W].copy()
    v = rig_view()
    prm = MOTION.params(t, energy=0.45)
    fig = v.render(prm)
    fig = L.relight(fig, ambient=L.NAVY, amb_k=0.42, key=0.8, rim_dir=(-1.0, -0.2), rim_color=L.MOON, rim_k=0.9, rim_px=4)
    cx, feet = int(W * 0.63 - 30 * u), int(H * 0.835)
    x = cx - fig.shape[1] // 2
    feet_y = int(rig_view().p((0, 1494))[1])  # boot soles in view px
    refl = L.reflection(fig[:feet_y + 4], fade=(0.5, 0.0), blur=2.2, ripple=(4.0, 0.06), t=t, tint=(0.55, 0.7, 1.0))
    L.over(f, refl, x, feet - 6)
    L.contact_glow(f, cx, feet + 4, 150, 14, color=L.MOON, k=0.28)
    L.over(f, fig[:feet_y + 4], x, feet - feet_y - 4)
    if not mirror_world:
        type_reveal(f, "強がりだって", chars_of(LINE, "強がりだって"), t, W * 0.505 - 30 * u, H * 0.13, 58, L.INK,
                    out_t=LINE["end"] + 0.4)
        type_reveal(f, "本気だもん", chars_of(LINE, "本気だもん"), t, W * 0.79 - 30 * u, HORIZON + 8, 50, L.CORAL,
                    ripple=True, out_t=LINE["end"] + 0.4)
    f = drift_motes(f, t)
    f = zoom(f, z)
    return f


def L_ease(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def zoom(f, z):
    if abs(z - 1) < 1e-4:
        return f
    M = np.float32([[z, 0, W / 2 * (1 - z)], [0, z, H / 2 * (1 - z)]])
    return cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


MOTE_RNG = np.random.default_rng(3)
MOTES = np.stack([MOTE_RNG.uniform(0, W, 50), MOTE_RNG.uniform(0, HORIZON, 50), MOTE_RNG.uniform(1.5, 3.5, 50),
                  MOTE_RNG.uniform(4, 14, 50), MOTE_RNG.uniform(0, 6.28, 50)], 1)


def drift_motes(f, t):
    layer = np.zeros_like(f)
    for x, y, r, sp, ph in MOTES:
        yy = (y - sp * (t - T0)) % HORIZON
        xx = x + 6 * np.sin(t * 0.7 + ph)
        cv2.circle(layer, (int(xx), int(yy)), int(max(r, 1)), L.MOON, -1, cv2.LINE_AA)
    layer = cv2.GaussianBlur(layer, (0, 0), 1.6)
    f[..., :3] += layer[..., :3] * 0.3
    return f


def mirror(t):
    """The reflection world: the same scene turned over at the horizon, coral-tinted, new line on top."""
    f = scene(t, mirror_world=True)
    f = np.ascontiguousarray(f[::-1])
    f[..., :3] = f[..., :3] * np.array((1.0, 0.9, 0.95), np.float32)
    words = chars_of(NEXT, "この声で")
    type_reveal(f, "この声で", words, t, W * 0.36, H * 0.16, 58, L.WHITE)
    return f


def frame(t):
    a, b = FLIP
    if t < a:
        f = scene(t)
    elif t >= b:
        f = mirror(t)
    else:
        # whip-tilt: the world above stacked on the world below (their water edges are the same row, so the
        # seam is invisible); the camera eases down one frame height, motion blur follows its speed
        u = (t - a) / (b - a)
        strip = np.concatenate([scene(t), mirror(t)], axis=0)
        e = u * u * u * (u * (6 * u - 15) + 10)  # smootherstep
        speed = 30 * u * u * (1 - u) * (1 - u)  # its derivative, peak 1.875
        y0 = int(round(H * e))
        f = strip[y0:y0 + H].copy()
        blur = int(1 + 90 * speed / 1.875)
        if blur > 1:
            f = cv2.blur(f, (1, blur))
        # the camera passes through the water surface: ripple strongest mid-move
        hh, ww = f.shape[:2]
        yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
        amp = 10 * speed / 1.875
        f = cv2.remap(f, xx + amp * np.sin(yy * 0.035 + t * 9), yy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    bars = int(H * 0.075)
    f[:bars] = np.array(L.INK, np.float32) * 0.6
    f[-bars:] = np.array(L.INK, np.float32) * 0.6
    return L.finish(f, int(t * FPS), bloom_k=0.12, chroma_px=1.4, vig=0.38)


def render_range(args):
    i0, i1, path = args
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt",
                          "yuv420p", path], stdin=subprocess.PIPE)
    for i in range(i0, i1):
        p.stdin.write((np.clip(frame(T0 + i / FPS), 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
    p.stdin.close()
    p.wait()
    return path


def main():
    if sys.argv[1] == "preview":
        ts = [float(x) for x in sys.argv[2:sys.argv.index("--out")]]
        tiles = [Image.fromarray((frame(t) * 255).astype(np.uint8)).resize((640, 360)) for t in ts]
        sheet = Image.new("RGB", (640 * 3, 360 * ((len(tiles) + 2) // 3)))
        for j, tl in enumerate(tiles):
            sheet.paste(tl, ((j % 3) * 640, (j // 3) * 360))
        sheet.save(sys.argv[-1], quality=90)
        return
    out = Path(sys.argv[2])
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    total = int((T1 - T0) * FPS)
    parts = [(total * k // n, total * (k + 1) // n, str(out.with_suffix(f".part{k}.mp4"))) for k in range(n)]
    with Pool(n) as pool:
        paths = pool.map(render_range, parts)
    lst = out.with_suffix(".txt")
    lst.write_text("".join(f"file '{Path(p).resolve()}'\n" for p in paths))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-ss", str(T0),
                    "-t", str(T1 - T0), "-i", str(HERE.parent / "audio/t2_optimized_full.mp3"), "-map", "0:v", "-map",
                    "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)], check=True)
    for p in paths:
        Path(p).unlink()
    lst.unlink()
    print("saved", out)


if __name__ == "__main__":
    main()
