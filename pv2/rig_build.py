"""Build the puppet rig from the owner's reference sheet, the only source of the character's pixels.

usage: rig_build.py <master_x4.png> <lama.onnx> <out_dir>

master_x4.png is the reference sheet upscaled 4x with Real-ESRGAN x4plus-anime (no redesign).
Writes three RGBA layers in sheet space (tail, body, upper) plus debug overlays:
  upper = head, face, ears, ahoge and the side hair strands (moves with the head, hair sways)
  body  = everything else, with the areas hidden under the hair and chin repainted by LaMa
  tail  = the tail (swings around its root)
All coordinates in RIG are in 1x sheet pixels (1024x1536); K scales them to the master.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image
from rembg import new_session, remove
from scipy import ndimage as ndi

K = 4
RIG = {
    # everything above this line is head (hair beside the face is picked up by colour below it)
    "head_cut": [(200, 0), (840, 0), (840, 300), (562, 309), (543, 325), (512, 337), (482, 326),
                 (464, 316), (443, 303), (200, 303)],
    # side hair strands: hair-coloured pixels inside these zones belong to the upper layer
    "hair_zone_l": [(250, 290), (452, 290), (486, 330), (486, 405), (452, 410), (448, 470), (425, 560),
                    (398, 645), (250, 645)],
    "hair_zone_r": [(556, 290), (780, 290), (780, 645), (668, 645), (642, 560), (602, 470), (590, 412),
                    (538, 405), (538, 330)],
    # torso and sleeves: holes under the hair inside this polygon are repainted, outside stay transparent
    "body_poly": [(407, 383), (374, 402), (350, 533), (331, 587), (299, 657), (272, 750), (275, 800),
                  (760, 800), (752, 750), (720, 657), (682, 571), (640, 450), (624, 394), (599, 381)],
    "neck_poly": [(452, 296), (556, 296), (556, 350), (452, 350)],
    # light skin, eye whites and ear fluff that must stay opaque even where paper-white
    "face_protect": [(428, 196), (602, 186), (604, 300), (560, 307), (512, 335), (466, 313), (428, 292)],
    "tail_box": (322, 872, 422, 1002),
    "leg_gap": [(400, 860), (630, 860), (640, 1520), (390, 1520)],
    # pivots and part anchors used by the renderer
    "neck_pivot": (512, 360), "tail_root": (405, 884), "waist": (512, 690), "feet": (512, 1500),
    "ear_l": {"poly": [(346, 113), (427, 98), (412, 150), (398, 182), (370, 180), (358, 150)], "pivot": (398, 165)},
    "ear_r": {"poly": [(573, 93), (634, 86), (630, 130), (617, 167), (590, 152), (570, 120)], "pivot": (597, 145)},
    "ahoge": {"box": (438, 14, 528, 100), "pivot": (482, 96)},
    "eye_l": {"box": (426, 254, 487, 286), "poly": [(427, 267), (431, 261), (440, 259), (452, 258), (466, 258),
              (476, 260), (483, 263), (484, 267), (480, 273), (472, 279), (462, 282.5), (450, 281), (441, 276), (434, 270)]},
    "eye_r": {"box": (522, 233, 586, 270), "poly": [(525, 257), (530, 247), (537, 242), (548, 238), (560, 236.5),
              (572, 237), (583, 239), (580, 244), (576, 252), (571, 261), (562, 266.5), (550, 267.5), (540, 265), (532, 262)]},
    "mouth": {"center": (513, 306), "width": 26},
    "face_center": (505, 280), "head_radius": 150,
}


def poly_mask(shape, pts):
    m = np.zeros(shape, np.uint8)
    cv2.fillPoly(m, [np.round(np.array(pts, np.float32) * K).astype(np.int32)], 1)
    return m.astype(bool)


def lama_fill(rgb, hole, sess, pad=48):
    """Repaint hole pixels with LaMa, working on crops at 1/2 scale and upsampling only into the hole."""
    out = rgb.copy()
    lab, n = ndi.label(ndi.binary_dilation(hole, iterations=8))
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        y0, y1 = max(sl[0].start - pad, 0), min(sl[0].stop + pad, rgb.shape[0])
        x0, x1 = max(sl[1].start - pad, 0), min(sl[1].stop + pad, rgb.shape[1])
        img, h = rgb[y0:y1, x0:x1], hole[y0:y1, x0:x1]
        s = 0.5
        w8, h8 = max(64, int(img.shape[1] * s) // 64 * 64), max(64, int(img.shape[0] * s) // 64 * 64)
        im_s = cv2.resize(img, (w8, h8), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        m_s = (cv2.resize(h.astype(np.uint8), (w8, h8), interpolation=cv2.INTER_NEAREST) > 0)
        m_s = ndi.binary_dilation(m_s, iterations=3).astype(np.float32)
        res = sess.run(None, {"image": im_s.transpose(2, 0, 1)[None], "mask": m_s[None, None]})[0][0]
        res = res.transpose(1, 2, 0)
        res = np.clip(res if res.max() > 2 else res * 255, 0, 255).astype(np.uint8)
        res = cv2.resize(res, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_CUBIC)
        soft = cv2.GaussianBlur(ndi.binary_dilation(h, iterations=3).astype(np.float32), (0, 0), 2)[..., None]
        out[y0:y1, x0:x1] = (img * (1 - soft) + res * soft).astype(np.uint8)
    return out


def main():
    src, lama_path, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    rgb = np.asarray(Image.open(src).convert("RGB"))
    H, W = rgb.shape[:2]

    # 1. alpha: coarse matte from isnet-anime, edges re-estimated from the distance to the white paper
    small = Image.fromarray(rgb).resize((W // K, H // K), Image.LANCZOS)
    coarse = np.asarray(remove(small, session=new_session("isnet-anime")).getchannel("A"))
    coarse = cv2.resize(coarse, (W, H), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255
    solid = coarse > 0.5
    dark = (255 - rgb.min(axis=2)).astype(np.float32)
    a_paper = np.clip((dark - 6) / 140, 0, 1)
    near = ndi.binary_dilation(solid, iterations=10)
    inner = ndi.binary_erosion(solid, iterations=10)
    alpha = np.where(inner, 1.0, np.where(near, a_paper, 0.0))
    alpha = np.maximum(alpha, ndi.binary_fill_holes(alpha > 0.5).astype(np.float32) * (alpha > 0.02))
    alpha = np.maximum(alpha, ndi.binary_erosion(ndi.binary_fill_holes(alpha > 0.5), iterations=2))
    # inside the hair (not the face or ears) paper-white gaps between strands are see-through
    hair_area = (poly_mask((H, W), RIG["head_cut"]) | poly_mask((H, W), RIG["hair_zone_l"])
                 | poly_mask((H, W), RIG["hair_zone_r"])) & ~poly_mask((H, W), RIG["face_protect"])
    for ear in ("ear_l", "ear_r"):
        hair_area &= ~poly_mask((H, W), RIG[ear]["poly"])
    hair_area &= ~poly_mask((H, W), RIG["body_poly"])
    alpha = np.where(hair_area, a_paper, alpha)
    # paper enclosed between the legs (and any other large pure-white island) is background, not skin
    paper = dark < 7
    lab_p, n_p = ndi.label(paper & (alpha > 0.5))
    if n_p:
        sizes = ndi.sum(np.ones_like(lab_p), lab_p, range(1, n_p + 1))
        big = np.isin(lab_p, 1 + np.nonzero(sizes > 600)[0]) & poly_mask((H, W), RIG["leg_gap"])
        alpha = np.where(ndi.binary_dilation(big, iterations=2), a_paper, alpha)
    # un-mix the white paper from edge pixels so no pale fringe shows on dark scenes
    a3 = np.clip(alpha, 1e-3, 1)[..., None]
    fg = np.clip((rgb.astype(np.float32) - (1 - a3) * 255) / a3, 0, 255)
    fg = np.where(alpha[..., None] > 0.02, fg, 0).astype(np.uint8)

    # 2. colour classes
    lab = cv2.cvtColor(rgb.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)
    R, G, B = [rgb[..., i].astype(int) for i in range(3)]
    hairish = (B > R + 40) & (B > 105) & (lab[..., 0] < 64)
    hairish = ndi.binary_closing(hairish, iterations=2)
    ys = np.arange(H)[:, None]

    # 3. upper layer = head region + hair-coloured pixels in the side zones (+ their antialiased rims)
    head = poly_mask((H, W), RIG["head_cut"]) & (alpha > 0.02)
    zones = poly_mask((H, W), RIG["hair_zone_l"]) | poly_mask((H, W), RIG["hair_zone_r"])
    side = zones & hairish & (alpha > 0.02)
    side = ndi.binary_opening(side, iterations=2)
    rim = ndi.binary_dilation(side, iterations=3) & zones & (alpha < 0.98) & (alpha > 0.02)
    lines = ndi.binary_dilation(side, iterations=6) & zones & (lab[..., 0] < 38) & (alpha > 0.5)  # strand outlines
    upper = head | side | rim | lines
    upper = ndi.binary_closing(upper, iterations=2) & (alpha > 0.02)

    # 4. tail
    x0, y0, x1, y1 = [v * K for v in RIG["tail_box"]]
    tail = np.zeros((H, W), bool)
    tail[y0:y1, x0:x1] = True
    tail &= hairish | ((alpha > 0.02) & (alpha < 0.98) & ndi.binary_dilation(hairish, iterations=4))
    lab_t, n = ndi.label(tail)
    if n:
        sizes = ndi.sum(tail, lab_t, range(1, n + 1))
        tail = lab_t == (1 + int(np.argmax(sizes)))
    tail = ndi.binary_closing(tail, iterations=3)
    tail_full = ndi.binary_dilation(tail, iterations=2) & (alpha > 0.02) & ~ndi.binary_dilation(
        (alpha > 0.5) & ~tail & (lab[..., 0] > 80), iterations=1)  # keep the thigh out

    # 5. body = rest; repaint what the hair and chin covered inside the torso/neck, clear the rest
    body_alpha = alpha.copy()
    covered = upper | tail_full
    support = poly_mask((H, W), RIG["body_poly"]) | poly_mask((H, W), RIG["neck_poly"])
    hole = covered & support
    body_alpha[covered & ~support] = 0
    body_alpha[zones & ~support] = 0  # loose outline bits and paper between strands
    body_alpha[hole] = 1
    # the tail's old outline must not stay painted on the body (the thigh edge at x >= 407 is kept)
    ghost = ndi.binary_dilation(tail_full, iterations=10) & ~tail_full & (lab[..., 0] < 75)
    ghost[:, int(407 * K):] = False
    body_alpha[ghost] = 0
    sess = ort.InferenceSession(lama_path, providers=["CPUExecutionProvider"])
    body_rgb = lama_fill(fg, hole, sess)
    # where LaMa continued the white paper (outside the real sleeve edge) the repaint is see-through
    paper_fill = np.clip((255 - body_rgb.min(axis=2).astype(np.float32) - 24) / 110, 0, 1)
    body_alpha[hole] = paper_fill[hole]

    def save(name, rgb_, a_):
        im = np.dstack([rgb_, (np.clip(a_, 0, 1) * 255).astype(np.uint8)])
        Image.fromarray(im).save(out / f"{name}.png", optimize=False, compress_level=3)

    save("upper", fg, alpha * upper)
    # eyelid plate: the face with both eye openings repainted as skin, for blinks and symbol eyes
    eyes = np.zeros((H, W, 3), np.uint8)
    for ch, key in ((0, "eye_l"), (1, "eye_r")):
        m = ndi.binary_dilation(poly_mask((H, W), RIG[key]["poly"]), iterations=3)
        eyes[..., ch] = (cv2.GaussianBlur(m.astype(np.float32), (0, 0), 2) * 255).astype(np.uint8)
    # closed lids are plain skin: the local skin tone around each eye, not a learned fill (which picks up the crease lines)
    lid_rgb = fg.copy()
    skinish = (lab[..., 0] > 86) & (rgb[..., 0] >= rgb[..., 2]) & (alpha > 0.98)
    for ch in (0, 1):
        m = eyes[..., ch].astype(np.float32) / 255
        ring = ndi.binary_dilation(m > 0.1, iterations=40) & ~ndi.binary_dilation(m > 0.1, iterations=8) & skinish
        tone = np.median(fg[ring], axis=0)
        lid_rgb = (lid_rgb * (1 - m[..., None]) + tone * m[..., None]).astype(np.uint8)
    save("upper_lid", lid_rgb, alpha * upper)
    Image.fromarray(eyes).save(out / "eyes.png")
    save("body", body_rgb, body_alpha)
    save("tail", fg, alpha * tail_full)
    json.dump({"K": K, "size": [W, H], **RIG}, open(out / "rig.json", "w"), indent=1)

    # debug overlay at 1/4 scale: red = upper, green = tail, blue = repainted
    dbg = rgb.astype(np.float32).copy()
    for m, c in ((upper, (255, 40, 40)), (tail_full, (40, 220, 40)), (hole, (40, 80, 255))):
        dbg[m] = dbg[m] * 0.45 + np.array(c) * 0.55
    Image.fromarray(dbg.astype(np.uint8)).resize((W // 4, H // 4), Image.LANCZOS).save(out / "debug_parts.jpg", quality=88)
    print("upper px", int(upper.sum()), "tail px", int(tail_full.sum()), "repainted px", int(hole.sum()))


if __name__ == "__main__":
    main()
