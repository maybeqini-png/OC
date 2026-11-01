"""XIYIN's in-game avatar for the v3 PV: a pixel chibi in true side view, facing right and looking where she runs
(the VTuber, not the avatar, is the one who looks at the viewer).

Run cycle: the upper body of the side-view master (sprites4/a01_run_9803) on the two-bone IK legs of legs.py
(knees bend forward, the legs alternate, the planted foot keeps pace with the ground). One stride per beat.
Attack / hurt frames are separate side-view drawings snapped to the same palette (sprites4/), shown briefly as in
Muse Dash, where the strike frames follow the chart.
"""
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

import legs

HERE = Path(__file__).parent
BEAT = 60 / 136
N_PHASE = 12
PAD = 24
CFG = legs.SIDE
BODY_CUT = 140                    # rows above this belong to the body (sweater, shorts, tail)
FAR_LEG_X = 52                    # left of this, rows >= 133 are the master's far leg (redrawn by the rig)
STANCE_SPEED = 203.0 * CFG["STRIDE"]
_FEET = {}


def _padded(im):
    c = Image.new("RGBA", (im.width + 2 * PAD, im.height + 2 * PAD), (0, 0, 0, 0))
    c.paste(im, (PAD, PAD))
    return c


@lru_cache(None)
def master():
    return Image.open(HERE / CFG["master"]).convert("RGBA")


@lru_cache(None)
def body_layer():
    a = np.asarray(master()).copy()
    H, W = a.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    keep = (yy < BODY_CUT) & ~((yy >= 133) & (xx < FAR_LEG_X))
    a[~keep] = 0
    return _padded(Image.fromarray(a, "RGBA"))


def feet_line():
    return int(CFG["GROUND_TOP"] + 31 + 1 + PAD)


def feet_of(im):
    return _FEET[id(im)][1] if id(im) in _FEET else grounded(im)


def grounded(im):
    a = np.asarray(im)[..., 3]
    rows = np.nonzero(a.any(1))[0]
    return int(rows.max()) + 1


def _register(im, feet):
    _FEET[id(im)] = (im, feet)
    return im


def flutter(im, phase, zone=(0, 30, 52, 128)):
    """1 px travelling wave on the trailing hair and tail."""
    a = np.asarray(im).copy()
    x0, y0, x1, y1 = (v + PAD for v in zone)
    for y in range(y0, y1):
        s = int(round(1.2 * math.sin(2 * math.pi * phase + (y - y0) / 9)))
        if s:
            row = a[y, x0:x1].copy()
            sh = np.roll(row, s, axis=0)
            if s > 0:
                sh[:s] = row[:s]
            else:
                sh[s:] = row[s:]
            a[y, x0:x1] = sh
    return Image.fromarray(a, "RGBA")


@lru_cache(None)
def run_frame(i, stride=1.0):
    """Feet row = the planted boot's lowest pixel (a rotated boot's sole height varies with the shin angle);
    in the two short flight phases the sprite rides 2 px above that."""
    phase = i / N_PHASE
    body = body_layer()
    lg, bob = legs.legs_frame(phase, (body.height, body.width), PAD, stride, CFG)
    out = Image.fromarray(lg, "RGBA")
    out.alpha_composite(flutter(body, phase), (0, int(round(bob))))
    flight = 0.38 <= phase < 0.5 or 0.88 <= phase < 1.0
    return _register(out, grounded(out) + (2 if flight else 0))


def run_at(t, speed=STANCE_SPEED):
    i = int((t / BEAT) * N_PHASE) % N_PHASE
    stride = min(1.25, max(0.6, round(speed / STANCE_SPEED * 10) / 10))
    return run_frame(i, stride)


@lru_cache(None)
def jump_frame(kind="up"):
    """Rigged jump: knees tucked (up) or legs reaching down for the landing (down)."""
    body = body_layer()
    if kind == "up":
        lg = legs.tucked_legs((body.height, body.width), PAD, CFG, near=(8, -24), far_=(-12, -20))
    else:
        lg = legs.tucked_legs((body.height, body.width), PAD, CFG, near=(10, -6), far_=(-10, -12))
    out = Image.fromarray(lg, "RGBA")
    out.alpha_composite(body, (0, -2))
    return _register(out, feet_line())


@lru_cache(None)
def frame(name):
    """A whole side-view drawing (attack / hurt), padded like the rig, feet on its lowest row."""
    im = _padded(Image.open(HERE / "sprites4" / f"{name}.png").convert("RGBA"))
    return _register(im, grounded(im))


POSES = {"punch": "a02_punch_9811", "air": "a03_airswipe_9821", "hurt": "a04_hurt_9831"}


def pose(kind):
    return frame(POSES[kind])


if __name__ == "__main__":
    import sys
    fr = [run_frame(i) for i in range(0, 12, 2)] + [jump_frame("up"), jump_frame("down")]
    w, h = fr[0].width, fr[0].height
    S = Image.new("RGBA", (w * len(fr), h), (235, 238, 250, 255))
    for k, f in enumerate(fr):
        S.alpha_composite(f, (k * w, 0))
    from PIL import ImageDraw
    ImageDraw.Draw(S).line([0, feet_line(), S.width, feet_line()], fill=(255, 120, 120))
    S.resize((S.width * 2, S.height * 2), Image.Resampling.NEAREST).save(sys.argv[1])
