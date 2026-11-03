"""XIYIN as a cut-out puppet made directly from the owner's reference sheet (art/reference/oc_reference_sheet.webp).

Owner (2026-11-03): "It must strictly follow the original design. Use the cute cat-girl OC reference image as the base
for her outfit, hair and all other features." Image models redraw the character every frame and drift, so poses are
made the way cut-out / skeletal-animation games do it: the sheet itself is cut into parts once and the parts are
rotated about joints. Nothing is redrawn; every pixel of her comes from the sheet.

Parts (sheet pixels): head + hair (incl. the long hair over the sleeves), torso (sweater + shorts), each sleeve with
its hand, each thigh, each shin with sock and boot, tail. Joints: neck, shoulders, hips, knees, tail root. The weapon
(the paw mic) is held in her right hand (screen right = forward) at a fixed angle to the forearm; her fingers are
drawn over the handle.

usage: python3 ocrig.py sheet out.png
"""
import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

import mdsprites as MD

ROOT = Path(__file__).parent.parent
SHEET = ROOT / "art/reference/oc_reference_sheet.webp"

# joints (sheet px)
NECK = (510, 372)
SH_B, SH_F = (402, 425), (612, 425)        # back (screen-left) and front (screen-right) shoulders
HIP_B, HIP_F = (462, 885), (558, 885)
KNEE_B, KNEE_F = (463, 1047), (560, 1047)
TAIL = (408, 895)
HAND_F = (697, 858)                          # front hand centre (holds the weapon)

ARM_B = [(405, 400), (330, 450), (285, 560), (258, 745), (282, 845), (300, 880), (360, 880), (405, 842)]
ARM_F = [(608, 400), (690, 450), (735, 560), (762, 745), (735, 845), (725, 880), (665, 880), (610, 842)]


@lru_cache(1)
def base():
    """Sheet cut out of its white background (RGBA, sheet coordinates); white background trapped between her legs,
    hair and sleeves (pure white, unsaturated, larger than an eye highlight) is removed too."""
    src = Image.open(SHEET).convert("RGB")
    a = np.asarray(src).astype(int)
    white = (a.mean(-1) > 246) & (a.max(-1) - a.min(-1) < 12)
    lab, n = ndimage.label(white)
    sizes = ndimage.sum(white, lab, range(1, n + 1))
    holes = []
    for i, z in enumerate(sizes, 1):
        if z > 350:
            ys, xs = np.nonzero(lab == i)
            holes.append((int(xs[0]), int(ys[0])))
    return MD.cutout(src, crop=False, holes=tuple(holes))


def _poly(poly, size):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).polygon(poly, fill=255)
    return np.asarray(m) > 0


def _hair(a):
    r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
    return (b > r + 45) & (b > 110) & (a[..., 3] > 0)


@lru_cache(1)
def parts():
    im = base()
    a = np.asarray(im)
    H, W = a.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    al = a[..., 3] > 0
    hair = _hair(a)
    # hair = hair-coloured pixels in the head box and in the side strips where the long hair hangs over the sleeves
    # (the torso middle is excluded so the cobalt collar stripe / side panel stay on the torso)
    sides = (yy < 640) & ((xx < 404) | (xx > 622))
    hair_main = hair & ((yy < 372) | sides)
    hair_main = ndimage.binary_dilation(hair_main, iterations=2) & al & ((yy < 372) | sides)
    head = ((yy < 372) & al) | hair_main
    tail = hair & (yy > 870) & (xx < 430)
    tail = ndimage.binary_dilation(tail, iterations=3) & al & (yy > 870) & (xx < 430)
    arm_b = _poly(ARM_B, (W, H)) & al & ~head
    arm_f = _poly(ARM_F, (W, H)) & al & ~head
    hand_f = arm_f & (yy > 840)
    legs = al & (yy >= 885) & ~tail
    thigh_b = legs & (xx < 507) & (yy < 1062)          # thighs overlap the shins by 30 px so knees never gap
    thigh_f = legs & (xx >= 507) & (yy < 1062)
    shin_b = legs & (xx < 507) & (yy >= 1032)
    shin_f = legs & (xx >= 507) & (yy >= 1032)
    torso = al & ~head & ~arm_b & ~arm_f & ~tail & ~legs

    def layer(m):
        out = a.copy()
        out[~m, 3] = 0
        return Image.fromarray(out, "RGBA")
    return {k: layer(m) for k, m in dict(head=head, torso=torso, arm_b=arm_b, arm_f=arm_f, hand_f=hand_f,
                                         thigh_b=thigh_b, thigh_f=thigh_f, shin_b=shin_b, shin_f=shin_f,
                                         tail=tail).items()}


def _rot_pt(p, piv, deg):
    """Rotate point p about piv by deg (counter-clockwise on screen, PIL's convention)."""
    t = math.radians(deg)
    dx, dy = p[0] - piv[0], p[1] - piv[1]
    return (piv[0] + dx * math.cos(t) + dy * math.sin(t), piv[1] - dx * math.sin(t) + dy * math.cos(t))


def _place(canvas, img, piv, deg, at):
    """Rotate img about its pivot piv (img coords) by deg and paste so the pivot lands on `at` (canvas coords)."""
    big = img.rotate(deg, Image.Resampling.BICUBIC, center=piv)
    canvas.alpha_composite(big, (int(round(at[0] - piv[0])), int(round(at[1] - piv[1]))))


@lru_cache(None)
def weapon_img(length):
    """The paw mic at a given length (pixels), vertical, head up; returns (img, grip_xy)."""
    import mdweapon as WP
    w, bottom, top = WP.weapon_sprite()
    k = length / (bottom[1] - top[1])
    img = w.resize((max(1, round(w.width * k)), max(1, round(w.height * k))), Image.Resampling.LANCZOS)
    return img, (bottom[0] * k, img.height * 0.80)        # grip a little above the handle end


POSES = {   # degrees CCW on screen. torso lean: negative = toward screen-right. arms: 0 = hanging down, 90 = forward
    # (screen-right), 180 = straight up. wpn: extra mic angle against the forearm (0 = mic held crosswise, head ahead).
    "idle": dict(torso=0, head=0, arm_b=-6, arm_f=10, thigh_b=0, thigh_f=0, shin_b=0, shin_f=0, tail=10, wpn=60),
    "run1": dict(torso=-6, head=3, arm_b=-20, arm_f=35, thigh_b=-10, thigh_f=14, shin_b=-28, shin_f=-6, tail=25,
                 wpn=50),
    "run2": dict(torso=-6, head=3, arm_b=18, arm_f=-10, thigh_b=14, thigh_f=-10, shin_b=-6, shin_f=-28, tail=15,
                 wpn=60),
    "windup": dict(torso=8, head=5, arm_b=-25, arm_f=150, thigh_b=-8, thigh_f=12, shin_b=-12, shin_f=0, tail=30,
                   wpn=30),
    "smash": dict(torso=-18, head=8, arm_b=-45, arm_f=55, thigh_b=-16, thigh_f=12, shin_b=-20, shin_f=-8, tail=40,
                  wpn=-20),
    "upper": dict(torso=6, head=6, arm_b=-15, arm_f=165, thigh_b=6, thigh_f=18, shin_b=-20, shin_f=-40, tail=20,
                  wpn=-30),
    "airslam": dict(torso=-4, head=5, arm_b=-70, arm_f=175, thigh_b=18, thigh_f=26, shin_b=-60, shin_f=-55, tail=35,
                    wpn=10),
    "swing": dict(torso=-10, head=3, arm_b=-50, arm_f=88, thigh_b=-14, thigh_f=10, shin_b=-12, shin_f=0, tail=40,
                  wpn=0),
}


def render(pose, weapon=True, wlen=900):
    """The puppet in a pose; returns RGBA on a padded canvas (sheet scale) and the feet y."""
    P = parts()
    p = POSES[pose] if isinstance(pose, str) else pose
    pad = 700
    W, H = base().size
    cv = Image.new("RGBA", (W + 2 * pad, H + 2 * pad), (0, 0, 0, 0))
    hip = ((HIP_B[0] + HIP_F[0]) / 2, HIP_B[1])
    root = (hip[0] + pad, hip[1] + pad)
    t = p["torso"]

    def child(pt):       # a joint on the torso, after the torso lean, in canvas coordinates
        q = _rot_pt(pt, hip, t)
        return (q[0] + pad, q[1] + pad)

    def leg(thigh, shin, hipj, knee, a1, a2):
        hj = (hipj[0] + pad, hipj[1] + pad)
        kn = _rot_pt(knee, hipj, a1)
        _place(cv, P[shin], knee, a1 + a2, (kn[0] + pad, kn[1] + pad))
        _place(cv, P[thigh], hipj, a1, hj)                       # thigh over the shin top (knee)
    # back to front: tail, back leg, back arm, torso, head, front leg, front arm, weapon, front hand
    _place(cv, P["tail"], TAIL, t + p["tail"], child(TAIL))
    leg("thigh_b", "shin_b", HIP_B, KNEE_B, p["thigh_b"], p["shin_b"])
    _place(cv, P["arm_b"], SH_B, t + p["arm_b"], child(SH_B))
    _place(cv, P["torso"], hip, t, root)
    _place(cv, P["head"], NECK, t + p["head"], child(NECK))
    leg("thigh_f", "shin_f", HIP_F, KNEE_F, p["thigh_f"], p["shin_f"])
    af = t + p["arm_f"]
    _place(cv, P["arm_f"], SH_F, af, child(SH_F))
    if weapon:
        img, grip = weapon_img(wlen)
        hand = _rot_pt(HAND_F, SH_F, af)
        hand = _rot_pt(hand, hip, 0)
        sh = child(SH_F)
        hx = sh[0] + (hand[0] - SH_F[0]) * 1.0
        hy = sh[1] + (hand[1] - SH_F[1]) * 1.0
        _place(cv, img, grip, af - 90 + p["wpn"], (hx, hy))   # arm down -> mic head forward
        _place(cv, P["hand_f"], SH_F, af, child(SH_F))
    al = np.asarray(cv.getchannel("A"))
    feet = int(np.nonzero(al.any(1))[0].max())
    return cv, feet


if __name__ == "__main__" and sys.argv[1] == "sheet":
    names = list(POSES)
    tiles = []
    for n in names:
        cv, feet = render(n)
        bb = cv.getbbox()
        tiles.append(cv.crop(bb))
    Hh = 520
    row = [t.resize((max(1, int(t.width * Hh / 1700)), max(1, int(t.height * Hh / 1700))), Image.Resampling.LANCZOS)
           for t in tiles]
    S = Image.new("RGBA", (sum(r.width + 20 for r in row), max(r.height for r in row) + 20), (70, 60, 120, 255))
    x = 0
    for r in row:
        S.alpha_composite(r, (x, S.height - 10 - r.height))
        x += r.width + 20
    S.convert("RGB").save(sys.argv[2])
