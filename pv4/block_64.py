"""v4 production block 64.40-84.60 s (笑ったでしょ → めっ → もういっかい → よそ見しないで → 強がりだって → この声で).

Built from MiniMax H3 clips that start on on-model frames (pv4/h3/), composited by the v4 rules derived from the
reference measurements (docs/research_pv_language.md §4-5), after frame-by-frame QA (docs/qa_h3_block64.md):
- only QA-passed source frame ranges are used (USE below); clips with tail / hand defects were replaced;
- the tail is not generated: full-body shots use tail-free first frames and the sheet's own tail is composited
  back (pv4/tail.py), hip-tracked, swaying on 2s, behind her legs, mirrored in the water;
- lip-sync by frame selection (pv4/mouth.py): on singing shots each drawing is chosen so her mouth is open when
  the separated vocal is loud and closed in the gaps; time stays monotonic, 0.6-1.6x speed;
- character footage on 2s; camera, light and type on 1s;
- one lyric layer (Mincho; one hook word behind her using the per-frame matte);
- joins: hit cut with a flash on めっ, rewind on もういっかい, white dissolve into the MIRROR SEA, dissolve inside the
  world, whip-tilt through the water into the inverted world, bloom-out at the end of the verse;
- scene acting: ripples from her boots (in the clips), the moonlight swells on 本気だもん, motes rise.

usage: block_64.py preview <t...> --out sheet.jpg | render <out.mp4> [workers]
"""
import json
import os
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
import look as L  # noqa: E402
from mouth import sync_path, vocal_env  # noqa: E402
from tail import TailComp  # noqa: E402

W, H, FPS = L.W, L.H, 24
T0, T1 = 64.40, 84.60
CLIPS = HERE / "h3/clips"
# rebuildable caches (not committed): mattes from pv4/qa_frames.py (<clip>_alpha.npz), vocal stem from
# tools/separate.py (UVR MDX-Net Voc_FT) on audio/t2_optimized_full.mp3
MATTES = Path(os.environ.get("OC_MATTES", HERE / ".cache/mattes"))
VOCALS = Path(os.environ.get("OC_VOCALS", HERE / ".cache/vocals.wav"))
PLACE = json.load(open(HERE / "h3/frames/placements.json"))

# phrase onsets (s), checked against the vocal envelope / pitch
PH = {"waratta": 64.40, "me": 66.82, "mouikkai": 67.50, "yosomi": 68.50, "mitete": 71.25, "tsuyogari": 72.60,
      "honki": 75.64, "konokoe": 76.55, "kime": 79.40, "voice_end": 83.30, "next": 84.60}

# shots: (start, end, clip, camera (z0, z1, x0, x1), world, mode, source range [a, b], tail placement)
# mode: "sync" = lip-sync frame selection inside the range, "play" = real time from a, on 2s
SHOTS = [
    (64.40, 66.82, "h3_d01_close_tease", (1.00, 1.05, 0.50, 0.48), "stage", "sync", (4, 110), None),
    (66.82, 67.50, "h3_p02b_me_poke", (1.06, 1.06, 0.50, 0.50), "stage", "play", (96, 112), None),
    (69.358, 72.60, "h3_p04_yosomi", (1.00, 1.04, 0.52, 0.50), "sea", "sync", (26, 88), None),
    (72.60, 76.30, "h3max_p05d_tsuyogari_nt_1080", (1.00, 1.05, 0.55, 0.55), "sea", "play", (0, 123), "N_mirror_right_nt"),
    (76.30, 84.60, "h3max_p07e_konokoe_nt_1080", (1.04, 1.00, 0.50, 0.50), "sea_inv", "sync", (0, 191), "N_mirror_center_nt"),
]
REWIND = (67.50, 68.38)
WHITE_IN = (68.38, 68.80)
# the MIRROR SEA is established on its own before she appears (composition rule 1, docs/research_pv_language.md §6)
ESTABLISH = (68.38, 69.358)
WHIP = (76.30, 76.75)
BLOOM_OUT = (83.30, 84.45)


@lru_cache(maxsize=8)
def clip(name):
    cap = cv2.VideoCapture(str(CLIPS / f"{name}.mp4"))
    fr = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        fr.append(f)
    cap.release()
    return fr


@lru_cache(maxsize=8)
def matte(name):
    p = MATTES / f"{name}_alpha.npz"
    return np.load(p)["alpha"] if p.exists() else None


@lru_cache(maxsize=1)
def sea_plate():
    p = L.grade(L.plate(L.ROOT / "art/generated/pv4/plates/p1_mirror_moon.png", zoom=1.35 * 1.04, cx=0.40, cy=0.40), k=0.45)
    return L.bloom(p, thresh=0.7, k=0.35)


def establish(t):
    """Empty MIRROR SEA, slow push toward where she will stand; motes rise; first line already appears."""
    u = (t - ESTABLISH[0]) / (ESTABLISH[1] - ESTABLISH[0])
    f = camera(sea_plate().copy(), 1.0 + 0.03 * ease(u), 0.5 + 0.02 * u)
    rng = np.random.default_rng(5)
    for _ in range(26):
        x, y, sp = rng.uniform(0, W), rng.uniform(H * 0.2, H * 0.62), rng.uniform(12, 30)
        cv2.circle(f, (int(x), int(y - sp * (t - ESTABLISH[0]))), int(rng.uniform(1.5, 3.5)), L.MOON, -1, cv2.LINE_AA)
    reveal(f, "よそ見しないで", t, PH["yosomi"], W * 0.30, H * 0.14, 54, L.WHITE)
    return letterbox(f)


@lru_cache(maxsize=1)
def vocal():
    import librosa
    y, sr = librosa.load(str(VOCALS), sr=22050, mono=True)
    return y, sr


@lru_cache(maxsize=8)
def plan(k):
    """Source frame per output frame of shot k."""
    s0, s1, name, _, _, mode, (a, b), _ = SHOTS[k]
    n_out = int(round((s1 - s0) * FPS))
    if mode == "play":
        return [min(a + 2 * (i // 2), b) for i in range(n_out)]
    op = np.load(HERE / f".cache/mouth_{name}.npy")[a:b + 1]
    y, sr = vocal()
    env = vocal_env(y, sr, s0, s1, FPS)
    env = np.pad(env, (0, max(0, n_out - len(env))), mode="edge")
    return [a + i for i in sync_path(op, env, start=0)]


@lru_cache(maxsize=4)
def tailcomp(k):
    s0, s1, name, _, _, _, _, place = SHOTS[k]
    if place is None:
        return None
    al = matte(name)
    return TailComp(PLACE[place], clip(name), al, scale=clip(name)[0].shape[1] / 1920)


def to_frame(rgb):
    if rgb.shape[1] == W:
        return rgb  # native 1080P (H3 Max): no resampling, no sharpening
    rgb = cv2.resize(rgb, (W, H), interpolation=cv2.INTER_LANCZOS4)
    blur = cv2.GaussianBlur(rgb, (0, 0), 1.2)
    return np.clip(rgb + 0.35 * (rgb - blur), 0, 1)  # restore line crispness after upscaling


def camera(f, z, cx):
    M = np.float32([[z, 0, W / 2 - z * W * cx], [0, z, H / 2 * (1 - z)]])
    return cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def ease(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


@lru_cache(maxsize=32)
def glyph(ch, face, size, color):
    return L.bbox_trim(L.type_rgba(ch, face, size, fill=color), pad=2)


def reveal(f, text, t, t_on, x, y, size, color, face="mincho", vertical=True, step=0.07, out_t=None, ripple=False):
    """Glyphs fade in 0.22 s each, rise 14 px and sharpen, staggered from the phrase onset."""
    adv = size * 1.28
    for k, ch in enumerate(text):
        u = (t - (t_on + k * step)) / 0.22
        if u <= 0:
            continue
        a = min(u, 1.0) * (np.clip((out_t - t) / 0.25, 0, 1) if out_t else 1.0)
        if a <= 0:
            continue
        g = glyph(ch, face, size, color)
        e = 1 - (1 - min(u, 1)) ** 3
        if e < 0.97:
            g = cv2.GaussianBlur(g, (0, 0), 5 * (1 - e) + 0.01)
        if ripple:
            hh, ww = g.shape[:2]
            yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
            g = cv2.remap(g, xx + 2.2 * np.sin(yy * 0.09 + t * 4), yy, cv2.INTER_LINEAR)
        if vertical:
            L.over(f, g, int(x - g.shape[1] / 2), int(y + k * adv + 14 * (1 - e)), a)
        else:
            L.over(f, g, int(x + k * adv * 0.82), int(y + 14 * (1 - e)), a)
    return f


@lru_cache(maxsize=8)
def word_img(text, face, size, color):
    """Whole word set once (real kerning), plus the x edge of every character for the reveal."""
    img = L.type_rgba(text, face, size, fill=color)
    f = L.font(face, size)
    pad = int(size * 0.3)
    edges = [pad + sum(f.getlength(c) for c in text[:k]) for k in range(len(text) + 1)]
    return img, edges


def reveal_word(f, text, t, t_on, x, y, size, color, face="heavy", step=0.06, angle=0.0):
    """Horizontal hook word: each character wipes in (soft edge, 0.12 s) at its time; the word never re-flows."""
    img, edges = word_img(text, face, size, color)
    hh, ww = img.shape[:2]
    xs = np.arange(ww, dtype=np.float32)
    a = np.zeros(ww, np.float32)
    for k in range(len(text)):
        u = np.clip((t - (t_on + k * step)) / 0.12, 0, 1)
        if u <= 0:
            continue
        x0, x1 = edges[k], edges[k + 1]
        a = np.maximum(a, np.clip((x0 + (x1 - x0 + 24) * u - xs) / 24, 0, 1) * (xs >= x0 - 12))
    if a.max() <= 0:
        return f
    a[int(edges[-1]) + 12:] = a[int(edges[-1]) + 12:] * 0 + a[int(edges[-1])] if int(edges[-1]) < ww else a[int(edges[-1]) + 12:]
    out = img * a[None, :, None]
    return L.put(f, out, x + ww / 2, y + hh / 2, angle=angle)


def letterbox(f):
    b = int(H * 0.075)
    f[:b] = np.array(L.INK, np.float32) * 0.6
    f[-b:] = np.array(L.INK, np.float32) * 0.6
    return f


def shot_frame(k, t, with_type=True):
    s0, s1, name, (z0, z1, x0, x1), world, mode, _, _ = SHOTS[k]
    u = (t - s0) / (s1 - s0)
    j = min(max(int(round((t - s0) * FPS)), 0), len(plan(k)) - 1)
    i = plan(k)[j]
    tc = tailcomp(k)
    if tc is not None:
        t_draw = s0 + (j // 2) * 2 / FPS  # tail sway on 2s, like the drawing
        src = tc.frame(i, clip(name)[i], t_draw)
    else:
        src = cv2.cvtColor(clip(name)[i], cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    f = to_frame(src)
    if world == "sea_inv":
        f = np.ascontiguousarray(f[::-1])
    al = None
    m = matte(name)
    if m is not None:
        al = cv2.resize(m[min(i, len(m) - 1)].astype(np.float32) / 255, (W, H), interpolation=cv2.INTER_LINEAR)
        if world == "sea_inv":
            al = al[::-1]
    # type that sits behind her: drawn on a copy, then her pixels are restored through the matte
    if name == "h3_d01_close_tease" and al is not None and with_type:
        back = f.copy()
        reveal_word(back, "笑ったでしょ", t, PH["waratta"], W * 0.035, H * 0.08, 132, L.CORAL, step=0.07, angle=4)
        a3 = np.clip((al - 0.15) / 0.7, 0, 1)[..., None]
        f = back * (1 - a3) + f * a3
    if name == "h3_p02b_me_poke" and with_type:
        u2 = t - PH["me"]
        g = L.type_rgba("めっ", "heavy", 150, fill=L.CORAL, stroke=L.WHITE, stroke_w=6)
        L.put(f, g, W * 0.30, H * 0.40, scale=1.0 + 0.3 * np.exp(-u2 / 0.06), angle=-8)
        if u2 < 2 / FPS:
            f = f * 0.7 + np.array(L.CORAL, np.float32) * 0.3
    if name == "h3_p04_yosomi":
        reveal(f, "よそ見しないで", t, PH["yosomi"], W * 0.30, H * 0.14, 54, L.WHITE, out_t=s1 + 0.2)
        reveal(f, "見ててよね", t, PH["mitete"], W * 0.22, H * 0.22, 54, L.SKY, out_t=s1 + 0.2)
    if "p05" in name:
        # scene acting: on 本気だもん the moon swells and the light reaches the water
        sw = np.clip((t - PH["honki"]) / 0.45, 0, 1) * np.exp(-max(t - PH["honki"] - 0.45, 0) / 1.6)
        if sw > 0:
            L.contact_glow(f, W * 0.36, H * 0.40, 330, 330, color=L.MOON, k=0.22 * sw)
            L.contact_glow(f, W * 0.40, H * 0.80, 600, 60, color=L.MOON, k=0.18 * sw)
        reveal(f, "強がりだって", t, PH["tsuyogari"], W * 0.50, H * 0.13, 56, L.INK, out_t=s1 + 0.3)
        reveal(f, "本気だもん", t, PH["honki"], W * 0.80, H * 0.58, 52, (1.0, 0.56, 0.62), ripple=True, out_t=s1 + 0.3)
    if "p07" in name:
        reveal(f, "この声で", t, PH["konokoe"], W * 0.30, H * 0.16, 56, L.WHITE, out_t=PH["voice_end"] + 0.4)
        reveal(f, "キメちゃうよ", t, PH["kime"], W * 0.72, H * 0.16, 62, L.WHITE, out_t=PH["voice_end"] + 0.4)
    z = z0 + (z1 - z0) * ease(u)
    cx = x0 + (x1 - x0) * ease(u)
    f = camera(f, z, cx)
    if world.startswith("sea"):
        f = letterbox(f)
    return f


def shot_at(t):
    for k, s in enumerate(SHOTS):
        if s[0] <= t < s[1]:
            return k
    return None


@lru_cache(maxsize=96)
def cached(k, fi):
    return shot_frame(k, fi / FPS, with_type=False)  # the rewind runs the picture back; type stays one layer


def frame(fi):
    t = fi / FPS
    if REWIND[0] <= t < WHITE_IN[1]:
        # もういっかい: the last 2.6 s play backwards at ~3x, losing colour and gaining light, into white
        u = (t - REWIND[0]) / (REWIND[1] - REWIND[0])
        if t < REWIND[1]:
            src_t = PH["mouikkai"] - 0.05 - u * 2.6
            k = shot_at(src_t)
            f = cached(k, int(src_t * FPS)).copy()
            f = cv2.blur(f, (int(1 + 30 * np.sin(np.pi * u)), 1))
            g = f.mean(axis=2, keepdims=True)
            f = f * (1 - 0.5 * u) + g * 0.5 * u
            f = f * (1 - 0.8 * ease(u)) + 0.8 * ease(u)
            if t >= PH["mouikkai"]:
                reveal(f, "もういっかい", t, PH["mouikkai"], W * 0.38, H * 0.46, 64, L.NAVY, vertical=False, step=0.05)
        else:
            v = (t - WHITE_IN[0]) / (WHITE_IN[1] - WHITE_IN[0])
            f = establish(t) * ease(v) + (1 - ease(v)) * 1.0
    elif ESTABLISH[0] <= t < ESTABLISH[1]:
        f = establish(t)
    elif WHIP[0] <= t < WHIP[1]:
        u = (t - WHIP[0]) / (WHIP[1] - WHIP[0])
        top = shot_frame(3, min(t, SHOTS[3][1] - 1 / FPS))
        bot = shot_frame(4, t)
        strip = np.concatenate([top, bot], 0)
        e = u * u * u * (u * (6 * u - 15) + 10)
        speed = 30 * u * u * (1 - u) * (1 - u) / 1.875
        y0 = int(round(H * e))
        f = strip[y0:y0 + H].copy()
        if speed > 0.02:
            f = cv2.blur(f, (1, int(1 + 90 * speed)))
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            f = cv2.remap(f, xx + 10 * speed * np.sin(yy * 0.035 + t * 9), yy, cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_REFLECT)
    else:
        k = shot_at(t)
        f = shot_frame(k, t)
        # dissolve inside the MIRROR SEA (よそ見 → 強がり), 6 frames
        if k == 3 and t < SHOTS[3][0] + 0.25:
            v = (t - SHOTS[3][0]) / 0.25
            f = f * ease(v) + shot_frame(2, SHOTS[2][1] - 1 / FPS) * (1 - ease(v))
    if BLOOM_OUT[0] <= t:
        v = ease((t - BLOOM_OUT[0]) / (BLOOM_OUT[1] - BLOOM_OUT[0]))
        f = L.bloom(f, thresh=0.6 - 0.4 * v, k=0.6 * v)
        f = f * (1 - v) + v
    return L.finish(f, fi, bloom_k=0.08, chroma_px=0.8, vig=0.28, grain_k=0.016)


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
    if sys.argv[1] == "plans":
        for k in range(len(SHOTS)):
            p = plan(k)
            print(SHOTS[k][2], len(p), "src", p[0], "-", p[-1], "unique", len(set(p)))
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
