"""v4.2 block 64.40-84.60 s: the fal (MiniMax H3) performances, repaired, in the v4.1 edit.

Owner review 2026-10-24 of v4.1 (sheet puppet): the motion is stiff, the blinks break the illusion, it is far behind
video generation + editing -> repair and refine using the clips tested on fal; examine the mouth during singing.
Against v4.0 (H3 composite: AI look, timing off the lyrics, weak story) and v4.1 (puppet):
- acting: each H3 clip plays at its own speed with drawings on 2s (no frame re-ordering for lip-sync, no code blinks,
  no puppet warps); holds are held drawings;
- mouth: pv4/mouth_layer.py times the mouth to the sung morae (vowel shapes, lips shut on m, shut in rests and after
  the phrase, the model's dissolve frames replaced); the body is never re-timed for the mouth;
- scenes: the generated backgrounds are replaced by designed ones (pv4/bg_design.py) laid out like each clip's own
  scene (moon centre and radius, horizon, spotlight), so the rim light already on her stays true. She is cut out with
  the isnet matte (pv4/matte.py), edge colours de-contaminated from the old background, the model's sparkle dots
  removed, the sheet's tail added on full-body shots (pv4/tail.py), her reflection made from her own cut-out;
- timing, type and story from v4.1 (glyphs and cuts on the morae, one lyric layer).

usage: block_64c.py preview <t...> --out sheet.jpg | render <out.mp4> [workers]
needs pv4/.cache: mattes/<clip>_alpha.npz (pv4/matte.py), vocals.wav (tools/separate.py); mouth tracks are built on
first use (pv4/.cache/mouth/).
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
import block_64b as B  # noqa: E402  (v4.1: mora times, type, flip, white-out)
import bg_design as BG  # noqa: E402
import look as L  # noqa: E402
import mouth_layer as ML  # noqa: E402
from tail import TailComp  # noqa: E402

W, H, FPS = L.W, L.H, 24
T0, T1 = 64.40, 84.60
MATTES = HERE / ".cache/mattes"
PLACE = json.load(open(HERE / "h3/frames/placements.json"))
M_WARA, M_ME, M_MOU, M_YOSO, M_MITE = B.M_WARA, B.M_ME, B.M_MOU, B.M_YOSO, B.M_MITE
M_TSUYO, M_HONKI, M_KONO, M_KIME = B.M_TSUYO, B.M_HONKI, B.M_KONO, B.M_KIME
FLIP, WHITE_OUT, BLOOM_OUT = B.FLIP, B.WHITE_OUT, B.BLOOM_OUT

# scene layouts measured on each clip's first frame (output pixels): moon centre + radius, horizon
SEA_P04 = dict(hy=679, moon=(1016, 419, 250))     # h3_p04_yosomi (768P x 1.4286)
SEA_P05 = dict(hy=611, moon=(987, 477, 275))      # h3max_p05d_tsuyogari_nt_1080
SEA_P07 = dict(hy=601, moon=(971, 427, 231))      # h3max_p07e_konokoe_nt_1080


# ---------------- mouth targets for the whole block (drawings on 2s) ----------------
@lru_cache(maxsize=1)
def mouth_plan():
    env, t0 = B.vocal_env()
    tl = ML.Timeline([p for line in B.LY for p in line["phrases"]], env, t0)
    n = int(np.ceil((T1 - T0) * FPS / 2)) + 2
    return tl.plan([T0 + 2 * k / FPS for k in range(n)])


def mouth_at(t):
    return mouth_plan()[max(int((t - T0) * FPS / 2 + 1e-6), 0)]


def on2s(t):
    return B.on2s(t)


def ease(u):
    return B.ease(u)


# ---------------- the performer: a fal clip cut out, repaired ----------------
class Actor:
    def __init__(self, name, donors=(), tail=None):
        self.name = name
        self.fr = ML.frames(name)
        self.al = np.load(MATTES / f"{name}_alpha.npz")["alpha"]
        self.h, self.w = self.fr[0].shape[:2]
        self.k = W / self.w
        self.oy = int(round((self.h * self.k - H) / 2))  # 768P clips are 7:4 -> centre crop to 16:9
        self.mouth = ML.MouthSwap(name, donors)
        self.tc = TailComp(PLACE[tail], self.fr, self.al, scale=self.w / 1920) if tail else None
        self.feet = PLACE[tail]["feet"] * self.w / 1920 if tail else None
        self.cache = {}

    def to_out(self, x, y):
        return x * self.k, y * self.k - self.oy

    def track(self, i):
        dx, dy = self.tc.track[min(i, len(self.tc.track) - 1)] if self.tc else (0.0, 0.0)
        return dx, dy

    def rgba(self, i, want, t_draw):
        key = (i, want, round(t_draw, 3))
        if key in self.cache:
            return self.cache[key]
        i = min(max(i, 0), len(self.fr) - 1)
        bgr, _ = self.mouth.apply(self.fr[i], i, want) if want is not None else (self.fr[i], None)
        f = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255
        a = self.al[min(i, len(self.al) - 1)].astype(np.float32) / 255
        if self.feet is not None:  # the model's own water reflection under her soles is not her
            a[int(self.feet + self.track(i)[1] + 3):] = 0
        a = np.clip((a - 0.12) / 0.76, 0, 1)
        # de-contaminate the edge: estimate the old background behind each edge pixel (normalised blur of the
        # pixels outside her), remove it from the mixed colour
        s = 6.0 * self.w / 1920 + 3
        wbg = 1 - a
        bg = cv2.GaussianBlur(f * wbg[..., None], (0, 0), s) / (cv2.GaussianBlur(wbg, (0, 0), s)[..., None] + 1e-4)
        fg = np.where(a[..., None] > 0.03, (f - (1 - a)[..., None] * bg) / np.maximum(a, 0.05)[..., None], f)
        fg = np.clip(fg, 0, 1)
        # generated sparkle dots over her: small spots much brighter than their surroundings
        u8 = (fg * 255).astype(np.uint8)
        med = cv2.medianBlur(u8, 5)
        lum = u8.astype(np.int16).mean(axis=2) - med.astype(np.int16).mean(axis=2)
        spk = ((lum > 34) & (a > 0.5)).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(spk, 8)
        small = np.isin(lab, [j for j in range(1, n) if st[j, cv2.CC_STAT_AREA] <= 14 * (self.w / 1920) ** 2 + 4])
        fg[small] = med[small].astype(np.float32) / 255
        rgba = np.concatenate([fg * a[..., None], a[..., None]], axis=-1)
        if self.tc is not None:  # the sheet's tail, behind her
            tl = L.swing_tail(self.tc.tail, self.tc.root_local, self.tc.angle(t_draw))
            dx, dy = self.track(i)
            ox = int(round(self.tc.root0[0] + dx - self.tc.root_local[0]))
            oy = int(round(self.tc.root0[1] + dy - self.tc.root_local[1]))
            under = np.zeros_like(rgba)
            L.over(under, tl, ox, oy)
            th, tw = tl.shape[:2]
            ta = np.zeros(rgba.shape[:2], np.float32)
            y0, y1, x0, x1 = max(oy, 0), min(oy + th, self.h), max(ox, 0), min(ox + tw, self.w)
            if y0 < y1 and x0 < x1:
                ta[y0:y1, x0:x1] = tl[y0 - oy:y1 - oy, x0 - ox:x1 - ox, 3]
            under[..., 3] = ta
            rgba = rgba + under * (1 - rgba[..., 3:])
        if self.k != 1.0:
            big = cv2.resize(rgba, None, fx=self.k, fy=self.k, interpolation=cv2.INTER_LANCZOS4)
            blur = cv2.GaussianBlur(big, (0, 0), 1.2)
            big = np.clip(big + 0.35 * (big - blur), 0, None)
            big[..., :3] = np.minimum(big[..., :3], big[..., 3:])
            rgba = np.ascontiguousarray(big[self.oy:self.oy + H, :W])
        self.cache = {key: rgba} if len(self.cache) > 6 else {**self.cache, key: rgba}
        return rgba

    def feet_out(self, i):
        dx, dy = self.track(i)
        x, y = self.to_out(self.tc.root0[0] + dx, self.feet + dy)
        return x, y


@lru_cache(maxsize=None)
def actor(name):
    return {"d01": lambda: Actor("h3_d01_close_tease"),
            "p02b": lambda: Actor("h3_p02b_me_poke"),
            "p04": lambda: Actor("h3_p04_yosomi"),
            "p05d": lambda: Actor("h3max_p05d_tsuyogari_nt_1080", donors=("h3max_p07e_konokoe_nt_1080",),
                                  tail="N_mirror_right_nt"),
            "p07e": lambda: Actor("h3max_p07e_konokoe_nt_1080", tail="N_mirror_center_nt")}[name]()


def src(t, t_start, f_start, f_end, hold=0):
    """Clip frame for song time t: real time from f_start on 2s, after `hold` frames of holding the first drawing;
    holds the last drawing at f_end."""
    o = int(round((t - t_start) * FPS))
    o = max(o - hold, 0)
    return min(f_start + (o // 2) * 2, f_end)


# ---------------- designed scenes laid out like the clips ----------------
@lru_cache(maxsize=4)
def mirror_sea(hy, moon, h=H):
    """Night sky + mirror-calm sea: the sky (with the moon) reflected below the horizon, darker, then plain water."""
    mx, my, r = moon
    base, hy_, moon_ = BG.sea_static(hy / h, (mx / W, my / h), r / h, W, h, "night")
    f = base.copy()
    n = min(hy, h - hy)
    f[hy:hy + n] = base[hy - n:hy][::-1] * 0.72
    if hy + n < h:
        f[hy + n:] = base[0] * 0.72
    cv2.line(f, (0, hy), (W, hy), (0.55, 0.68, 0.95), 2, cv2.LINE_AA)
    return f, hy, moon_


def sea_frame(t, lay, h=H):
    f, hy, moon = mirror_sea(lay["hy"], lay["moon"], h)
    f = f.copy()
    BG.stars(f, t, y_max=int(hy * 0.8))
    BG.moon_road(f, t, hy, moon, width=0.9)
    return f, hy


def put_actor(f, rgba, x=0, y=0, alpha=1.0):
    return L.over(f, rgba, int(x), int(y), alpha)


def reflect(f, rgba, feet_y, tq, k=0.85):
    """Her mirror image on the calm water: flipped about the soles, slight ripple, darker and bluer with depth."""
    fy = int(round(feet_y))
    body = rgba[:fy + 2]
    rows = np.where(body[..., 3].max(axis=1) > 0.3)[0]
    if not len(rows):
        return f
    top = int(rows.min())
    part = body[top:fy + 2]
    r = L.reflection(part, fade=(0.62, 0.05), blur=1.3, ripple=(2.4, 0.05), t=tq, tint=(0.62, 0.74, 1.0), squash=1.0)
    return L.over(f, r, 0, fy, alpha=k)


def camera(f, z, cx=0.5, cy=0.5, sharp=False):
    if abs(z - 1.0) < 1e-4:
        return f
    M = np.float32([[z, 0, W * cx * (1 - z)], [0, z, H * cy * (1 - z)]])
    out = cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_LANCZOS4 if sharp else cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_REFLECT)
    if sharp and z > 1.15:
        blur = cv2.GaussianBlur(out, (0, 0), 1.0)
        out = np.clip(out + 0.3 * (out - blur), 0, 1.4)
    return out


# ---------------- shots ----------------
@lru_cache(maxsize=1)
def stage_bg():
    return BG.stage(0.0, spot_x=0.58)


def s1_waratta(t):
    """Stage: the tease close-up on the right, the hook word slams in behind her, mora by mora."""
    tq = on2s(t)
    f = stage_bg().copy()
    c = B.chars(0, 0)
    B.wall(f, "笑った", c[0:3], t, W * 0.03, H * 0.30, 215, L.CORAL)
    B.wall(f, "でしょ", c[3:6], t, W * 0.06, H * 0.62, 215, L.CORAL)
    i = src(t, 64.40, 4, 110)
    put_actor(f, actor("d01").rgba(i, mouth_at(t), tq))
    z = 1.0 + 0.05 * ease((t - 64.40) / (M_ME[0] - 64.40))
    return camera(f, z, 0.64, 0.42)


def s2_me(t):
    """めっ: the poke, a white flash on the hit, the word stamps in."""
    tq = on2s(t)
    f = stage_bg().copy()
    i = src(t, M_ME[0], 104, 107)  # finger up by her face, lips shut for め-っ (f102-103, f110-112: finger over the mouth)
    put_actor(f, actor("p02b").rgba(i, mouth_at(t), tq))
    u = (t - M_ME[0]) * FPS / 3
    g = L.type_rgba("めっ", "heavy", 210, fill=L.CORAL, stroke=L.WHITE, stroke_w=10)
    L.put(f, g, W * 0.22, H * 0.70, scale=1.0 + 0.25 * max(1 - u, 0), angle=-8)
    if t - M_ME[0] < 2 / FPS:
        f = f * 0.35 + 0.65
    return f


def s3_mouikkai(t):
    """もういっかい: three punch-ins on the mora groups, the colour field flips with each cut; she laughs."""
    tq = on2s(t)
    m = M_MOU
    k = 0 if t < m[2] else 1 if t < m[5] else 2
    f = np.empty((H, W, 3), np.float32)
    f[:] = (L.SKY, L.WHITE, L.CORAL)[k]
    i = src(t, m[0], 6, 36)
    rgba = actor("p02b").rgba(i, mouth_at(t), tq)
    # her face lands at a new place per punch-in; zoom and position are chosen so the clip's own frame edges
    # (her shoulders are cut by the clip's bottom edge) always stay outside the picture
    z = (1.05, 1.30, 1.65)[k]
    cx, cy = actor("p02b").to_out(906, 560)  # her face in the clip, output pixels
    px, py = ((W * 0.68, H * 0.74), (W * 0.60, H * 0.67), (W * 0.50, H * 0.60))[k]
    px = min(max(px, W - z * (W - cx)), z * cx)
    py = min(max(py, H - z * (H - cy)), z * cy)
    M = np.float32([[z, 0, px - z * cx], [0, z, py - z * cy]])
    lay = cv2.warpAffine(rgba, M, (W, H), flags=cv2.INTER_LANCZOS4, borderValue=(0, 0, 0, 0))
    lay = np.clip(lay, 0, None)
    lay[..., :3] = np.minimum(lay[..., :3], lay[..., 3:])
    L.over(f, lay, 0, 0)
    txt = "もういっかい"
    shown = 2 if k == 0 else 4 if k == 1 else 6
    lab = L.type_rgba(txt[:shown], "heavy", 92, fill=L.NAVY if k != 2 else L.WHITE)
    L.over(f, lab, int(W * 0.06), int(H * 0.80))
    if WHITE_OUT[0] <= t:
        v = (t - WHITE_OUT[0]) / (WHITE_OUT[1] - WHITE_OUT[0])
        f = f * (1 - ease(v)) + ease(v)
    return f


@lru_cache(maxsize=1)
def tall_sea():
    return mirror_sea(SEA_P04["hy"] + 540, (SEA_P04["moon"][0], SEA_P04["moon"][1] + 540, SEA_P04["moon"][2]), h=H + 540)


def s4_establish(t):
    """The night sea on its own first: the camera tilts down from the stars to the horizon (lands on み)."""
    y = M_YOSO
    f, hy, moon = tall_sea()
    f = f.copy()
    BG.stars(f, t, y_max=int(hy * 0.85))
    BG.moon_road(f, t, hy, moon, width=0.9)
    u = ease((t - y[0]) / (y[2] - y[0]))
    out = np.ascontiguousarray(f[int(540 * u):int(540 * u) + H])
    B.vtype(out, "よそ見しないで", B.chars(1, 0), t, W * 0.20, H * 0.13, 58, L.WHITE, out_t=M_MITE[0] + 0.05)
    if t < y[0] + 0.25:
        v = (t - y[0]) / 0.25
        out = out * ease(v) + (1 - ease(v))
    return out


def s5_mitete(t):
    """Waist shot, she asks for our eyes (finger to her eye), the moon behind her shoulder."""
    tq = on2s(t)
    f, hy = sea_frame(t, SEA_P04)
    i = src(t, M_YOSO[2], 26, 88, hold=6)
    put_actor(f, actor("p04").rgba(i, mouth_at(t), tq))
    B.vtype(f, "よそ見しないで", B.chars(1, 0), t, W * 0.20, H * 0.13, 58, L.WHITE, out_t=M_MITE[0] + 0.05)
    B.vtype(f, "見ててよね", B.chars(1, 1), t, W * 0.27, H * 0.13, 62, L.WHITE)
    z = 1.0 + 0.04 * ease((t - M_YOSO[2]) / (M_TSUYO[0] - M_YOSO[2]))
    return camera(f, z, 0.62, 0.40)


def full_shot(t, name, lay, i, ext=0, rings=(), ring_kw=None):
    """Full figure on the mirror sea: water -> her reflection -> rings on the surface -> her (boots occlude rings)."""
    tq = on2s(t)
    f, hy = sea_frame(t, lay, H + ext)
    a = actor(name)
    rgba = a.rgba(i, mouth_at(t), tq)
    fx, fy = a.feet_out(i)
    canvas = np.zeros((H + ext, W, 4), np.float32)
    canvas[:H] = rgba
    reflect(f, canvas, fy, tq)
    if len(rings):
        BG.ripples(f, t, fx, fy + 2, list(rings), **(ring_kw or {}))
    L.contact_glow(f, fx, fy + 3, 90, 9, color=L.MOON, k=0.16)
    L.over(f, rgba, 0, 0)
    return f, fx, fy


def s6_tsuyogari(t):
    """強がりだって: small beside the setting moon, she looks up at us and sings; the camera tilts down to her
    reflection, arriving on 本. (Source from f56: in f0-55 she looks down, where no front-facing mouth fits.)"""
    ts, hk = M_TSUYO, M_HONKI
    i = src(t, ts[0], 56, 123)
    f, fx, fy = full_shot(t, "p05d", SEA_P05, i, ext=560, rings=list(ts), ring_kw=dict(rx0=30, grow=420, squash=0.12))
    u = ease((t - ts[1]) / (hk[0] - ts[1])) if t > ts[1] else 0.0
    y0 = int(520 * u)
    out = np.ascontiguousarray(f[y0:y0 + H])
    B.vtype(out, "強がりだって", B.chars(2, 0), t, W * 0.20, 150, 60, L.WHITE)  # screen space: stays while sung
    return out


@lru_cache(maxsize=1)
def night_water():
    base, hy, moon = BG.sea_static(0.95, (0.74, 0.30), 0.22, W, H, "night")
    return base[:H][::-1].copy() * 0.7


def s7_honki(t):
    """本気だもん: her reflection's face in the water, upside down, looking straight up at us: the honest one.
    (The tease close-up from f84, not used in shot 1; the laughing clip has no mouth shapes for the line.)"""
    tq = on2s(t)
    hk = M_HONKI
    f = night_water().copy()
    BG.stars(f, t, y_max=H, k=0.5)
    i = src(t, hk[0], 84, 110)
    rgba = actor("d01").rgba(i, mouth_at(t), tq)[::-1].copy()
    hh, ww = rgba.shape[:2]
    yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
    amp = 3.0 + 4.0 * np.exp(-max(t - hk[0], 0) / 0.5)
    rgba = cv2.remap(rgba, (xx + amp * np.sin(yy * 0.035 + tq * 4.0)).astype(np.float32), yy, cv2.INTER_LINEAR)
    rgba[..., :3] *= np.array((0.82, 0.9, 1.0), np.float32)
    L.over(f, rgba, int(W * 0.06), 0, alpha=0.95)
    sw = np.clip((t - hk[0]) / 0.3, 0, 1)
    L.contact_glow(f, W * 0.62, H * 0.55, 520, 420, color=(0.45, 0.6, 1.0), k=0.12 * sw)
    BG.ripples(f, t, W * 0.62, H * 0.9, hk, rx0=60, grow=900, squash=0.18)
    B.vtype(f, "本気だもん", B.chars(2, 1), t, W * 0.14, H * 0.14, 66, (1.0, 0.6, 0.66), ripple=True)
    return camera(f, 1.0 + 0.04 * ease((t - hk[0]) / (FLIP[0] - hk[0])), 0.6, 0.45)


def s8_konokoe(t):
    """この声で: through the surface, she stands in front of the moon and sings; rings spread with each mora."""
    i = src(t, FLIP[1], 0, 191)
    f, fx, fy = full_shot(t, "p07e", SEA_P07, i, rings=M_KONO, ring_kw=dict(rx0=30, grow=520, squash=0.12))
    B.vtype(f, "この声で", B.chars(3, 0), t, W * 0.22, H * 0.12, 64, L.WHITE)
    z = 1.0 + 0.05 * ease((t - FLIP[1]) / (M_KIME[0] - FLIP[1]))
    return camera(f, z, 0.5, 0.45)


def s9_kime(t):
    """キメちゃうよ: punch-in on キ, slow push through the held よ, bloom to white."""
    i = src(t, FLIP[1], 0, 191)
    f, fx, fy = full_shot(t, "p07e", SEA_P07, i, rings=M_KIME, ring_kw=dict(rx0=30, grow=520, squash=0.12))
    km = M_KIME
    z = 1.42 + 0.14 * ease((t - km[0]) / (B.VOICE_END - km[0]))
    out = camera(f, z, 971 / W, 0.40, sharp=True)
    B.vtype(out, "キメちゃうよ", B.chars(3, 1), t, W * 0.86, H * 0.12, 64, L.WHITE)
    if t >= BLOOM_OUT[0]:
        v = ease((t - BLOOM_OUT[0]) / (BLOOM_OUT[1] - BLOOM_OUT[0]))
        out = L.bloom(out, thresh=0.75 - 0.4 * v, k=0.7 * v)
        out = out * (1 - v) + v
    return out


SHOTS = [(64.40, M_ME[0], s1_waratta), (M_ME[0], M_MOU[0], s2_me), (M_MOU[0], M_YOSO[0], s3_mouikkai),
         (M_YOSO[0], M_YOSO[2], s4_establish), (M_YOSO[2], M_TSUYO[0], s5_mitete), (M_TSUYO[0], M_HONKI[0], s6_tsuyogari),
         (M_HONKI[0], FLIP[0], s7_honki), (FLIP[1], M_KIME[0], s8_konokoe), (M_KIME[0], T1 + 1, s9_kime)]


def flip(t):
    """Through the surface: the frame turns over (180 deg) from the reflection into her world."""
    u = (t - FLIP[0]) / (FLIP[1] - FLIP[0])
    e = ease(u)
    src_f = s7_honki(FLIP[0] - 1 / FPS) if e < 0.5 else s8_konokoe(FLIP[1])
    ang = 180 * e if e < 0.5 else 180 * (e - 1)
    acc = np.zeros_like(src_f)
    for dk in (-6, -2, 2, 6):  # rotational motion blur
        M = cv2.getRotationMatrix2D((W / 2, H / 2), ang + dk * (1 - abs(2 * e - 1)), 1.0 + 0.15 * np.sin(np.pi * e))
        acc += cv2.warpAffine(src_f, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    return acc / 4 + 0.35 * np.sin(np.pi * e)


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
