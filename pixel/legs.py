"""Two-bone pixel legs for XIYIN's run cycle (replaces the rigid hip swing, whose straight legs looked broken).

Each leg is a thigh and a shin solved with IK (the knee always bends forward), drawn as shaded, outlined pixel
limbs in the sheet's colours: skin thighs, navy kneehighs with a blue band, and the boot cut from the run-A
master. The boot is rigid with the shin (chunky boots barely flex), so at heel strike the toe points up and at
push-off the heel lifts. The two legs are half a cycle apart and pass each other; the far leg uses shadow tones.
All coordinates are master-sprite pixels (131x200, before padding).
"""
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).parent
OUT = (24, 28, 54)
SKIN, SKIN_SH, SKIN_FAR = (255, 236, 226), (240, 196, 186), (226, 178, 172)
SOCK, SOCK_HI = (40, 44, 68), (60, 66, 96)
SOCK_FAR, SOCK_FAR_HI = (32, 35, 56), (46, 50, 78)
BAND, BAND_HI = (73, 99, 173), (118, 146, 214)
BAND_FAR = (56, 78, 148)

L1, L2 = 29.0, 16.0                       # thigh (hip-knee), shin (knee-boot top)
R_THIGH = (7.0, 5.8)                      # radius at hip, at knee
R_SHIN = (5.6, 5.4)
HIP_NEAR, HIP_FAR = (74.0, 119.0), (65.0, 118.0)
GROUND_TOP = 165.0                        # boot-top height when standing on the ground
BOOT_TOP = (88.0, 168.0)                  # boot pivot on the master (top centre of the shaft)
BOOT_AXIS = math.degrees(math.atan2(5, 17))   # master shin direction, degrees from straight down toward +x

# boot-top path relative to the hip over one stride (phase, dx, y); y is absolute so the stance foot stays on
# the ground while the hip bobs. Stance 0-0.38, swing after.
PATH = [(0.00, 17, GROUND_TOP), (0.12, 7, GROUND_TOP), (0.25, -5, GROUND_TOP), (0.38, -17, GROUND_TOP - 1),
        (0.50, -26, GROUND_TOP - 12), (0.62, -23, GROUND_TOP - 27), (0.75, -4, GROUND_TOP - 30),
        (0.87, 15, GROUND_TOP - 20), (1.00, 17, GROUND_TOP)]


def catmull(points, u):
    """Closed Catmull-Rom through PATH-style points (phase, x, y) at phase u."""
    pts = points[:-1]
    n = len(pts)
    u = u % 1.0
    for i in range(n):
        a = pts[i][0]
        b = points[i + 1][0]
        if a <= u <= b:
            f = (u - a) / (b - a)
            p0, p1, p2, p3 = (pts[(i - 1) % n], pts[i], pts[(i + 1) % n], pts[(i + 2) % n])
            out = []
            for k in (1, 2):
                v0, v1, v2, v3 = p0[k], p1[k], p2[k], p3[k]
                out.append(0.5 * ((2 * v1) + (-v0 + v2) * f + (2 * v0 - 5 * v1 + 4 * v2 - v3) * f * f
                                  + (-v0 + 3 * v1 - 3 * v2 + v3) * f ** 3))
            return out
    return pts[0][1:]


def hip_bob(u):
    """Hip lowest at mid-stance of each leg, highest in the flight phases."""
    return 1.6 * math.cos(4 * math.pi * (u - 0.25))


def ik(hip, ankle, l1=L1, l2=L2):
    """Knee for a two-bone leg, knee bending toward +x (forward)."""
    hx, hy = hip
    ax, ay = ankle
    dx, dy = ax - hx, ay - hy
    d = max(1e-6, math.hypot(dx, dy))
    if d >= l1 + l2 - 1e-3:                          # out of reach: straighten toward the target
        k = l1 / d
        return hx + dx * k, hy + dy * k, (hx + dx * (l1 + l2) / d, hy + dy * (l1 + l2) / d)
    a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    h = math.sqrt(max(0.0, l1 * l1 - a * a))
    mx, my = hx + dx * a / d, hy + dy * a / d
    nx, ny = -dy / d, dx / d                         # unit normal; pick the one pointing forward (+x)
    if nx < 0:
        nx, ny = -nx, -ny
    return mx + nx * h, my + ny * h, (ax, ay)


def capsule(shape, p0, p1, r0, r1):
    """Mask of a tapered capsule and, per pixel, (t along the bone, signed side distance)."""
    H, W = shape
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    vx, vy = p1[0] - p0[0], p1[1] - p0[1]
    L2_ = max(1e-6, vx * vx + vy * vy)
    t = np.clip(((xx - p0[0]) * vx + (yy - p0[1]) * vy) / L2_, 0, 1)
    px, py = p0[0] + t * vx, p0[1] + t * vy
    r = r0 + (r1 - r0) * t
    L = math.sqrt(L2_)
    side = ((xx - px) * (-vy) + (yy - py) * vx) / L     # >0 on the side to the left of p0->p1
    return (xx - px) ** 2 + (yy - py) ** 2 <= r * r, t, side


@lru_cache(None)
def boot_piece():
    """The run-A front boot (rows from the shaft top down), with the sheet's blue trim; sock pixels removed."""
    m = np.asarray(Image.open(HERE / "sprites3" / "p02_run_a.png").convert("RGBA")).copy()
    a = np.zeros_like(m)
    region = (slice(166, 200), slice(76, 131))
    a[region] = m[region]
    sock = np.isin(a[..., :3].reshape(-1, 3).view([("", a.dtype)] * 3).ravel(),
                   np.array([BAND, BAND_HI, (56, 78, 148), (248, 250, 255)], np.uint8).view([("", np.uint8)] * 3).ravel())
    a.reshape(-1, 4)[sock] = 0
    op = a[..., 3] > 0
    rows = np.nonzero(op.any(1))[0]
    top = rows.min()
    for y in (top + 1, top + 2):                        # blue rim at the top of the shaft (sheet)
        xs = np.nonzero(op[y])[0]
        if len(xs) > 2:
            a[y, xs[1]:xs[-1]] = (*BAND, 255)
    for x in range(op.shape[1]):                        # blue line just above the sole
        ys = np.nonzero(op[:, x])[0]
        if len(ys) > 4:
            a[ys[-1] - 2, x] = (*BAND, 255)
    return Image.fromarray(a, "RGBA")


def rot_about(im, pivot, deg, k=4):
    """RotSprite-style rotation (x4 nearest, rotate, majority back down) about pivot."""
    big = im.resize((im.width * k, im.height * k), Image.Resampling.NEAREST)
    big = big.rotate(deg, resample=Image.Resampling.NEAREST, center=(pivot[0] * k, pivot[1] * k))
    a = np.asarray(big).reshape(im.height, k, im.width, k, 4).transpose(0, 2, 1, 3, 4).reshape(im.height, im.width, k * k, 4)
    opaque = a[..., 3] > 0
    keep = opaque.sum(2) >= (k * k) // 2
    out = np.zeros((im.height, im.width, 4), np.uint8)
    for y, x in zip(*np.nonzero(keep)):
        px = a[y, x][opaque[y, x]]
        cols, cnt = np.unique(px.view(np.uint32).ravel(), return_counts=True)
        out[y, x] = np.frombuffer(np.uint32(cols[cnt.argmax()]).tobytes(), np.uint8)
    return Image.fromarray(out, "RGBA")


@lru_cache(None)
def boot_rotated(deg):
    """Boot piece rotated by a whole number of degrees about its shaft top."""
    return rot_about(boot_piece(), BOOT_TOP, deg)


def draw_leg(canvas, hip, ankle, far, pad):
    """Draw one leg (thigh, sock, boot, outline) into the RGBA array canvas; pad offsets master coordinates."""
    kx, ky, ankle = ik(hip, ankle)
    hip_p = (hip[0] + pad, hip[1] + pad)
    knee_p = (kx + pad, ky + pad)
    ank_p = (ankle[0] + pad, ankle[1] + pad)
    shape = canvas.shape[:2]
    m1, t1, s1 = capsule(shape, hip_p, knee_p, *R_THIGH)
    m2, t2, s2 = capsule(shape, knee_p, ank_p, *R_SHIN)
    layer = np.zeros_like(canvas)
    skin, skin_back = (SKIN_FAR, SKIN_FAR) if far else (SKIN, SKIN_SH)
    sock, sock_hi = (SOCK_FAR, SOCK_FAR_HI) if far else (SOCK, SOCK_HI)
    band = BAND_FAR if far else BAND
    layer[m1] = (*skin, 255)
    layer[m1 & (s1 > R_THIGH[1] * 0.35)] = (*skin_back, 255)      # hamstring side in shadow
    sock_m = m2 & ~m1 | (m2 & (t2 > 0.2))
    layer[sock_m] = (*sock, 255)
    layer[sock_m & (s2 < -R_SHIN[1] * 0.45)] = (*sock_hi, 255)   # shin front highlight
    L = math.dist(knee_p, ank_p)
    dist_from_knee = t2 * L
    layer[sock_m & (dist_from_knee >= 3) & (dist_from_knee < 5)] = (*band, 255)
    if not far:
        layer[sock_m & (dist_from_knee >= 6) & (dist_from_knee < 7)] = (*BAND_HI, 255)
    # boot, rigid with the shin
    theta = math.degrees(math.atan2(ank_p[0] - knee_p[0], ank_p[1] - knee_p[1]))
    boot = boot_rotated(int(round(theta - BOOT_AXIS)))
    b = np.asarray(boot)
    ox, oy = int(round(ank_p[0] - BOOT_TOP[0])), int(round(ank_p[1] - BOOT_TOP[1]))
    h, w = b.shape[:2]
    ys0, xs0 = max(0, -oy), max(0, -ox)
    ys1, xs1 = min(h, shape[0] - oy), min(w, shape[1] - ox)
    sub = b[ys0:ys1, xs0:xs1]
    bm = sub[..., 3] > 0
    tgt = layer[oy + ys0:oy + ys1, ox + xs0:ox + xs1]
    if far:
        dark = sub.copy()
        dark[..., :3] = (sub[..., :3] * 0.8).astype(np.uint8)
        tgt[bm] = dark[bm]
    else:
        tgt[bm] = sub[bm]
    # outline around thigh + sock (the boot carries its own)
    limb = m1 | m2
    ring = limb.copy()
    ring[1:] |= limb[:-1]; ring[:-1] |= limb[1:]; ring[:, 1:] |= limb[:, :-1]; ring[:, :-1] |= limb[:, 1:]
    ring &= ~limb & (layer[..., 3] == 0)
    layer[ring] = (*OUT, 255)
    op = layer[..., 3] > 0
    canvas[op] = layer[op]


def legs_frame(u, shape, pad, stride=1.0):
    """Both legs at stride phase u: returns (canvas RGBA, hip bob in px). stride scales the step length so the
    planted foot keeps pace with the ground at different running speeds."""
    canvas = np.zeros((*shape, 4), np.uint8)
    bob = hip_bob(u)
    for far, uu, hip in ((True, (u + 0.5) % 1.0, HIP_FAR), (False, u % 1.0, HIP_NEAR)):
        hx, hy = hip[0], hip[1] + bob
        dx, ay = catmull(PATH, uu)
        draw_leg(canvas, (hx, hy), (hx + dx * stride, ay), far, pad)
    return canvas, bob


def tucked_legs(shape, pad):
    """Jump: both knees up (near leg forward, far leg tucked back)."""
    canvas = np.zeros((*shape, 4), np.uint8)
    for far, hip, ank in ((True, HIP_FAR, (-14, 150)), (False, HIP_NEAR, (6, 146))):
        draw_leg(canvas, hip, (hip[0] + ank[0], ank[1]), far, pad)
    return canvas
