"""Snap XIYIN's HD game drawings to the owner's sheet colours (art/reference/oc_reference_sheet.webp).

V5 drew her hair darker and more saturated than the sheet (with a bright cyan underlayer streak) and gave hair and
sweater the same blue; the sheet has muted indigo hair and a darker, greyer navy sweater. Recolour, per drawing:
- regions = connected flat-colour areas between the line art, picked by seed points (hair incl. ears and tail,
  sweater incl. sleeves and collar);
- each region class is reduced to its flat tones (shadow / base / light, 1-D k-means on lightness) and each tone is
  given the sheet's measured colour (TONES); every pixel keeps its lightness ratio to its tone, so the line art's
  anti-aliasing survives; the cyan underlayer streak is folded into the hair's shadow / base tones;
- bright accents (tie, stripes, clip, soles) are snapped the same way to the sheet's cobalt accents.

usage: python3 mdrecolor.py check out.png
"""
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).parent.parent
SHEET = ROOT / "art/reference/oc_reference_sheet.webp"
SRC = ROOT / "art/generated/md_style"

# sheet tones, dark to light (median colours of 1-D k-means clusters on clean sheet areas: hair top and strands,
# sweater chest and sleeve, cuff / collar stripes). Hair shine is kept a little lighter than the sheet's light tone
# (87,109,176, nearly the base) so the drawing's highlights stay readable, same hue.
TONES = {"hair": [(55, 74, 133), (79, 101, 169), (104, 126, 190)],
         "sweater": [(43, 47, 74), (55, 60, 89)],
         "accent": [(74, 100, 171), (119, 151, 217)]}

# per drawing (drawing px): seed points of hair (incl. ears, ahoge, tail), the cyan hair underlayer, the tie and
# extra sweater parts; sweater_box = blue regions inside it that are not hair / tie / accents are sweater.
SEEDS = {
    "z_run_49102": dict(hair=[(400, 330), (630, 100), (610, 130), (600, 440), (60, 722), (250, 778), (172, 775)],
                        streak=[(230, 560)], tie=[],
                        sweater=[(470, 475), (470, 670), (565, 505), (540, 530), (325, 610), (635, 705)],
                        sweater_box=(160, 420, 720, 830)),
    "z_punch_49113": dict(hair=[(283, 381), (541, 256), (535, 127), (547, 151), (100, 768)],
                          streak=[(218, 529), (100, 600)], tie=[(482, 620)], sweater=[(646, 469)],
                          sweater_box=(130, 385, 800, 760)),
    "z_air_49123": dict(hair=[(276, 407), (503, 94), (484, 105), (454, 127), (230, 915)],
                        streak=[], tie=[(555, 651)], sweater=[(717, 331)],
                        sweater_box=(40, 440, 620, 850)),
}


LEGS_Y = {"z_run_49102": 860, "z_punch_49113": 830, "z_air_49123": 870}   # below: socks, soles (drawing px)


def _colored(a):
    lum = a[..., :3].mean(-1)
    return (a[..., 2] > a[..., 0] + 30) & (lum >= 28)


def _tones(lum, k, iters=30):
    """1-D k-means on lightness: sorted tone centres."""
    c = np.percentile(lum, np.linspace(15, 85, k))
    for _ in range(iters):
        lab = np.argmin(np.abs(lum[:, None] - c[None, :]), 1)
        c = np.array([lum[lab == j].mean() if (lab == j).any() else c[j] for j in range(k)])
    return np.sort(c)


def _snap(a, mask, tones, shift=0):
    """Flat-tone recolour: the drawing's tones in this class (as many as the sheet has) map to the sheet's tones;
    each pixel keeps its lightness ratio to its own tone (anti-aliasing into the line art survives) and takes the
    sheet tone's colour. shift > 0 moves pixels down by that many tones (folds the cyan streak into the base)."""
    if not mask.any():
        return
    cols = np.array(tones, np.float32)
    k = len(cols)
    px = a[..., :3][mask]
    lum = px.mean(-1)
    c_src = _tones(lum, k)
    t = np.argmin(np.abs(lum[:, None] - c_src[None, :]), 1)
    ratio = np.clip(lum / np.maximum(c_src[t], 1), 0, 1.15)[:, None]
    a[..., :3][mask] = np.clip(cols[np.clip(t - shift, 0, k - 1)] * ratio, 0, 255)


@lru_cache(None)
def recolor(name):
    """RGB drawing (on white) with the sheet's colours."""
    a = np.asarray(Image.open(SRC / f"{name}.png").convert("RGB")).astype(np.float32)
    col = _colored(a)
    core = ndimage.binary_erosion(col, iterations=2)      # seals pin-hole gaps in the line art between regions
    lab, n = ndimage.label(core)
    _, (iy, ix) = ndimage.distance_transform_edt(lab == 0, return_indices=True)
    lab = np.where(col, lab[iy, ix], 0)
    lab0, n0 = ndimage.label(col)                         # small areas that vanish in the erosion (irises, hair
    gone = ndimage.sum(core, lab0, range(n0 + 1)) == 0    # clip) keep their own label instead of a neighbour's
    lab = np.where(gone[lab0] & col, n + lab0, lab)
    n = n + n0
    s = SEEDS[name]

    def region(pts):
        ids = {lab[y, x] for x, y in pts} - {0}
        return np.isin(lab, list(ids))

    hair, streak, tie = region(s["hair"]), region(s["streak"]), region(s["tie"])
    sat = a.max(-1) - a.min(-1)
    H, W = col.shape
    yy, xx = np.mgrid[0:H, 0:W]
    x0, y0, x1, y1 = s["sweater_box"]
    inbox = (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)
    sizes = ndimage.sum(np.ones_like(lab), lab, range(n + 1))
    auto = np.zeros(n + 1, bool)
    for i in range(1, n + 1):
        m = lab == i
        if sizes[i] > 300 and inbox[m].mean() > 0.6 and np.median(sat[m]) < 120:
            auto[i] = True
    sweater = (region(s["sweater"]) | auto[lab]) & ~hair & ~streak & ~tie
    stripes = sweater & (sat > 120)                       # cuff / collar stripes share a region with the sweater
    sweater &= ~stripes
    # every other large hair-blue region above the legs is hair too (the hand-picked seeds missed some bangs, which
    # kept the take's darker blue): dark ones take the hair tones, big bright ones (cyan underlayer) the hair base,
    # small bright ones (shine spots) the hair's light tone; below LEGS_Y blue regions are socks / soles
    idx = np.arange(n + 1)
    med_l = ndimage.median(a.mean(-1), lab, idx)
    med_r = ndimage.median(a[..., 0], lab, idx)
    med_s = ndimage.median(sat, lab, idx)
    cy = ndimage.mean(yy, lab, idx)
    thick = ndimage.sum(ndimage.binary_erosion(col, iterations=4), lab, idx)
    taken = np.zeros(n + 1, bool)
    taken[np.unique(lab[hair | streak | tie | sweater | stripes])] = True
    cand = ~taken & (sizes > 300) & (thick > 0.25 * sizes) & (med_r < 90) & (med_s > 50) & (cy < LEGS_Y[name])
    cand[0] = False
    shine = cand & (med_l >= 110) & (sizes < 2500)
    hair |= (cand & (med_l < 110))[lab]
    streak |= (cand & (med_l >= 110) & (sizes >= 2500))[lab]
    shine_m = shine[lab]
    accent = (col & ~hair & ~streak & ~sweater & ~shine_m & (sat > 120)) | stripes | tie
    _snap(a, shine_m, TONES["hair"][2:])
    _snap(a, hair, TONES["hair"])
    _snap(a, streak, TONES["hair"][:2])
    _snap(a, sweater, TONES["sweater"])
    _snap(a, accent, TONES["accent"])
    return Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGB")


if __name__ == "__main__" and sys.argv[1] == "check":
    ref = Image.open(SHEET).convert("RGB")
    ims = [ref.resize((round(ref.width * 1216 / ref.height), 1216))]
    for name in SEEDS:
        ims += [Image.open(SRC / f"{name}.png").convert("RGB"), recolor(name)]
    out = Image.new("RGB", (sum(i.width for i in ims), 1216), "white")
    x = 0
    for im in ims:
        out.paste(im, (x, 0))
        x += im.width
    out.resize((out.width // 2, 608)).save(sys.argv[2])


@lru_cache(1)
def _transfer_table():
    """Colour pairs (generated -> sheet) learned from the approved run drawing and its seeded recolour."""
    src = np.asarray(Image.open(SRC / "z_run_49102.png").convert("RGB")).astype(np.float32).reshape(-1, 3)
    dst = np.asarray(recolor("z_run_49102")).astype(np.float32).reshape(-1, 3)
    keep = (src.mean(1) < 235) & (np.abs(dst - src).sum(1) > 6)          # only pixels the recolour changed
    src, dst = src[keep], dst[keep]
    q = np.round(src / 4).astype(np.int32)                                # dedupe by 4-level bins, average targets
    key = q[:, 0] * 4096 + q[:, 1] * 64 + q[:, 2]
    uniq, inv = np.unique(key, return_inverse=True)
    s_mean = np.zeros((len(uniq), 3)); d_mean = np.zeros((len(uniq), 3)); cnt = np.zeros(len(uniq))
    np.add.at(s_mean, inv, src); np.add.at(d_mean, inv, dst); np.add.at(cnt, inv, 1)
    return s_mean / cnt[:, None], d_mean / cnt[:, None]


def recolor_auto(img):
    """Seed-free sheet colours for new poses: each pixel takes the correction (sheet - generated) of the most
    similar colours in the approved run drawing (k-nearest, distance weighted), so hair, sweater, stripes and the
    cyan underlayer move exactly as they did in the approved frame; colours far from anything in it (skin, white,
    the pale prop stick) are left alone."""
    from scipy.spatial import cKDTree
    s_tab, d_tab = _transfer_table()
    tree = cKDTree(s_tab)
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    flat = a.reshape(-1, 3)
    cand = flat.mean(1) < 235
    dist, idx = tree.query(flat[cand], k=8)
    w = 1 / (dist + 2.0)
    corr = ((d_tab[idx] - s_tab[idx]) * w[..., None]).sum(1) / w.sum(1, keepdims=True)
    fade = np.clip((40 - dist[:, 0]) / 25, 0, 1)[:, None]               # only where a close colour exists
    out = flat.copy()
    out[cand] = flat[cand] + corr * fade
    return Image.fromarray(out.reshape(a.shape).clip(0, 255).astype(np.uint8), "RGB")


# ---- armed pose pack (art/generated/md_style/v3_*): owner 2026-11-03 "revert to fixing this character design".
# Per drawing only the parts that are NOT hair are seeded (sweater incl. collar and knee socks; accents = tie and boot
# soles); every other large blue region is hair: dark ones take the sheet's hair tones, the bright cyan underlayer
# regions are folded into the sheet's hair base (the sheet has one flat hair colour, no underlayer). Thin saturated
# regions (collar / cuff / sock stripes) snap to the sheet's cobalt.
POSE_SEEDS = {
    "v3_windup_49701": dict(sweater=[(500, 650), (560, 400), (390, 600), (470, 720), (450, 970), (600, 935)],
                            accent=[(470, 1130), (700, 1090), (590, 620)]),
    "v3_smash_49701": dict(sweater=[(300, 640), (520, 700), (470, 600), (430, 515), (190, 705), (390, 930)],
                           accent=[(60, 640), (490, 1060), (600, 680)]),
    "v3_smash_49702": dict(sweater=[(300, 720), (450, 760), (560, 850), (380, 640), (430, 860), (230, 920),
                                    (320, 990), (300, 965)],
                           accent=[(90, 920), (400, 1160)]),
    "v3_upper_49701": dict(sweater=[(470, 650), (560, 420), (500, 550), (360, 600), (600, 910), (450, 980)],
                           accent=[(750, 960), (460, 1150), (570, 620)]),
    "v3_upper_49702": dict(sweater=[(450, 700), (560, 580), (380, 780), (360, 640), (370, 920), (410, 1010)],
                           accent=[(230, 960), (380, 1160), (560, 720)]),
    "v3_airslam_49701": dict(sweater=[(520, 650), (450, 350), (560, 420), (380, 680), (450, 930), (500, 1000)],
                             accent=[(300, 930), (400, 1110), (620, 640)]),
    "v3_airslam_49702": dict(sweater=[(520, 750), (600, 600), (420, 700), (390, 960), (420, 1040), (300, 1090)],
                             accent=[(250, 930), (310, 1080), (640, 780)]),
}


def _regions(a):
    col = _colored(a)
    core = ndimage.binary_erosion(col, iterations=2)
    lab, n = ndimage.label(core)
    _, (iy, ix) = ndimage.distance_transform_edt(lab == 0, return_indices=True)
    lab = np.where(col, lab[iy, ix], 0)
    lab0, n0 = ndimage.label(col)
    gone = ndimage.sum(core, lab0, range(n0 + 1)) == 0
    lab = np.where(gone[lab0] & col, n + lab0, lab)
    return col, lab, n + n0


@lru_cache(None)
def recolor_pose(name):
    """RGB pose drawing (on white) in the sheet's colours (see POSE_SEEDS)."""
    a = np.asarray(Image.open(SRC / f"{name}.png").convert("RGB")).astype(np.float32)
    col, lab, n = _regions(a)
    s = POSE_SEEDS[name]
    pick = lambda pts: np.isin(lab, list({lab[y, x] for x, y in pts} - {0}))
    sweater, accent = pick(s["sweater"]), pick(s["accent"])
    lum, sat = a.mean(-1), a.max(-1) - a.min(-1)
    idx = np.arange(n + 1)
    size = ndimage.sum(np.ones_like(lab), lab, idx)
    thick = ndimage.sum(ndimage.binary_erosion(col, iterations=4), lab, idx)   # thin stripes vanish in the erosion
    med_l = ndimage.median(lum, lab, idx)
    med_r = ndimage.median(a[..., 0], lab, idx)             # the pale stick / ground shadow have red > 100
    med_s = ndimage.median(sat, lab, idx)                   # grey shorts / boots are not hair
    taken = np.zeros(n + 1, bool)
    taken[np.unique(lab[sweater | accent])] = True
    big = (size > 800) & (thick > 0.25 * size) & ~taken & (med_r < 90) & (med_s > 50)
    big[0] = False
    hair_d = big & (med_l < 110)
    hair_b = big & (med_l >= 110)                       # cyan underlayer
    hair, streak = hair_d[lab], hair_b[lab]
    stripes = col & ~hair & ~streak & ~sweater & ~accent & (sat > 120) & ~taken[lab] & (a[..., 0] < 90)
    _snap(a, hair, TONES["hair"])
    _snap(a, streak, TONES["hair"][:2], shift=0)
    _snap(a, sweater, TONES["sweater"])
    _snap(a, accent | stripes, TONES["accent"])
    return Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGB")
