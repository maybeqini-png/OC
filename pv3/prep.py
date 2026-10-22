"""Turn generated drawings into on-model stickers: cut out, colour-lock to the reference sheet, white sticker border.

usage: prep.py [ids...]      (default: every art/generated/pv3/<id>.png without a sticker yet)
writes pv3/stickers/<id>.png (RGBA, 1216 px tall canvas) and pv3/stickers/qa.json (per-region colour error).

Colour lock (digital 色指定): pixels inside the character are classed as hair/trim blue, dark clothing or skin;
each class's CIELAB mean is moved onto the reference sheet's class mean (spread kept), so every drawing has the
sheet's hair, sweater and skin tones. Errors before/after are logged as deltaE.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import new_session, remove

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "art/generated/pv3"
OUT = ROOT / "pv3/stickers"
SHEET = ROOT / "art/reference/oc_reference_sheet.webp"
SESSION = new_session("isnet-anime")


def lab(rgb):
    return cv2.cvtColor(rgb.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)


def classes(L, a, b):
    C = np.hypot(a, b)
    skin = (L > 70) & (a > 1) & (b > 1) & (C < 35)
    dark = ~skin & ((L < 30) | ((C < 18) & (L < 52)))
    blue = ~skin & ~dark & (b < -10) & (C > 18)
    return {"blue": blue, "dark": dark, "skin": skin}


def stats(img_lab, mask):
    out = {}
    for k, m in classes(*[img_lab[..., i] for i in range(3)]).items():
        m = m & mask
        if m.sum() > 400:
            out[k] = (img_lab[m].mean(0), img_lab[m].std(0) + 1e-3)
    return out


def ref_stats():
    im = np.asarray(Image.open(SHEET).convert("RGB"))
    a = np.asarray(remove(Image.fromarray(im), session=SESSION).getchannel("A")) > 128
    return stats(lab(im), a)


def lock(rgb, mask, ref, k=0.85):
    L = lab(rgb)
    cls = classes(*[L[..., i] for i in range(3)])
    out = L.copy()
    report = {}
    for name, m in cls.items():
        m = m & mask
        if name not in ref or m.sum() < 400:
            continue
        mu, sd = L[m].mean(0), L[m].std(0) + 1e-3
        rmu, rsd = ref[name]
        ratio = np.clip(rsd / sd, 0.85, 1.18)
        tgt = (L[m] - mu) * ratio + rmu
        out[m] = L[m] * (1 - k) + tgt * k
        report[name] = round(float(np.linalg.norm(mu - rmu)), 1)
    soft = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 1.0)[..., None]
    res = cv2.cvtColor(out, cv2.COLOR_LAB2RGB) * 255
    res = rgb * (1 - soft) + res * soft
    return np.clip(res, 0, 255).astype(np.uint8), report


def sticker(rgb, alpha, border=14, shadow=(27, 35, 64)):
    """White die-cut border around the character (sticker look as a designed style, not a raw cutout)."""
    H, W = alpha.shape
    pad = border * 3
    a = np.pad(alpha, pad)
    rgbp = np.pad(rgb, ((pad, pad), (pad, pad), (0, 0)))
    solid = (a > 0.5).astype(np.uint8)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * border + 1, 2 * border + 1))
    outer = cv2.dilate(solid, k)
    outer = cv2.morphologyEx(outer, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)))
    outer = cv2.GaussianBlur(outer.astype(np.float32), (0, 0), 1.2)
    white = np.full_like(rgbp, 255, dtype=np.float32)
    col = white * (1 - a[..., None]) + rgbp * a[..., None]
    alpha_out = np.maximum(outer, a)
    rgba = np.dstack([col, alpha_out * 255]).astype(np.uint8)
    return rgba


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ids = sys.argv[1:] or [p.stem for p in sorted(SRC.glob("*.png")) if not p.stem.endswith("_raw")
                           and not (OUT / f"{p.stem}.png").exists()]
    qa_path = OUT / "qa.json"
    qa = json.load(open(qa_path)) if qa_path.exists() else {}
    ref = ref_stats()
    for aid in ids:
        im = np.asarray(Image.open(SRC / f"{aid}.png").convert("RGB"))
        alpha = np.asarray(remove(Image.fromarray(im), session=SESSION).getchannel("A")).astype(np.float32) / 255
        alpha = np.clip((alpha - 0.05) / 0.9, 0, 1)
        locked, report = lock(im, alpha > 0.5, ref)
        Image.fromarray(sticker(locked, alpha)).save(OUT / f"{aid}.png")
        after = {k: round(float(np.linalg.norm(v[0] - ref[k][0])), 1) for k, v in stats(lab(locked), alpha > 0.5).items() if k in ref}
        qa[aid] = {"dE_before": report, "dE_after": after}
        print(aid, qa[aid], flush=True)
    json.dump(qa, open(qa_path, "w"), indent=1)


if __name__ == "__main__":
    main()
