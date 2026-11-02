"""Clean motion for XIYIN's VTuber model v3 (frames from vt3.py), for the stream PV.

Research notes: docs/motion_cleanliness_reference.md. In short:
- Idle motion as in Live2D Cubism's breath controller: offset + peak * sin(2 pi t / cycle) on several parameters
  with non-commensurate cycles (3.2345 s breath, 5.5345 s roll, 15.5345 s body sway), so it never visibly loops.
- Blinks as in CubismEyeBlink: mean interval 4 s (randomised, 0-2x), closing 0.1 s, closed 0.05 s, opening 0.15 s.
- Lip-sync from the sung syllables (lyric timings), three mouth shapes as in anime 口パク (closed / small / open),
  changed on twos (15 per second).
- Expressions switch on a cut with a small pop, never a cross-fade (a cross-fade of two drawings doubles the lines).
- Hair: only the long side strands and the ahoge sway, with the phase lagging down the strand (follow-through);
  face, hand and sleeve stay rigid. One smooth displacement field, so nothing tears.
- No white edges: every pixel that is not fully opaque takes the colour of the nearest fully opaque pixel
  (the cut-out's transparent pixels still hold V5's light-grey background), and all resampling is premultiplied.

usage: python3 vtmotion.py test <t0> <t1> <out.mp4|png> [size]
"""
import math
import random
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import vt3  # noqa: E402

MASTERS = (720, 1100, 1600)       # working resolutions (px for 1024 units); the smallest >= target is used
NEUTRAL_FAMILY = ("neutral",)      # expressions that get lip-sync and blinks


# ---------------------------------------------------------------- clean frames
@lru_cache(None)
def clean2048(name):
    """Straight RGBA float32 at 2048: colour of every not-fully-opaque pixel = nearest fully opaque pixel."""
    m = np.asarray(vt3.model3(name)).astype(np.float32)
    a = m[..., 3] / 255
    inner = a >= 0.995
    _, (iy, ix) = ndimage.distance_transform_edt(~inner, return_indices=True)
    rgb = m[..., :3][iy, ix]
    rgb[inner] = m[..., :3][inner]
    return np.dstack([rgb, a * 255])


def _premul_resize(rgba, size):
    """Straight float RGBA -> premultiplied float RGBA at size (Pillow resizes RGBA premultiplied)."""
    im = Image.fromarray(rgba.clip(0, 255).astype(np.uint8), "RGBA").resize((size, size), Image.Resampling.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    a[..., :3] *= a[..., 3:4] / 255
    return a


@lru_cache(None)
def master(name, res):
    return _premul_resize(clean2048(name), res)


@lru_cache(None)
def region_mask(other, res):
    """Where frame `other` differs from neutral (its eye or mouth region), feathered, at res."""
    d = np.abs(clean2048(other)[..., :3] - clean2048("neutral")[..., :3]).max(-1) > 3
    d = ndimage.binary_dilation(d, iterations=6)
    m = Image.fromarray((d * 255).astype(np.uint8), "L").resize((res, res), Image.Resampling.BILINEAR)
    m = ndimage.gaussian_filter(np.asarray(m).astype(np.float32) / 255, 1.0 * res / 1024)
    return m[..., None]


@lru_cache(maxsize=64)
def face_state(name, eyes_closed, mouth, res):
    """Premultiplied RGBA at res. For the neutral family the eyes (blink) and mouth (talk_a / talk_o) are pasted from
    the frames built on the same body, so the result is exact outside those regions."""
    im = master(name, res).copy()
    if name in NEUTRAL_FAMILY:
        if mouth in ("talk_a", "talk_o"):
            k = region_mask(mouth, res)
            im = im * (1 - k) + master(mouth, res) * k
        if eyes_closed:
            k = region_mask("blink", res)
            im = im * (1 - k) + master("blink", res) * k
    return im


# ---------------------------------------------------------------- motion
def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


@lru_cache(None)
def hair_weights(res):
    """Weights (0-1) of the swaying hair at res: long strands on the viewer-left (x < 390, y > 580 in 1024 units),
    the strands right of the raised sleeve (x > 835, y > 660), and the ahoge (top). Zero on face, hand, sleeve."""
    u = res / 1024
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32) / u
    left = smoothstep((yy - 580) / 260) * smoothstep((390 - xx) / 70)
    right = smoothstep((yy - 660) / 240) * smoothstep((xx - 835) / 40)
    ahoge = smoothstep((205 - yy) / 110) * smoothstep((xx - 290) / 30) * smoothstep((490 - xx) / 30)
    return left, right, ahoge, yy, xx


def motion(t, beat=None):
    """Motion parameters at t (all continuous)."""
    breath = 0.5 + 0.5 * math.sin(2 * math.pi * t / 3.2345)
    roll = 0.40 * math.sin(2 * math.pi * t / 5.5345) + 0.30 * math.sin(2 * math.pi * t / 15.5345 + 0.7)   # degrees
    bob = 0.0
    if beat is not None:                       # a small nod on the beat while she plays
        ph = beat % 1.0
        bob = 2.2 * math.exp(-ph * 5.0) * math.sin(math.pi * min(1.0, ph * 3))
    return breath, roll, bob


def warp(im, t, res, beat=None, pop=1.0):
    """One resample for everything: rotation about the bottom centre (body sway / roll), breath (vertical scale of
    the body), the beat nod, the pop, and the hair displacement. Premultiplied, bilinear."""
    breath, roll, bob = motion(t, beat)
    u = res / 1024
    left, right, ahoge, yy, xx = hair_weights(res)
    px, py = 500 * u, 1024 * u
    th = math.radians(roll)
    sy = (1 + 0.0045 * breath) * pop
    sx = pop
    # inverse map: output (x, y) -> source
    X = xx * u - px
    Y = yy * u - py + (bob + 2.0 * breath) * u
    c, s = math.cos(th), math.sin(th)
    sxr = (c * X - s * Y) / sx
    syr = (s * X + c * Y) / sy
    # hair: horizontal sway, phase lagging down the strand (follow-through)
    wave_l = 5.0 * np.sin(2 * math.pi * t / 3.7 - (yy - 580) / 210)
    wave_r = 3.5 * np.sin(2 * math.pi * t / 3.3 + 1.3 - (yy - 660) / 190)
    wave_a = 4.0 * math.sin(2 * math.pi * t / 2.6 + 0.4) * smoothstep((205 - yy) / 160)
    dx = (left * wave_l + right * wave_r + ahoge * wave_a) * u
    src_x = sxr + px - dx
    src_y = syr + py
    out = np.empty_like(im)
    for ch in range(4):
        out[..., ch] = ndimage.map_coordinates(im[..., ch], [src_y, src_x], order=1, mode="constant", cval=0.0)
    return out


def to_image(pm, size):
    """Premultiplied float -> straight RGBA PIL image at size."""
    a = pm[..., 3:4]
    rgb = np.where(a > 0.5, pm[..., :3] * 255 / np.maximum(a, 1e-3), 0)
    im = Image.fromarray(np.dstack([rgb, a]).clip(0, 255).astype(np.uint8), "RGBA")
    if im.width != size:
        im = im.resize((size, size), Image.Resampling.LANCZOS)
    return im


def render(name, t, size, eyes_closed=False, mouth=None, beat=None, pop=1.0):
    """The model at size x size (1024 units -> size px) at time t."""
    res = next((r for r in MASTERS if r >= size), MASTERS[-1])
    im = face_state(name, eyes_closed, mouth, res)
    return to_image(warp(im, t, res, beat, pop), size)


# ---------------------------------------------------------------- blinks and lip-sync
@lru_cache(None)
def blink_times(t_end=200.0, seed=20261102):
    """Blink start times: CubismEyeBlink's interval (mean 4 s, random 0-2x), at least 1.2 s apart."""
    rnd = random.Random(seed)
    out, t = [], 1.3
    while t < t_end:
        out.append(t)
        t += max(1.2, rnd.random() * 2 * 4.0)
    return out


def eyes_closed_at(t):
    """Closed for the closing + closed part of a blink (0.1 + 0.05 s); with two drawings the opening 0.15 s shows
    the open eye again after one more frame."""
    for b in blink_times():
        if b <= t < b + 0.17:
            return True
        if b > t:
            break
    return False


VOWEL = {}
for row, v in (("あかさたなはまやらわがざだばぱぁゃ", "a"), ("いきしちにひみりぎじぢびぴぃ", "i"),
               ("うくすつぬふむゆるぐずづぶぷぅゅ", "u"), ("えけせてねへめれげぜでべぺぇ", "e"),
               ("おこそとのほもよろをごぞどぼぽぉょ", "o")):
    for ch in row:
        VOWEL[ch] = v
        VOWEL[chr(ord(ch) + 0x60)] = v                 # the katakana of the same row
VOWEL.update({"ん": "n", "ン": "n", "っ": "q", "ッ": "q", "ー": "-", "〜": "-"})


def _vowel(ch):
    if ch in VOWEL:
        return VOWEL[ch]
    return "a" if "一" <= ch <= "鿿" else None      # kanji: an open syllable


@lru_cache(None)
def mouth_track(fps=30):
    """Mouth shape per video frame: None (closed), 'talk_o' (small / round), 'talk_a' (open).
    Built from the lyric syllables, changed on twos; consecutive same-shape syllables get a one-step 'talk_o'
    in between so the syllables read; open and close pass through 'talk_o'."""
    import stage
    n = int(200 * fps)
    tgt = [None] * n
    for ln in stage.lyrics():
        phrases = ln["phrases"]
        for pi, ph in enumerate(phrases):
            end = phrases[pi + 1]["t"] - 0.08 if pi + 1 < len(phrases) else ln["end"]
            sylls = []
            for ch, ct in zip(ph["text"], ph["chars"]):
                v = _vowel(ch)
                if v is None:
                    continue
                if ch in "ゃゅょャュョぁぃぅぇぉ" and sylls and abs(sylls[-1][0] - ct) < 0.05:
                    sylls[-1] = (sylls[-1][0], v)       # small kana: same syllable, its vowel
                    continue
                sylls.append((ct, v))
            for k, (ct, v) in enumerate(sylls):
                nxt = sylls[k + 1][0] if k + 1 < len(sylls) else end
                if v == "-" and k > 0:
                    v = sylls[k - 1][1]
                shape = {"a": "talk_a", "e": "talk_a", "i": "talk_a", "o": "talk_o", "u": "talk_o"}.get(v)
                stop = min(nxt, end)
                for f in range(int(ct * fps), int(stop * fps)):
                    if 0 <= f < n:
                        tgt[f] = (shape, k)
    out = [None] * n
    prev, prev_k = None, None
    f = 0
    while f < n:                                     # on twos
        cur = tgt[f]
        shape, k = cur if cur else (None, None)
        if shape == prev and shape is not None and k != prev_k:
            shape = "talk_o" if shape == "talk_a" else None     # articulate repeated syllables
        elif prev is None and shape == "talk_a":
            shape = "talk_o"                         # open through the small mouth
        elif prev == "talk_a" and shape is None:
            shape = "talk_o"                         # close through the small mouth
        for g in (f, f + 1):
            if g < n:
                out[g] = shape
        prev, prev_k = shape, k
        f += 2
    return out


def mouth_at(t, fps=30):
    tr = mouth_track(fps)
    f = int(t * fps)
    return tr[f] if 0 <= f < len(tr) else None


# ---------------------------------------------------------------- test clip
if __name__ == "__main__" and sys.argv[1] == "test":
    import subprocess
    t0, t1, out = float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
    size = int(sys.argv[5]) if len(sys.argv) > 5 else 720
    bg = (52, 48, 70, 255)
    if out.endswith(".png"):
        im = render("neutral", t0, size, eyes_closed_at(t0), mouth_at(t0))
        c = Image.new("RGBA", im.size, bg)
        c.alpha_composite(im)
        c.convert("RGB").save(out)
    else:
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                              f"{size}x{size}", "-r", "30", "-i", "-", "-ss", str(t0), "-t", str(t1 - t0), "-i",
                              str(HERE.parent / "audio" / "t2_optimized_full.mp3"), "-c:v", "libx264", "-crf", "16",
                              "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", out], stdin=subprocess.PIPE)
        for f in range(int(t0 * 30), int(t1 * 30)):
            t = f / 30
            im = render("neutral", t, size, eyes_closed_at(t), mouth_at(t))
            c = Image.new("RGBA", im.size, bg)
            c.alpha_composite(im)
            p.stdin.write(c.convert("RGB").tobytes())
        p.stdin.close()
        p.wait()
