"""XIYIN sprite animation from one master drawing (character consistency: every gameplay frame comes from the
same pixels, nothing is re-generated).

Run cycle (Muse Dash-like): the upper body is the run-A master above the shorts hem; the legs are drawn by
legs.py as two-bone IK legs (knees bend forward, the legs alternate and pass each other, the planted foot keeps
pace with the ground, boots cut from the master). The hip bobs twice per stride and the trailing hair flutters
by one pixel. A full stride takes one beat; N_PHASE frames per stride are precomputed per stride length.
"""
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

import legs as legs_mod

HERE = Path(__file__).parent
BEAT = 60 / 136
N_PHASE = 12
PAD = 24                                   # canvas margin so swinging legs are not clipped

MASTER = "p02_run_a"
HIP_Y = 126                                # first row of the legs on the master (sprite px)
SPLIT_X = 64                               # back leg x < SPLIT_X, front leg x >= SPLIT_X (below HIP_Y)
PIVOT_BACK = (60, 128)
PIVOT_FRONT = (70, 128)
SWING = 24                                 # degrees, each way
HAIR_ZONE = (0, 40, 46, 120)               # trailing hair that flutters (x0, y0, x1, y1)


@lru_cache(None)
def master(name=MASTER):
    return Image.open(HERE / "sprites3" / f"{name}.png").convert("RGBA")


def rotsprite(part, pivot, deg):
    """Rotate a pixel-art RGBA part about pivot (x, y) with a majority resample, keeping one pixel grid."""
    k = 4
    big = part.resize((part.width * k, part.height * k), Image.Resampling.NEAREST)
    big = big.rotate(deg, resample=Image.Resampling.NEAREST, center=(pivot[0] * k + k / 2, pivot[1] * k + k / 2))
    a = np.asarray(big).reshape(part.height, k, part.width, k, 4).transpose(0, 2, 1, 3, 4).reshape(
        part.height, part.width, k * k, 4)
    out = np.zeros((part.height, part.width, 4), np.uint8)
    opaque = a[..., 3] > 0
    keep = opaque.sum(2) >= (k * k) // 2
    ys, xs = np.nonzero(keep)
    for y, x in zip(ys, xs):
        px = a[y, x][opaque[y, x]]
        cols, cnt = np.unique(px.view(np.uint32).ravel(), return_counts=True)
        out[y, x] = np.frombuffer(np.uint32(cols[cnt.argmax()]).tobytes(), np.uint8)
    return Image.fromarray(out, "RGBA")


def _padded(im):
    c = Image.new("RGBA", (im.width + 2 * PAD, im.height + 2 * PAD), (0, 0, 0, 0))
    c.paste(im, (PAD, PAD))
    return c


@lru_cache(None)
def run_parts():
    m = np.asarray(_padded(master()))
    H, W = m.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    legs = yy >= HIP_Y + PAD
    back = legs & (xx < SPLIT_X + PAD)
    front = legs & (xx >= SPLIT_X + PAD)

    def layer(mask):
        a = m.copy()
        a[~mask] = 0
        return Image.fromarray(a, "RGBA")
    return layer(~legs), layer(back), layer(front)


def flutter(im, phase):
    """Shift rows of the trailing hair by up to 1 px in a travelling wave."""
    a = np.asarray(im).copy()
    x0, y0, x1, y1 = (v + PAD for v in HAIR_ZONE)
    for y in range(y0, y1):
        s = int(round(1.2 * math.sin(2 * math.pi * phase + (y - y0) / 9)))
        if s:
            row = a[y, x0:x1].copy()
            shifted = np.roll(row, s, axis=0)
            if s > 0:                       # keep the original pixels where the shift opens a gap
                shifted[:s] = row[:s]
            else:
                shifted[s:] = row[s:]
            a[y, x0:x1] = shifted
    return Image.fromarray(a, "RGBA")


BODY_CUT = 127                             # body = master rows above the shorts hem; legs are drawn by legs.py
_FEET = {}


def feet_of(im):
    """Feet row of a sprite: fixed ground line for rigged frames, lowest opaque row otherwise."""
    return _FEET[id(im)][1] if id(im) in _FEET else grounded(im)[1]


@lru_cache(None)
def body_layer():
    m = np.asarray(_padded(master())).copy()
    m[BODY_CUT + PAD:] = 0
    return Image.fromarray(m, "RGBA")


def _assemble(legs, bob, phase):
    body = flutter(body_layer(), phase) if phase is not None else body_layer()
    out = Image.fromarray(legs, "RGBA")
    out.alpha_composite(body, (0, int(round(bob))))
    feet = int(legs_mod.GROUND_TOP + 31 + 1 + PAD)
    _FEET[id(out)] = (out, feet)
    return out, feet


STANCE_SPEED = 203.0                       # ground speed (px/s) at which a stride of 1.0 has no foot slide


@lru_cache(None)
def run_frame(i, stride=1.0):
    """Phase frame i of N_PHASE (one stride: both legs step once)."""
    phase = i / N_PHASE
    size = body_layer().size
    legs, bob = legs_mod.legs_frame(phase, (size[1], size[0]), PAD, stride)
    return _assemble(legs, bob, phase)


def grounded(im):
    """(sprite, feet_y): feet_y is the lowest opaque row, so the sprite can stand exactly on the ground."""
    a = np.asarray(im)[..., 3]
    rows = np.nonzero(a.any(1))[0]
    return im, int(rows.max()) + 1


@lru_cache(None)
def jump_frame():
    """Tucked jump from the same master body."""
    size = body_layer().size
    legs = legs_mod.tucked_legs((size[1], size[0]), PAD)
    return _assemble(legs, -2, None)


def run_at(t, speed=STANCE_SPEED):
    """(sprite, feet_y) of the run cycle at song time t (one stride per beat), stride matched to the ground speed."""
    i = int((t / BEAT) * N_PHASE) % N_PHASE
    stride = min(1.25, max(0.6, round(speed / STANCE_SPEED * 10) / 10))
    return run_frame(i, stride)


@lru_cache(None)
def breathe(name, k):
    """Standing pose with the upper body lowered k px (a 1 px idle breath on the beat)."""
    im, feet = pose(name)
    if not k:
        return im
    a = np.asarray(im)
    rows = np.nonzero(a[..., 3].any(1))[0]
    cut = int(rows.min() + (rows.max() - rows.min()) * 0.62)
    out = a.copy()
    out[rows.min() + k:cut + k] = a[rows.min():cut]
    out[rows.min():rows.min() + k] = 0
    im2 = Image.fromarray(out, "RGBA")
    _FEET[id(im2)] = (im2, feet)
    return im2


@lru_cache(None)
def pose(name):
    """Front-facing reaction pose (sprites3), with the same canvas margin, and its feet row."""
    im = Image.open(HERE / "sprites3" / f"{name}.png").convert("RGBA")
    return grounded(_padded(im))


_RIM = {}


def rim(im, colour):
    """1 px light rim outside the silhouette (for dark scenes); cached per sprite object."""
    key = (id(im), colour)
    if key not in _RIM:
        _RIM[key] = (im, _rim(im, colour))
    return _RIM[key][1]


def _rim(im, colour):
    a = np.asarray(im)[..., 3] > 0
    d = a.copy()
    d[1:] |= a[:-1]; d[:-1] |= a[1:]; d[:, 1:] |= a[:, :-1]; d[:, :-1] |= a[:, 1:]
    ring = d & ~a
    out = np.zeros((*a.shape, 4), np.uint8)
    out[ring] = (*colour, 255)
    r = Image.fromarray(out, "RGBA")
    r.alpha_composite(im)
    return r


if __name__ == "__main__":
    frames = [run_frame(i)[0] for i in range(0, N_PHASE, 2)] + [jump_frame()[0]]
    W = sum(f.width for f in frames)
    sheet = Image.new("RGBA", (W, frames[0].height), (235, 238, 250, 255))
    x = 0
    for f in frames:
        sheet.alpha_composite(f, (x, 0)); x += f.width
    sheet.resize((W * 2, sheet.height * 2), Image.Resampling.NEAREST).save(
        "/tmp/claude-0/-home-user/db3ff6df-4ecc-53f0-8344-cdc41c79f92b/scratchpad/ana/run_rig.png")
