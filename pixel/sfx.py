"""Sound-effect and ambience track for the stream PV, mixed UNDER the song (the song itself is never altered).

Benchmark: the official Muse Dash trailer's audio, measured at hits (docs/rhythm_game_style_reference.md): a hit
adds a sharp mid "snap" (500-2000 Hz rises x2-2.6) plus some top sparkle, sometimes a low thump. So every strike
here is a short punch body + a bright tick + a glass sparkle on PERFECT, with +-5 % pitch variation per hit.

Sources: Kenney "Impact Sounds" and "Interface Sounds" (CC0, audio/sfx/kenney/, licence files alongside); whooshes,
risers, the climb drone and heartbeat are synthesized here (no samples).

Cues (song time, from pixel/stream.py): ground / air strikes, saw jumps (whoosh + PASS chime), misses, note and
heart pickups, hold note (shimmer + release bell), pause menu, ノーカン paw wipes, Fever start (riser + bell
crash), the climb (116.6-124.6 s: low drone, heartbeat lub-dub on every beat, a riser into "こっからが本番"),
stage clear, the monitor push-in / pull-out whooshes and the PC shutdown.
"""
import math
import random
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent.parent
KEN = ROOT / "audio" / "sfx" / "kenney"
SR = 48000


@lru_cache(None)
def sample(name):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(KEN / f"{name}.ogg"), "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.float32).copy()
    return a / max(1e-6, np.abs(a).max())


def pitched(a, ratio):
    if abs(ratio - 1) < 1e-3:
        return a
    n = int(len(a) / ratio)
    return np.interp(np.arange(n) * ratio, np.arange(len(a)), a).astype(np.float32)


def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR)).astype(np.float32)


def lowpass(a, fc):
    k = 1 - math.exp(-2 * math.pi * fc / SR)
    out = np.empty_like(a)
    y = 0.0
    for i, x in enumerate(a):
        y += k * (x - y)
        out[i] = y
    return out


def _lp_fast(a, fc):
    """One-pole low-pass via IIR in numpy (scipy.signal.lfilter)."""
    from scipy.signal import lfilter
    k = 1 - math.exp(-2 * math.pi * fc / SR)
    return lfilter([k], [1, -(1 - k)], a).astype(np.float32)


def _bp(a, lo, hi):
    from scipy.signal import butter, sosfilt
    sos = butter(2, [lo, hi], btype="band", fs=SR, output="sos")
    return sosfilt(sos, a).astype(np.float32)


@lru_cache(None)
def whoosh(dur=0.32, lo=500, hi=4500, seed=1):
    """Filtered-noise swoosh: band sweeps up, swell then fade."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    x = rng.standard_normal(n).astype(np.float32)
    out = np.zeros(n, np.float32)
    seg = n // 8
    for i in range(8):                                          # stepped band sweep, cross-faded
        f0 = lo * (hi / lo) ** (i / 8)
        part = _bp(x, f0, min(SR / 2 - 100, f0 * 2.2))
        w = np.zeros(n, np.float32)
        a, b = max(0, (i - 1) * seg), min(n, (i + 2) * seg)
        w[a:b] = np.hanning(b - a)
        out += part * w
    shape = np.sin(np.linspace(0, math.pi, n)) ** 1.5
    return (out / max(1e-6, np.abs(out).max()) * shape).astype(np.float32)


@lru_cache(None)
def riser(dur, seed=2):
    """Tension riser: noise band sweeping up + a rising sine, growing louder, cut at the end."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = rng.standard_normal(n).astype(np.float32)
    out = np.zeros(n, np.float32)
    seg = n // 12
    for i in range(12):
        f0 = 200 * (6000 / 200) ** (i / 12)
        part = _bp(x, f0, min(SR / 2 - 100, f0 * 1.8))
        w = np.zeros(n, np.float32)
        a, b = max(0, (i - 1) * seg), min(n, (i + 2) * seg)
        w[a:b] = np.hanning(b - a)
        out += part * w
    out /= max(1e-6, np.abs(out).max())
    f = 110 * (880 / 110) ** (t / dur)
    tone = np.sin(2 * math.pi * np.cumsum(f) / SR).astype(np.float32) * 0.35
    g = (t / dur) ** 2.2
    return ((out * 0.8 + tone) * g).astype(np.float32)


@lru_cache(None)
def heart_thump(strength=1.0):
    """One heartbeat thump: a 50 Hz sine with a fast pitch drop and a soft click on top."""
    n = int(0.28 * SR)
    t = np.arange(n) / SR
    f = 46 + 40 * np.exp(-t / 0.03)
    body = np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t / 0.08)
    click = np.random.default_rng(3).standard_normal(n) * np.exp(-t / 0.004) * 0.15
    return ((body + _lp_fast(click.astype(np.float32), 900)) * strength).astype(np.float32)


@lru_cache(None)
def drone(dur, seed=4):
    """Low uneasy drone: detuned sub sines beating slowly + a dark noise bed, slow swell."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = (np.sin(2 * math.pi * 41.2 * t) + 0.8 * np.sin(2 * math.pi * 41.9 * t)
         + 0.5 * np.sin(2 * math.pi * 61.7 * t + 0.4 * np.sin(2 * math.pi * 0.21 * t))
         + 0.25 * np.sin(2 * math.pi * 87.3 * t))
    nb = _lp_fast(np.random.default_rng(seed).standard_normal(n).astype(np.float32), 220) * 2.5
    out = (s / 2.6 + nb).astype(np.float32)
    fade = np.minimum(1, t / 1.2) * np.minimum(1, (dur - t) / 0.25)
    return (out * fade).astype(np.float32)


@lru_cache(None)
def shimmer(dur, seed=5):
    """Held-note shimmer: soft bright partials with tremolo."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = sum(np.sin(2 * math.pi * f * t) * a for f, a in ((1568, 0.5), (2093, 0.35), (2637, 0.25), (3136, 0.15)))
    trem = 0.7 + 0.3 * np.sin(2 * math.pi * 9 * t)
    fade = np.minimum(1, t / 0.08) * np.minimum(1, (dur - t) / 0.12)
    return (s * trem * fade).astype(np.float32)


class Track:
    def __init__(self, t0, t1):
        self.t0, self.n = t0, int((t1 - t0) * SR)
        self.a = np.zeros(self.n, np.float32)

    def add(self, t, snd, gain=1.0, ratio=1.0):
        snd = pitched(snd, ratio) * gain
        i = int(round((t - self.t0) * SR))
        a, b = max(0, i), min(self.n, i + len(snd))
        if b > a:
            self.a[a:b] += snd[a - i:b - i]


def build(t0, t1, ST):
    """Return the SFX / ambience track (float32, mono, 48 kHz) for song time t0..t1; ST = the stream module."""
    tr = Track(t0, t1)
    rng = random.Random(42)
    gt_inv = {}

    def song_t(g):
        """Chart times are song times (the game clock only freezes inside the pause, where no notes fall)."""
        return g

    def jit():
        return 1 + rng.uniform(-0.05, 0.05)

    for tt, kind in ST.chart():
        st = song_t(tt)
        if kind in ("g", "a"):
            body = sample(rng.choice(["impactPunch_medium_000", "impactPunch_medium_001", "impactPunch_medium_002"]))
            tr.add(st, body, 0.55, jit() * (1.0 if kind == "g" else 1.18))
            tr.add(st, sample(rng.choice(["click_002", "click_003"])), 0.40, jit() * 1.25)    # mid snap
            tr.add(st + 0.005, sample(rng.choice(["impactGlass_light_000", "impactGlass_light_001",
                                                  "impactGlass_light_002"])), 0.16, jit() * 1.3)   # sparkle
            if kind == "a":
                tr.add(st - 0.12, whoosh(0.18, 900, 6000, 7), 0.10)
        elif kind == "gear":
            tr.add(st - 0.24, whoosh(0.34, 400, 3500, 3), 0.20)                             # jump over the saw
            tr.add(st + 0.03, sample("pluck_001"), 0.22, jit() * 1.5)                       # PASS chime
            tr.add(st + 0.24, sample("impactSoft_heavy_000"), 0.16, jit() * 1.2)            # landing
        elif kind in ("gear_miss", "a_miss"):
            tr.add(st, sample("impactPunch_heavy_000"), 0.55, 0.85)
            tr.add(st + 0.02, sample("error_004"), 0.30, 0.9)
        elif kind == "note":
            tr.add(st, sample("pluck_002"), 0.24, jit() * 1.6)
        elif kind == "heart":
            tr.add(st, sample("confirmation_001"), 0.30)
    h0, h1 = song_t(ST.HOLD[0]), song_t(ST.HOLD[1])                 # hold note
    tr.add(h0, sample("impactBell_heavy_000"), 0.18, 1.5)
    tr.add(h0, shimmer(h1 - h0), 0.10)
    tr.add(h1, sample("impactBell_heavy_001"), 0.26, 1.3)
    tr.add(h1, sample("impactGlass_light_001"), 0.2, 1.2)
    # pause menu, ノーカン paw wipes
    tr.add(ST.PAUSE[0], sample("open_001"), 0.35)
    tr.add(ST.PAUSE[1] - 0.15, sample("close_001"), 0.35)
    for a in (46.66, 62.6):
        tr.add(a - 0.4, whoosh(0.3, 700, 5000, 9), 0.14)
        tr.add(a, sample("drop_001"), 0.3, 1.2)
    # climb: drone + heartbeat on every beat + riser into Fever
    c0, c1 = 116.55, ST.FEVER_T
    tr.add(c0, drone(c1 - c0 + 0.3), 0.14)
    k0, k1 = math.ceil(ST.beat_of(c0)), math.floor(ST.beat_of(c1 - 0.05))
    for k in range(k0, k1 + 1):
        tb = ST.beat_t(k)
        u = (tb - c0) / (c1 - c0)
        tr.add(tb, heart_thump(), 0.22 + 0.16 * u)
        tr.add(tb + 0.18 * ST.BEAT, heart_thump(0.6), 0.22 + 0.16 * u)
    tr.add(c1 - 2.4, riser(2.4), 0.22)
    # Fever start
    tr.add(ST.FEVER_T, sample("impactBell_heavy_000"), 0.30, 0.9)
    tr.add(ST.FEVER_T, sample("impactPunch_heavy_001"), 0.30, 0.8)
    tr.add(ST.FEVER_T, whoosh(0.5, 300, 8000, 11), 0.22)
    # stage clear
    tr.add(ST.CLEAR_T, sample("confirmation_002"), 0.38)
    tr.add(ST.CLEAR_T + 0.12, sample("impactBell_heavy_001"), 0.2, 1.6)
    # monitor push-in / pull-out, PC shutdown
    tr.add(10.6, whoosh(1.3, 200, 3000, 12), 0.16)
    tr.add(ST.GAME_OUT, whoosh(0.9, 3000, 300, 13)[::-1].copy(), 0.14)
    tr.add(169.6, whoosh(0.8, 200, 3000, 14), 0.14)
    tr.add(ST.SHUT_T + 0.2, sample("maximize_006"), 0.22, 0.8)
    off = ST.SHUT_T + (ST.DUR - ST.SHUT_T - 1.3)
    tr.add(off, sample("bong_001"), 0.22, 0.7)
    return tr.a
