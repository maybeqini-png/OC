"""v4.1 block 64.40-84.60 s, rebuilt without generated pixels (owner review: H3 footage and plates still read as AI;
timing not on the lyrics; editing/story weak).

- Character: the owner's sheet itself, animated by pv4/sheet_puppet.py (one displacement field, no layer seams),
  acted pose-to-pose: every pose change lands ON a sung mora (anticipation 2 frames, move, overshoot, settle),
  drawings on 2s, mouth flaps (closed / half / open) from the separated vocal, natural blinks.
- Backgrounds: designed in code (pv4/bg_design.py): cel-painted clouds, crisp moon, drawn water strokes on 3s.
- Timing: mora onsets from pv4/syllables.py (checked on the vocal spectrogram), lyric glyphs appear on their mora,
  every cut is on a mora onset.
- Story ("cool her vs real her"): she teases (stage colours) -> boop -> insists -> night sea: "look at me" ->
  above the water the smug bluff, in the reflection her honest face -> the frame turns over into the reflection
  world (light) -> she sings with her own voice -> white.

usage: block_64b.py preview <t...> --out sheet.jpg | render <out.mp4> [workers]
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
import bg_design as BG  # noqa: E402
import look as L  # noqa: E402
from sheet_puppet import Performance, Puppet  # noqa: E402

W, H, FPS = L.W, L.H, 24
T0, T1 = 64.40, 84.60
LY = json.load(open(HERE / "lyrics_block64.json"))
BEATS = np.array(json.load(open(HERE.parent / "pv/assets/timing.json"))["beats"])
PERF = Performance(BEATS, seed=5, t0=60, t1=90)


def mora(line, phrase):
    return [m["t"] for m in LY[line]["phrases"][phrase]["morae"]]


def chars(line, phrase):
    return LY[line]["phrases"][phrase]["chars"]


M_WARA, M_ME, M_MOU = mora(0, 0), mora(0, 1), mora(0, 2)
M_YOSO, M_MITE = mora(1, 0), mora(1, 1)
M_TSUYO, M_HONKI = mora(2, 0), mora(2, 1)
M_KONO, M_KIME = mora(3, 0), mora(3, 1)
VOICE_END = LY[3]["phrases"][1]["end"]

CUTS = [64.40, M_ME[0], M_MOU[0], M_MOU[2], M_MOU[5], M_YOSO[0], M_MITE[0], M_TSUYO[0], M_HONKI[0], 76.50, M_KIME[0]]
FLIP = (76.40, 76.62)
WHITE_OUT = (68.36, M_YOSO[0])
BLOOM_OUT = (VOICE_END + 0.05, 84.45)


# ---------------- puppets (built once per process) ----------------
@lru_cache(maxsize=None)
def puppet(kind):
    return {"bust": lambda: Puppet((300, 40, 730, 520), 2.25),
            "ecu": lambda: Puppet((395, 195, 625, 300), 8.3),
            "waist": lambda: Puppet((270, 40, 740, 800), 1.42),
            "full_s": lambda: Puppet((250, 10, 770, 1500), 0.43),
            "full_m": lambda: Puppet((250, 10, 770, 1500), 0.56)}[kind]()


@lru_cache(maxsize=1)
def vocal_env():
    import librosa
    y, sr = librosa.load(str(HERE / ".cache/vocals.wav"), sr=22050, mono=True, offset=T0 - 1, duration=T1 - T0 + 2)
    hop = int(sr / FPS)
    rms = np.array([np.sqrt(np.mean(y[i:i + hop] ** 2) + 1e-12) for i in range(0, len(y) - hop, hop)])
    db = 20 * np.log10(rms + 1e-6)
    e = np.clip((db - (db.max() - 30)) / 24, 0, 1)
    return e, T0 - 1


def env_at(t):
    e, t0 = vocal_env()
    i = int(round((t - t0) * FPS))
    return float(e[min(max(i, 0), len(e) - 1)])


def on2s(t):
    return float(np.floor(t * FPS / 2) * 2 / FPS)


# ---------------- acting ----------------
def snap(t, keys, base=0.0, lead=0.21, settle=0.25, antic=0.15, over=0.10):
    """Pose-to-pose value: each (t_hit, v) is reached exactly at t_hit (the mora), with a 2-frame anticipation,
    an ease-out move with a small overshoot, and a settle. Holds between keys."""
    v = base
    for th, v1 in keys:
        if t < th - lead:
            break
        v0, d = v, v1 - v
        a = th - lead
        if t < a + 0.08:
            u = (t - a) / 0.08
            v = v0 - antic * d * np.sin(np.pi / 2 * u)
        elif t < th:
            u = (t - a - 0.08) / (lead - 0.08)
            e = 1 - (1 - u) ** 3
            v = (v0 - antic * d) + (v1 + over * d - (v0 - antic * d)) * e
        elif t < th + settle:
            u = (t - th) / settle
            v = v1 + over * d * (1 - u) ** 2
        else:
            v = v1
    return v


def twitch(t, hits, amp=10.0):
    v = 0.0
    for h in hits:
        u = t - h
        if 0 <= u < 0.5:
            v += amp * np.exp(-u / 0.1) * np.cos(u * 30)
    return v


def mouth(t, smile=0.0):
    e = env_at(t)
    o = 0.0 if e < 0.30 else 0.35 if e < 0.62 else 0.68
    return dict(mouth_open=o, mouth_form=smile)


def act(t, keys, ears=(), energy=0.6, mouth_on=True, smile=0.0, eye_keys=None, extra=None):
    """Full parameter set at drawing time t (already on 2s)."""
    p = PERF.idle(t, energy)
    for k, ks in keys.items():
        p[k] = p.get(k, 0.0) + snap(t, ks)
    p["hair_lag"] = p.get("hair_lag", 0.0) + snap(t - 0.12, keys.get("tilt", []))  # hair follows a beat late
    blink = PERF.eye(t)
    for side in ("eye_l", "eye_r"):
        target = snap(t, eye_keys.get(side, []), base=1.0, antic=0.0, over=0.0, lead=0.09) if eye_keys else 1.0
        p[side] = min(blink, target)
    p["ear_l"] = twitch(t, ears)
    p["ear_r"] = twitch(t - 0.04, ears) * 0.7
    if mouth_on:
        p.update(mouth(t, smile))
    if extra:
        p.update(extra)
    return p


# ---------------- type ----------------
@lru_cache(maxsize=64)
def glyph(ch, face, size, color):
    return L.bbox_trim(L.type_rgba(ch, face, size, fill=color), pad=2)


def vtype(f, text, times, t, x, y, size, color, face="mincho", out_t=None, ripple=False, alpha=1.0):
    """Vertical line, each glyph appears ON its sung time: 2-frame fade + 10 px rise, then holds."""
    adv = size * 1.26
    for k, (ch, ct) in enumerate(zip(text, times)):
        u = (t - ct) / (2 / FPS)
        if u < 0:
            continue
        a = min(u, 1.0) * alpha * (np.clip((out_t - t) / 0.2, 0, 1) if out_t else 1.0)
        if a <= 0:
            continue
        g = glyph(ch, face, size, color)
        if ripple:
            hh, ww = g.shape[:2]
            yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
            g = cv2.remap(g, xx + 2.0 * np.sin(yy * 0.09 + on2s(t) * 5), yy, cv2.INTER_LINEAR)
        L.over(f, g, int(x - g.shape[1] / 2), int(y + k * adv + 10 * (1 - min(u, 1.0))), a)
    return f


def wall(f, text, times, t, x, y, size, color, step=None):
    """Hook-word wall: each kana slams in on its mora (1.18 -> 1.0 over 3 frames)."""
    fnt = L.font("heavy", size)
    cx = x
    for ch, ct in zip(text, times):
        wch = fnt.getlength(ch)
        u = (t - ct) * FPS / 3
        if u >= 0:
            g = glyph(ch, "heavy", size, color)
            s = 1.0 + 0.18 * max(1 - u, 0)
            L.put(f, g, cx + wch / 2, y, scale=s)
        cx += wch * (step or 0.96)
    return f


# ---------------- character placement ----------------
def place(f, rgba, cx, bottom=None, top=None, cy=None, alpha=1.0):
    h, w = rgba.shape[:2]
    if bottom is not None:
        y = int(bottom - h)
    elif top is not None:
        y = int(top)
    else:
        y = int(cy - h / 2)
    return L.over(f, rgba, int(cx - w / 2), y, alpha)


def night_light(rgba, rim_dir=(-1.0, -0.25)):
    return L.relight(rgba, ambient=L.NAVY, amb_k=0.34, key=0.86, rim_dir=rim_dir, rim_color=L.MOON, rim_k=0.75, rim_px=3)


def day_light(rgba):
    return L.relight(rgba, ambient=(0.7, 0.8, 1.0), amb_k=0.08, key=1.0, rim_dir=(0.0, -1.0), rim_color=(1, 1, 1),
                     rim_k=0.55, rim_px=3)


def camera(f, z, cx=0.5, cy=0.5):
    M = np.float32([[z, 0, W * cx * (1 - z)], [0, z, H * cy * (1 - z)]])
    return cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def ease(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * u * (u * (6 * u - 15) + 10)


# ---------------- shots ----------------
def s1_waratta(t):
    """Stage colours: tease close-up on the right two thirds, the hook word slams in behind her, mora by mora."""
    tq = on2s(t)
    f = np.empty((H, W, 3), np.float32)
    f[:] = L.CORAL
    cv2.circle(f, (int(W * 0.66), int(H * 0.40)), int(H * 0.46), (1.0, 0.62, 0.67), -1, cv2.LINE_AA)
    c = chars(0, 0)
    wall(f, "笑った", c[0:3], t, W * 0.03, H * 0.30, 215, L.WHITE)
    wall(f, "でしょ", c[3:6], t, W * 0.06, H * 0.62, 215, L.WHITE)
    w = M_WARA
    p = act(tq, {"tilt": [(w[1], 5.0), (w[4], 2.0), (w[5], 6.5)], "turn": [(w[5], 0.55)], "nod": [(w[4], 3.0)]},
            ears=[w[1], w[5]], eye_keys={"eye_l": [(w[4], 0.55)], "eye_r": [(w[4], 0.55)]}, smile=0.3)
    rgba = puppet("bust").render(p)
    place(f, rgba, W * 0.66, bottom=H + 4)
    z = 1.0 + 0.05 * ease((t - 64.40) / (M_ME[0] - 64.40))
    return camera(f, z, 0.66, 0.42)


def s2_me(t):
    """めっ: eye strip, wink on the っ, white flash on the hit."""
    tq = on2s(t)
    f = np.empty((H, W, 3), np.float32)
    f[:] = L.CORAL
    p = act(tq, {}, eye_keys={"eye_l": [(M_ME[1], 0.0)]}, mouth_on=False, energy=0.2)
    rgba = puppet("ecu").render(p)
    band = (int(H * 0.21), int(H * 0.79))
    strip = np.zeros((band[1] - band[0], W, 3), np.float32)
    strip[:] = L.WHITE
    L.over(strip, rgba, int(W / 2 - rgba.shape[1] / 2), int(strip.shape[0] / 2 - rgba.shape[0] * 0.48))
    f[band[0]:band[1]] = strip
    u = (t - M_ME[0]) * FPS / 3
    g = L.type_rgba("めっ", "heavy", 210, fill=L.CORAL, stroke=L.WHITE, stroke_w=10)
    L.put(f, g, W * 0.80, H * 0.78, scale=1.0 + 0.25 * max(1 - u, 0), angle=-8)
    if t - M_ME[0] < 2 / FPS:
        f = f * 0.35 + 0.65
    return f


def s3_mouikkai(t):
    """もういっかい: three punch-ins, one per mora group, the colour field flips with each cut."""
    tq = on2s(t)
    m = M_MOU
    k = 0 if t < m[2] else 1 if t < m[5] else 2
    cols = [L.SKY, L.WHITE, L.CORAL]
    f = np.empty((H, W, 3), np.float32)
    f[:] = cols[k]
    p = act(tq, {"tilt": [(m[0], -4.0), (m[2], 3.0), (m[5], 6.0)], "nod": [(m[4], 2.5)]}, ears=[m[2], m[5]],
            smile=0.85, extra={"blush": 0.35 + 0.3 * (k == 2), "eye_smile": 1.0 if t >= m[5] + 0.1 else 0.0})
    rgba = puppet("bust").render(p)
    zooms = [0.86, 1.08, 1.42]
    if zooms[k] != 1.0:
        rgba = cv2.resize(rgba, None, fx=zooms[k], fy=zooms[k], interpolation=cv2.INTER_AREA if zooms[k] < 1 else cv2.INTER_CUBIC)
    cxs = [W * 0.60, W * 0.38, W * 0.52]
    place(f, rgba, cxs[k], cy=H * (0.56 if k < 2 else 0.62))
    txt = "もういっかい"
    shown = 2 if k == 0 else 4 if k == 1 else 6
    lab = L.type_rgba(txt[:shown], "heavy", 92, fill=L.NAVY if k != 2 else L.WHITE)
    L.over(f, lab, int(W * (0.07 if k != 1 else 0.62)), int(H * 0.80))
    if WHITE_OUT[0] <= t:
        v = (t - WHITE_OUT[0]) / (WHITE_OUT[1] - WHITE_OUT[0])
        f = f * (1 - ease(v)) + ease(v)
    return f


@lru_cache(maxsize=2)
def tall_night():
    base, hy, moon = BG.sea_static(0.72, (0.30, 0.58), 0.16, W, 1620, "night")
    return base, hy, moon


def s4_yosomi(t):
    """Night sea: the camera tilts down from the stars and the moon to her (lands on み), ripples on each mora."""
    tq = on2s(t)
    base, hy, moon = tall_night()
    f = base.copy()
    BG.stars(f, t, y_max=int(hy * 0.7))
    BG.moon_road(f, t, hy, moon)
    feet = (int(W * 0.66), 1480)
    BG.ripples(f, t, feet[0], feet[1] + 4, M_YOSO, rx0=30, grow=420, squash=0.14)
    y = M_YOSO
    p = act(tq, {"tilt": [(y[2], -3.0), (y[5], 2.5)], "look_y": [(y[2], 0.4)]}, ears=[y[4]], energy=0.5, smile=0.2)
    pp = puppet("full_s")
    rgba = night_light(pp.render(p))
    feet_v = int(np.where(rgba[..., 3].max(axis=1) > 0.5)[0].max())
    refl = L.reflection(rgba[:int(feet_v) + 2], fade=(0.45, 0.0), blur=1.4, ripple=(2.5, 0.06), t=tq, tint=(0.55, 0.68, 1.0))
    L.over(f, refl, feet[0] - rgba.shape[1] // 2, feet[1] - 1)
    L.contact_glow(f, feet[0], feet[1] + 4, 120, 12, color=L.MOON, k=0.22)
    L.over(f, rgba[:int(feet_v) + 2], feet[0] - rgba.shape[1] // 2, feet[1] - int(feet_v) - 1)
    u = ease((t - y[0]) / (y[2] - y[0]))
    y0 = int(540 * u)
    out = np.ascontiguousarray(f[y0:y0 + H])
    vtype(out, "よそ見しないで", chars(1, 0), t, W * 0.50, H * 0.13, 56, L.WHITE, out_t=M_MITE[0] + 0.1)
    if t < y[0] + 0.25:
        v = (t - y[0]) / 0.25
        out = out * ease(v) + (1 - ease(v))
    return out


@lru_cache(maxsize=2)
def waist_bg():
    base, hy, moon = BG.sea_static(0.80, (0.24, 0.42), 0.22, W, H, "night")
    return base, hy, moon


def s5_mitete(t):
    """Waist-up, she holds our eye; wink + nod + ear twitch on ね."""
    tq = on2s(t)
    base, hy, moon = waist_bg()
    f = base.copy()
    BG.stars(f, t, y_max=int(hy * 0.6))
    BG.moon_road(f, t, hy, moon, width=0.8)
    m = M_MITE
    p = act(tq, {"tilt": [(m[1], 2.0), (m[2], -2.5), (m[4], 4.0)], "nod": [(m[4], 3.5)]}, ears=[m[4]],
            eye_keys={"eye_l": [(m[4], 0.0)]}, energy=0.5, smile=0.35)
    rgba = night_light(puppet("waist").render(p), rim_dir=(-1.0, -0.4))
    place(f, rgba, W * 0.63, bottom=H + 2)
    vtype(f, "見ててよね", chars(1, 1), t, W * 0.41, H * 0.14, 60, L.WHITE)
    return camera(f, 1.0 + 0.03 * ease((t - m[0]) / (M_TSUYO[0] - m[0])), 0.63, 0.4)


@lru_cache(maxsize=2)
def mirror_world(world):
    """Uyuni-like mirror sea on a 2H canvas: sky above the waterline, the same sky mirrored below (darker)."""
    hh = 2 * H
    base, hy, moon = BG.sea_static(0.463, (0.30, 640 / hh), 280 / hh, W, hh, world)
    f = base.copy()
    k = 0.72 if world == "night" else 0.86
    f[hy:2 * hy] = base[:hy][::-1] * k
    f[2 * hy:] = base[0] * k
    cv2.line(f, (0, hy), (W, hy), (0.7, 0.8, 1.0), 1, cv2.LINE_AA)
    return f, hy, moon


def mirror_shot(t, world, real_p, refl_p, fig_cx, puppet_kind="full_m", rings=(), ring_kw=None):
    f, hy, moon = mirror_world(world)
    f = f.copy()
    BG.stars(f, t, y_max=int(hy * 0.8), k=1.0 if world == "night" else 0.35)
    mx, my, r = moon
    pp = puppet(puppet_kind)
    lit = night_light if world == "night" else day_light
    real = lit(pp.render(real_p))
    rows = np.where(real[..., 3].max(axis=1) > 0.5)[0]
    feet_v = int(rows.max()) if len(rows) else int((1500 - 10) * pp.s)  # lowest opaque row = the boot soles
    real = real[:feet_v + 2]
    x0 = int(fig_cx - real.shape[1] / 2)
    refl = lit(pp.render(refl_p))[:feet_v + 2][::-1].copy()  # soles meet their mirror image at the waterline
    hh, ww = refl.shape[:2]
    yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
    refl = cv2.remap(refl, (xx + 2.2 * np.sin(yy * 0.05 + on2s(t) * 3) * (yy / hh)).astype(np.float32), yy, cv2.INTER_LINEAR)
    refl[..., :3] *= np.array((0.78, 0.86, 1.0), np.float32) if world == "night" else np.array((0.9, 0.95, 1.0), np.float32)
    # order: water -> reflection -> rings on the surface -> her (her boots occlude the rings)
    L.over(f, refl, x0, hy - 1, alpha=0.92)
    if len(rings):
        BG.ripples(f, t, fig_cx, hy + 2, list(rings), **(ring_kw or {}))
    L.over(f, real, x0, hy - feet_v - 1)
    return f, hy, moon


def s6_tsuyogari(t):
    """Above the water the bluff, below it the truth: the camera tilts from the smug her down to her reflection,
    whose face is the honest one; it arrives on 本 of 本気だもん."""
    tq = on2s(t)
    ts, hk = M_TSUYO, M_HONKI
    real_p = act(tq, {"tilt": [(ts[1], 3.5), (ts[4], -1.5)], "look_y": [(ts[1], -0.5)]}, ears=[ts[1]], energy=0.45,
                 mouth_on=False)
    real_p.update(mouth(tq) if tq < hk[0] else {})
    refl_p = act(tq + 0.0, {"tilt": [(hk[0], -3.0), (hk[3], -5.0)], "look_y": [(hk[0], 0.6)]}, ears=[hk[2]], energy=0.45,
                 mouth_on=False, extra={"blush": 0.9})
    if tq >= hk[0]:
        refl_p.update(mouth(tq))
    fig_cx = W * 0.62
    f, hy, moon = mirror_shot(t, "night", real_p, refl_p, fig_cx, rings=list(ts) + list(hk),
                              ring_kw=dict(rx0=40, grow=520, squash=0.12))
    # scene acting: on 本 the moonlight swells and reaches the water around the reflection
    sw = np.clip((t - hk[0]) / 0.3, 0, 1) * np.exp(-max(t - hk[0] - 0.3, 0) / 1.5)
    if sw > 0:
        L.contact_glow(f, fig_cx, hy + 380, 260, 420, color=(0.45, 0.6, 1.0), k=0.20 * sw)
    vtype(f, "強がりだって", chars(2, 0), t, W * 0.30, 400, 60, L.INK)
    u = ease((t - ts[1]) / (hk[0] - ts[1])) if t > ts[1] else 0.0
    y0 = int(60 + (H - 60) * u)  # ends with the waterline at the top edge
    out = np.ascontiguousarray(f[y0:y0 + H])
    return out


@lru_cache(maxsize=1)
def night_water():
    """The water seen from above: the night sky mirrored (darker), with the moon's reflection low on the frame."""
    base, hy, moon = BG.sea_static(0.95, (0.74, 0.30), 0.22, W, H, "night")
    f = base[:H][::-1].copy() * 0.7
    return f


def s7_honki(t):
    """本気だもん: cut to her reflection's face, upside down in the water - blushing, honest; the water ripples."""
    tq = on2s(t)
    hk = M_HONKI
    f = night_water().copy()
    BG.stars(f, t, y_max=H, k=0.5)
    p = act(tq, {"tilt": [(hk[0], -3.0), (hk[3], -5.0)], "look_y": [(hk[0], 0.6)]}, ears=[hk[2]], energy=0.45,
            extra={"blush": 0.95})
    rgba = night_light(puppet("bust").render(p), rim_dir=(1.0, 0.3))[::-1].copy()
    hh, ww = rgba.shape[:2]
    yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
    amp = 3.0 + 4.0 * np.exp(-max(t - hk[0], 0) / 0.5)
    rgba = cv2.remap(rgba, (xx + amp * np.sin(yy * 0.035 + tq * 4.0)).astype(np.float32), yy, cv2.INTER_LINEAR)
    rgba[..., :3] *= np.array((0.86, 0.92, 1.0), np.float32)
    place(f, rgba, W * 0.58, top=-4)
    sw = np.clip((t - hk[0]) / 0.3, 0, 1)
    L.contact_glow(f, W * 0.58, H * 0.55, 520, 420, color=(0.45, 0.6, 1.0), k=0.12 * sw)
    BG.ripples(f, t, W * 0.58, H * 0.9, hk, rx0=60, grow=900, squash=0.18)
    vtype(f, "本気だもん", chars(2, 1), t, W * 0.20, H * 0.14, 66, (1.0, 0.6, 0.66), ripple=True)
    return camera(f, 1.0 + 0.04 * ease((t - hk[0]) / (FLIP[0] - hk[0])), 0.58, 0.45)


def s8_konokoe(t):
    """The reflection world, upright and light: she sings この声で; rings spread from her with each mora."""
    tq = on2s(t)
    k = M_KONO
    p = act(tq, {"tilt": [(k[0], -2.0), (k[2], 3.0), (k[4], -1.5)], "look_y": [(k[4], -0.6)]}, ears=[k[2], k[4]],
            energy=0.5, extra={"blush": 0.5})
    refl_p = dict(p)
    fig_cx = W * 0.5
    f, hy, moon = mirror_shot(t, "honest", p, refl_p, fig_cx, rings=k,
                              ring_kw=dict(rx0=40, grow=640, squash=0.12, color=(1.0, 1.0, 1.0)))
    y0 = int(hy - H * 0.82)
    out = np.ascontiguousarray(f[y0:y0 + H])
    vtype(out, "この声で", chars(3, 0), t, W * 0.24, H * 0.12, 64, L.NAVY)
    z = 1.08 - 0.08 * ease((t - 76.50) / (M_KIME[0] - 76.50))
    return camera(out, z, 0.5, 0.55)


@lru_cache(maxsize=1)
def honest_bust_bg():
    base, hy, moon = BG.sea_static(0.86, (0.50, 0.36), 0.30, W, H, "honest")
    return base, hy, moon


def s9_kime(t):
    """Bust in the light world, the moon as her halo; eyes close on the held よ, open with a smile before the end."""
    tq = on2s(t)
    base, hy, moon = honest_bust_bg()
    f = base.copy()
    km = M_KIME
    # rising light motes on 2s during the held note
    rng = np.random.default_rng(9)
    for i in range(40):
        x = rng.uniform(0, W)
        sp = rng.uniform(40, 110)
        y = (rng.uniform(0, H) - sp * (tq - km[0])) % H
        a = 0.5 + 0.5 * rng.random()
        s = rng.uniform(2, 5)
        cv2.circle(f, (int(x), int(y)), int(s), (a, a, a), -1, cv2.LINE_AA)
    p = act(tq, {"tilt": [(km[0], 4.0), (km[2], -2.0), (km[4], 2.0)], "nod": [(km[1], 2.5)], "turn": [(km[2], -0.35)],
                 "look_y": [(km[4], -0.5)]}, ears=[km[0], km[4]], energy=0.5,
            eye_keys={"eye_l": [(km[4] + 0.1, 0.0), (82.70, 1.0)], "eye_r": [(km[4] + 0.1, 0.0), (82.70, 1.0)]},
            extra={"blush": 0.55})
    rgba = day_light(puppet("bust").render(p))
    place(f, rgba, W * 0.5, bottom=H + 4)
    vtype(f, "キメちゃうよ", chars(3, 1), t, W * 0.82, H * 0.12, 64, L.NAVY)
    z = 1.0 + 0.07 * ease((t - km[0]) / (VOICE_END - km[0]))
    f = camera(f, z, 0.5, 0.42)
    if t >= BLOOM_OUT[0]:
        v = ease((t - BLOOM_OUT[0]) / (BLOOM_OUT[1] - BLOOM_OUT[0]))
        f = L.bloom(f, thresh=0.75 - 0.4 * v, k=0.7 * v)
        f = f * (1 - v) + v
    return f


def flip(t):
    """Through the surface: the frame turns over (180 deg) from the night reflection into the light world."""
    u = (t - FLIP[0]) / (FLIP[1] - FLIP[0])
    e = ease(u)
    a = FLIP[0] - 1 / FPS
    src = s7_honki(a) if e < 0.5 else s8_konokoe(FLIP[1])
    ang = 180 * e if e < 0.5 else 180 * (e - 1)
    acc = np.zeros_like(src)
    for dk in (-6, -2, 2, 6):  # rotational motion blur
        M = cv2.getRotationMatrix2D((W / 2, H / 2), ang + dk * (1 - abs(2 * e - 1)), 1.0 + 0.15 * np.sin(np.pi * e))
        acc += cv2.warpAffine(src, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    f = acc / 4
    f = f + 0.35 * np.sin(np.pi * e)
    return f


SHOTS = [(64.40, M_ME[0], s1_waratta), (M_ME[0], M_MOU[0], s2_me), (M_MOU[0], M_YOSO[0], s3_mouikkai),
         (M_YOSO[0], M_MITE[0], s4_yosomi), (M_MITE[0], M_TSUYO[0], s5_mitete), (M_TSUYO[0], M_HONKI[0], s6_tsuyogari), (M_HONKI[0], FLIP[0], s7_honki),
         (FLIP[1], M_KIME[0], s8_konokoe), (M_KIME[0], T1 + 1, s9_kime)]


def frame(i):
    t = i / FPS
    if FLIP[0] <= t < FLIP[1]:
        f = flip(t)
    else:
        f = next(fn for a, b, fn in SHOTS if a <= t < b)(t)
    return L.finish(np.clip(f, 0, 1.4), i, bloom_k=0.06, chroma_px=0, vig=0.18, grain_k=0.010)


def render_range(args):
    i0, i1, path = args
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt",
                          "yuv420p", path], stdin=subprocess.PIPE)
    for i in range(i0, i1):
        p.stdin.write((np.clip(frame(i), 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
    p.stdin.close()
    p.wait()
    return path


def main():
    if sys.argv[1] == "preview":
        ts = [float(x) for x in sys.argv[2:sys.argv.index("--out")]]
        tiles = [Image.fromarray((frame(int(round(t * FPS))) * 255).astype(np.uint8)).resize((640, 360)) for t in ts]
        sheet = Image.new("RGB", (640 * 4, 360 * ((len(tiles) + 3) // 4)))
        for j, tl in enumerate(tiles):
            sheet.paste(tl, ((j % 4) * 640, (j // 4) * 360))
        sheet.save(sys.argv[-1], quality=90)
        return
    out = Path(sys.argv[2])
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    a, b = int(round(T0 * FPS)), int(round(T1 * FPS))
    parts = [(a + (b - a) * k // n, a + (b - a) * (k + 1) // n, str(out.with_suffix(f".part{k}.mp4"))) for k in range(n)]
    with Pool(n) as pool:
        paths = pool.map(render_range, parts)
    lst = out.with_suffix(".txt")
    lst.write_text("".join(f"file '{Path(p).resolve()}'\n" for p in paths))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-ss", str(a / FPS),
                    "-t", str((b - a) / FPS), "-i", str(HERE.parent / "audio/t2_optimized_full.mp3"), "-map", "0:v", "-map",
                    "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)], check=True)
    for p in paths:
        Path(p).unlink()
    lst.unlink()
    print("saved", out)


if __name__ == "__main__":
    main()
