"""v4 style frames: the OC exactly as on the reference sheet, integrated by light, in four compositions taken from
the reference research (docs/research_pv_language.md). One lyric line per frame, set as part of the picture.

usage: style_frames.py <out_dir>
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import look as L  # noqa: E402

P = L.ROOT / "art/generated/pv4/plates"
W, H = L.W, L.H


def letterbox(f, k=0.075):
    b = int(H * k)
    f[:b] = f[:b] * 0.0 + np.array(L.INK, np.float32) * 0.6
    f[-b:] = f[-b:] * 0.0 + np.array(L.INK, np.float32) * 0.6
    return f


def caption(f, text, x, y, size=22, alpha=0.75):
    """Small letter-spaced Latin line (section marker), never a second lyric track."""
    t = L.type_rgba(text, "latin", size, fill=L.WHITE, tracking=0.35)
    return L.over(f, t, int(x), int(y), alpha)


def motes(f, seed, n, box, size=(1.5, 4.0), k=0.5, color=L.MOON):
    rng = np.random.default_rng(seed)
    layer = np.zeros_like(f)
    x0, y0, x1, y1 = box
    for _ in range(n):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        r = rng.uniform(*size)
        cv2.circle(layer, (int(x), int(y)), int(max(r, 1)), color, -1, cv2.LINE_AA)
    layer = cv2.GaussianBlur(layer, (0, 0), 1.6)
    f[..., :3] += layer[..., :3] * k
    return f


# ---------------- A: mirror (強がりだって / 本気だもん, 72.7 s) ----------------
def frame_mirror(clean=False):
    f = L.grade(L.plate(P / "p1_mirror_moon.png", zoom=1.12, cx=0.62, cy=0.42), k=0.45)
    f = L.bloom(f, thresh=0.7, k=0.35)
    horizon = int(H * 0.585)
    fig = L.figure(640)
    # the moon is behind her, left: front in shadow (ambient), strong rim on the left edge
    fig = L.relight(fig, ambient=L.NAVY, amb_k=0.42, key=0.8, rim_dir=(-1.0, -0.2), rim_color=L.MOON, rim_k=0.9,
                    rim_px=4)
    cx, feet = int(W * 0.63), int(H * 0.835)
    x = cx - fig.shape[1] // 2
    # reflection first (it sits in the water), then the light pool, then her
    refl = L.reflection(fig, fade=(0.5, 0.0), blur=2.2, ripple=(4.0, 0.06), tint=(0.55, 0.7, 1.0))
    L.over(f, refl, x, feet - 6)
    L.contact_glow(f, cx, feet + 4, 150, 14, color=L.MOON, k=0.28)
    L.over(f, fig, x, feet - fig.shape[0])
    if clean:  # first frame for a video model: no type, no bars (type is composited afterwards)
        return L.finish(motes(f, 3, 40, (0, 0, W, horizon), k=0.35), 1, chroma_px=0, grain_k=0.0, vig=0.38)
    # lyric: the bluff above the horizon (white Mincho), the truth in the water (coral, rippled)
    # set in ink on the moon: the brightest thing in the frame carries the darkest letters
    up = L.type_rgba("強がりだって", "mincho", 58, fill=L.INK, tracking=0.28, vertical=True)
    L.over(f, up, int(W * 0.465), int(H * 0.13))
    low = L.type_rgba("本気だもん", "mincho", 50, fill=L.CORAL, tracking=0.22, vertical=True)
    hh, ww = low.shape[:2]
    yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
    low = cv2.remap(low, xx + 2.5 * np.sin(yy * 0.09), yy, cv2.INTER_LINEAR)
    low = cv2.GaussianBlur(low, (0, 0), 0.8)
    L.over(f, low, int(W * 0.765), horizon + 8, alpha=0.9)
    f = motes(f, 3, 40, (0, 0, W, horizon), k=0.35)
    f = letterbox(f)
    f = caption(f, "VERSE II  —  TSUYOGARI / HONKI", 64, H - 62)
    return L.finish(f, 1, bloom_k=0.5, chroma_px=1.4, vig=0.38)


# ---------------- B: inverted world (今日の私は だいてんさい, 14.2 s) ----------------
def frame_inverted():
    low = L.grade(L.plate(P / "p2_city_roof.png", zoom=1.05, cx=0.5, cy=0.65, blur=2.2), k=0.7, contrast=0.85)
    split = int(H * 0.5)
    # the lower half: the rooftop she stands on; the upper half: the same city hanging upside down
    src_horizon = int(H * 0.47)
    f = np.empty((H, W, 3), np.float32)
    f[split:] = low[src_horizon:src_horizon + (H - split)]
    f[:split] = low[src_horizon:src_horizon + split][::-1]
    # a thin band of sky where the two worlds meet
    band = np.exp(-((np.arange(H) - split) / 26.0) ** 2)[:, None, None].astype(np.float32)
    f = f * (1 - 0.6 * band) + np.array(L.SKY, np.float32) * 0.6 * band
    # giant word behind both figures
    f = L.bloom(f, thresh=0.6, k=0.4)
    word = L.type_rgba("大天才", "heavy", 360, fill=L.WHITE, stroke=L.WHITE, stroke_w=4, outline_only=True)
    L.put(f, word, W / 2, split + 4, alpha=0.9)
    word2 = L.type_rgba("大天才", "heavy", 360, fill=L.COBALT)
    L.put(f, word2, W / 2 + 10, split + 14, alpha=0.35)
    rim = dict(ambient=L.NAVY, amb_k=0.26, key=0.95, rim_color=(0.55, 0.75, 1.0), rim_k=1.2, rim_px=5)
    fig = L.relight(L.figure(470), rim_dir=(0.0, 1.0), **rim)
    cx, cxi = int(W * 0.36), int(W * 0.64)
    L.shadow_pool(f, cx, H - 72, 120, 16, k=0.5)
    L.over(f, fig, cx - fig.shape[1] // 2, H - 70 - fig.shape[0])
    inv = L.relight(L.figure(470), rim_dir=(0.0, 1.0), **rim)[::-1, ::-1]
    L.shadow_pool(f, cxi, 72, 120, 16, k=0.5)
    L.over(f, inv, cxi - inv.shape[1] // 2, 70)
    line = L.type_rgba("今日の私は", "mincho", 40, fill=L.WHITE, tracking=0.5)
    L.put(f, line, W * 0.5, split - 205)
    f = caption(f, "No.03  —  HIGH  /  LOW", W - 420, H - 54)
    return L.finish(f, 2, bloom_k=0.45, chroma_px=1.8, vig=0.3)


# ---------------- C: layered screens (スクショは きんし, 84.8 s) ----------------
def window(content, title, w, h, accent=L.COBALT):
    """A floating app window drawn in code (crisp, on palette), content fitted inside."""
    bar = 34
    win = np.zeros((h, w, 4), np.float32)
    win[..., :3] = np.array(L.INK, np.float32) * 0.9
    win[..., 3] = 1
    win[:bar, :, :3] = np.array(L.NAVY, np.float32) * 1.3
    for i, c in enumerate((L.CORAL, L.LEMON, L.SKY)):
        cv2.circle(win, (18 + i * 22, bar // 2), 6, (*c, 1.0), -1, cv2.LINE_AA)
    t = L.type_rgba(title, "gothic", 18, fill=L.WHITE, tracking=0.1)
    L.over(win, t, 92, 2)
    ch, cw = h - bar, w
    if content is not None:
        c = content
        s = max(cw / c.shape[1], ch / c.shape[0])
        c = cv2.resize(c, (int(c.shape[1] * s) + 1, int(c.shape[0] * s) + 1), interpolation=cv2.INTER_AREA)
        oy = 0
        c = c[oy:oy + ch, (c.shape[1] - cw) // 2:(c.shape[1] - cw) // 2 + cw]
        L.over(win, c, 0, bar)
    cv2.rectangle(win, (0, 0), (w - 1, h - 1), (*accent, 1.0), 2, cv2.LINE_AA)
    return win


def frame_screens():
    room = L.grade(L.plate(L.ROOT / "art/generated/bg/b1_room.png", blur=9, zoom=1.15, cx=0.6, cy=0.5), k=0.5)
    f = room * 0.55 + np.array(L.INK, np.float32) * 0.2
    # far windows: small, soft, cool
    full = L.relight(L.figure(900), rim_k=0.0, amb_k=0.1)
    bust = L.relight(L.figure(1400, (0.12, 0.0, 0.88, 0.36)), rim_dir=(1.0, 0.2), rim_color=(0.6, 0.8, 1.0),
                     rim_k=0.5, rim_px=3, amb_k=0.18, key=0.92)
    bg_room = L.plate(L.ROOT / "art/generated/bg/b1_room.png", zoom=1.0)
    bg_room = np.concatenate([bg_room * 0.9, np.ones((H, W, 1), np.float32)], -1)
    def framed(fig_rgba, w, h, title):
        canvas = cv2.resize(bg_room, (w, h - 34), interpolation=cv2.INTER_AREA).copy()
        s = (h - 34) * 0.98 / fig_rgba.shape[0]
        fr = cv2.resize(fig_rgba, (int(fig_rgba.shape[1] * s), int(fig_rgba.shape[0] * s)), interpolation=cv2.INTER_AREA)
        L.over(canvas, fr, (w - fr.shape[1]) // 2, (h - 34) - fr.shape[0])
        return window(canvas, title, w, h)
    w1 = cv2.GaussianBlur(framed(full, 380, 300, "cam_02.mov"), (0, 0), 3.2)
    L.put(f, w1, W * 0.14, H * 0.28, angle=6, alpha=0.75)
    w2 = cv2.GaussianBlur(framed(full, 300, 240, "IMG_0866.png"), (0, 0), 2.6)
    L.put(f, w2, W * 0.86, H * 0.74, angle=-5, alpha=0.7)
    # main window: her stream, sharp
    main = framed(bust, 1000, 600, "LIVE  ●  余裕だもん配信")
    live = L.type_rgba("● REC  00:01:24:19", "gothic", 20, fill=L.CORAL, tracking=0.1)
    L.over(main, live, 1000 - live.shape[1] - 16, 46)
    for (x, y, dx, dy) in ((26, 60, 1, 1), (974, 60, -1, 1), (26, 574, 1, -1), (974, 574, -1, -1)):  # crop marks
        cv2.line(main, (x, y), (x + 40 * dx, y), (*L.WHITE, 1.0), 2, cv2.LINE_AA)
        cv2.line(main, (x, y), (x, y + 40 * dy), (*L.WHITE, 1.0), 2, cv2.LINE_AA)
    shadow = np.zeros((600 + 80, 1000 + 80, 4), np.float32)
    shadow[40:-40, 40:-40, 3] = 0.55
    shadow = cv2.GaussianBlur(shadow, (0, 0), 18)
    L.put(f, shadow, W * 0.47 + 18, H * 0.47 + 26, angle=-2)
    L.put(f, main, W * 0.47, H * 0.47, angle=-2)
    # glow of the screen on the room
    L.contact_glow(f, W * 0.47, H * 0.5, 700, 420, color=L.COBALT, k=0.12)
    # front: the system dialog (the gag), slightly overlapping the main window
    dlg = np.zeros((230, 520, 4), np.float32)
    dlg[..., :3], dlg[..., 3] = np.array(L.WHITE, np.float32), 1
    dlg[:40, :, :3] = np.array(L.NAVY, np.float32)
    L.over(dlg, L.type_rgba("system", "latin", 22, fill=L.WHITE, tracking=0.3), 16, 2)
    L.over(dlg, L.type_rgba("スクショは", "gothic", 30, fill=L.NAVY, tracking=0.1), 34, 62)
    L.over(dlg, L.type_rgba("きんし", "heavy", 64, fill=L.NAVY, tracking=0.05), 30, 100)
    cv2.rectangle(dlg, (350, 160), (500, 208), (*L.LEMON, 1.0), -1, cv2.LINE_AA)
    L.over(dlg, L.type_rgba("わすれる", "gothic", 24, fill=L.NAVY), 372, 160)
    dshadow = np.zeros((230 + 60, 520 + 60, 4), np.float32)
    dshadow[30:-30, 30:-30, 3] = 0.5
    L.put(f, cv2.GaussianBlur(dshadow, (0, 0), 14), W * 0.72 + 12, H * 0.66 + 18, angle=3)
    L.put(f, dlg, W * 0.72, H * 0.66, angle=3)
    # foreground: an out-of-focus window edge sliding past (depth layer)
    fg = cv2.GaussianBlur(window(None, "", 600, 500), (0, 0), 14)
    L.put(f, fg, -60, H * 0.95, alpha=0.6)
    # shutter flash residue
    f = f + 0.04
    f = caption(f, "No.17  —  SCREENSHOT", 64, 40)
    return L.finish(f, 3, bloom_k=0.35, chroma_px=2.4, vig=0.36)


# ---------------- D: tease close-up, word behind her (笑ったでしょ, 64.5 s) ----------------
def frame_tease(clean=False):
    f = L.grade(L.plate(P / "p3_theatre.png", blur=7, zoom=1.25, cx=0.45, cy=0.3), k=0.4) * 0.85
    f = L.bloom(f, thresh=0.55, k=0.35)
    # big word behind her head
    word = L.type_rgba("笑ったでしょ", "heavy", 205, fill=L.CORAL, stroke=L.CORAL, stroke_w=5, outline_only=True)
    if not clean:
        L.put(f, word, W * 0.34, H * 0.34, angle=-6, alpha=0.95)
    head = L.figure(1500, (0.1, 0.0, 0.9, 0.34))
    head = L.relight(head, ambient=L.NAVY, amb_k=0.3, key=0.9, rim_dir=(0.6, -1.0), rim_color=(0.75, 0.85, 1.0),
                     rim_k=0.55, rim_px=4)
    L.put(f, head, W * 0.66, H * 0.47 + 190, angle=7)
    # spotlight from above, motes in the beam
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    beam = np.clip(1 - np.abs(xx - (W * 0.6 + (yy - H) * 0.12)) / (260 + yy * 0.25), 0, 1) ** 2 * (1 - yy / H * 0.6)
    f += np.array((0.85, 0.9, 1.0), np.float32) * beam[..., None] * 0.18
    f = motes(f, 9, 60, (W * 0.4, 0, W * 0.85, H), size=(1.5, 3.5), k=0.45, color=(0.9, 0.95, 1.0))
    if clean:
        return L.finish(f, 4, chroma_px=0, grain_k=0.0, vig=0.4)
    f = caption(f, "CHORUS I  —  64.46", 64, H - 62)
    return L.finish(f, 4, bloom_k=0.4, chroma_px=1.6, vig=0.4)


def frame_mirror_waist():
    """MIRROR SEA, waist-up on the right third, horizon behind her chest, moon rim from the left (よそ見しないで)."""
    f = L.grade(L.plate(P / "p1_mirror_moon.png", zoom=1.35, cx=0.40, cy=0.40), k=0.45)
    f = L.bloom(f, thresh=0.7, k=0.35)
    fig = L.figure(int(H * 1.0 / 0.52), (0.0, 0.0, 1.0, 1.0))[: int(H * 0.95)]
    fig = L.relight(fig, ambient=L.NAVY, amb_k=0.4, key=0.82, rim_dir=(-1.0, -0.2), rim_color=L.MOON, rim_k=0.9, rim_px=6)
    L.over(f, fig, int(W * 0.66 - fig.shape[1] / 2), H - fig.shape[0])
    f = motes(f, 5, 30, (0, 0, W, H * 0.6), k=0.3)
    return L.finish(f, 6, chroma_px=0, grain_k=0.0, vig=0.36)


def frame_mirror_medium():
    """MIRROR SEA, knee-up centred, for the singing shot that is later turned over into the inverted world."""
    f = L.grade(L.plate(P / "p1_mirror_moon.png", zoom=1.2, cx=0.55, cy=0.45), k=0.45)
    f = L.bloom(f, thresh=0.7, k=0.35)
    fig = L.figure(int(H * 0.92 / 0.78), (0.0, 0.0, 1.0, 1.0))[: int(H * 0.92)]
    fig = L.relight(fig, ambient=L.NAVY, amb_k=0.38, key=0.85, rim_dir=(-0.8, -0.6), rim_color=L.MOON, rim_k=0.9, rim_px=5)
    L.over(f, fig, int(W * 0.56 - fig.shape[1] / 2), H - fig.shape[0])
    f = motes(f, 8, 30, (0, 0, W, H * 0.6), k=0.3)
    return L.finish(f, 7, chroma_px=0, grain_k=0.0, vig=0.36)


def frame_mirror_full_center():
    """MIRROR SEA, full figure centred with her boots on the water (ripples need a surface to spread on)."""
    f = L.grade(L.plate(P / "p1_mirror_moon.png", zoom=1.12, cx=0.5, cy=0.42), k=0.45)
    f = L.bloom(f, thresh=0.7, k=0.35)
    fig = L.figure(760)
    fig = L.relight(fig, ambient=L.NAVY, amb_k=0.4, key=0.82, rim_dir=(-0.6, -0.8), rim_color=L.MOON, rim_k=0.9, rim_px=4)
    cx, feet = int(W * 0.5), int(H * 0.86)
    x = cx - fig.shape[1] // 2
    L.over(f, L.reflection(fig, fade=(0.5, 0.0), blur=2.2, ripple=(4.0, 0.06), tint=(0.55, 0.7, 1.0)), x, feet - 6)
    L.contact_glow(f, cx, feet + 4, 160, 14, color=L.MOON, k=0.28)
    L.over(f, fig, x, feet - fig.shape[0])
    f = motes(f, 9, 30, (0, 0, W, H * 0.58), k=0.3)
    return L.finish(f, 8, chroma_px=0, grain_k=0.0, vig=0.36)


def mirror_full_nt(cx_frac=0.5, fig_h=760, plate_cx=0.5, seed=8):
    """MIRROR SEA full figure WITHOUT the tail (for video generation; the sheet's own tail is composited back by
    pv4/tail.py, because the video model cannot keep a tail attached). Returns frame + placement for the tail."""
    f = L.grade(L.plate(P / "p1_mirror_moon.png", zoom=1.12, cx=plate_cx, cy=0.42), k=0.45)
    f = L.bloom(f, thresh=0.7, k=0.35)
    body, tail, root = L.figure_parts(fig_h)
    rl = dict(ambient=L.NAVY, amb_k=0.4, key=0.82, rim_dir=(-0.6, -0.8), rim_color=L.MOON, rim_k=0.9, rim_px=4)
    body = L.relight(body, **rl)
    cx, feet = int(W * cx_frac), int(H * 0.86)
    x = cx - body.shape[1] // 2
    L.over(f, L.reflection(body, fade=(0.5, 0.0), blur=2.2, ripple=(4.0, 0.06), tint=(0.55, 0.7, 1.0)), x, feet - 6)
    L.contact_glow(f, cx, feet + 4, 160, 14, color=L.MOON, k=0.28)
    L.over(f, body, x, feet - body.shape[0])
    f = motes(f, seed, 30, (0, 0, W, H * 0.58), k=0.3)
    place = dict(x=x, y=feet - body.shape[0], fig_h=fig_h, root=[root[0] + x, root[1] + feet - body.shape[0]], feet=feet,
                 relight=rl)
    return L.finish(f, seed, chroma_px=0, grain_k=0.0, vig=0.36), place


def frame_sheet_waist():
    """Core shot: the sheet itself, waist up, on the sheet's white - the identity test for video models."""
    f = np.ones((H, W, 3), np.float32)
    fig = L.figure(int(H * 0.98 / 0.5), (0.0, 0.0, 1.0, 1.0))[: int(H * 0.98)]
    L.over(f, fig, (W - fig.shape[1]) // 2, int(H * 0.02))
    return f


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    frames = {"A_mirror": frame_mirror, "B_inverted": frame_inverted, "C_screens": frame_screens, "D_tease": frame_tease,
              "A_mirror_clean": lambda: frame_mirror(clean=True), "D_tease_clean": lambda: frame_tease(clean=True),
              "S_sheet_waist": frame_sheet_waist, "M_mirror_waist": frame_mirror_waist,
              "M_mirror_medium": frame_mirror_medium, "M_mirror_full_center": frame_mirror_full_center,
              "N_mirror_center_nt": lambda: mirror_full_nt()[0],
              "N_mirror_right_nt": lambda: mirror_full_nt(cx_frac=0.63, fig_h=640, plate_cx=0.62, seed=1)[0]}
    only = sys.argv[2:] or list(frames)
    for k in only:
        L.save(frames[k](), out / f"{k}.jpg")
        print("saved", k)
    import json
    json.dump({"N_mirror_center_nt": mirror_full_nt()[1],
               "N_mirror_right_nt": mirror_full_nt(cx_frac=0.63, fig_h=640, plate_cx=0.62, seed=1)[1]},
              open(out / "placements.json", "w"), indent=1, default=float)
