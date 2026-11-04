"""XIYIN's paw mic, identical in every pose.

N5 cannot keep a weapon's design or length consistent, so it does not draw the weapon: poses are drawn gripping a
plain light blue stick (art/generated/md_style/v3_*), and this module
- finds the stick (light, unsaturated blue, elongated, touching her hands; the pale ground shadow is excluded because
  it touches no skin), and its axis by PCA;
- takes the head end = the stick end farther from her body's centre, the grip = the other end;
- erases the drawn stick and lays the ONE canonical weapon sprite (w_pawmic_49502, cut out) along the axis, handle
  end at the grip, at a fixed length relative to her height;
- puts her fingers (skin pixels near the grip) back on top, so she visibly holds it.

usage: python3 mdweapon.py sheet out.png
"""
import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

import mdsprites as MD

SRC = Path(__file__).parent.parent / "art/generated/md_style"
WEAPON = "w_pawmic_49502"
HEAD_DIR = {"v3_upper_49702": (0, -1)}         # v3_windup_49702 rejected (stick across her face)
HEAD_CUT = 500          # sprite rows above this are the mic head (ball, ears, collar)
LENGTH = 0.46          # weapon length / character height (head of ears to soles)
INFO = {}              # per armed drawing: feet row, body anchor x, body height (filled by armed())


@lru_cache(None)
def weapon_sprite():
    """Cut-out weapon, vertical (head up); returns (RGBA, handle_bottom_xy, head_top_xy)."""
    im = MD.cutout(Image.open(SRC / f"{WEAPON}.png"))
    a = np.asarray(im.getchannel("A")) > 128
    ys, xs = np.nonzero(a)
    bottom = (float(xs[ys > ys.max() - 6].mean()), float(ys.max()))
    top = (float(xs[ys < ys.min() + 6].mean()), float(ys.min()))
    return im, bottom, top


@lru_cache(None)
def mic_sprite(length, width):
    """The paw mic exactly as the armed poses draw it (canonical head + handle bars), vertical, head up, `length` px
    from pommel to head top, handle `width` px; returns (RGBA, pommel_xy)."""
    w, bottom, top = weapon_sprite()
    wl = math.hypot(top[0] - bottom[0], top[1] - bottom[1])
    k = length / wl
    head = w.crop((0, 0, w.width, HEAD_CUT))
    head = head.resize((max(1, round(head.width * k)), max(1, round(head.height * k))), Image.Resampling.LANCZOS)
    hl = (wl - HEAD_CUT) * k
    W, H = head.width + 40, int(head.height + hl + 40)
    cx = bottom[0] * k + 20
    S2 = 3
    lay = Image.new("RGBA", (W * S2, H * S2), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    pom_y = H - 20
    neck_y = pom_y - hl
    def bar(y0, y1, half, col):
        dl.rectangle(((cx - half) * S2, y1 * S2, (cx + half) * S2, y0 * S2), fill=col)
    hw = width / 2
    bar(pom_y + 3, neck_y, hw, (16, 24, 84, 255))
    bar(pom_y + 0.5, neck_y, hw - 3.5 * width / 22, (196, 238, 250, 255))
    bar(pom_y + 0.5, neck_y, hw * 0.25, (240, 252, 255, 255))
    for c0 in (0.0, 0.86):
        bar(pom_y - hl * c0, pom_y - hl * (c0 + 0.1), hw - 3.5 * width / 22, (70, 110, 200, 255))
    out = lay.resize((W, H), Image.Resampling.LANCZOS)
    out.alpha_composite(head, (int(round(cx - bottom[0] * k)), int(round(neck_y - head.height + 2))))
    return out, (cx, pom_y)


def skin_mask(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return (r > 205) & (g > 165) & (b > 140) & (r > b + 8) & (r >= g)


def find_stick(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    sat = a.max(-1) - a.min(-1)
    lum = a.mean(-1)
    m = ((b > r + 25) & (g > r + 10) & (lum > 150) & (lum < 245) & (sat < 110) & (r > 110)) | \
        ((g > 140) & (b > 200) & (r < 170) & (lum > 120) & (lum < 245))      # saturated cyan sticks (V4.5 takes)
    m = ndimage.binary_opening(m, iterations=1)
    lab, n = ndimage.label(m)
    skin = ndimage.binary_dilation(skin_mask(a), iterations=30)
    best = None
    touching = [i for i in range(1, n + 1) if ((lab == i) & skin).any() and (lab == i).sum() >= 1500]
    for i in range(1, n + 1):
        c = lab == i
        size = int(c.sum())
        # pieces touching her hands win; a large piece away from them (V4.5 takes) only when none touch, so the pale
        # ground shadow under her feet is never taken for the stick
        if size < 1500 or (i not in touching and (touching or size < 6000)):
            continue
        ys, xs = np.nonzero(c)
        pts = np.stack([xs, ys], 1).astype(np.float32)
        mu = pts.mean(0)
        u, s, vt = np.linalg.svd(pts - mu, full_matrices=False)
        elong = s[0] / max(1e-6, s[1])
        if best is None or elong * size > best[0]:
            proj = (pts - mu) @ vt[0]
            best = (elong * size, c, mu + vt[0] * proj.min(), mu + vt[0] * proj.max())
    if best is None:
        raise ValueError("no stick found")
    # the hands split the stick into pieces: take every stick-coloured pixel near the fitted line, beyond the ends too
    e1, e2 = best[2], best[3]
    d = (e2 - e1) / max(1e-6, np.linalg.norm(e2 - e1))
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]].astype(np.float32)
    rel = np.stack([xx - e1[0], yy - e1[1]], -1)
    t = rel @ d
    dist = np.abs(rel @ np.array([-d[1], d[0]]))
    line = (dist < 24) & (t > -1.2 * np.linalg.norm(e2 - e1)) & (t < 2.2 * np.linalg.norm(e2 - e1))
    full = ndimage.binary_dilation(m, iterations=1) & line            # erase mask (all pieces on the line)
    # ends: the longest piece plus pieces on the line that start within a hand's width of it (not the ground shadow)
    lab2, n2 = ndimage.label(full)
    keep = best[1].copy()
    L = np.linalg.norm(e2 - e1)
    for i in range(1, n2 + 1):
        c = lab2 == i
        if (c & best[1]).any() or c.sum() < 150:
            continue
        ys, xs = np.nonzero(c)
        tt = (np.stack([xs, ys], 1) - e1) @ d
        if (-0.35 * L < tt.max() < 0) or (L < tt.min() < 1.35 * L):
            keep |= c
    ys, xs = np.nonzero(keep)
    tt = (np.stack([xs, ys], 1) - e1) @ d
    return full, e1 + d * tt.min(), e1 + d * tt.max()


@lru_cache(None)
def armed(name, length=LENGTH, src=None):
    """RGBA drawing (drawing coordinates, cut out) with the canonical weapon in her hands. src: an already
    processed (e.g. recoloured) RGB version of the drawing, else the file."""
    if src is None:
        import mdrecolor
        import mdface
        if name.startswith("brat/"):                   # V4.5 run-proportion poses: sheet colours + sheet details
            import mdbrat
            src = mdbrat.colour(name)
        elif name in mdface.FACES:
            src = mdface.fix(name)                     # sheet colours + canonical eye + N5-fitted face (mdface.py)
        else:
            src = mdrecolor.recolor_pose(name) if name in mdrecolor.POSE_SEEDS else Image.open(SRC / f"{name}.png")
    src = src.convert("RGB")
    # the stick and her hands are found in the ORIGINAL drawing (the recolour turns boot soles / stripes into the
    # sheet's light cobalt, which is close to the stick's colour); the body itself comes from src
    a = np.asarray(Image.open(SRC / f"{name}.png").convert("RGB")).astype(np.int16)
    stick, e1, e2 = find_stick(a)
    # background white trapped between hair strands, tail and body (pure white, unsaturated, bigger than a highlight)
    # is cut out too
    sa = np.asarray(src).astype(int)
    white = (sa.mean(-1) > 246) & (sa.max(-1) - sa.min(-1) < 12)
    wl, wn = ndimage.label(white)
    wsz = ndimage.sum(white, wl, range(1, wn + 1))
    warm = (sa[..., 0] > sa[..., 2] + 15)                       # skin, blush, the skin's red-brown line art
    keep_ids = []
    for i, z in enumerate(wsz, 1):
        if z > 350:
            sl = ndimage.find_objects((wl == i).astype(int))[0]
            sl = tuple(slice(max(0, q.start - 4), q.stop + 4) for q in sl)
            comp = wl[sl] == i
            ring = ndimage.binary_dilation(comp, iterations=4) & ~comp
            if warm[sl][ring].mean() < 0.05:                    # white inside skin (highlights) stays
                keep_ids.append(i)
    trapped = np.isin(wl, keep_ids)
    body = MD.cutout(src, crop=False, band_px=1)   # 1 px band: her dark outline (2-4 px) stays a dark line
    ba = np.asarray(body).copy()
    ba[ndimage.binary_dilation(trapped, iterations=1), 3] = 0     # exact white areas only (her pale skin is warmer)
    # loose bits (impact debris, sparks) are not part of her
    bl, bn = ndimage.label(ba[..., 3] > 0)
    if bn > 1:
        bsz = ndimage.sum(ba[..., 3] > 0, bl, range(1, bn + 1))
        ba[np.isin(bl, [i + 1 for i, z in enumerate(bsz) if z < 2500]), 3] = 0
    # the drawn ground shadow (pale blue, flat, under her feet) goes: the game draws its own
    pale = (ba[..., 3] > 0) & (ba[..., :3].astype(int).mean(-1) > 140) & \
        (ba[..., 2].astype(int) > ba[..., 0].astype(int) + 15) & ~stick
    pl, pn = ndimage.label(pale)
    for i, sl in enumerate(ndimage.find_objects(pl), 1):
        h_, w_ = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if w_ > 3 * h_ and w_ > 80 and sl[0].start > 0.7 * ba.shape[0]:
            ba[sl][pl[sl] == i, 3] = 0
    al = ba[..., 3] > 0
    ys, xs = np.nonzero(al & ~stick)
    centre = np.array([xs.mean(), ys.mean()])
    height = ys.max() - ys.min()
    # grip = where her hands are on the stick: skin pixels hugging the stick axis, projected onto it.
    # The weapon head goes toward the longer side of the stick from the grip (the swing end), and the handle runs
    # through her fists with a short pommel showing past them, as in the benchmark (the character's fist wraps the
    # prop's handle, prop drawn behind the fingers).
    d = (e2 - e1) / max(1e-6, np.linalg.norm(e2 - e1))
    nrm = np.array([-d[1], d[0]])
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    rel = np.stack([xx - e1[0], yy - e1[1]], -1).astype(np.float32)
    t_all, dist = rel @ d, np.abs(rel @ nrm)
    L = float(np.linalg.norm(e2 - e1))
    hand = skin_mask(a) & al & (dist < 0.045 * height) & (t_all > -0.1 * L) & (t_all < 1.1 * L)
    lab, n = ndimage.label(hand)
    if n:
        sizes = ndimage.sum(hand, lab, range(1, n + 1))
        hand = np.isin(lab, [i + 1 for i, z in enumerate(sizes) if z > 60])
    if hand.any():
        th = t_all[hand]
        tg = float(np.clip(th.mean(), 0, L))
        span = (float(th.min()), float(th.max()))
    else:                                   # hands hidden in her long sleeves: grip = stick end nearest her body
        tc = float(np.clip((centre - e1) @ d, 0, L))
        tg = 0.0 if tc < L / 2 else L
        span = (tg, tg)
    head_dir = d if (L - tg) >= tg else -d
    if name in HEAD_DIR:
        v = np.array(HEAD_DIR[name], np.float32)
        head_dir = d if d @ v > 0 else -d
    # stick width including its outline (handle drawn at exactly this width so her fingers fit around it)
    st = ndimage.binary_dilation(stick, iterations=2)
    sw = float(np.clip(st.sum() / max(1.0, L), 0.018 * height, 0.05 * height))
    ba[st, 3] = 0
    # the stick's own outline survives outside the body as thin lines: along the stick line, keep only pixels that
    # survive a 3 px opening of the alpha (thin lines vanish, body areas stay)
    strip = (dist < sw / 2 + 8) & (t_all > -0.3 * L) & (t_all < 1.3 * L)
    opened = ndimage.binary_opening(ba[..., 3] > 0, iterations=3)
    ba[strip & ~opened, 3] = 0
    body = Image.fromarray(ba, "RGBA")
    # weapon = canonical head (sprite above its collar) + handle drawn here at the stick's width
    w, bottom, top = weapon_sprite()
    wl = math.hypot(top[0] - bottom[0], top[1] - bottom[1])
    k = length * height / wl
    head_img = w.crop((0, 0, w.width, HEAD_CUT))
    head_img = head_img.resize((max(1, round(head_img.width * k)), max(1, round(head_img.height * k))),
                               Image.Resampling.LANCZOS)
    hl = (wl - HEAD_CUT) * k                                    # handle length
    rear = min(span, key=lambda v: (v - tg) * (1 if head_dir @ d > 0 else -1)) if hand.any() else tg
    pom = e1 + d * rear - head_dir * 0.05 * height              # pommel just past the rear fist
    neck = pom + head_dir * hl
    P = 500
    out = Image.new("RGBA", (body.width + 2 * P, body.height + 2 * P), (0, 0, 0, 0))     # the weapon layer
    # handle: rounded bar, light cyan with a white shine stripe, dark navy outline, a cobalt band at each end
    S2 = 3
    lay = Image.new("RGBA", (out.width * S2 // 2, out.height * S2 // 2), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    q = lambda p_: ((p_[0] + P) * S2 / 2, (p_[1] + P) * S2 / 2)
    nn = np.array([-head_dir[1], head_dir[0]])
    def bar(p0, p1, half, col):
        pts = [p0 + nn * half, p1 + nn * half, p1 - nn * half, p0 - nn * half]
        dl.polygon([q(v) for v in pts], fill=col)
    hw = sw / 2
    bar(pom - head_dir * 3, neck, hw, (16, 24, 84, 255))
    bar(pom - head_dir * 0.5, neck, hw - 3.5, (196, 238, 250, 255))
    bar(pom - head_dir * 0.5, neck, hw * 0.25, (240, 252, 255, 255))
    for c0 in (0.0, 0.86):
        bar(pom + head_dir * hl * c0, pom + head_dir * hl * (c0 + 0.1), hw - 3.5, (70, 110, 200, 255))
    out.alpha_composite(lay.resize(out.size, Image.Resampling.LANCZOS))
    # head on top of the neck
    ang = math.degrees(math.atan2(head_dir[0], -head_dir[1]))
    pad = int(max(head_img.size) * 1.2)
    canvas = Image.new("RGBA", (head_img.width + 2 * pad, head_img.height + 2 * pad), (0, 0, 0, 0))
    canvas.paste(head_img, (pad, pad))
    piv = (pad + bottom[0] * k, pad + head_img.height - 2)
    rot = canvas.rotate(-ang, Image.Resampling.BICUBIC, center=piv)
    out.alpha_composite(rot, (int(round(neck[0] - piv[0])) + P, int(round(neck[1] - piv[1])) + P))
    # the weapon is drawn BEHIND her (owner: her face must always show; a mic head swung past her head goes behind
    # it, as props held behind the body do in the benchmark); her hands are part of the body, so the fists close over
    # the handle
    weapon = out
    # anything of the drawn stick left in the body (outline crumbs, pale pixels) inside the weapon's footprint goes
    wa = np.asarray(weapon.getchannel("A"))[P:P + body.height, P:P + body.width] > 0
    bb = np.asarray(body).copy()
    ci = bb[..., :3].astype(int)
    pale = (ci.mean(-1) > 140) & (ci[..., 2] > ci[..., 0] + 15)          # stick-coloured (her skin / face is warm)
    bb[wa & ndimage.binary_dilation(pale, iterations=2) & ~ndimage.binary_dilation(hand, iterations=6)
       & ~ndimage.binary_dilation(skin_mask(ci), iterations=3), 3] = 0
    body = Image.fromarray(bb, "RGBA")
    out = Image.new("RGBA", weapon.size, (0, 0, 0, 0))
    out.alpha_composite(weapon)
    out.alpha_composite(body, (P, P))
    # body-only measures in `out` coordinates: soles row and the anchor (mean x of her upper body) used by the game
    bal = np.asarray(body.getchannel("A")) > 128
    ys_, xs_ = np.nonzero(bal)
    top = ys_.min()
    upper = ys_ < top + 0.55 * (ys_.max() - top)
    INFO[name] = dict(feet=float(ys_.max() + 1 + P), ax=float(xs_[upper].mean() + P), height=float(ys_.max() - top),
                      length=float(length * height), width=float(sw))
    return out


if __name__ == "__main__" and sys.argv[1] == "sheet":
    names = sys.argv[3:] or sorted(p.stem for p in SRC.glob("v3_*.png"))
    W, H = 300, 440
    S = Image.new("RGB", (len(names) * W, H), (60, 50, 110))
    for i, n in enumerate(names):
        im = armed(n)
        im = im.crop(im.getbbox())
        s = min((W - 10) / im.width, (H - 10) / im.height)
        im = im.resize((int(im.width * s), int(im.height * s)), Image.Resampling.LANCZOS)
        S.paste(im, (i * W + (W - im.width) // 2, H - 5 - im.height), im)
    S.save(sys.argv[2])
